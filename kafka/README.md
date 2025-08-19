# Kafka Multi-Agent System

A comprehensive Kafka-based multi-agent system that analyzes GitHub issues, performs research, and generates helpful comments using AI. The system includes a Streamlit UI and can be deployed to OpenShift clusters.

## 🏗️ Architecture

The system consists of multiple specialized agents working together through Kafka topics:

- **Issue Reader Agent** - Fetches and analyzes GitHub issues
- **Researcher Agent** - Performs web research on issues
- **Reasoner Agent** - Generates intelligent comment drafts
- **Commenter Agent** - Posts approved comments to GitHub
- **Monitor Agent** - Tracks system performance and metrics
- **UI Consumer** - Provides real-time monitoring interface

## 🚀 Quick Start

### Local Development

#### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 2. Set Up Environment
Create a `.env` file:
```env
OPENAI_API_KEY=your_openai_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
GITHUB_PAT=your_github_personal_access_token_here
GITHUB_MCP_URL=https://api.githubcopilot.com/mcp/
```

#### 3. Run the System
```bash
python launch_kafka_system.py
```

This will:
- Start all Kafka agents
- Launch the Streamlit UI at http://localhost:8501
- Create necessary Kafka topics
- Begin processing GitHub issues
