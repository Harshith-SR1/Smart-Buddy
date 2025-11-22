"""ADK-style Agent wrapper integrating existing Smart Buddy RouterAgent.

Fallback implementation since `adk init` failed due to dependency import issues.

Run locally (no ADK CLI required):
  python main.py "your message here"

If ADK CLI later works, the `agent.json` provides minimal metadata.
"""
from typing import Any, Dict
import sys

from smart_buddy.agents.router import RouterAgent
from smart_buddy.memory import MemoryBank

class SmartBuddyAgent:
    def __init__(self):
        self.memory = MemoryBank()
        self.router = RouterAgent(memory=self.memory)

    def run(self, user_input: str, user_id: str = "user", session_id: str = "adk_session") -> Dict[str, Any]:
        routed = self.router.route(user_id, session_id, user_input)
        return routed


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py \"your message\"")
        sys.exit(1)
    message = sys.argv[1]
    agent = SmartBuddyAgent()
    result = agent.run(message)
    reply = result.get("result", {}).get("reply")
    print(f"Agent Reply: {reply}")
    print(f"Trace ID: {result.get('envelope', {}).get('meta', {}).get('trace_id')}")

if __name__ == "__main__":
    main()
