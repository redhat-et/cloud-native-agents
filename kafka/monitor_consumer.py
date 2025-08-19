import json
import asyncio
import logging
from aiokafka import AIOKafkaConsumer
from typing import Dict, Any
import os
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MonitorConsumer:
    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        self.bootstrap_servers = bootstrap_servers
        self.consumer = None
        self.completed_tasks = []

    async def start(self):
        """Initialize the Kafka consumer."""
        # Initialize consumer for completed tasks
        self.consumer = AIOKafkaConsumer(
            "completed-tasks",
            bootstrap_servers=self.bootstrap_servers,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            key_deserializer=lambda k: k.decode('utf-8') if k else None,
            group_id="monitor-consumer-group"
        )
        
        await self.consumer.start()
        logger.info("Monitor Consumer started successfully")

    async def stop(self):
        """Stop the Kafka consumer."""
        if self.consumer:
            await self.consumer.stop()
        logger.info("Monitor Consumer stopped")

    def display_completion_summary(self, completion: Dict[str, Any]):
        """Display a summary of the completed task."""
        issue_link = completion.get("issue_link")
        comment_text = completion.get("comment_text")
        post_result = completion.get("post_result")
        timestamp = completion.get("timestamp")
        
        print("\n" + "="*80)
        print("TASK COMPLETED")
        print("="*80)
        if isinstance(timestamp, str):
            try:
                print(f"Timestamp: {datetime.fromisoformat(timestamp).strftime('%Y-%m-%d %H:%M:%S')}")
            except ValueError:
                print(f"Timestamp: {timestamp} (Invalid ISO format)")
        else:
            # If no timestamp is provided, print a default message.
            print(f"Timestamp: Not available")
        print(f"Issue: {issue_link}")
        print("-" * 80)
        print("Posted Comment:")
        print(comment_text[:200] + "..." if len(comment_text) > 200 else comment_text)
        print("-" * 80)
        print("Post Result:")
        print(json.dumps(post_result, indent=2) if post_result else "No result data")
        print("="*80)
        
        # Store in memory for potential reporting``
        self.completed_tasks.append(completion)

    def get_statistics(self):
        """Get statistics about completed tasks."""
        total_tasks = len(self.completed_tasks)
        if total_tasks == 0:
            return "No tasks completed yet."
        
        # Group by agent
        agent_stats = {}
        for task in self.completed_tasks:
            agent = task.get("agent", "unknown")
            agent_stats[agent] = agent_stats.get(agent, 0) + 1
        
        stats = f"Total completed tasks: {total_tasks}\n"
        stats += "Tasks by agent:\n"
        for agent, count in agent_stats.items():
            stats += f"  {agent}: {count}\n"
        
        return stats

    async def run(self):
        """Main loop to consume messages and process them."""
        try:
            async for message in self.consumer:
                logger.info(f"Received completion: {message.value.get('issue_link')}")
                
                # Display the completion summary
                self.display_completion_summary(message.value)
                
                # Print current statistics
                print("\nCurrent Statistics:")
                print(self.get_statistics())
                
        except Exception as e:
            logger.error(f"Error in run loop: {e}")
            raise

async def main():
    """Main function to run the Monitor Consumer."""
    consumer = MonitorConsumer(os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"))
    try:
        await consumer.start()
        await consumer.run()
    except KeyboardInterrupt:
        logger.info("Shutting down Monitor Consumer...")
        print("\nFinal Statistics:")
        print(consumer.get_statistics())
    finally:
        await consumer.stop()

if __name__ == "__main__":
    asyncio.run(main()) 