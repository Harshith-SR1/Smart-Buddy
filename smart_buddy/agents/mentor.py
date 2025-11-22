"""Mentor Agent: Comprehensive AI teacher and guide with specialized mentoring modes.

Architecture:
    This agent implements a sophisticated multi-mode mentoring system that adapts
    its behavior based on the type of guidance needed. It combines 5 specialized
    sub-modes into one intelligent agent.

Five Specialized Modes:
    1. Teaching Mode 📚 - Explains concepts with examples and analogies
    2. Advice Mode 💡 - Provides thoughtful guidance with trade-offs
    3. Planning Mode 🗺️ - Creates detailed roadmaps with 6-10 steps
    4. Problem-Solving Mode 🔍 - Breaks down problems and suggests solutions
    5. Review Mode ✍️ - Provides constructive feedback on work

Design Decisions:
    - Keyword-based mode detection for transparency and control
    - Each mode has specialized LLM prompts for optimal responses
    - Plans are saved to memory for later retrieval
    - Falls back to general mentoring for unmatched queries
    - Natural conversation flow with minimal questioning

Behavior:
    - Analyzes user message to detect which mentoring mode is needed
    - Activates appropriate mode with specialized prompt engineering
    - Generates contextual, helpful responses via LLM
    - Saves important content (plans, roadmaps) to persistent memory
    - Provides warm, supportive general mentoring for casual queries
"""

import time
from typing import Dict, Optional

from smart_buddy.memory import MemoryBank
from smart_buddy.logging import get_logger
from smart_buddy.llm import LLM


