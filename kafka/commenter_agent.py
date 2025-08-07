import json
import asyncio
import logging
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from agents import AgentManager
from typing import Dict, Any

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CommenterAgent:
    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        self.bootstrap_servers = bootstrap_servers
        self.consumer = None
        self.producer = None
        self.agent_manager = None

    async def start(self):
        """Initialize the Kafka consumer and producer."""
        # Initialize consumer
        self.consumer = AIOKafkaConsumer(
            "approved-comments",
            bootstrap_servers=self.bootstrap_servers,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            key_deserializer=lambda k: k.decode('utf-8') if k else None,
            group_id="commenter-group"
        )
        
        # Initialize producer
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None
        )
        
        await self.consumer.start()
        await self.producer.start()
        
        # Initialize agent manager
        self.agent_manager = AgentManager()
        await self.agent_manager.initialize_agents()
        
        logger.info("Commenter Agent started successfully")

    async def stop(self):
        """Stop the Kafka consumer and producer."""
        if self.consumer:
            await self.consumer.stop()
        if self.producer:
            await self.producer.stop()
        logger.info("Commenter Agent stopped")

    async def process_approved_comment(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process an approved comment and post it to GitHub."""
        issue_link = message.get("issue_link")
        comment_text = message.get("comment_text")
        
        if not issue_link or not comment_text:
            logger.error("No issue_link or comment_text found in message")
            return None

        try:
            logger.info(f"Posting comment for issue: {issue_link}")
            
            # Use the commenter agent to post the comment
            commenter = self.agent_manager.agents["commenter"]
            
            # Get the add_issue_comment tool
            add_comment_tool = commenter.tools[0]  # Assuming add_issue_comment is the first tool
            
            # Post the comment to GitHub
            result = await add_comment_tool.func(issue_link, comment_text)
            
            # Create completion message
            completion = {
                "issue_link": issue_link,
                "comment_text": comment_text,
                "post_result": result,
                "timestamp": message.get("timestamp"),
                "metadata": message.get("metadata", {}),
                "agent": "commenter",
                "status": "completed"
            }
            
            logger.info(f"Successfully posted comment for issue: {issue_link}")
            return completion
            
        except Exception as e:
            logger.error(f"Error posting comment for issue {issue_link}: {e}")
            return None

    async def run(self):
        """Main loop to consume messages and process them."""
        try:
            async for message in self.consumer:
                logger.info(f"Received approved comment: {message.value.get('issue_link')}")
                
                # Process the approved comment
                completion = await self.process_approved_comment(message.value)
                
                if completion:
                    # Send the completion to the final topic
                    await self.producer.send_and_wait(
                        topic="completed-tasks",
                        value=completion,
                        key=message.key
                    )
                    logger.info(f"Sent completion for: {completion['issue_link']}")
                else:
                    logger.error("Failed to process approved comment")
                    
        except Exception as e:
            logger.error(f"Error in run loop: {e}")
            raise

async def main():
    """Main function to run the Commenter Agent."""
    agent = CommenterAgent()
    try:
        await agent.start()
        await agent.run()
    except KeyboardInterrupt:
        logger.info("Shutting down Commenter Agent...")
    finally:
        await agent.stop()

if __name__ == "__main__":
    asyncio.run(main()) 