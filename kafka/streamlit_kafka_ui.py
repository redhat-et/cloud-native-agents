#!/usr/bin/env python3
"""
Streamlit UI for Kafka Multi-Agent System
Integrates with Kafka topics for distributed processing using a background
asyncio event loop for stable connections.
"""

import streamlit as st
import asyncio
import json
import pandas as pd
from datetime import datetime
import aiokafka
from aiokafka.structs import TopicPartition # <-- IMPORT THE FIX
from typing import Dict, Any, List
import logging
from threading import Thread
from concurrent.futures import Future

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title="Kafka Multi-Agent System",
    layout="wide",
    initial_sidebar_state="expanded"
)

class KafkaManager:
    """
    Manages a background asyncio event loop and Kafka clients for Streamlit.
    """
    def __init__(self, bootstrap_servers: str):
        self.bootstrap_servers = bootstrap_servers
        self._loop = asyncio.new_event_loop()
        self._thread = Thread(target=self._run_loop, daemon=True)
        self._producer = None
        self._thread.start()

    def _run_loop(self):
        """Runs the event loop in the background thread."""
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    async def _get_producer(self):
        """Initializes and returns the singleton AIOKafkaProducer."""
        if self._producer is None:
            logger.info("Initializing Kafka producer...")
            self._producer = aiokafka.AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None
            )
            await self._producer.start()
            logger.info("Kafka producer initialized successfully.")
        return self._producer

    async def _send_message(self, topic: str, value: Dict, key: str):
        """Coroutine to send a single message."""
        producer = await self._get_producer()
        await producer.send_and_wait(topic=topic, value=value, key=key)
        logger.info(f"Message sent to topic '{topic}' with key '{key}'")

    def submit_message(self, topic: str, value: Dict, key: str) -> Future:
        """
        Submits a message-sending task to the event loop from an external thread.
        """
        return asyncio.run_coroutine_threadsafe(
            self._send_message(topic, value, key), self._loop
        )

    async def _fetch_messages(self, topic: str, group_id: str, max_messages: int) -> List[Dict]:
        """Coroutine to fetch recent messages from a topic without blocking indefinitely."""
        consumer = aiokafka.AIOKafkaConsumer(
            topic,
            bootstrap_servers=self.bootstrap_servers,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            key_deserializer=lambda k: k.decode('utf-8') if k else None,
            group_id=group_id,
            auto_offset_reset='earliest'
        )
        await consumer.start()
        messages = []
        try:
            partition_numbers = consumer.partitions_for_topic(topic)
            if not partition_numbers:
                logger.warning(f"No partitions found for topic {topic}")
                return []

            topic_partitions = [TopicPartition(topic, p) for p in partition_numbers]

            end_offsets = await consumer.end_offsets(topic_partitions)

            while True:
                batch = await consumer.getmany(timeout_ms=1000)
                if not batch:
                    break
                
                for tp, msgs in batch.items():
                    for msg in msgs:
                        messages.append({
                            "topic": msg.topic,
                            "key": msg.key,
                            "value": msg.value,
                            "timestamp": datetime.fromtimestamp(msg.timestamp / 1000).isoformat()
                        })
                
                # Define an async helper function to check all partition positions
                async def all_partitions_at_end(consumer, partitions, offsets):
                    for p in partitions:
                        # await the position for each partition
                        current_position = await consumer.position(p)
                        if current_position < offsets[p]:
                            return False
                    return True

                # Use the helper function in your if condition
                if len(messages) >= max_messages or await all_partitions_at_end(consumer, topic_partitions, end_offsets):
                    # Now this will work as expected
                    break
                # if len(messages) >= max_messages or all(consumer.position(p) >= end_offsets[p] for p in topic_partitions):
                #     break
        finally:
            await consumer.stop()
            logger.info(f"Fetched {len(messages)} messages from {topic} and stopped consumer.")
        
        return sorted(messages, key=lambda x: x['timestamp'], reverse=True)[:max_messages]


    def monitor_topic(self, topic: str, group_id: str, max_messages: int = 10) -> List[Dict]:
        """
        Submits a message-fetching task to the event loop.
        Blocks until the result is available.
        """
        future = asyncio.run_coroutine_threadsafe(
            self._fetch_messages(topic, group_id, max_messages), self._loop
        )
        return future.result(timeout=15)

