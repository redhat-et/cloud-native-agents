#!/bin/bash

# Delete existing topics if they exist
/opt/homebrew/bin/kafka-topics --bootstrap-server localhost:9092 --delete --topic github-issue-links
/opt/homebrew/bin/kafka-topics --bootstrap-server localhost:9092 --delete --topic issue-summaries
/opt/homebrew/bin/kafka-topics --bootstrap-server localhost:9092 --delete --topic research-findings
/opt/homebrew/bin/kafka-topics --bootstrap-server localhost:9092 --delete --topic drafted-comments
/opt/homebrew/bin/kafka-topics --bootstrap-server localhost:9092 --delete --topic approved-comments
/opt/homebrew/bin/kafka-topics --bootstrap-server localhost:9092 --delete --topic completed-tasks

# Create new topics for the workflow
/opt/homebrew/bin/kafka-topics --bootstrap-server localhost:9092 --create --topic github-issue-links --partitions 1 --replication-factor 1
/opt/homebrew/bin/kafka-topics --bootstrap-server localhost:9092 --create --topic issue-summaries --partitions 1 --replication-factor 1
/opt/homebrew/bin/kafka-topics --bootstrap-server localhost:9092 --create --topic research-findings --partitions 1 --replication-factor 1
/opt/homebrew/bin/kafka-topics --bootstrap-server localhost:9092 --create --topic drafted-comments --partitions 1 --replication-factor 1
/opt/homebrew/bin/kafka-topics --bootstrap-server localhost:9092 --create --topic approved-comments --partitions 1 --replication-factor 1
/opt/homebrew/bin/kafka-topics --bootstrap-server localhost:9092 --create --topic completed-tasks --partitions 1 --replication-factor 1

echo "Kafka topics created successfully for GitHub issue workflow!" 