class MentorAgent:
    """AI mentor providing teaching, advice, planning, problem-solving, and reviews.
    
    This agent acts as a comprehensive mentor by detecting the type of guidance
    needed and responding with specialized expertise in that area.
    
    Attributes:
        memory (MemoryBank): Shared memory for storing plans and user progress
        _ns (str): Namespace for mentor data in memory ("mentor")
        llm (LLM): Language model interface for generating mentoring responses
    """
    def __init__(
        self, memory: Optional[MemoryBank] = None, db_path: Optional[str] = None
    ):
        # allow injection for tests
        self.memory = memory or MemoryBank(db_path)
        self._ns = "mentor"
        self._logger = get_logger(__name__)
        self.llm = LLM()

    def handle(self, envelope: Dict) -> Dict:
        """Main entry point for mentor interactions with intelligent mode detection.
        
        Mode Detection System:
            Uses keyword analysis to determine which type of mentoring is needed.
            Each mode has specific trigger words that indicate user intent.
        
        Detection Keywords:
            - Teaching: "explain", "teach", "what is", "how does", "learn"
            - Advice: "advice", "suggest", "recommend", "should i", "opinion"
            - Planning: "plan", "roadmap", "steps", "how to", "guide"
            - Problem-Solving: "problem", "stuck", "help", "confused", "issue"
            - Review: "review", "feedback", "check", "improve", "better"
        
        Design Philosophy:
            - Multiple keywords can trigger same mode for flexibility
            - Case-insensitive matching for user convenience
            - First matching mode takes priority in the order above
            - Falls back to general mentoring if no mode matches
        
        Args:
            envelope (Dict): Message envelope with meta and payload
        
        Returns:
            Dict: Response with status, mode indicator, and mentor's reply
        """
        payload = envelope.get("payload", {})
        user = payload.get("user_id", "u1")
        text = payload.get("text", "")
        trace_id = envelope.get("meta", {}).get("trace_id")
        extra_base = {"user": user, "text_preview": text[:200]}
        if trace_id:
            extra_base["trace_id"] = trace_id
        self._logger.info("mentor_handle_start", extra=extra_base)

        # Check if there's existing saved content
        saved_content = self.memory.get(self._ns, user, trace_id=trace_id)
        
        # Determine the type of mentoring needed
        is_teaching = any(word in text.lower() for word in ["explain", "teach", "what is", "how does", "understand", "learn", "concept"])
        is_advice = any(word in text.lower() for word in ["advice", "suggest", "recommend", "should i", "what do you think", "opinion"])
        is_planning = any(word in text.lower() for word in ["plan", "roadmap", "steps", "how to", "guide", "prepare"])
        is_problem_solving = any(word in text.lower() for word in ["problem", "stuck", "help", "don't know", "confused", "issue"])
        is_reviewing = any(word in text.lower() for word in ["review", "feedback", "check", "correct", "improve", "better"])
        
        # TEACHING MODE - Explain concepts clearly
        if is_teaching:
            prompt = f"""You are an excellent teacher explaining: "{text}"

Teach clearly and effectively:
- Break down concepts simply
- Use real-world examples and analogies
- Structure: concept → example → key takeaway
- Be thorough but not overwhelming (3-5 paragraphs)

Just explain it well. Don't ask follow-up questions unless necessary."""
            
            try:
                result = self.llm.generate(prompt)
                if result and result.get("candidates"):
                    reply = result["candidates"][0].get("content", "").strip()
                    if reply:
                        return {"status": "ok", "reply": f"📚 **Teaching Mode**\n\n{reply}"}
            except:
                pass
            
            return {"status": "ok", "reply": "📚 I'll explain that for you right away."}
        
        # ADVICE/SUGGESTION MODE
        elif is_advice:
            prompt = f"""You are a wise mentor giving advice on: "{text}"

Provide direct, thoughtful guidance:
- Consider perspectives and trade-offs
- Give actionable suggestions
- Be supportive but realistic
- Structure clearly (2-4 paragraphs)

Give the advice directly. Don't ask for more details unless critical."""
            
            try:
                result = self.llm.generate(prompt)
                if result and result.get("candidates"):
                    reply = result["candidates"][0].get("content", "").strip()
                    if reply:
                        return {"status": "ok", "reply": f"💡 **Mentor's Advice**\n\n{reply}"}
            except:
                pass
            
            return {"status": "ok", "reply": "💡 Here's my guidance on that..."}
        
        # PLANNING/ROADMAP MODE
        elif is_planning:
            prompt = f"""You are a strategic mentor creating a plan for: "{text}"

Create a detailed, actionable roadmap:
- 6-10 specific, numbered steps
- Include timeframes and milestones
- Make steps achievable and concrete
- Add brief tips for each step

Just create the plan. Don't ask for more context."""
            
            try:
                result = self.llm.generate(prompt)
                if result and result.get("candidates"):
                    plan_content = result["candidates"][0].get("content", "").strip()
                    if plan_content:
                        # Save the plan
                        plan_data = {"content": plan_content, "topic": text, "done": True}
                        self.memory.set(self._ns, user, plan_data, trace_id=trace_id)
                        
                        return {"status": "completed", "plan": plan_data, "reply": f"🗺️ **Your Personalized Roadmap**\n\n{plan_content}\n\n✓ Plan saved! Type 'show my plan' anytime to review."}
            except Exception as e:
                self._logger.warning("mentor_planning_failed", extra={"error": str(e), "trace_id": trace_id})
            
            return {"status": "ok", "reply": "🗺️ Let me create a roadmap for you..."}
        
        # PROBLEM-SOLVING MODE
        elif is_problem_solving:
            prompt = f"""You are a problem-solving mentor. Issue: "{text}"

Provide problem-solving guidance:
- Identify the core issue
- Break into manageable parts
- Offer practical solutions
- Be analytical and clear (2-4 paragraphs)

Give solutions directly. Don't interrogate about the problem."""
            
            try:
                result = self.llm.generate(prompt)
                if result and result.get("candidates"):
                    reply = result["candidates"][0].get("content", "").strip()
                    if reply:
                        return {"status": "ok", "reply": f"🔍 **Problem-Solving Mode**\n\n{reply}"}
            except:
                pass
            
            return {"status": "ok", "reply": "🔍 Let me help you work through this..."}
        
        # REVIEW/FEEDBACK MODE
        elif is_reviewing:
            prompt = f"""You are a mentor reviewing work: "{text}"

Provide constructive review:
- Acknowledge strengths
- Point out improvement areas with specifics
- Give actionable suggestions
- Be encouraging and balanced (2-3 paragraphs)

Provide the review directly. Don't ask for more context unless absolutely needed."""
            
            try:
                result = self.llm.generate(prompt)
                if result and result.get("candidates"):
                    reply = result["candidates"][0].get("content", "").strip()
                    if reply:
                        return {"status": "ok", "reply": f"✍️ **Review & Feedback**\n\n{reply}"}
            except:
                pass
            
            return {"status": "ok", "reply": "✍️ I'll review that for you..."}
        
        # VIEW SAVED CONTENT
        elif saved_content and any(word in text.lower() for word in ["show", "view", "see", "my plan", "saved"]):
            content = saved_content.get('content', '')
            topic = saved_content.get('topic', 'your previous request')
            return {"status": "ok", "reply": f"📋 **Saved Plan: {topic}**\n\n{content}"}
        
        # GENERAL MENTORING CONVERSATION
        else:
            prompt = f"""You are a supportive mentor. Student said: "{text}"

Respond naturally and helpfully:
- Understand what they're asking or sharing
- Provide relevant insights or support
- Be conversational and warm (1-3 sentences)
- Give substantive responses, not just questions

Flow naturally with the conversation."""
            
            try:
                result = self.llm.generate(prompt)
                if result and result.get("candidates"):
                    reply = result["candidates"][0].get("content", "").strip()
                    if reply:
                        return {"status": "ok", "reply": reply}
            except:
                pass
            
            return {"status": "ok", "reply": "I'm here to help guide you. Let's talk about that."}
