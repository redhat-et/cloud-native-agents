import json
import asyncio
from aiokafka import AIOKafkaProducer
from typing import Dict, Any
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KafkaProducer:
    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        self.bootstrap_servers = bootstrap_servers
        self.producer = None

    async def start(self):
        """Initialize the Kafka producer."""
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None
        )
        await self.producer.start()
        logger.info("Kafka producer started successfully")

    async def stop(self):
        """Stop the Kafka producer."""
        if self.producer:
            await self.producer.stop()
            logger.info("Kafka producer stopped")

    async def send_github_issue_link(self, issue_link: str, metadata: Dict[str, Any] = None):
        """Send a GitHub issue link to the github-issue-links topic."""
        if not self.producer:
            raise RuntimeError("Producer not started. Call start() first.")

        message = {
            "issue_link": issue_link,
            "timestamp": asyncio.get_event_loop().time(),
            "metadata": metadata or {}
        }

        try:
            await self.producer.send_and_wait(
                topic="github-issue-links",
                value=message,
                key=issue_link
            )
            logger.info(f"Sent GitHub issue link: {issue_link}")
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False

    async def send_approved_comment(self, issue_link: str, comment_text: str, metadata: Dict[str, Any] = None):
        """Send an approved comment to the approved-comments topic."""
        if not self.producer:
            raise RuntimeError("Producer not started. Call start() first.")

        message = {
            "issue_link": issue_link,
            "comment_text": comment_text,
            "timestamp": asyncio.get_event_loop().time(),
            "metadata": metadata or {}
        }

        try:
            await self.producer.send_and_wait(
                topic="approved-comments",
                value=message,
                key=issue_link
            )
            logger.info(f"Sent approved comment for issue: {issue_link}")
            return True
        except Exception as e:
            logger.error(f"Failed to send approved comment: {e}")
            return False

# Example usage
async def main():
    producer = KafkaProducer(os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"))
    await producer.start()
    
    # Example: Send a GitHub issue link
    issue_link = "https://github.com/example/repo/issues/123"
    success = await producer.send_github_issue_link(issue_link, {"user_id": "user123"})
    
    if success:
        print(f"Successfully sent issue link: {issue_link}")
    else:
        print("Failed to send issue link")
    
    await producer.stop()

if __name__ == "__main__":
    asyncio.run(main()) 