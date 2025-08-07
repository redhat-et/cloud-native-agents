#!/usr/bin/env python3
"""
Comprehensive launcher for the Kafka Multi-Agent System
Starts all agents and the Streamlit UI.
"""

import subprocess
import sys
import os
import time
import signal
import threading
from typing import List

class KafkaSystemLauncher:
    def __init__(self):
        self.processes = []
        self.agent_scripts = [
            "issue_reader_agent.py",
            "researcher_agent.py", 
            "reasoner_agent.py",
            "commenter_agent.py",
            "ui_consumer.py",
            "monitor_consumer.py"
        ]
        
    def check_kafka_running(self) -> bool:
        """Check if Kafka is running."""
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', 9092))
            sock.close()
            return result == 0
        except:
            return False
    
    def check_topics_exist(self) -> bool:
        """Check if Kafka topics exist."""
        try:
            # Try to create topics (this will fail if they already exist, which is fine)
            result = subprocess.run([
                "/opt/homebrew/bin/kafka-topics", 
                "--bootstrap-server", "localhost:9092",
                "--list"
            ], capture_output=True, text=True)
            return "github-issue-links" in result.stdout
        except:
            return False
    
    def create_topics(self):
        """Create Kafka topics."""
        print("📋 Creating Kafka topics...")
        try:
            subprocess.run(["bash", "kafka_topics.sh"], check=True)
            print("✅ Kafka topics created successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create topics: {e}")
            return False
        return True
    
    def start_agents(self):
        """Start all Kafka agents."""
        print("🤖 Starting Kafka agents...")
        print("=" * 50)
        
        for script in self.agent_scripts:
            if os.path.exists(script):
                print(f"Starting {script}...")
                process = subprocess.Popen([sys.executable, script])
                self.processes.append(process)
                print(f"✅ Started {script} with PID: {process.pid}")
                time.sleep(2)  # Delay between starts
            else:
                print(f"⚠️  Warning: {script} not found!")
        
        print(f"\n✅ Started {len(self.processes)} agents")
        print("=" * 50)
    
    def start_streamlit(self):
        """Start the Streamlit UI."""
        print("🌐 Starting Streamlit UI...")
        try:
            # Start Streamlit in a separate thread
            def run_streamlit():
                subprocess.run([
                    sys.executable, "-m", "streamlit", "run", "streamlit_kafka_ui.py",
                    "--server.port", "8501",
                    "--server.headless", "true"
                ])
            
            streamlit_thread = threading.Thread(target=run_streamlit, daemon=True)
            streamlit_thread.start()
            
            print("✅ Streamlit UI started at http://localhost:8501")
            return True
        except Exception as e:
            print(f"❌ Failed to start Streamlit: {e}")
            return False
    
    def stop_all(self):
        """Stop all processes."""
        print("\n🛑 Stopping all processes...")
        
        # Stop agents
        for process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
                print(f"✅ Stopped process {process.pid}")
            except subprocess.TimeoutExpired:
                print(f"⚠️  Force killing process {process.pid}")
                process.kill()
            except Exception as e:
                print(f"❌ Error stopping process {process.pid}: {e}")
        
        print("✅ All processes stopped")
    
    def signal_handler(self, signum, frame):
        """Handle interrupt signal."""
        print(f"\n🛑 Received signal {signum}. Shutting down...")
        self.stop_all()
        sys.exit(0)
    
    def run(self):
        """Main run method."""
        print("🚀 Kafka Multi-Agent System Launcher")
        print("=" * 50)
        
        # Check prerequisites
        print("🔍 Checking prerequisites...")
        
        # Check Kafka
        if not self.check_kafka_running():
            print("❌ Kafka is not running!")
            print("Please start Kafka first:")
            print("  docker run -p 9092:9092 apache/kafka:2.13-3.6.1")
            print("  or")
            print("  brew services start kafka")
            return
        
        print("✅ Kafka is running")
        
        # Check topics
        if not self.check_topics_exist():
            print("📋 Creating Kafka topics...")
            if not self.create_topics():
                print("❌ Failed to create topics")
                return
        else:
            print("✅ Kafka topics exist")
        
        # Check dependencies
        print("📦 Checking dependencies...")
        try:
            import streamlit
            import aiokafka
            import pandas
            print("✅ All dependencies are installed")
        except ImportError as e:
            print(f"❌ Missing dependency: {e}")
            print("Please install dependencies:")
            print("  pip install -r requirements_minimal.txt")
            return
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        try:
            # Start agents
            self.start_agents()
            
            # Start Streamlit
            self.start_streamlit()
            
            print("\n🎉 System is running!")
            print("=" * 50)
            print("📊 Streamlit UI: http://localhost:8501")
            print("🔗 Kafka: localhost:9092")
            print("🤖 Agents: Running in background")
            print("\nPress Ctrl+C to stop all services")
            print("=" * 50)
            
            # Keep running
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n🛑 Received keyboard interrupt")
        finally:
            self.stop_all()

def main():
    """Main function."""
    launcher = KafkaSystemLauncher()
    launcher.run()

if __name__ == "__main__":
    main() 