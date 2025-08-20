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
from autogen_agentchat.agents import UserProxyAgent, AssistantAgent
from typing import Dict, Any, List

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IssueReaderAgent:
    """
    A Kafka-based agent that consumes GitHub issue links, uses an AutoGen agent 
    to read and summarize the issue, and produces the summary to another Kafka topic.
    This version uses a more direct agent invocation method.
    """
    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        self.bootstrap_servers = bootstrap_servers
        self.consumer = None
        self.producer = None
        self.agent_manager = None

    async def start(self):
        """Initialize Kafka clients and the AgentManager."""
        self.consumer = AIOKafkaConsumer(
            "github-issue-links",
            bootstrap_servers=self.bootstrap_servers,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            key_deserializer=lambda k: k.decode('utf-8') if k else None,
            group_id="issue-reader-group",
            auto_offset_reset='earliest'
        )
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(AgentManager.convert_datetime_to_string(v)).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None
        )
        await self.consumer.start()
        await self.producer.start()
        
        self.agent_manager = AgentManager()
        await self.agent_manager.initialize_agents()
        
        logger.info("Issue Reader Agent started successfully")

    async def stop(self):
        """Gracefully stop the Kafka clients."""
        if self.consumer:
            await self.consumer.stop()
        if self.producer:
            await self.producer.stop()
        if self.agent_manager and self.agent_manager.model_client:
            await self.agent_manager.model_client.close()
        logger.info("Issue Reader Agent stopped")

    async def process_issue_link(self, message_value: Dict[str, Any]) -> Dict[str, Any] | None:
        """
        Processes a single GitHub issue link by directly invoking the agent.
        """
        issue_link = message_value.get("issue_link")
        if not issue_link:
            logger.error(f"No 'issue_link' found in message: {message_value}")
            return None

        try:
            logger.info(f"Processing issue link: {issue_link}")

            issue_reader_agent = self.agent_manager.agents.get("issue_reader")

            if not issue_reader_agent:
                logger.error("The 'issue_reader' agent is not initialized.")
                return None

            # Use the helper to get a direct response from the agent.
            summary_content = await issue_reader_agent.run(task=f"Please use your tool to read the GitHub issue from the following link: {issue_link}.\
                                                           After reading, provide a structured summary containing key problem details,\
                                                           any error messages, and the user's environment, as per your instructions.")

            if not summary_content:
                logger.error(f"Agent failed to produce a summary for issue: {issue_link}")
                return None
            
            # extract title and bosy from the LLM response
            tool_execution_event = summary_content.messages[2]
            stringified_json_array = tool_execution_event.content[0].content
            parsed_list = json.loads(stringified_json_array)
            stringified_json_object = parsed_list[0]['text']
            issue_detail = json.loads(stringified_json_object)

            # 2. Extract the 'title' and 'body' from the final dictionary
            title = issue_detail.get('title')
            body = issue_detail.get('body')
            issue_summary = summary_content.messages[-1].content
            final_dict = {
                "title": title,
                "body": body,
                "ai_summary": issue_summary
            }

            output_message = {
                "issue_link": issue_link,
                "issue_summary": final_dict,
                "source_message": message_value,
                "processed_by": "IssueReaderAgent"
            }
            
            logger.info(f"Successfully summarized issue: {issue_link}")
            return output_message
            
        except Exception as e:
            logger.error(f"Error processing issue {issue_link}: {e}", exc_info=True)
            return None

    async def run(self):
        """Main loop to consume messages, process them, and produce results."""
        try:
            async for msg in self.consumer:
                logger.info(f"Received message on topic '{msg.topic}': key={msg.key} value={msg.value}")
                
                summary_payload = await self.process_issue_link(msg.value)
                # final_summary_text = summary_payload['issue_summary'].messages[-1].content

                kafka_message = {
                            "issue_link": summary_payload.get("issue_link"),
                            "issue_summary": summary_payload.get('issue_summary'),  # Use the clean string here
                            "source_message": summary_payload.get("source_message"),
                            "processed_by": summary_payload.get("processed_by")
                        }
                
                if summary_payload:
                    await self.producer.send_and_wait(
                        topic="issue-summaries",
                        value=kafka_message,
                        key=msg.key
                    )
                    logger.info(f"Sent issue summary to 'issue-summaries' for: {summary_payload['issue_link']}")
                else:
                    logger.error(f"Failed to process message with key {msg.key}, skipping.")
                    
        except Exception as e:
            logger.error(f"Critical error in run loop: {e}", exc_info=True)
            raise

async def main():
    """Main function to create and run the IssueReaderAgent."""
    agent = IssueReaderAgent(bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"))
    try:
        await agent.start()
        await agent.run()
    except KeyboardInterrupt:
        logger.info("Shutdown signal received.")
    finally:
        logger.info("Shutting down Issue Reader Agent...")
        await agent.stop()

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(main())