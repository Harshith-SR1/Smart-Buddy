"""BestFriend Agent: Virtual bestie for casual, supportive conversations.

Architecture:
    This agent provides emotional support and casual conversation using a
    text-message style interaction pattern similar to chatting with a close friend.

Design Philosophy:
    - Casual, warm, and authentic communication
    - Heavy use of emojis for emotional expression (2-4 per message)
    - Brief responses (1-3 sentences) mimicking real text conversations
    - Natural reactions to user's emotional state
    - No formal language or excessive questioning

Behavior:
    - Responds with genuine excitement, empathy, or support
    - Uses casual slang ("omg", "aww", "yesss", "honestly")
    - Keeps messages short and conversational
    - Flows naturally without interrogating
    - Acts as emotional support and celebration partner

LLM Strategy:
    - Specialized prompt engineering for casual tone
    - Emphasis on brevity and emotional authenticity
    - Falls back to supportive default on LLM failure
    - No memory persistence (stateless emotional support)
""" 

from typing import Dict
from smart_buddy.llm import LLM
from smart_buddy.logging import get_logger


class BestFriendAgent:
    """Casual conversation agent providing emotional support like a best friend.
    
    This agent focuses on emotional connection and supportive interaction
    without task management or information retrieval.
    
    Attributes:
        llm (LLM): Language model interface for generating bestie-style responses
        _logger: Structured logger for tracking interactions
    """
    def __init__(self):
        self._logger = get_logger(__name__)
        self.llm = LLM()
    
    def handle(self, envelope: Dict) -> Dict:
        """Generate casual, supportive responses like texting a best friend.
        
        Prompt Engineering Strategy:
            - Positions LLM as user's best friend in casual conversation
            - Emphasizes emoji usage (2-4 per message) for emotional expression
            - Enforces brevity (1-3 sentences) for text-message authenticity
            - Encourages natural reactions over questions
            - Uses casual slang and informal language
        
        Design Decision:
            No memory persistence - each interaction is fresh emotional support.
            This prevents the agent from referencing past conversations, keeping
            interactions spontaneous and in-the-moment like real text chats.
        
        Args:
            envelope (Dict): Message envelope with user's text and metadata
        
        Returns:
            Dict: Response with status and casual bestie reply
        """
        payload = envelope.get("payload", {})
        text = payload.get("text", "")
        trace_id = envelope.get("meta", {}).get("trace_id")
        
        # Create a bestie-style conversational prompt
        prompt = f"""You are my BEST FRIEND chatting casually. I just said: "{text}"

Respond like texting your bestie:
- Use 2-4 emojis naturally 💕✨😊
- Be casual ("omg", "aww", "yesss", "honestly", "literally")
- Keep it brief (1-3 sentences)
- React naturally - be supportive, excited, or empathetic
- Chat and flow naturally - don't ask follow-up questions
- Sound like a text message, not formal

Just vibe with the conversation!"""
        
        try:
            # Get bestie response from LLM
            result = self.llm.generate(prompt)
            
            if result and result.get("candidates"):
                reply = result["candidates"][0].get("content", "").strip()
                if reply:
                    self._logger.info(
                        "bestfriend_response_generated",
                        extra={"trace_id": trace_id, "user_text_preview": text[:50]}
                    )
                    return {"status": "ok", "reply": reply}
        except Exception as e:
            self._logger.warning(
                "bestfriend_llm_failed",
                extra={"error": str(e), "trace_id": trace_id}
            )
        
        # Fallback to bestie reply
        reply = f"aww bestie 💕 i'm here for you always! {text[:80]}... i totally get it 🫂"
        return {"status": "ok", "reply": reply}
