#!/usr/bin/env python3
"""
Streamlit UI for Kafka Multi-Agent System with real-time, auto-updating
workflow visualization for all 6 stages.
"""

import streamlit as st
import asyncio
import json
import time
from datetime import datetime
import aiokafka
from typing import Dict, Any
import logging
from threading import Thread
from concurrent.futures import Future
from queue import Queue, Empty

# --- Basic Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Kafka Multi-Agent System",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Real-Time Kafka Manager ---
class KafkaManager:
    """
    Manages a background asyncio event loop and Kafka clients,
    including long-running consumers for real-time updates.
    """
    def __init__(self, bootstrap_servers: str):
        self.bootstrap_servers = bootstrap_servers
        self._loop = asyncio.new_event_loop()
        self._thread = Thread(target=self._run_loop, daemon=True)
        self._producer = None
        # Queues for each stage of the workflow for the UI to read from
        self.message_queues = {
            "issue-summaries": Queue(),
            "research-findings": Queue(),
            "drafted-comments": Queue(),
            "approved-comments": Queue(), # Added for approval tracking
            "completed-tasks": Queue()
        }
        self._thread.start()
        # Start the consumers in the background thread
        asyncio.run_coroutine_threadsafe(self._start_consumers(), self._loop)

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    async def _get_producer(self):
        if self._producer is None:
            self._producer = aiokafka.AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None
            )
            await self._producer.start()
        return self._producer

    async def _send_message(self, topic: str, value: Dict, key: str):
        producer = await self._get_producer()
        await producer.send_and_wait(topic=topic, value=value, key=key)

    def submit_message(self, topic: str, value: Dict, key: str) -> Future:
        return asyncio.run_coroutine_threadsafe(
            self._send_message(topic, value, key), self._loop
        )

    async def _run_consumer(self, topic: str, group_id: str, queue: Queue):
        """A long-running consumer that puts messages into a thread-safe queue."""
        consumer = aiokafka.AIOKafkaConsumer(
            topic,
            bootstrap_servers=self.bootstrap_servers,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            group_id=group_id,
            auto_offset_reset='latest' # Only process new messages
        )
        await consumer.start()
        try:
            async for message in consumer:
                logger.info(f"Real-time consumer got message from {topic}")
                queue.put(message.value)
        finally:
            await consumer.stop()

    async def _start_consumers(self):
        """Starts all the consumers that will run in the background."""
        tasks = []
        for topic, queue in self.message_queues.items():
            group_id = f"st-dashboard-consumer-{topic}"
            task = self._loop.create_task(self._run_consumer(topic, group_id, queue))
            tasks.append(task)
        logger.info("All real-time consumers have been started.")

    def get_message_from_queue(self, topic: str) -> Dict | None:
        """Non-blocking method to get a message from a queue."""
        try:
            return self.message_queues[topic].get_nowait()
        except Empty:
            return None

@st.cache_resource
def get_kafka_manager(bootstrap_servers: str) -> KafkaManager:
    return KafkaManager(bootstrap_servers)

# --- UI Rendering Functions ---
def display_workflow_card(title: str, state: Dict):
    """Renders a card for a single stage of the workflow."""
    with st.container(border=True):
        st.subheader(title)
        st.markdown(f"**Status:** {state['status']}")
        if state.get('content'):
            st.json(state['content'], expanded=False)

def display_review_card(kafka_manager: KafkaManager, key: str, state: Dict):
    """Renders the special card for human-in-the-loop review."""
    with st.container(border=True):
        st.subheader("4. Reasoner & Human-in-the-Loop")
        st.markdown(f"**Status:** {state['status']}")
        draft_message = state.get('content', {})
        with st.form(key=f"review_form_{key}"):
            st.markdown(f"**Issue:** `{draft_message.get('issue_link')}`")
            comment_text = st.text_area(
                "Drafted Comment (edit if needed):",
                value=draft_message.get("drafted_comment", ""),
                height=250
            )
            if st.form_submit_button("✅ Approve and Send"):
                approved_message = {
                    "issue_link": draft_message.get("issue_link"),
                    "comment_text": comment_text,
                    "timestamp": datetime.now().isoformat(),
                    "metadata": draft_message.get("metadata", {}),
                    "agent": "human_reviewer_ui"
                }
                try:
                    future = kafka_manager.submit_message(
                        "approved-comments",
                        approved_message,
                        draft_message.get("issue_link")
                    )
                    future.result(timeout=10)
                    st.success("Approval sent!")
                    st.session_state.workflows[key]['reasoner']['status'] = "✅ Approved"
                    st.session_state.workflows[key]['approver']['status'] = "⏳ Processing..."
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to send approval: {e}")

