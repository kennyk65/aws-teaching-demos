"""
Memory module for Bedrock AgentCore
Provides SessionManager implementation for Strands using AWS Bedrock AgentCore Memory
"""

from bedrock_agentcore.memory import MemoryClient
from strands.session import SessionManager
from typing import Any
import logging
import time

logger = logging.getLogger("agent_activity")


class AgentCoreMemory:
    """
    Initializer for Bedrock AgentCore Memory.
    
    Creates or finds an existing AgentCore Memory resource and ensures it's active before use.
    Provides the memory client and ID for use by AgentCoreSessionManager.
    """
    
    def __init__(self, memory_name: str = "weather_memory", region_name: str = "us-west-2"):
        self.memory_name = memory_name
        self.client = MemoryClient(region_name=region_name)
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


class AgentCoreSessionManager(SessionManager):
    """
    SessionManager implementation for Strands that integrates with Bedrock AgentCore Memory.
    
    This class automatically persists conversation history and agent state to AgentCore Memory,
    eliminating the need for manual memory management in agent code.
    
    Note: This implementation doesn't use the automatic hook-based persistence because
    hooks fire on every message addition (including tool calls), which causes duplicates.
    Instead, we manually save the conversation after each agent invocation.
    """
    
    def __init__(self, memory_client: MemoryClient, memory_id: str):
        """
        Initialize the session manager.
        
        Args:
            memory_client: Initialized MemoryClient instance
            memory_id: The AgentCore Memory ID to use for storage
        """
        # Don't call super().__init__() to avoid registering hooks
        self.memory_client = memory_client
        self.memory_id = memory_id
        self.session_id = None
        logger.info(f"Initialized SessionManager with memory_id: {memory_id}")
    
    def initialize(self, agent: "Agent", session_id: str = None, **kwargs: Any) -> None:
        """
        Initialize/restore a session for the agent.
        
        Args:
            agent: The agent to initialize
            session_id: Optional session identifier
            **kwargs: Additional arguments
        """
        session_id = session_id or "default"
        
        # Clear agent's messages when switching to a different session
        if self.session_id != session_id:
            logger.info(f"Switching from session '{self.session_id}' to '{session_id}' - clearing agent messages")
            agent.messages.clear()
        
        self.session_id = session_id
        logger.info(f"Initializing session: {self.session_id}")
        
        # Restore conversation history from AgentCore Memory
        if self.memory_id:
            try:
                # Use get_last_k_turns to retrieve conversation history in order
                # This returns turns (pairs of user/assistant exchanges)
                turns = self.memory_client.get_last_k_turns(
                    memory_id=self.memory_id,
                    actor_id=self.session_id,
                    session_id=self.session_id,
                    k=50  # Retrieve last 50 turns (100 messages)
                )
                
                # Flatten turns into messages and restore to agent
                restored_count = 0
                for turn in turns:
                    # Each turn is a list of messages (user + assistant)
                    for msg in turn:
                        role = msg.get('role', 'user').lower()
                        
                        # Only restore user and assistant messages, skip tool messages
                        if role not in ['user', 'assistant']:
                            continue
                        
                        # Extract text content - handle both string and dict formats
                        content_text = ""
                        raw_content = msg.get('content', '')
                        
                        if isinstance(raw_content, str):
                            content_text = raw_content
                        elif isinstance(raw_content, list):
                            # Content is already in the [{text: '...'}] format
                            for item in raw_content:
                                if isinstance(item, dict) and 'text' in item:
                                    content_text = str(item['text'])
                                    break
                        elif isinstance(raw_content, dict):
                            # Content is a dict, try to extract text
                            content_text = str(raw_content.get('text', raw_content))
                        
                        if content_text:
                            # Create message in Strands format
                            message = {
                                "role": role,
                                "content": [{"text": content_text}]
                            }
                            agent.messages.append(message)
                            restored_count += 1
                
                if restored_count > 0:
                    logger.info(f"Restored {restored_count} messages from memory for session {self.session_id}")
                    
            except Exception as e:
                logger.debug(f"No existing session to restore or error: {e}")
    
    def save_conversation(self, agent, session_id: str = None):
        """
        Save the current conversation to AgentCore Memory.
        Only saves user and assistant messages, skipping tool calls.
        
        Args:
            agent: The agent whose conversation to save
            session_id: Optional session ID (uses stored session_id if not provided)
        """
        if session_id:
            self.session_id = session_id
            
        if not self.memory_id or not self.session_id:
            logger.warning("Cannot save - missing memory_id or session_id")
            return
        
        try:
            # Extract only user and assistant messages
            messages_to_store = []
            for msg in agent.messages:
                role = msg.get('role', '').lower()
                
                # Only save user and assistant messages
                if role not in ['user', 'assistant']:
                    continue
                
                # Extract text content
                content_text = ""
                raw_content = msg.get('content', [])
                
                if isinstance(raw_content, list):
                    for item in raw_content:
                        if isinstance(item, dict) and 'text' in item:
                            content_text = str(item['text'])
                            break
                
                if content_text:
                    messages_to_store.append((content_text, role.upper()))
            
            # Store to AgentCore Memory if we have messages
            if messages_to_store:
                self.memory_client.create_event(
                    memory_id=self.memory_id,
                    actor_id=self.session_id,
                    session_id=self.session_id,
                    messages=messages_to_store
                )
                logger.info(f"Saved conversation with {len(messages_to_store)} messages to memory")
                
        except Exception as e:
            logger.error(f"Error saving conversation to memory: {e}")
    
    # Required abstract methods (not used in our implementation)
    def append_message(self, message, agent, **kwargs: Any) -> None:
        """Not used - we save manually instead of via hooks."""
        pass
    
    def sync_agent(self, agent, **kwargs: Any) -> None:
        """Not used - we save manually instead of via hooks."""
        pass
    
    def redact_latest_message(self, redact_message, agent, **kwargs: Any) -> None:
        """Not supported by AgentCore Memory."""
        logger.warning("Message redaction not supported by AgentCore Memory")
