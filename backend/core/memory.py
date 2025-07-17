"""
Memory module for ChromaDB integration with AutoGen agents.
Handles conversation storage and retrieval using ChromaDB vector database.
"""

import os
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
import logging
import chromadb

from autogen_core.memory import MemoryContent, MemoryMimeType
from autogen_ext.memory.chromadb import (
    ChromaDBVectorMemory,
    HttpChromaDBVectorMemoryConfig,
)
from dotenv import load_dotenv

load_dotenv()

# Setup logging
logger = logging.getLogger(__name__)

class ConversationMemory:
    """Manages conversation storage and retrieval using ChromaDB."""
    
    def __init__(self):
        print("[ConversationMemory] __init__ called")
        # Use the same approach as customvectorDB_http.py
        self.host = os.getenv("CHROMADB_URL")
        print(f"[ConversationMemory] CHROMADB_URL: {self.host}")
        self.port = int(os.getenv("CHROMADB_PORT", "80"))
        self.collection_name = os.getenv("CHROMADB_COLLECTION")
        print(f"[ConversationMemory] CHROMADB_COLLECTION: {self.collection_name}")
        self.memory = None
        self.initialized = False
        
        # Only initialize if CHROMADB_URL is set
        if self.host:
            try:
                # Initialize ChromaDB memory - using the same config as working example
                self.memory = ChromaDBVectorMemory(
                    config=HttpChromaDBVectorMemoryConfig(
                        collection_name=self.collection_name,
                        host=self.host,  # Use the full URL as host
                        port=self.port,
                        ssl=False,
                        k=5,  # Return top 5 results
                        score_threshold=0.3,  # Minimum similarity score
                    )
                )
                self.initialized = True
                print(f"[ConversationMemory] ✅ Initialized ChromaDB memory with host={self.host}, port={self.port}, collection={self.collection_name}")
                logger.info(f"✅ Initialized ChromaDB memory with host={self.host}, port={self.port}, collection={self.collection_name}")
            except Exception as e:
                print(f"[ConversationMemory] ⚠️  Failed to initialize ChromaDB memory: {e}")
                logger.warning(f"⚠️  Failed to initialize ChromaDB memory: {e}")
                logger.info("   Memory functionality will be disabled - backend will still work")
                self.initialized = False
        else:
            print("[ConversationMemory] ⚠️  CHROMADB_URL not set - memory functionality disabled")
            logger.warning("⚠️  CHROMADB_URL not set - memory functionality disabled")
            logger.info("   Set CHROMADB_URL environment variable to enable memory")
            self.initialized = False
    
    async def store_conversation(
        self, 
        user_query: str, 
        agent_response: str, 
        session_id: str = "default",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Store a conversation in ChromaDB memory.
        
        Args:
            user_query: The user's input/query
            agent_response: The final response from the agent team
            session_id: Unique identifier for the conversation session
            metadata: Additional metadata to store
            
        Returns:
            bool: True if successfully stored, False otherwise
        """
        if not self.initialized or not self.memory:
            logger.debug("Memory not initialized - skipping conversation storage")
            return False
            
        try:
            # Combine user query and agent response
            conversation_content = f"User Query: {user_query}\nAgent Response: {agent_response}"
            
            # Prepare metadata
            conversation_metadata = {
                "type": "conversation",
                "user_query": user_query,
                "agent_response": agent_response,
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id,
            }
            
            # Add any additional metadata
            if metadata:
                conversation_metadata.update(metadata)
            
            # Store in ChromaDB
            await self.memory.add(
                MemoryContent(
                    content=conversation_content,
                    mime_type=MemoryMimeType.TEXT,
                    metadata=conversation_metadata,
                )
            )
            
            logger.info(f"💾 Stored conversation: {user_query[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error storing conversation: {e}")
            return False
    
    async def query_similar_conversations(self, query: str) -> list:
        """
        Query for similar conversations based on the input query.
        
        Args:
            query: The search query
            
        Returns:
            list: List of similar conversations
        """
        if not self.initialized or not self.memory:
            logger.debug("Memory not initialized - returning empty results")
            return []
            
        try:
            # The k parameter (number of results) is configured in HttpChromaDBVectorMemoryConfig
            # We can't override it per query, so we use the configured value
            results = await self.memory.query(query)
            return results.results
        except Exception as e:
            logger.error(f"❌ Error querying conversations: {e}")
            return []
    
    async def get_memory_for_agents(self):
        """
        Get the ChromaDB memory instance for use with AutoGen agents.
        
        Returns:
            ChromaDBVectorMemory or None: The memory instance if available
        """
        if self.initialized and self.memory:
            return self.memory
        else:
            logger.debug("Memory not available for agents - returning None")
            return None
    
    async def reload_collection_config(self) -> bool:
        """
        Reload the collection configuration from environment variables.
        This is useful when the CHROMADB_COLLECTION environment variable changes.
        
        Returns:
            bool: True if successfully reloaded, False otherwise
        """
        # Get the current collection name from environment
        new_collection_name = os.getenv("CHROMADB_COLLECTION", "preferences")
        
        # Check if collection name has changed
        if new_collection_name == self.collection_name:
            logger.info(f"ℹ️  Collection name unchanged: {self.collection_name}")
            return True
        
        logger.info(f"🔄 Collection name changed from '{self.collection_name}' to '{new_collection_name}'")
        
        # Update the collection name
        self.collection_name = new_collection_name
        
        # Reinitialize memory with the new collection
        if self.host:
            try:
                # Close existing memory connection if any
                if self.memory:
                    try:
                        await self.memory.close()
                    except:
                        pass
                
                # Initialize ChromaDB memory with new collection
                self.memory = ChromaDBVectorMemory(
                    config=HttpChromaDBVectorMemoryConfig(
                        collection_name=self.collection_name,
                        host=self.host,
                        port=self.port,
                        ssl=False,
                        k=5,
                        score_threshold=0.3,
                    )
                )
                self.initialized = True
                logger.info(f"✅ Reinitialized ChromaDB memory with collection: {self.collection_name}")
                return True
                
            except Exception as e:
                logger.error(f"❌ Error reinitializing memory with new collection: {e}")
                self.initialized = False
                return False
        else:
            logger.warning("⚠️  CHROMADB_URL not set - cannot reinitialize memory")
            return False
    
    async def display_all_memory(self):
        """
        Display all memory content stored in ChromaDB.
        """
        if not self.initialized or not self.memory:
            print("📭 Memory not initialized - no data to display")
            return
        
        try:
            # Use the same approach as customvectorDB_http.py
            chromadb_url = os.getenv("CHROMADB_URL")
            HOST = chromadb_url
            PORT = 80
            
            # Connect directly to ChromaDB
            client = chromadb.HttpClient(host=HOST, port=PORT)
            
            # Get collection data
            try:
                collection = client.get_collection(name=self.collection_name)
                all_data = collection.get()

                if len(all_data['ids']) > 0:
                    print("\n📄 All documents in Chroma:")
                    for i, (doc_id, doc_content, metadata) in enumerate(zip(
                        all_data['ids'], 
                        all_data['documents'], 
                        all_data['metadatas']
                    )):
                        print(f"  {i+1}. ID: {doc_id}")
                        print(f"     Content: {doc_content}")
                        print(f"     Metadata: {metadata}")
                        print()
                else:
                    print("📭 No documents found in Chroma collection: ", self.collection_name)
        
            except Exception as e:
                print(f"⚠️  Could not get collection '{self.collection_name}': {e}")
                
        except Exception as e:
            print(f"❌ Error checking Chroma storage: {e}")

    
    async def clear_memory(self) -> bool:
        """
        Clear all stored conversations.
        
        Returns:
            bool: True if successfully cleared, False otherwise
        """
        if not self.initialized or not self.memory:
            logger.debug("Memory not initialized - nothing to clear")
            return True
            
        try:
            await self.memory.clear()
            logger.info("🗑️ Cleared all stored conversations")
            return True
        except Exception as e:
            logger.error(f"❌ Error clearing memory: {e}")
            return False
    
    async def create_collection(self) -> bool:
        """
        Create a new collection with the specified name.
        If collection already exists, it will be deleted first.
        
        Returns:
            bool: True if successfully created, False otherwise
        """
        if not self.host:
            logger.warning("⚠️  CHROMADB_URL not set - cannot create collection")
            return False
            
        try:
            # Connect directly to ChromaDB
            client = chromadb.HttpClient(host=self.host, port=self.port)
            
            # Check if collection exists and delete it first
            try:
                existing_collection = client.get_collection(name=self.collection_name)
                logger.info(f"🗑️ Collection '{self.collection_name}' already exists - deleting first")
                client.delete_collection(name=self.collection_name)
                logger.info(f"✅ Deleted existing collection: {self.collection_name}")
            except Exception as e:
                if "does not exist" in str(e):
                    logger.info(f"ℹ️  Collection '{self.collection_name}' does not exist - will create new one")
                else:
                    logger.warning(f"⚠️  Error checking existing collection: {e}")
            
            # Create new collection
            logger.info(f"📝 Creating new collection: {self.collection_name}")
            new_collection = client.create_collection(name=self.collection_name)
            logger.info(f"✅ Successfully created new collection: {self.collection_name}")
            
            # Reinitialize the memory object with the new collection
            self.memory = ChromaDBVectorMemory(
                config=HttpChromaDBVectorMemoryConfig(
                    collection_name=self.collection_name,
                    host=self.host,
                    port=self.port,
                    ssl=False,
                    k=5,
                    score_threshold=0.3,
                )
            )
            self.initialized = True
            logger.info(f"🔄 Reinitialized memory with new collection: {self.collection_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creating collection: {e}")
            return False
    
    async def delete_collection(self) -> bool:
        """
        Delete the entire collection from ChromaDB.
        
        Returns:
            bool: True if successfully deleted, False otherwise
        """
        if not self.host:
            logger.warning("⚠️  CHROMADB_URL not set - cannot delete collection")
            return False
            
        try:
            # Connect directly to ChromaDB
            client = chromadb.HttpClient(host=self.host, port=self.port)
            
            # Check if collection exists and delete it
            try:
                existing_collection = client.get_collection(name=self.collection_name)
                logger.info(f"🗑️ Deleting collection: {self.collection_name}")
                client.delete_collection(name=self.collection_name)
                logger.info(f"✅ Successfully deleted collection: {self.collection_name}")
                
                # Reset memory state
                self.memory = None
                self.initialized = False
                logger.info("🔄 Memory state reset - collection deleted")
                
                return True
                
            except Exception as e:
                if "does not exist" in str(e):
                    logger.info(f"ℹ️  Collection '{self.collection_name}' does not exist")
                    return True
                else:
                    logger.error(f"❌ Error deleting collection: {e}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Error connecting to ChromaDB: {e}")
            return False
    
    async def delete_documents(self) -> bool:
        """
        Delete all documents from the collection but keep the collection structure.
        This is equivalent to clearing the collection.
        
        Returns:
            bool: True if successfully cleared, False otherwise
        """
        if not self.initialized or not self.memory:
            logger.warning("⚠️  Memory not initialized - cannot delete documents")
            return False
            
        try:
            await self.memory.clear()
            logger.info("🗑️ Deleted all documents from collection")
            return True
        except Exception as e:
            logger.error(f"❌ Error deleting documents: {e}")
            return False
    
    async def list_collections(self) -> list:
        """
        List all collections in ChromaDB.
        
        Returns:
            list: List of collection names
        """
        if not self.host:
            logger.warning("⚠️  CHROMADB_URL not set - cannot list collections")
            return []
            
        try:
            # Connect directly to ChromaDB
            client = chromadb.HttpClient(host=self.host, port=self.port)
            
            # Get all collections
            collections = client.list_collections()
            
            collection_info = []
            for collection in collections:
                try:
                    doc_count = len(collection.get()['ids'])
                    collection_info.append({
                        'name': collection.name,
                        'document_count': doc_count
                    })
                except Exception as e:
                    logger.warning(f"⚠️  Error getting document count for collection '{collection.name}': {e}")
                    collection_info.append({
                        'name': collection.name,
                        'document_count': 'unknown'
                    })
            
            return collection_info
            
        except Exception as e:
            logger.error(f"❌ Error listing collections: {e}")
            return []
    
    async def display_collections(self):
        """
        Display all collections in ChromaDB with their document counts.
        """
        collections = await self.list_collections()
        
        if not collections:
            print("📭 No collections found in ChromaDB")
            return
        
        print("📋 ChromaDB Collections:")
        print("=" * 40)
        
        for i, collection in enumerate(collections, 1):
            doc_count = collection['document_count']
            current_marker = " 👈 Current" if collection['name'] == self.collection_name else ""
            print(f"  {i}. {collection['name']} ({doc_count} documents){current_marker}")
        
        print(f"\n📍 Current collection: {self.collection_name}")
    

    
    async def close(self):
        """Close the memory connection."""
        if self.initialized and self.memory:
            try:
                await self.memory.close()
                logger.info("🔒 Closed ChromaDB memory connection")
            except Exception as e:
                logger.error(f"❌ Error closing memory: {e}")

# Global instance
conversation_memory = ConversationMemory()

async def main():
    """Command-line interface for memory management"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: CHROMADB_COLLECTION=collection_name python memory.py [command]")
        print("Commands:")
        print("  list       - List all collections in ChromaDB")
        print("  display    - Display all memory content")
        print("  create     - Create a new collection (delete existing if present)")
        print("  delete     - Delete the entire collection")
        print("  clear      - Delete all documents (keep collection)")
        print("  reload     - Reload collection config from environment variables")
        return
    
    command = sys.argv[1].lower()
    
    # Initialize memory
    memory = ConversationMemory()
    
    if command == "list":
        print("📋 Listing all collections...")
        await memory.display_collections()
    
    elif command == "display":
        if not memory.initialized:
            print("❌ Memory not initialized - cannot display content")
            return
        print("📊 Displaying memory content:")
        await memory.display_all_memory()
    
    elif command == "create":
        print("📝 Creating collection...")
        success = await memory.create_collection()
        if success:
            print("✅ Collection created successfully!")
        else:
            print("❌ Failed to create collection")
    
    elif command == "delete":
        print("🗑️ Deleting collection...")
        success = await memory.delete_collection()
        if success:
            print("✅ Collection deleted successfully!")
        else:
            print("❌ Failed to delete collection")
    
    elif command == "clear":
        if not memory.initialized:
            print("❌ Memory not initialized - cannot clear documents")
            return
        print("🗑️ Deleting all documents (keeping collection)...")
        success = await memory.delete_documents()
        if success:
            print("✅ Documents deleted successfully!")
        else:
            print("❌ Failed to delete documents")
    
    elif command == "reload":
        print("🔄 Reloading collection configuration...")
        success = await memory.reload_collection_config()
        if success:
            print("✅ Collection configuration reloaded successfully!")
            print(f"📍 Current collection: {memory.collection_name}")
        else:
            print("❌ Failed to reload collection configuration")
    
    else:
        print(f"❌ Unknown command: {command}")

if __name__ == "__main__":
    asyncio.run(main()) 