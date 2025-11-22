"""Router Agent: Orchestrates multi-agent system with intent-based routing.

Architecture:
    Central orchestrator implementing envelope-based messaging pattern.
    Routes user messages to specialized agents based on intent classification.

Agent Topology:
    RouterAgent (orchestrator)
    ├── IntentAgent (classifier)
    ├── GeneralAgent (calendar/tasks/general queries)
    ├── MentorAgent (teaching/advice/planning/problem-solving/review)
    └── BestFriendAgent (emotional support/casual conversation)

Design Decisions:
    - Envelope pattern for structured message passing
    - UUID-based trace IDs for request tracking across agents
    - Shared MemoryBank instance for data persistence
    - Intent classification determines routing destination
    - Session footprints recorded for observability

Envelope Structure:
    meta: {from, to, trace_id} - routing and tracing info
    payload: {user_id, session_id, text, intent} - message content

Behavior:
    1. Generate unique trace_id for request tracking
    2. Classify user intent via IntentAgent
    3. Log routing decision with trace_id
    4. Route to appropriate specialized agent
    5. Record session footprint in shared memory
    6. Return agent response with envelope metadata
"""

import uuid
from typing import Dict
from smart_buddy.logging import get_logger

from .intent import IntentAgent
from .general_agent import GeneralAgent
from .mentor import MentorAgent
from .bestfriend import BestFriendAgent
from .planner import PlannerAgent


class RouterAgent:
    """Central orchestrator routing messages to specialized agents via intent.
    
    Implements envelope-based messaging with trace ID propagation for
    observability across the multi-agent system.
    
    Attributes:
        intent (IntentAgent): Classifies user messages into intent categories
        memory (MemoryBank): Shared persistent storage for all agents
        general (GeneralAgent): Handles calendar, tasks, general queries
        mentor (MentorAgent): Provides teaching, advice, planning, reviews
        bestfriend (BestFriendAgent): Casual emotional support conversations
    """
    def __init__(self, memory=None):
        self._logger = get_logger(__name__)
        # memory can be a MemoryBank instance shared across agents
        self.intent = IntentAgent()
        self.memory = memory
        # defer importing MemoryBank to avoid cyclic import issues in some setups
        self.general = GeneralAgent(memory=memory)
        self.mentor = MentorAgent(memory=memory)
        self.bestfriend = BestFriendAgent()
        self.planner = PlannerAgent(memory=memory)

    def route(self, user_id: str, session_id: str, text: str) -> Dict:
        """Route user message to appropriate agent based on intent classification.
        
        Routing Process:
            1. Generate unique trace_id (UUID) for this request
            2. Classify intent using IntentAgent
            3. Log routing decision with trace_id for observability
            4. Construct envelope with metadata and payload
            5. Dispatch to target agent based on intent
            6. Record session footprint in MemoryBank
            7. Return envelope and agent result
        
        Intent Mapping:
            - "task" → GeneralAgent (calendar, todos, general queries)
            - "planner" → MentorAgent (teaching, advice, planning)
            - "emotion" → BestFriendAgent (casual support)
            - other → Default general response
        
        Envelope Pattern:
            Standardized message structure for agent communication:
            - Enables consistent message passing
            - Includes routing metadata (from/to/trace_id)
            - Carries user context (user_id, session_id, text)
            - Allows request tracing across agent boundaries
        
        Observability:
            - trace_id propagates through all log entries
            - Session recorded in memory for analytics
            - Enables distributed tracing in multi-agent system
        
        Args:
            user_id (str): Unique user identifier
            session_id (str): Current conversation session ID
            text (str): User's message text
        
        Returns:
            Dict: Contains envelope (metadata) and result (agent response)
        """
        # Generate UUID for request tracing across agents
        trace_id = str(uuid.uuid4())
        # include trace_id when classifying so downstream logs can be correlated
        intent = self.intent.classify(text, trace_id=trace_id)
        self._logger.info(
            "route_received",
            extra={
                "user_id": user_id,
                "session_id": session_id,
                "intent": intent,
                "trace_id": trace_id,
            },
        )
        envelope = {
            "meta": {"from": "router", "to": intent["intent"], "trace_id": trace_id},
            "payload": {
                "user_id": user_id,
                "session_id": session_id,
                "text": text,
                "intent": intent,
            },
        }

        to = intent["intent"]
        if to == "task":
            self._logger.debug("dispatch", extra={"to": "general", "trace_id": trace_id})
            result = self.general.handle(envelope)
        elif to == "planner":
            self._logger.debug(
                "dispatch", extra={"to": "planner", "trace_id": trace_id}
            )
            result = self.planner.handle(envelope)
        elif to == "emotion":
            self._logger.debug(
                "dispatch", extra={"to": "bestfriend", "trace_id": trace_id}
            )
            result = self.bestfriend.handle(envelope)
        else:
            result = {
                "status": "ok",
                "reply": f"Handled by general router: {text[:120]}",
            }

        # Optionally record a lightweight session footprint in the MemoryBank (if provided)
        try:
            if self.memory:
                self.memory.set(
                    "sessions",
                    session_id,
                    {"user_id": user_id, "intent": intent},
                    trace_id=trace_id,
                )
                try:
                    # Emit a complementary INFO-level memory footprint so tests and logs
                    # that only capture INFO+ will still see a memory-related entry.
                    self.memory._logger.info(
                        "session_recorded",
                        extra={
                            "session_id": session_id,
                            "user_id": user_id,
                            "trace_id": trace_id,
                        },
                    )
                except Exception:
                    # best-effort; do not fail routing on logger access issues
                    pass
        except Exception:
            self._logger.exception(
                "route_session_record_failed", extra={"trace_id": trace_id}
            )

        self._logger.info(
            "route_completed", extra={"trace_id": trace_id, "result": result}
        )
        return {"envelope": envelope, "result": result}