# --- Main App ---
def main():
    st.title("🚀 Real-Time Multi-Agent Workflow")

    if 'workflows' not in st.session_state:
        st.session_state.workflows = {}

    kafka_manager = get_kafka_manager("localhost:9092")

    with st.form("submission_form"):
        issue_link = st.text_input("Enter a GitHub Issue Link", placeholder="https://github.com/owner/repo/issues/123")
        submitted = st.form_submit_button("Start Analysis")
        if submitted and issue_link:
            message = {"issue_link": issue_link, "action": "review", "timestamp": datetime.now().isoformat()}
            st.session_state.workflows[issue_link] = {
                "submission": {"status": "✅ Submitted to `github-issue-links`", "content": message},
                "issue_reader": {"status": "⏳ Waiting for submission...", "content": None},
                "researcher": {"status": "⚪ Waiting for summary...", "content": None},
                "reasoner": {"status": "⚪ Waiting for research...", "content": None},
                "approver": {"status": "⚪ Waiting for draft...", "content": None},
                "commenter": {"status": "⚪ Waiting for approval...", "content": None},
            }
            kafka_manager.submit_message("github-issue-links", message, issue_link)
            st.success(f"Workflow started for: {issue_link}")

    st.markdown("---")

    if not st.session_state.workflows:
        st.info("Submit a GitHub issue link above to start a workflow.")
    else:
        # Check queues for updates from each agent
        summary_msg = kafka_manager.get_message_from_queue("issue-summaries")
        if summary_msg and summary_msg.get("issue_link") in st.session_state.workflows:
            key = summary_msg["issue_link"]
            st.session_state.workflows[key]['issue_reader'] = {"status": "✅ Done", "content": summary_msg}
            st.session_state.workflows[key]['researcher']['status'] = "⏳ Processing..."

        research_msg = kafka_manager.get_message_from_queue("research-findings")
        if research_msg and research_msg.get("issue_link") in st.session_state.workflows:
            key = research_msg["issue_link"]
            st.session_state.workflows[key]['researcher'] = {"status": "✅ Done", "content": research_msg}
            st.session_state.workflows[key]['reasoner']['status'] = "⏳ Processing..."

        draft_msg = kafka_manager.get_message_from_queue("drafted-comments")
        if draft_msg and draft_msg.get("issue_link") in st.session_state.workflows:
            key = draft_msg["issue_link"]
            st.session_state.workflows[key]['reasoner'] = {"status": "📝 Awaiting Review", "content": draft_msg}

        approved_msg = kafka_manager.get_message_from_queue("approved-comments")
        if approved_msg and approved_msg.get("issue_link") in st.session_state.workflows:
            key = approved_msg["issue_link"]
            st.session_state.workflows[key]['approver'] = {"status": "✅ Approved by Human", "content": approved_msg}
            st.session_state.workflows[key]['commenter']['status'] = "⏳ Processing..."

        completed_msg = kafka_manager.get_message_from_queue("completed-tasks")
        if completed_msg and completed_msg.get("issue_link") in st.session_state.workflows:
            key = completed_msg["issue_link"]
            st.session_state.workflows[key]['commenter'] = {"status": f"✅ Done - {completed_msg.get('status')}", "content": completed_msg}

        # Display the workflows in a 3x2 grid
        for key, workflow in st.session_state.workflows.items():
            st.subheader(f"Workflow for: `{key}`")
            col1, col2, col3 = st.columns(3)
            with col1:
                display_workflow_card("1. UI Submission", workflow["submission"])
                if workflow["reasoner"]["status"] == "📝 Awaiting Review":
                    display_review_card(kafka_manager, key, workflow["reasoner"])
                else:
                    display_workflow_card("4. Reasoner", workflow["reasoner"])
            with col2:
                display_workflow_card("2. Issue Reader", workflow["issue_reader"])
                display_workflow_card("5. UI Consumer (Approval)", workflow["approver"])
            with col3:
                display_workflow_card("3. Researcher", workflow["researcher"])
                display_workflow_card("6. Commenter", workflow["commenter"])
            st.markdown("---")

    # Auto-refresh loop
    time.sleep(1)
    st.rerun()

if __name__ == "__main__":
    main()
