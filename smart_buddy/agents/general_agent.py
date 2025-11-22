"""General Agent: ChatGPT-like assistant with calendar, tasks, and conversation.

Architecture:
    This agent serves as a multi-purpose AI assistant similar to ChatGPT, combining
    three core capabilities:
    1. Calendar/Event Management - Schedule appointments, meetings, reminders
    2. Task/Todo Management - Create and track tasks with priorities and deadlines
    3. General Conversation - Answer questions, provide information, generate content

Design Decisions:
    - Uses separate namespaces in MemoryBank for data isolation (tasks vs events)
    - Keyword-based routing to detect user intent (calendar/task/general)
    - Smart context extraction with minimal questions for better UX
    - LLM-powered responses for natural, conversational interactions
    - JSON-based structured data for event/task creation via LLM

Behavior:
    - Detects intent from keywords in user messages
    - Routes to specialized handlers (_handle_calendar_event, _handle_task_management)
    - Falls back to general conversation for unmatched queries
    - Persists all data (tasks, events) in SQLite-backed memory
    - Generates confirmations and natural responses via Google Gemini

Handles:
- General conversations and questions
- Creating and managing calendar events
- Creating and managing todo lists
- Scheduling and time management
- Any general queries like ChatGPT
"""

from typing import Dict, Optional, List
from datetime import datetime, timedelta
import json

from smart_buddy.memory import MemoryBank
from smart_buddy.logging import get_logger
from smart_buddy.llm import LLM


