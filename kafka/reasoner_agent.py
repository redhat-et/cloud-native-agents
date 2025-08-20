import json
import sys
import asyncio
import logging
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
import os

# Add the project root directory (the parent of 'kafka') to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from backend.core.agents import AgentManager
from typing import Dict, Any


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReasonerAgent:
    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        self.bootstrap_servers = bootstrap_servers
        self.consumer = None
        self.producer = None
        self.agent_manager = None

    async def start(self):
        """Initialize the Kafka consumer and producer."""
        # Initialize consumer
        self.consumer = AIOKafkaConsumer(
            "research-findings",
            bootstrap_servers=self.bootstrap_servers,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            key_deserializer=lambda k: k.decode('utf-8') if k else None,
            group_id="reasoner-group"
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
        
        logger.info("Reasoner Agent started successfully")

    async def stop(self):
        """Stop the Kafka consumer and producer."""
        if self.consumer:
            await self.consumer.stop()
        if self.producer:
            await self.producer.stop()
        logger.info("Reasoner Agent stopped")

    async def process_research_findings(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process research findings and draft a comment."""
        issue_link = message.get("issue_link")
        issue_details = message.get("issue_details", {})
        research_results = message.get("research_results", [])
        
        if not issue_link:
            logger.error("No issue_link found in message")
            return None

        try:
            logger.info(f"Drafting comment for issue: {issue_link}")
            
            # Use the reasoner agent to draft a comment
            reasoner = self.agent_manager.agents["reasoner"]
            
            # Create a comprehensive prompt for the reasoner
            prompt = f"""
            Based on the following GitHub issue and research findings, draft a comprehensive comment suggesting potential root causes and actionable next steps.

            Issue Details:
            - Title: {issue_details.get('title', 'N/A')}
            - Body: {issue_details.get('body', 'N/A')}
            
            Research Findings:
            {json.dumps(research_results, indent=2)}
            
            Please provide:
            1. A brief summary of the issue
            2. Potential root causes
            3. Actionable next steps
            4. Any relevant references from the research
            
            Format this as a well-structured GitHub comment.
            """
            
            # Use the reasoner to generate the comment
            # Since reasoner doesn't have tools, we'll use the model client directly
            # model_client = self.agent_manager.model_client
            
            # Create a simple message for the model
            # messages = [
            #     {"role": "system", "content": reasoner.system_message},
            #     {"role": "user", "content": prompt}
            # ]
            
            # Get the response from the model
            response = await reasoner.run(task=prompt)
            drafted_comment = response.messages[-1].content
            
            # Create the draft comment message
            draft = {
                "issue_link": issue_link,
                "issue_details": issue_details,
                "research_results": research_results,
                "drafted_comment": drafted_comment,
                "timestamp": message.get("timestamp"),
                "metadata": message.get("metadata", {}),
                "agent": "reasoner"
            }
            
            logger.info(f"Successfully drafted comment for issue: {issue_link}")
            return draft
            
        except Exception as e:
            logger.error(f"Error drafting comment for issue {issue_link}: {e}")
            return None

    async def run(self):
        """Main loop to consume messages and process them."""
        try:
            async for message in self.consumer:
                logger.info(f"Received research findings: {message.value.get('issue_link')}")
                
                # Process the research findings
                draft = await self.process_research_findings(message.value)
                
                if draft:
                    # Send the draft to the next topic
                    await self.producer.send_and_wait(
                        topic="drafted-comments",
                        value=draft,
                        key=message.key
                    )
                    logger.info(f"Sent drafted comment for: {draft['issue_link']}")
                else:
                    logger.error("Failed to process research findings")
                    
        except Exception as e:
            logger.error(f"Error in run loop: {e}")
            raise

async def main():
    """Main function to run the Reasoner Agent."""
    agent = ReasonerAgent(bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"))
    try:
        await agent.start()
        await agent.run()
    except KeyboardInterrupt:
        logger.info("Shutting down Reasoner Agent...")
    finally:
        await agent.stop()

if __name__ == "__main__":
    asyncio.run(main()) 