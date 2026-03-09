"""
Memory module for Bedrock AgentCore
Provides HookProvider implementation for Strands using AWS Bedrock AgentCore Memory
"""

from bedrock_agentcore.memory import MemoryClient
from strands.hooks import (
    AfterInvocationEvent,
    BeforeInvocationEvent,
    HookProvider,
    HookRegistry,
)
from typing import Any
import logging
import time
import json

logger = logging.getLogger("agent_activity")


class AgentCoreMemory:
    """
    Initializer for Bedrock AgentCore Memory.
    
    Creates or finds an existing AgentCore Memory resource and ensures it's active before use.
    This should be created by the CloudFormation stack, but there is a chance the creation is still in progress.
    Provides the memory client and ID for use by AgentCoreSessionManager.
    """
    
    def __init__(self, memory_name: str = "weather_memory"):
        self.memory_name = memory_name
        self.client = MemoryClient()
        self.memory_id = None
        self._ensure_memory_exists()
    
    def _ensure_memory_exists(self):
        """Create memory resource if it doesn't exist, or get existing one"""
        try:
            # List existing memories to find ours
            # Memory names get suffixed with unique ID, so we need to search by prefix
            memories_response = self.client.list_memories()
            memories_list = memories_response if isinstance(memories_response, list) else memories_response.get('memories', [])
            
            for memory in memories_list:
                memory_id = memory.get('id', '')
                # Check if memory ID starts with our prefix (e.g., "weather_agent_memory-JlzL2wDHIT")
                if memory_id.startswith(self.memory_name):
                    self.memory_id = memory_id
                    status = memory.get('status', 'UNKNOWN')
                    logger.info(f"Found existing memory: {memory_id} (Status: {status})")
                    
                    # Wait for memory to be active if it's still creating
                    if status != 'ACTIVE':
                        logger.info("Memory exists but is not active yet...")
                        self._wait_for_memory_active()
                    return
        except Exception as e:
            logger.debug(f"Could not list memories: {e}")
        
        # Memory doesn't exist, create it
        try:
            memory = self.client.create_memory(
                name=self.memory_name,
                description="Weather agent conversation memory"
            )
            self.memory_id = memory.get('id')
            logger.info(f"Created new memory with ID: {self.memory_id}")
            
            # Wait for the memory to become active
            self._wait_for_memory_active()
            
        except Exception as e:
            # If creation failed due to existing memory, try to find it again
            if "already exists" in str(e):
                logger.warning(f"Memory creation failed (already exists), attempting to find it...")
                try:
                    memories_response = self.client.list_memories()
                    memories_list = memories_response if isinstance(memories_response, list) else memories_response.get('memories', [])
                    
                    for memory in memories_list:
                        memory_id = memory.get('id', '')
                        if memory_id.startswith(self.memory_name):
                            self.memory_id = memory_id
                            status = memory.get('status', 'UNKNOWN')
                            logger.info(f"Found existing memory: {memory_id} (Status: {status})")
                            if status != 'ACTIVE':
                                self._wait_for_memory_active()
                            return
                    
                    logger.error(f"Could not find memory with prefix: {self.memory_name}")
                    raise Exception(f"Memory exists but could not be located")
                except Exception as retry_error:
                    logger.error(f"Failed to find existing memory: {retry_error}")
                    raise
            
            logger.error(f"Failed to create memory: {e}")
            raise
    
    def _wait_for_memory_active(self, max_wait_seconds: int = 300):
        """Wait for memory to become active (can take several minutes)"""
        start_time = time.time()
        logger.info("Waiting for memory to become active (this may take several minutes)...")
        while time.time() - start_time < max_wait_seconds:
            try:
                memories_response = self.client.list_memories()
                memories_list = memories_response if isinstance(memories_response, list) else memories_response.get('memories', [])
                
                for memory in memories_list:
                    if memory.get('id') == self.memory_id:
                        status = memory.get('status', 'UNKNOWN')
                        if status == 'ACTIVE':
                            elapsed = int(time.time() - start_time)
                            logger.info(f"Memory is now active after {elapsed} seconds")
                            return
                        elapsed = int(time.time() - start_time)
                        logger.info(f"Memory status: {status}, still waiting... ({elapsed}s elapsed)")
                        time.sleep(10)
                        break
            except Exception as e:
                logger.debug(f"Error checking memory status: {e}")
                time.sleep(10)