class GeneralAgent:
    """Multi-purpose AI assistant combining calendar, tasks, and general conversation.
    
    This agent acts as the primary interface for general user interactions,
    intelligently routing requests to specialized handlers based on detected intent.
    
    Attributes:
        memory (MemoryBank): Shared memory instance for persistent data storage
        _tasks_ns (str): Namespace for task storage in memory ("tasks")
        _events_ns (str): Namespace for event storage in memory ("events")
        llm (LLM): Language model interface for generating responses
    """
    def __init__(
        self, memory: Optional[MemoryBank] = None, db_path: Optional[str] = None
    ):
        # memory may be injected for testing; otherwise create a file-backed DB
        self.memory = memory or MemoryBank(db_path)
        # namespaces for different data types
        self._tasks_ns = "tasks"
        self._events_ns = "events"
        self._logger = get_logger(__name__)
        self.llm = LLM()

    def handle(self, envelope: Dict) -> Dict:
        """Main entry point for processing user messages with intelligent routing.
        
        This method implements a keyword-based intent detection system to route
        user messages to the appropriate specialized handler.
        
        Routing Logic:
            1. Extract user message and metadata from envelope
            2. Convert text to lowercase for case-insensitive keyword matching
            3. Check for calendar keywords (schedule, event, appointment, etc.)
            4. Check for task keywords (todo, task, need to do, etc.)
            5. Default to general conversation for everything else
        
        Design Decision:
            Using keyword matching instead of ML classification for:
            - Simplicity and transparency
            - No training data required
            - Fast execution without model overhead
            - Easy to debug and extend
        
        Args:
            envelope (Dict): Message envelope containing:
                - meta: Metadata (from, to, trace_id)
                - payload: User data (user_id, session_id, text)
        
        Returns:
            Dict: Response containing status, action, and reply message
                May also include tasks/events arrays depending on action
        """
        payload = envelope.get("payload", {})
        user = payload.get("user_id", "u1")
        text = payload.get("text", "")
        trace_id = envelope.get("meta", {}).get("trace_id")
        extra_base = {"user": user, "text_preview": text[:200]}
        if trace_id:
            extra_base["trace_id"] = trace_id
        self._logger.info("general_handle", extra=extra_base)

        text_lower = text.lower()
        
        # Retrieve current user data from persistent memory
        # These are loaded fresh on each request to ensure consistency
        tasks = self.memory.get(self._tasks_ns, user, [], trace_id=trace_id) or []
        events = self.memory.get(self._events_ns, user, [], trace_id=trace_id) or []
        
        # INTENT DETECTION & ROUTING
        # Using keyword-based detection for transparency and simplicity
        
        # CALENDAR EVENT MANAGEMENT
        # Keywords: schedule, calendar, event, appointment, meeting, remind me
        # Handles: Creating events, listing calendar, event management
        if any(keyword in text_lower for keyword in ["schedule", "calendar", "event", "appointment", "meeting", "remind me", "set reminder"]):
            return self._handle_calendar_event(user, text, events, trace_id)
        
        # TODO/TASK MANAGEMENT  
        # Keywords: todo, task, add task, create task, need to do
        # Handles: Creating tasks, listing todos, task management
        elif any(keyword in text_lower for keyword in ["todo", "task", "add task", "create task", "need to do"]):
            return self._handle_task_management(user, text, tasks, trace_id)
        
        # GENERAL CONVERSATION (like ChatGPT)
        else:
            return self._handle_general_conversation(user, text, tasks, events, trace_id)
    
    def _handle_calendar_event(self, user: str, text: str, events: List, trace_id: str) -> Dict:
        """Handle calendar event creation and management with smart context extraction.
        
        Design Philosophy:
            - Minimize user friction by making intelligent assumptions
            - Only ask for truly critical missing information
            - Use LLM to extract structured data from natural language
            - Provide clear confirmations when events are created
        
        Implementation:
            1. Check if user wants to list existing events (show/list/view keywords)
            2. Otherwise, attempt to create new event from user's message
            3. Use LLM to extract: title, date, time from natural language
            4. LLM returns special marker "EVENT_CREATED:" + JSON when successful
            5. Parse JSON and persist to memory with auto-incremented ID
            6. Return confirmation with event details
        
        Smart Assumptions:
            - "tomorrow" -> use next day's date
            - No time specified -> use "all day" or reasonable default
            - Minimal required info: activity description + when
        
        Args:
            user (str): User identifier for memory storage
            text (str): User's original message
            events (List): Current list of user's events from memory
            trace_id (str): Request trace ID for logging
        
        Returns:
            Dict: Response with status, events list, and reply message
                  On creation: includes "action": "event_created"
        """
        text_lower = text.lower()
        
        # Check if listing events
        if any(word in text_lower for word in ["show", "list", "what", "my events", "my calendar"]):
            if not events:
                return {"status": "ok", "events": [], "reply": "📅 Your calendar is empty right now."}
            
            event_list = "\n".join([f"{i+1}. {e['title']} - {e['date']} at {e['time']}" for i, e in enumerate(events)])
            return {"status": "ok", "events": events, "reply": f"📅 Here are your scheduled events:\n\n{event_list}"}
        
        # Create new event - extract what you can, only ask for critical missing info
        prompt = f"""You're a helpful assistant. User wants to schedule something: "{text}"

Extract any details mentioned and create the event. Be smart:
- If they say "tomorrow" or "Friday" → use that as date
- If they mention a time → use it
- If no time given → assume "all day" or a reasonable time
- Title: extract what they want to do

ONLY ask if BOTH date AND activity are completely unclear. Otherwise, make reasonable assumptions.

If you can create the event, output: EVENT_CREATED: {{"title": "...", "date": "...", "time": "..."}}
If truly unclear, ask ONE brief question for the most critical missing piece.

Be conversational and flowing, not interrogative."""
        
        try:
            result = self.llm.generate(prompt)
            if result and result.get("candidates"):
                reply = result["candidates"][0].get("content", "").strip()
                
                # Check if event was created
                if "EVENT_CREATED:" in reply:
                    try:
                        json_str = reply.split("EVENT_CREATED:")[1].strip()
                        event_data = json.loads(json_str)
                        event_data["id"] = len(events) + 1
                        events.append(event_data)
                        self.memory.set(self._events_ns, user, events, trace_id=trace_id)
                        return {"status": "ok", "action": "event_created", "events": events, 
                                "reply": f"✅ Got it! Added to your calendar:\n\n📅 {event_data['title']}\n📆 {event_data['date']} at {event_data['time']}"}
                    except:
                        pass
                
                return {"status": "ok", "events": events, "reply": reply}
        except:
            pass
        
        return {"status": "ok", "events": events, 
                "reply": "I can help schedule that. When would you like it?"}
    
    def _handle_task_management(self, user: str, text: str, tasks: List, trace_id: str) -> Dict:
        """Handle todo list management with intelligent task extraction.
        
        Design Philosophy:
            - Extract task descriptions from natural language seamlessly
            - Don't interrupt flow with unnecessary questions about priority/deadline
            - Use LLM to understand user intent and create tasks immediately
            - Priority and deadline are optional enhancements, not requirements
        
        Implementation:
            1. Check if user wants to view existing tasks (show/list keywords)
            2. Otherwise, parse message to extract task information
            3. Use LLM to identify: task description, optional priority, optional deadline
            4. LLM returns "TASK_CREATED:" + JSON when ready to create
            5. Persist task with auto-incremented ID to memory
            6. Return confirmation with task details
        
        Context Awareness:
            - Understands phrases like "I need to", "should", "must"
            - Extracts deadlines from "by Friday", "tomorrow", date mentions
            - Infers priority from "urgent", "important" keywords
        
        Args:
            user (str): User identifier for memory storage
            text (str): User's original message  
            tasks (List): Current list of user's tasks from memory
            trace_id (str): Request trace ID for logging
        
        Returns:
            Dict: Response with status, tasks list, and reply message
                  On creation: includes "action": "task_created"
        """
        text_lower = text.lower()
        
        # Check if this is an ADD request first (higher priority)
        add_keywords = ["add", "create", "new task", "need to", "have to", "should do", "remember to"]
        is_adding = any(keyword in text_lower for keyword in add_keywords)
        
        # Check if listing tasks (only if NOT adding)
        list_keywords = ["show", "list", "what", "my tasks", "view tasks", "see tasks"]
        is_listing = any(word in text_lower for word in list_keywords) and not is_adding
        
        if is_listing:
            if not tasks:
                return {"status": "ok", "tasks": [], "reply": "📝 Your todo list is empty right now."}
            
            task_list = "\n".join([f"{i+1}. {t['text']}" for i, t in enumerate(tasks)])
            return {"status": "ok", "tasks": tasks, "reply": f"📝 Your todo list:\n\n{task_list}"}
        
        # Create new task - extract and create immediately if clear
        prompt = f"""You're a helpful assistant. User wants to add a task: "{text}"

Extract the task description from what they said. Be understanding:
- Main task is usually obvious from context
- Priority/deadline are nice-to-have, not required
- If they say "by Friday" or "urgent" → note it

If you understand what they want to do, create it: TASK_CREATED: {{"text": "...", "priority": "...", "deadline": "..."}}
Don't ask questions unless the task itself is completely unclear.

Flow naturally with the conversation."""
        
        try:
            result = self.llm.generate(prompt)
            if result and result.get("candidates"):
                reply = result["candidates"][0].get("content", "").strip()
                
                # Check if task was created
                if "TASK_CREATED:" in reply:
                    try:
                        json_str = reply.split("TASK_CREATED:")[1].strip()
                        task_data = json.loads(json_str)
                        task_data["id"] = len(tasks) + 1
                        tasks.append(task_data)
                        self.memory.set(self._tasks_ns, user, tasks, trace_id=trace_id)
                        
                        task_str = f"✅ Added: {task_data['text']}"
                        if task_data.get("priority"):
                            task_str += f" (Priority: {task_data['priority']})"
                        if task_data.get("deadline"):
                            task_str += f" - Due: {task_data['deadline']}"
                        
                        return {"status": "ok", "action": "task_created", "tasks": tasks, "reply": task_str}
                    except:
                        pass
                
                return {"status": "ok", "tasks": tasks, "reply": reply}
        except:
            pass
        
        return {"status": "ok", "tasks": tasks, "reply": "Got it, I'll add that to your list."}
    
    def _handle_general_conversation(self, user: str, text: str, tasks: List, events: List, trace_id: str) -> Dict:
        """Handle general ChatGPT-like conversation for all other queries.
        
        Design Philosophy:
            - Act as a general-purpose AI assistant for any question
            - Provide direct, helpful responses without unnecessary probing
            - Generate content, answer questions, explain concepts
            - Natural conversational flow similar to ChatGPT
        
        Capabilities:
            - Answer factual questions on any topic
            - Explain concepts with examples
            - Generate content (schedules, plans, summaries)
            - Provide advice and suggestions
            - Have casual conversations
            - Help with problems and troubleshooting
        
        Implementation:
            - Constructs prompt positioning as "Smart Buddy" assistant
            - Sends user query to LLM (Google Gemini)
            - Returns generated response directly
            - Falls back to friendly default on LLM failure
        
        Args:
            user (str): User identifier (not used in general conversation)
            text (str): User's question or message
            tasks (List): User's tasks (available for context if needed)
            events (List): User's events (available for context if needed)
            trace_id (str): Request trace ID for logging
        
        Returns:
            Dict: Response with status and reply message from LLM
        """
        
        prompt = f"""You are Smart Buddy, a helpful AI assistant like ChatGPT.

User: {text}

Respond naturally and conversationally like ChatGPT:
- Answer questions directly and clearly
- Provide explanations, help, advice as needed
- Generate content when asked (schedules, plans, summaries, etc.)
- Be friendly but not overly enthusiastic
- Don't ask unnecessary questions - give useful responses
- If creating schedules/plans, format them nicely with structure
- Flow with the conversation naturally

Just respond helpfully to what they asked."""
        
        try:
            result = self.llm.generate(prompt)
            if result and result.get("candidates"):
                reply = result["candidates"][0].get("content", "").strip()
                if reply:
                    return {"status": "ok", "reply": reply}
        except Exception as e:
            self._logger.error(f"general_conversation_error", extra={"error": str(e)})
        
        return {"status": "ok", "reply": "I'm here to help! What would you like to know?"}

