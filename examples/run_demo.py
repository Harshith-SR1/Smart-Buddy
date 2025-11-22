"""Small demo runner showing use of Router and agents."""

from smart_buddy.agents import RouterAgent
from smart_buddy.llm import LLM
from smart_buddy.memory import MemoryBank


def main():
    # create a shared MemoryBank file for demo persistence
    mem = MemoryBank(db_path="smart_buddy_memory.db")
    router = RouterAgent(memory=mem)
    llm = LLM()

    examples = [
        ("u1", "s1", "Add task: buy groceries tomorrow"),
        ("u1", "s1", "Create a 3-month roadmap to learn backend development"),
        ("u2", "s2", "I feel lonely and stressed lately"),
    ]

    for user, session, text in examples:
        out = router.route(user, session, text)
        print("---")
        print("Input:", text)
        print("Envelope:", out["envelope"])
        print("Result:", out["result"])
        # demonstrate LLM stub/gemini call
        resp = llm.generate(f"Respond to: {text}")
        print("LLM sample reply:", resp)

    # close memory connection when done
    try:
        mem.close()
    except Exception:
        pass


if __name__ == "__main__":
    main()
