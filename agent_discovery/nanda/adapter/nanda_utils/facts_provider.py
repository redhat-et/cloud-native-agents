import os
import json
from typing import List
import requests

def fetch_agent_facts() -> str:
    """Return agent facts text fetched from a List39 registry.

    Environment variables:
    - LIST39_AGENT: agent handle, with or without leading '@' (e.g. '@rephrase_agent_fact' or 'rephrase_agent_fact')
    - LIST39_BASE: base URL for List39 (default 'https://list39.org')
    """
    agent_handle = os.getenv("LIST39_AGENT", "").strip()
    if not agent_handle:
        return ""

    fact_registry_base_url = "https://list39.org"

    agent_path = agent_handle if agent_handle.startswith("@") else f"@{agent_handle}"
    url = f"{fact_registry_base_url}/{agent_path}.json"

    parts: List[str] = []
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        body_text = resp.text or ""
        parts.append(body_text)
    except Exception as exc:
        print(f"[facts_provider] Failed to fetch facts from {url}: {exc}")

    return ("\n\n".join(p for p in parts if p).strip())


