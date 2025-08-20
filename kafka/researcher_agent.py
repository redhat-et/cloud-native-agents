import json
import os
import asyncio
import sys
import logging
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

# Add the project root directory (the parent of 'kafka') to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from backend.core.agents import AgentManager
from typing import Dict, Any


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResearcherAgent:
    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        self.bootstrap_servers = bootstrap_servers
        self.consumer = None
        self.producer = None
        self.agent_manager = None

    async def start(self):
        """Initialize the Kafka consumer and producer."""
        # Initialize consumer
        self.consumer = AIOKafkaConsumer(
            "issue-summaries",
            bootstrap_servers=self.bootstrap_servers,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            key_deserializer=lambda k: k.decode('utf-8') if k else None,
            group_id="researcher-group"
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
        
        logger.info("Researcher Agent started successfully")

    async def stop(self):
        """Stop the Kafka consumer and producer."""
        if self.consumer:
            await self.consumer.stop()
        if self.producer:
            await self.producer.stop()
        logger.info("Researcher Agent stopped")

    async def process_issue_summary(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process an issue summary and perform research."""
        issue_link = message.get("issue_link")
        issue_details = message.get("issue_summary", {})
        
        if not issue_link:
            logger.error("No issue_link found in message")
            return None

        try:
            logger.info(f"Researching issue: {issue_link}")
            
            # Use the researcher agent to find related information
            researcher = self.agent_manager.agents["researcher"]
            
            # Extract key information for research
            title = issue_details.get("title", "")
            body = issue_details.get("body", "")
            # logger.info(f"Researching issue: {title}")
            # Create search queries based on the issue

            search_queries = [
                f"{title} GitHub issue solution",
                f"{title} troubleshooting",
                f"{title} similar problems",
            ]
            
            research_results = []
            
            # Perform searches for each query
            for query in search_queries:
                try:
                    # Use the tavily tool to search
                    summary_content = await researcher.run(task=query)
                    issue_summary = summary_content.messages[-1].content
                    research_results.append(issue_summary)
                except Exception as e:
                    logger.error(f"Error searching for query '{query}': {e}")
            
            # Create research findings
            findings = {
                "issue_link": issue_link,
                "issue_details": issue_details,
                "research_results": research_results,
                "timestamp": message.get("timestamp"),
                "metadata": message.get("metadata", {}),
                "agent": "researcher"
            }
            
            logger.info(f"Successfully researched issue: {issue_link}")
            return findings
            
        except Exception as e:
            logger.error(f"Error researching issue {issue_link}: {e}")
            return None

    async def run(self):
        """Main loop to consume messages and process them."""
        try:
            async for message in self.consumer:
                logger.info(f"Received issue summary: {message.value.get('issue_link')}")
                
                # Process the issue summary
                findings = await self.process_issue_summary(message.value)
                
                if findings:
                    # Send the findings to the next topic
                    await self.producer.send_and_wait(
                        topic="research-findings",
                        value=findings,
                        key=message.key
                    )
                    logger.info(f"Sent research findings for: {findings['issue_link']}")
                else:
                    logger.error("Failed to process issue summary")
                    
        except Exception as e:
            logger.error(f"Error in run loop: {e}")
            raise

async def main():
    """Main function to run the Researcher Agent."""
    agent = ResearcherAgent(bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"))
    try:
        await agent.start()
        await agent.run()
    except KeyboardInterrupt:
        logger.info("Shutting down Researcher Agent...")
    finally:
        await agent.stop()

if __name__ == "__main__":
    asyncio.run(main()) 