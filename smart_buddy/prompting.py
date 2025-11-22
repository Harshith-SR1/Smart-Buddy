"""
Prompt templating utilities for Smart Buddy.

Provides a small `PromptTemplate` class to build system+instruction+context prompts
and to run moderation before generating.
"""

from typing import Any, Dict, Optional
from . import safety


class PromptTemplate:
    def __init__(
        self,
        system: str = "",
        instruction_template: str = "{instruction}",
        examples: Optional[list] = None,
    ):
        self.system = system
        self.instruction_template = instruction_template
        self.examples = examples or []

    def render(self, instruction: str, context: Optional[Dict] = None) -> str:
        """Render the full prompt text given an instruction and optional context dict."""
        ctx = context or {}
        # Fill instruction_template with context variables if present
        try:
            instruction_text = self.instruction_template.format(
                instruction=instruction, **ctx
            )
        except Exception:
            instruction_text = instruction

        parts = []
        if self.system:
            parts.append(f"SYSTEM: {self.system}\n")
        for ex in self.examples:
            parts.append(f"EXAMPLE:\n{ex}\n")
        parts.append(f"USER:\n{instruction_text}\n")
        return "\n".join(parts)

    def safe_render(
        self,
        instruction: str,
        context: Optional[Dict[str, Any]] = None,
        allowlist: Optional[list] = None,
    ) -> Dict[str, Any]:
        """Render and run local moderation. Returns a dict with keys:
        - allowed: bool
        - prompt: the rendered prompt
        - moderation: moderation result
        """
        prompt = self.render(instruction, context=context)
        mod = safety.moderate_text(prompt, allowlist=allowlist or [])
        return {"allowed": mod["allowed"], "prompt": prompt, "moderation": mod}