@st.cache_resource
def get_kafka_manager(bootstrap_servers: str) -> KafkaManager:
    """Caches the KafkaManager instance for the Streamlit session."""
    logger.info(f"Creating and caching new KafkaManager for {bootstrap_servers}")
    return KafkaManager(bootstrap_servers)

def main():
    st.title("Kafka Multi-Agent System")
    st.markdown("---")

    with st.sidebar:
        st.header("⚙️ Configuration")
        kafka_host = st.text_input("Kafka Server", value="localhost:9092", key="kafka_host")
        
        try:
            kafka_manager = get_kafka_manager(kafka_host)
            st.success("✅ Kafka Manager is running.")
        except Exception as e:
            st.error(f"❌ Failed to initialize Kafka Manager: {e}")
            st.stop()

        st.subheader("📊 Topic Monitor")
        monitor_topic = st.selectbox(
            "Select topic to monitor",
            ["github-issue-links", "issue-summaries", "research-findings",
             "drafted-comments", "approved-comments", "completed-tasks"]
        )

        if st.button("Refresh Topic"):
            with st.spinner(f"Fetching messages from {monitor_topic}..."):
                try:
                    group_id = f"streamlit-monitor-{monitor_topic}-{datetime.now().timestamp()}"
                    messages = kafka_manager.monitor_topic(monitor_topic, group_id)
                    st.session_state[f"topic_messages_{monitor_topic}"] = messages
                    st.success(f"✅ Retrieved {len(messages)} messages.")
                except Exception as e:
                    st.error(f"Failed to fetch messages: {e}")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.header("📋 Issue Submission")
        st.subheader("➕ Submit New Issue")
        new_issue = st.text_input("GitHub Issue URL", placeholder="https://github.com/owner/repo/issues/123")

        if new_issue:
            action = st.selectbox(
                "Select Action",
                ["analyze", "comment", "review"],
                help="analyze: Full analysis workflow, comment: Direct comment posting, review: Analysis with human review"
            )

            if st.button("🚀 Submit to Kafka"):
                message = {
                    "issue_link": new_issue,
                    "action": action,
                    "timestamp": datetime.now().isoformat(),
                    "source": "streamlit_ui"
                }
                try:
                    future = kafka_manager.submit_message(
                        topic="github-issue-links",
                        value=message,
                        key=new_issue
                    )
                    future.result(timeout=10)
                    st.success("✅ Issue submitted to Kafka successfully!")

                    if "submitted_issues" not in st.session_state:
                        st.session_state.submitted_issues = []
                    st.session_state.submitted_issues.append({
                        "url": new_issue, "action": action, "timestamp": datetime.now(),
                        "status": "submitted"
                    })
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Failed to submit issue to Kafka: {e}")

    with col2:
        st.header("📊 System Status")
        if "submitted_issues" in st.session_state:
            total_submitted = len(st.session_state.submitted_issues)
            st.metric("Submitted Issues", total_submitted)
            actions = { "analyze": 0, "comment": 0, "review": 0 }
            for issue in st.session_state.submitted_issues:
                action = issue["action"]
                if action in actions:
                    actions[action] += 1
            for action, count in actions.items():
                st.metric(f"{action.title()} Issues", count)
        else:
            st.info("No issues submitted yet.")

    if "submitted_issues" in st.session_state and st.session_state.submitted_issues:
        st.header("📋 Submitted Issues Log")
        df_data = [{
            "URL": issue["url"], "Action": issue["action"], "Status": issue["status"],
            "Timestamp": issue["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
        } for issue in st.session_state.submitted_issues]
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True)

    if f"topic_messages_{monitor_topic}" in st.session_state:
        st.header(f"📊 Topic Inspector: {monitor_topic}")
        messages = st.session_state[f"topic_messages_{monitor_topic}"]
        if messages:
            for i, msg in enumerate(messages):
                with st.expander(f"Message {i+1} - Key: {msg['key']} @ {msg['timestamp']}"):
                    st.json(msg["value"])
        else:
            st.info(f"No recent messages found in {monitor_topic}")

    if st.sidebar.button("🗑️ Clear All Data"):
        for key in list(st.session_state.keys()):
            if "submitted_issues" in key or "topic_messages_" in key:
                del st.session_state[key]
        st.success("All session data cleared!")
        st.rerun()

if __name__ == "__main__":
    main()
