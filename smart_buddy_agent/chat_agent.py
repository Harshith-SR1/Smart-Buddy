"""Interactive chat interface for Smart Buddy Agent.

Run this for continuous conversation with your multi-agent assistant.
Type 'quit' or 'exit' to end the session.
"""
import sys
import os

# Add parent directory to path so we can import smart_buddy modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from smart_buddy.agents.router import RouterAgent
from smart_buddy.agents.general_agent import GeneralAgent
from smart_buddy.agents.mentor import MentorAgent
from smart_buddy.agents.bestfriend import BestFriendAgent
from smart_buddy.memory import MemoryBank


def print_banner():
    print("\n" + "="*70)
    print("  🤖 SMART BUDDY - Interactive Chat")
    print("  Multi-Agent AI Assistant powered by Google Gemini 2.5 Flash")
    print("="*70 + "\n")


def display_modes():
    """Display available modes"""
    print("\n" + "=" * 70)
    print("  SMART BUDDY MODES")
    print("=" * 70)
    print("\n1. 🤖 GENERAL MODE - Your AI Assistant (like ChatGPT)")
    print("   • Answer questions, manage calendar & todos")
    print("   • Example: 'Schedule gym tomorrow 6pm' or 'Explain AI'")
    print("\n2. 🎓 MENTOR MODE - Your AI Teacher & Guide")
    print("   • Teaching, advice, planning, problem-solving, feedback")
    print("   • Example: 'Explain quantum physics' or 'Career advice'")
    print("\n3. 💕 BESTFRIEND MODE - Chat with your virtual bestie!")
    print("   • Casual, fun conversations with emojis & support")
    print("   • Example: 'I got a promotion!' or 'feeling down today'")
    print("\n4. 🔄 AUTO MODE - Smart routing (automatically picks best mode)")
    print("   • Let Smart Buddy decide which mode fits your message")
    print("\n" + "=" * 70)


def select_mode():
    """Let user select a mode"""
    while True:
        print("\nSelect a mode (1-4) or 'q' to quit:")
        choice = input("Your choice: ").strip().lower()
        
        if choice == 'q':
            return None
        elif choice == '1':
            return 'general'
        elif choice == '2':
            return 'mentor'
        elif choice == '3':
            return 'bestfriend'
        elif choice == '4':
            return 'auto'
        else:
            print("❌ Invalid choice. Please enter 1, 2, 3, 4, or 'q'")


def main():
    print_banner()
    
    # Initialize memory and agents
    memory = MemoryBank()
    router = RouterAgent(memory=memory)
    general_agent = GeneralAgent(memory=memory)
    mentor_agent = MentorAgent(memory=memory)
    bestfriend_agent = BestFriendAgent()
    
    # Get user name
    user_id = input("👤 Enter your name (or press Enter for 'User'): ").strip() or "User"
    session_id = "interactive_chat"
    
    print(f"\n✨ Hello {user_id}! Welcome to Smart Buddy!")
    
    # Mode selection
    current_mode = None
    
    # Mode selection
    current_mode = None
    message_count = 0
    
    try:
        while True:
            # If no mode selected, show mode selection
            if current_mode is None:
                display_modes()
                current_mode = select_mode()
                
                if current_mode is None:
                    print("\n👋 Goodbye! Thanks for using Smart Buddy!")
                    break
                
                # Display mode-specific welcome
                mode_names = {
                    'general': '🤖 GENERAL MODE',
                    'mentor': '🎓 MENTOR MODE',
                    'bestfriend': '💕 BESTFRIEND MODE',
                    'auto': '🔄 AUTO MODE'
                }
                print(f"\n✓ Switched to {mode_names[current_mode]}")
                print("Commands: 'switch' to change mode, 'exit' to quit\n")
            
            # Get user input
            try:
                user_input = input(f"{user_id}: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n\n👋 Goodbye! Thanks for chatting with Smart Buddy!")
                break
            
            # Handle empty input
            if not user_input:
                continue
            
            # Check for mode switch command
            if user_input.lower() == 'switch':
                current_mode = None
                continue
            
            # Check for exit commands
            if user_input.lower() in ['quit', 'exit', 'bye', 'goodbye']:
                print("\n👋 Goodbye! Thanks for chatting with Smart Buddy!")
                break
            
            # Process message based on mode
            try:
                agent_result = {}
                
                if current_mode == 'auto':
                    # Use router for automatic mode selection
                    result = router.route(user_id, session_id, user_input)
                    envelope = result.get("envelope", {})
                    agent_result = result.get("result", {})
                else:
                    # Direct mode - call specific agent
                    envelope = {
                        "meta": {"from": "chat", "to": current_mode, "trace_id": f"chat_{message_count}"},
                        "payload": {
                            "user_id": user_id,
                            "session_id": session_id,
                            "text": user_input
                        }
                    }
                    
                    if current_mode == 'general':
                        agent_result = general_agent.handle(envelope)
                    elif current_mode == 'mentor':
                        agent_result = mentor_agent.handle(envelope)
                    elif current_mode == 'bestfriend':
                        agent_result = bestfriend_agent.handle(envelope)
                
                # Extract reply
                reply = agent_result.get("reply") or agent_result.get("message") or "I'm not sure how to respond to that."
                
                # Display response
                print(f"\n🤖 Smart Buddy: {reply}\n")
                
                message_count += 1
                
            except Exception as e:
                print(f"\n❌ Error: {e}\n")
                print("Please try again or type 'quit' to exit.\n")
    
    except KeyboardInterrupt:
        print("\n\n👋 Session interrupted. Goodbye!")
    
    print(f"\n📊 Session Summary: {message_count} messages exchanged")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
