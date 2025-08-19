import json
import asyncio
import logging
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from typing import Dict, Any
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UIConsumer:
    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        self.bootstrap_servers = bootstrap_servers
        self.consumer = None
        self.producer = None

    async def start(self):
        """Initialize the Kafka consumer and producer."""
        # Initialize consumer for drafted comments
        self.consumer = AIOKafkaConsumer(
            "drafted-comments",
            bootstrap_servers=self.bootstrap_servers,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            key_deserializer=lambda k: k.decode('utf-8') if k else None,
            group_id="ui-consumer-group"
        )
        
        # Initialize producer for approved comments
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None
        )
        
        await self.consumer.start()
        await self.producer.start()
        
        logger.info("UI Consumer started successfully")

    async def stop(self):
        """Stop the Kafka consumer and producer."""
        if self.consumer:
            await self.consumer.stop()
        if self.producer:
            await self.producer.stop()
        logger.info("UI Consumer stopped")

    async def display_draft_for_review(self, draft: Dict[str, Any]) -> str:
        """Display the drafted comment and get user approval/modification."""
        issue_link = draft.get("issue_link")
        drafted_comment = draft.get("drafted_comment")
        
        print("\n" + "="*80)
        print("DRAFTED COMMENT FOR REVIEW")
        print("="*80)
        print(f"Issue: {issue_link}")
        print("-" * 80)
        print("Drafted Comment:")
        print(drafted_comment)
        print("-" * 80)
        
        while True:
            print("\nOptions:")
            print("1. Approve and post comment")
            print("2. Modify comment")
            print("3. Reject comment")
            
            choice = input("\nEnter your choice (1-3): ").strip()
            
            if choice == "1":
                return drafted_comment
            elif choice == "2":
                print("\nEnter your modified comment (press Enter twice to finish):")
                lines = []
                while True:
                    line = input()
                    if line == "" and lines and lines[-1] == "":
                        break
                    lines.append(line)
                
                modified_comment = "\n".join(lines[:-1])  # Remove the last empty line
                return modified_comment
            elif choice == "3":
                return None
            else:
                print("Invalid choice. Please enter 1, 2, or 3.")

    async def run(self):
        """Main loop to consume messages and process them."""
        try:
            async for message in self.consumer:
                logger.info(f"Received drafted comment: {message.value.get('issue_link')}")
                
                # Display the draft for user review
                approved_comment = await self.display_draft_for_review(message.value)
                
                if approved_comment:
                    # Send the approved comment to the next topic
                    approved_message = {
                        "issue_link": message.value.get("issue_link"),
                        "comment_text": approved_comment,
                        "timestamp": message.value.get("timestamp"),
                        "metadata": message.value.get("metadata", {}),
                        "agent": "ui_consumer"
                    }
                    
                    await self.producer.send_and_wait(
                        topic="approved-comments",
                        value=approved_message,
                        key=message.key
                    )
                    logger.info(f"Sent approved comment for: {approved_message['issue_link']}")
                else:
                    logger.info("Comment rejected by user")
                    
        except Exception as e:
            logger.error(f"Error in run loop: {e}")
            raise

async def main():
    """Main function to run the UI Consumer."""
    consumer = UIConsumer(os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"))
    try:
        await consumer.start()
        await consumer.run()
    except KeyboardInterrupt:
        logger.info("Shutting down UI Consumer...")
    finally:
        await consumer.stop()

if __name__ == "__main__":
    asyncio.run(main()) 