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
GITHUB_MCP_URL = "https://api.githubcopilot.com/mcp/"
```

### 3. Run the UI
```bash
python launch_kafka_system.py
```

This gives you an interactive interface to:
1. Enter GitHub issue URLs
2. See analysis step-by-step
3. Review generated comments
4. Post comments to GitHub

## 🎉 Features

- **Issue Analysis** - Extract details from GitHub issues
- **Web Research** - Find related solutions and documentation
- **AI Comment Generation** - Create helpful, actionable comments
- **Direct Posting** - Post comments directly to GitHub
- **Interactive UI** - Easy-to-use command-line interface

## 📝 License

MIT License 