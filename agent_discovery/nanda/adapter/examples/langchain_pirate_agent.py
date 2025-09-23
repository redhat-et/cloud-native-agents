#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from typing import Optional

from nanda_adapter import NANDA
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from langchain_ollama import ChatOllama  # type: ignore

def langchain_pirate_agent() -> Optional[callable]:

    load_dotenv()
    ollama_host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2:3b-instruct-fp16")

    llm = ChatOllama(model=ollama_model, base_url=ollama_host, temperature=0.2)

    system_text = (
        """Rewrite the input to sound like a pirate. Use pirate vocabulary,
        grammar, and expressions like 'ahoy', 'matey', 'ye', 'arrr', etc."""
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_text),
        ("human", "Original message:\n{message}\n\nRewrite:"),
    ])

    chain = prompt | llm | StrOutputParser()

    def improve(message_text: str) -> str:
        try:
            return chain.invoke({"message": message_text}).strip()
        except Exception as exc:
            print(f"[langchain_ollama] error: {exc}; returning original text")
            return message_text

    return improve


def main() -> None:
    """Run a NANDA server that uses LangChain+Ollama for rewriting."""

    nanda = NANDA(langchain_pirate_agent())
    nanda.start_server_api(
        anthropic_key=os.getenv('ANTHROPIC_API_KEY', ''),
        domain='localhost',
        agent_id=os.getenv('LANGCHAIN_AGENT_ID', 'langchain_agent'),
        port=int(os.getenv('LANGCHAIN_AGENT_PORT', '6010')),
        api_port=int(os.getenv('LANGCHAIN_AGENT_API_PORT', '6011')),
        public_url=os.getenv('LANGCHAIN_AGENT_PUBLIC_URL', 'http://localhost:6010'),
        api_url=os.getenv('LANGCHAIN_AGENT_API_URL', 'http://localhost:6011'),
        ssl=os.getenv('SSL', 'false').lower() == 'true'
    )


if __name__ == "__main__":
    main()


