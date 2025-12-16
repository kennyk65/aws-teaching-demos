"""
Memory module for Bedrock AgentCore
Provides simple get/set interface for conversation history storage using AWS Bedrock AgentCore Memory
"""

from bedrock_agentcore.memory import MemoryClient
import logging
import time

logger = logging.getLogger("agent_activity")


class AgentCoreMemory:
    """Wrapper for Bedrock AgentCore Memory with simple get/set interface"""
    
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
    
    def get_conversation_history(self, user_id: str, session_id: str = None) -> list:
        """
        Retrieve conversation history for a user session
        
        Args:
            user_id: Unique identifier for the user (actor_id)
            session_id: Optional session identifier (defaults to user_id)
            
        Returns:
            List of conversation messages in format:
            [{"role": "user", "content": [{"text": "..."}]}, ...]
        """
        if session_id is None:
            session_id = user_id
        
        if not self.memory_id:
            logger.warning("Memory ID not available")
            return []
        
        try:
            # Retrieve memories for this session
            namespace = f"/sessions/{user_id}/{session_id}"
            memories = self.client.retrieve_memories(
                memory_id=self.memory_id,
                namespace=namespace,
                query="conversation history"
            )
            
            # Parse and return conversation history
            # The memories are stored as events, we need to reconstruct the conversation
            conversation_history = []
            for memory in memories.get('memories', []):
                content = memory.get('content', '')
                role = memory.get('metadata', {}).get('role', 'user')
                conversation_history.append({
                    "role": role,
                    "content": [{"text": content}]
                })
            
            if conversation_history:
                logger.info(f"Retrieved {len(conversation_history)} messages from memory")
            return conversation_history
            
        except Exception as e:
            logger.debug(f"No existing session found or error retrieving: {e}")
            return []
    
    def set_conversation_history(self, user_id: str, conversation_history: list, session_id: str = None) -> bool:
        """
        Store conversation history for a user session
        
        Args:
            user_id: Unique identifier for the user (actor_id)
            conversation_history: List of messages to store
            session_id: Optional session identifier (defaults to user_id)
            
        Returns:
            True if successful, False otherwise
        """
        if session_id is None:
            session_id = user_id
        
        if not self.memory_id:
            logger.error("Memory ID not available")
            return False
        
        try:
            # Convert conversation history to messages format for create_event
            messages = []
            for msg in conversation_history:
                text = msg.get('content', [{}])[0].get('text', '')
                role = msg.get('role', 'USER').upper()
                messages.append((text, role))
            
            # Store the conversation as an event
            self.client.create_event(
                memory_id=self.memory_id,
                actor_id=user_id,
                session_id=session_id,
                messages=messages
            )
            
            logger.info(f"Stored {len(conversation_history)} messages to memory")
            return True
            
        except Exception as e:
            logger.error(f"Error storing memory: {e}")
            return False
