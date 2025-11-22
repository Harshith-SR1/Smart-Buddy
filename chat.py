#!/usr/bin/env python3
"""
Interactive chat with Smart Buddy AI Agent
Powered by Google Gemini SDK
"""
import sys
from smart_buddy.agents.general_agent import GeneralAgent
from smart_buddy.agents.mentor import MentorAgent
from smart_buddy.agents.bestfriend import BestFriendAgent
from smart_buddy.memory import MemoryBank

def display_modes():
    """Display available modes"""
    print("\n" + "=" * 60)
    print("  SMART BUDDY MODES")
    print("=" * 60)
    print("\n1. 🤖 GENERAL MODE - Your AI Assistant (like ChatGPT)")
    print("   • Answer questions, manage calendar & todos")
    print("   • Example: 'Schedule gym tomorrow 6pm' or 'Explain AI'")
    print("\n2. 🎓 MENTOR MODE - Your AI Teacher & Guide")
    print("   • Teaching, advice, planning, problem-solving, feedback")
    print("   • Example: 'Explain quantum physics' or 'Career advice'")
    print("\n3. 💕 BESTFRIEND MODE - Chat with your virtual bestie!")
    print("   • Casual, fun conversations with emojis & support")
    print("   • Example: 'I got a promotion!' or 'feeling down today'")
    print("\n" + "=" * 60)

def select_mode():
    """Let user select a mode"""
    while True:
        print("\nSelect a mode (1-3) or 'q' to quit:")
        choice = input("Your choice: ").strip().lower()
        
        if choice == 'q':
            return None
        elif choice == '1':
            return 'general'
        elif choice == '2':
            return 'mentor'
        elif choice == '3':
            return 'bestfriend'
        else:
            print("❌ Invalid choice. Please enter 1, 2, 3, or 'q'")

def main():
    print("=" * 60)
    print("  Smart Buddy AI Agent - Interactive Chat")
    print("  Powered by Google Gemini 2.5 Flash")
    print("=" * 60)
    
    # Initialize memory and agents
    memory = MemoryBank()
    general_agent = GeneralAgent(memory=memory)
    mentor_agent = MentorAgent(memory=memory)
    bestfriend_agent = BestFriendAgent()
    
    # Get user name
    user_id = input("\nEnter your name (or press Enter for 'User'): ").strip() or "User"
    session_id = "interactive_session"
    
    print(f"\nHello {user_id}! Welcome to Smart Buddy!")
    
    # Main loop
    current_mode = None
    print(f"\nHello {user_id}! Welcome to Smart Buddy!")
    
    # Main loop
    current_mode = None
    
    try:
        while True:
            # If no mode selected, show mode selection
            if current_mode is None:
                display_modes()
                current_mode = select_mode()
                
                if current_mode is None:
                    print("\nGoodbye! 👋 Thanks for using Smart Buddy!")
                    break
                
                # Display mode-specific welcome
                mode_names = {
                    'general': '🤖 GENERAL MODE',
                    'mentor': '🎓 MENTOR MODE',
                    'bestfriend': '💕 BESTFRIEND MODE'
                }
                print(f"\n✓ Switched to {mode_names[current_mode]}")
                print("Commands: 'switch' to change mode, 'exit' to quit\n")
            
            # Get user input
            try:
                user_input = input(f"{user_id}: ").strip()
            except EOFError:
                print("\n\nGoodbye! 👋")
                break
            
            if not user_input:
                continue
            
            # Handle commands
            if user_input.lower() in ['exit', 'quit', 'bye']:
                print("\nGoodbye! 👋 Thanks for chatting with Smart Buddy!")
                break
            
            if user_input.lower() in ['switch', 'change', 'mode']:
                current_mode = None
                continue
            
            # Process based on selected mode
            try:
                result = None
                
                if current_mode == 'general':
                    # Create envelope for general agent
                    envelope = {
                        'meta': {'from': 'user', 'to': 'general', 'trace_id': f'{session_id}_{current_mode}'},
                        'payload': {
                            'user_id': user_id,
                            'session_id': session_id,
                            'text': user_input
                        }
                    }
                    result = general_agent.handle(envelope)
                
                elif current_mode == 'mentor':
                    # Create envelope for mentor agent
                    envelope = {
                        'meta': {'from': 'user', 'to': 'mentor', 'trace_id': f'{session_id}_{current_mode}'},
                        'payload': {
                            'user_id': user_id,
                            'session_id': session_id,
                            'text': user_input
                        }
                    }
                    result = mentor_agent.handle(envelope)
                
                elif current_mode == 'bestfriend':
                    # Create envelope for bestfriend agent
                    envelope = {
                        'meta': {'from': 'user', 'to': 'bestfriend', 'trace_id': f'{session_id}_{current_mode}'},
                        'payload': {
                            'user_id': user_id,
                            'session_id': session_id,
                            'text': user_input
                        }
                    }
                    result = bestfriend_agent.handle(envelope)
                
                # Display response
                if result:
                    print(f"\n🤖 Smart Buddy: ", end="")
                    
                    if isinstance(result, dict):
                        if 'reply' in result:
                            print(result['reply'])
                        elif 'action' in result and result.get('action') == 'added':
                            tasks = result.get('tasks', [])
                            if tasks and 'reply' not in result:
                                latest_task = tasks[-1]
                                print(f"✓ Added: '{latest_task['text']}' (Total: {len(tasks)} tasks)")
                        elif 'status' in result and result['status'] in ['resumed', 'completed']:
                            if 'reply' not in result:
                                checkpoint = result.get('checkpoint') or result.get('plan', {})
                                plan_text = "\n".join([f"  {i+1}. {step}" for i, step in enumerate(checkpoint.get('steps', []))])
                                print(f"Your plan:\n{plan_text}")
                                if checkpoint.get('done'):
                                    print("\n✓ Plan ready!")
                        else:
                            if 'reply' not in result:
                                print(f"Got it! (Status: {result.get('status', 'ok')})")
                    else:
                        print(str(result))
                    
                    print()
                
            except Exception as e:
                print(f"\n❌ Error: {e}")
                print("Type 'switch' to change mode or 'exit' to quit.\n")
    
    except KeyboardInterrupt:
        print("\n\nGoodbye! 👋")
    
    finally:
        # Close memory connection
        try:
            memory.close()
        except:
            pass

if __name__ == "__main__":
    main()
