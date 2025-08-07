# GitHub Issue Analysis System

A simple system that analyzes GitHub issues and generates helpful comments using AI.

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Up Environment
Create a `.env` file:
```env
OPENAI_API_KEY=your_openai_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
GITHUB_PAT=your_github_personal_access_token_here
```

### 3. Run the UI
```bash
python launch_kafka_system.py
```

## 📁 Files

### Core Files
- `simple_agents.py` - Core agent functionality
- `simple_ui.py` - Interactive UI for testing
- `simple_issue_reader_agent.py` - Kafka agent (if using Kafka)

### Dependencies
- `requirements_minimal.txt` - Minimal dependencies
- `requirements.txt` - Full dependencies with autogen

### Original System (Kafka-based)
- `agents.py` - Original agent manager
- `issue_reader_agent.py` - Issue reader agent
- `researcher_agent.py` - Research agent
- `reasoner_agent.py` - Comment generation agent
- `commenter_agent.py` - Comment posting agent
- `ui_consumer.py` - UI for human review
- `monitor_consumer.py` - Monitoring agent
- `kafka_producer.py` - Kafka producer
- `kafka_topics.sh` - Kafka topic setup

## 🎯 Usage

### Simple UI (Recommended)
```bash
python simple_ui.py
```

This gives you an interactive interface to:
1. Enter GitHub issue URLs
2. See analysis step-by-step
3. Review generated comments
4. Post comments to GitHub

### Example
```
GitHub Issue Analysis System
==================================================

Options:
1. Analyze a GitHub issue
2. Post a comment to GitHub
3. Exit

Enter your choice (1-3): 1

Enter GitHub issue URL: https://github.com/example/repo/issues/123

🔍 Step 1: Fetching issue details...
✓ Issue: Some bug title
✓ State: open

🔍 Step 2: Researching related solutions...
✓ Found 3 research results

🤖 Step 3: Generating helpful comment...

================================================================================
GENERATED COMMENT
================================================================================
[AI-generated helpful comment here]
================================================================================

Do you want to post this comment? (y/n): y
✓ Comment posted successfully!
```

## 🔧 Requirements

### API Keys
- **OpenAI API Key** - Required for comment generation
- **Tavily API Key** - Optional for web research
- **GitHub PAT** - Optional for posting comments

### Python Dependencies
- `aiokafka` - Kafka client
- `openai` - OpenAI API
- `aiohttp` - Async HTTP client
- `python-dotenv` - Environment variables
- `pydantic` - Data validation
- `tavily-python` - Web search

## 🎉 Features

- **Issue Analysis** - Extract details from GitHub issues
- **Web Research** - Find related solutions and documentation
- **AI Comment Generation** - Create helpful, actionable comments
- **Direct Posting** - Post comments directly to GitHub
- **Interactive UI** - Easy-to-use command-line interface

## 📝 License

MIT License 