class AgentCoreMemoryHookProvider(HookProvider):
    """
    HookProvider implementation for Strands + Bedrock AgentCore Memory.
    Uses Strands lifecycle hooks to restore and persist short-term memory.
    Note: This code is NOT threadsafe or session-safe. Any agent using it will also not be threadsafe or session-safe.
    """

    def __init__(self, memory_client: MemoryClient, memory_id: str, session_id: str, actor_id: str, ):
        if not memory_id:
            raise ValueError("memory_id is required for AgentCoreMemoryHookProvider")

        self.memory_client = memory_client
        self.memory_id = memory_id
        self.session_id = session_id or "default"
        self.actor_id = actor_id or self.session_id
        self._baseline_message_count = 0
        logger.info(f"Initialized HookProvider with memory_id: {memory_id}")

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        """Register Strands typed lifecycle callbacks."""
        registry.add_callback(BeforeInvocationEvent, self.on_before_invocation)
        registry.add_callback(AfterInvocationEvent, self.on_after_invocation)

    def on_before_invocation(self, event: BeforeInvocationEvent) -> None:
        self._baseline_message_count = 0
        event.agent.messages.clear()

        try:
            restored_messages = self._load_session_messages()
            for message in restored_messages:
                event.agent.messages.append(message)

            self._baseline_message_count = len(event.agent.messages)
            if self._baseline_message_count:
                logger.info(
                    f"Restored {self._baseline_message_count} messages for session {self.session_id}"
                )
        except Exception as e:
            logger.debug(f"Unable to restore memory for session {self.session_id}: {e}")

    def on_after_invocation(self, event: AfterInvocationEvent) -> None:
        try:
            new_messages = event.agent.messages[self._baseline_message_count:]
            payload_messages = self._to_event_payload(new_messages)

            if payload_messages:
                self.memory_client.create_event(
                    memory_id=self.memory_id,
                    actor_id=self.actor_id,
                    session_id=self.session_id,
                    messages=payload_messages,
                )
        except Exception as e:
            logger.error(f"Error persisting messages for session {self.session_id}: {e}")

    def _load_session_messages(self) -> list[dict]:
        collected: list[dict] = []
        next_token = None

        while True:
            params = {
                "memory_id": self.memory_id,
                "actor_id": self.actor_id,
                "session_id": self.session_id,
            }
            if next_token:
                params["next_token"] = next_token

            response = self.memory_client.list_events(**params)
            events = response.get("events", []) if isinstance(response, dict) else response or []

            for event in events:
                if not isinstance(event, dict):
                    continue

                if not self._event_matches_scope(event):
                    continue

                event_messages = self._extract_event_messages(event)
                for message in event_messages:
                    normalized = self._normalize_agent_message(message)
                    if normalized is not None:
                        collected.append(normalized)

            if isinstance(response, dict):
                next_token = response.get("next_token") or response.get("nextToken")
            else:
                next_token = None

            if not next_token:
                break

        return collected

    def _event_matches_scope(self, event: dict) -> bool:
        event_actor = (
            event.get("actor_id")
            or event.get("actorId")
            or event.get("actor")
            or event.get("actorID")
        )
        event_session = (
            event.get("session_id")
            or event.get("sessionId")
            or event.get("session")
            or event.get("sessionID")
        )

        if event_actor is None or event_session is None:
            return False

        return str(event_actor) == self.actor_id and str(event_session) == self.session_id

    def _extract_event_messages(self, event: dict) -> list[dict]:
        if "messages" in event and isinstance(event.get("messages"), list):
            return [m for m in event.get("messages", []) if isinstance(m, dict)]

        payload = event.get("payload")
        if not isinstance(payload, list):
            return []

        extracted: list[dict] = []
        for item in payload:
            if not isinstance(item, dict):
                continue

            conversational = item.get("conversational")
            if not isinstance(conversational, dict):
                continue

            role = conversational.get("role", "assistant")
            content = conversational.get("content", {})
            extracted.append({"role": role, "content": content})

        return extracted

    def _normalize_agent_message(self, message: Any) -> dict | None:
        if not isinstance(message, dict):
            return None

        role = str(message.get("role", "assistant")).lower()
        content = message.get("content", "")
        text = self._content_to_text(content)
        if not text:
            return None

        return {
            "role": role,
            "content": [{"text": text}],
        }

    def _to_event_payload(self, messages: list[dict]) -> list[tuple[str, str]]:
        payload: list[tuple[str, str]] = []
        for message in messages:
            if not isinstance(message, dict):
                continue

            role = str(message.get("role", "assistant")).strip().upper() or "ASSISTANT"
            text = self._content_to_text(message.get("content", ""))
            if text:
                payload.append((text, role))

        return payload

    def _content_to_text(self, content: Any) -> str:
        if isinstance(content, str):
            return content

        if isinstance(content, dict):
            if "text" in content:
                return str(content["text"])
            return json.dumps(content, ensure_ascii=False)

        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    parts.append(str(item["text"]))
                elif isinstance(item, (dict, list)):
                    parts.append(json.dumps(item, ensure_ascii=False))
                else:
                    parts.append(str(item))
            return "\n".join(part for part in parts if part)

        if content is None:
            return ""

        return str(content)





