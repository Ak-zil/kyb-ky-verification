import asyncio
from typing import Dict
from contextlib import asynccontextmanager

from app.utils.llm import BedrockClient
from app.utils.logging import get_logger

logger = get_logger("connection_pool")


class ConnectionPool:
    """
    Connection pool for managing LLM client connections
    Provides connection reuse and proper cleanup
    """
    
    def __init__(self, max_connections: int = 10):
        """
        Initialize connection pool
        
        Args:
            max_connections: Maximum number of concurrent connections
        """
        self.max_connections = max_connections
        self._semaphore = asyncio.Semaphore(max_connections)
        self._clients: Dict[str, BedrockClient] = {}
        self.logger = logger
        
    @asynccontextmanager
    async def get_client(self, client_type: str = "bedrock"):
        """
        Get a client from the pool
        
        Args:
            client_type: Type of client to get
            
        Yields:
            Client instance
        """
        async with self._semaphore:
            try:
                # Get or create client
                if client_type not in self._clients:
                    if client_type == "bedrock":
                        self._clients[client_type] = BedrockClient()
                    else:
                        raise ValueError(f"Unknown client type: {client_type}")
                
                client = self._clients[client_type]
                yield client
                
            except Exception as e:
                self.logger.error(f"Error getting client {client_type}: {str(e)}")
                raise
                
    async def close_all(self):
        """Close all clients in the pool"""
        for client_type, client in self._clients.items():
            try:
                if hasattr(client, 'close'):
                    await client.close()
                self.logger.info(f"Closed client: {client_type}")
            except Exception as e:
                self.logger.error(f"Error closing client {client_type}: {str(e)}")
        
        self._clients.clear()


# Global connection pool instance
connection_pool = ConnectionPool()