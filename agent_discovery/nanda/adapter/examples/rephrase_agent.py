#!/usr/bin/env python3
import os, requests
from dotenv import load_dotenv
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()
from nanda_utils.facts_provider import fetch_agent_facts
from nanda_adapter import NANDA

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b-instruct-fp16")

def rephrase_agent(message_text: str) -> str:
    try:
        # Ensure facts_provider reads the desired agent handle
        os.environ["LIST39_AGENT"] = os.getenv("REPHRASE_AGENT_HANDLE", "@rephrase_agent_fact")
        facts = fetch_agent_facts()

        prompt = "Rewrite the following to be clearer and more professional:\n\n"
        if facts:
            print("\n\n ACCESSING FACTS \n\n")
            prompt = (
                "You may use the following agent facts when helpful (do not invent facts).\n"
                + facts + "\n\n"
            )

            print(f"\n {prompt} \n\n")
        payload = {"model": OLLAMA_MODEL, "prompt": prompt + message_text, "stream": False}
        r = requests.post(f"{OLLAMA_HOST}/api/generate", json=payload, timeout=60)
        r.raise_for_status()
        return r.json().get("response", message_text)
        
    except Exception as e:
        print(f"[ollama] error: {e}; returning original text")
        return message_text

if __name__ == "__main__":
    nanda = NANDA(rephrase_agent)
    nanda.start_server_api(
        anthropic_key=os.getenv('ANTHROPIC_API_KEY', ''),
        domain=os.getenv('REPHRASE_DOMAIN', 'localhost'),
        agent_id=os.getenv('REPHRASE_AGENT_ID', 'rephrase_agent'),
        port=int(os.getenv('REPHRASE_PORT', '6000')),
        api_port=int(os.getenv('REPHRASE_API_PORT', '6001')),
        public_url=os.getenv('REPHRASE_PUBLIC_URL', 'http://localhost:6000'),
        api_url=os.getenv('REPHRASE_API_URL', 'http://localhost:6001'),
        ssl=os.getenv('SSL', 'false').lower() == 'true'
    )
