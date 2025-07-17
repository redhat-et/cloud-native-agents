# Memory Usage Guide

This guide explains how to use the ChromaDB memory system in the GitHub Issue Analyzer.

## Overview

The system uses ChromaDB to store conversation history, allowing agents to learn from previous interactions and provide more contextual responses.

## Memory Storage

### Automatic Storage
Memory is automatically stored for:
- **Regular Analysis**: When using `/issue_next_steps_analysis` endpoint
- **Auto Comment**: When using `/issue_next_steps_with_comment` endpoint  
- **HITL Conversations**: When using the WebSocket HITL endpoint

### What Gets Stored
- **User Query**: The GitHub issue URL
- **Agent Response**: 
`/issue_next_steps_analysis` endpoint: The final analysis 
`/issue_next_steps_with_comment` endpoint: comment content
`/ws/issue_next_steps_with_hitl_comment` endpoint: user edited comment
- **Metadata**: Endpoint, agent name, timestamp, session ID

## Memory Commands

### Display All Memory for current collection
```bash
cd backend
python memory.py display
```

### Collection Management
```bash
# List all collections
python memory.py list

# Create a new collection
CHROMADB_COLLECTION=collection_name python memory.py create

# Delete a collection
CHROMADB_COLLECTION=collection_name python memory.py delete

# Clear all data in a collection
CHROMADB_COLLECTION=collection_namepython memory.py clear

# Reload memory connection, update chrombd collection with agent
python memory.py reload
```

## Environment Variables

Make sure these are set in your `.env` file:
```bash
CHROMADB_URL=https://your-chromadb-instance.com
CHROMADB_COLLECTION=issue_analyzer_memory
```
Make sure this collection is created before running agent scripts.

## Example Memory Entry

```
📄 Document ID: abc123-def456
Content: User Query: https://github.com/user/repo/issues/123
Agent Response: Here's my analysis of the issue...

Metadata:
- endpoint: issue_next_steps_analysis
- agent: reasoner
- timestamp: 2025-07-14T12:00:00
- session_id: session_20250714_120000
```

## Troubleshooting

### Memory Not Storing
1. Check ChromaDB connection: `python memory.py display`
2. Verify environment variables are set
3. Check backend logs for memory errors

### Connection Issues
1. Ensure ChromaDB instance is running
2. Verify `CHROMADB_URL` is correct
3. Check network connectivity

### Collection Issues
1. List collections: `python memory.py list`
2. Create collection if missing: `python memory.py create issue_analyzer_memory`
3. Reload connection: `python memory.py reload`

## Benefits

- **Contextual Responses**: Agents can reference previous similar issues
- **Learning**: System improves over time with more data
- **Consistency**: Similar issues get similar treatment
- **Audit Trail**: Track all interactions and decisions 