"""
Extended base agent with shared utilities for all concrete agents.

Provides common functionality for LLM interaction, structured output parsing,
context formatting, and interaction logging.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from orchestify.core.agent import BaseAgent, AgentContext, AgentResult

logger = logging.getLogger(__name__)


class ConcreteAgent(BaseAgent):
    """
    Extended base agent with shared utilities for all concrete agents.

    Implements common patterns for:
    - LLM calls with persona integration
    - Parsing structured ABD output format (9 sections)
    - Context formatting for LLM consumption
    - Interaction logging for memory and debugging
    """

    async def _call_llm(self, context: AgentContext) -> str:
        """
        Call LLM provider with persona and context.

        Builds message array from context and persona, calls provider,
        and returns the raw response text.

        Args:
            context: Agent execution context

        Returns:
            Raw LLM response text

        Raises:
            RuntimeError: If LLM call fails
        """
        messages = self._build_messages(context)

        try:
            response, tokens = await super()._call_llm(
                messages=messages,
                temperature=self.config.get("temperature", 0.7),
                max_tokens=self.config.get("max_tokens", 4096),
            )

            logger.debug(
                f"Agent {self.agent_id} LLM call: {tokens} tokens used"
            )

            return response

        except Exception as e:
            logger.error(f"LLM call failed for agent {self.agent_id}: {e}")
            raise RuntimeError(f"LLM call failed: {e}") from e

    def _parse_structured_output(self, raw: str) -> Dict[str, Any]:
        """
        Parse the 9-section ABD output format.

        Expected format with sections:
        1. Analysis
        2. Strategy
        3. Implementation
        4. Testing
        5. Documentation
        6. Code Changes
        7. Risk Assessment
        8. Metrics
        9. Scorecard (JSON)

        Args:
            raw: Raw LLM output text

        Returns:
            Dictionary with parsed sections

        Raises:
            ValueError: If format is invalid or scorecard JSON is malformed
        """
        sections = {
            "analysis": "",
            "strategy": "",
            "implementation": "",
            "testing": "",
            "documentation": "",
            "code_changes": "",
            "risk_assessment": "",
            "metrics": "",
            "scorecard": {},
        }

        # Split by markdown headers
        lines = raw.split("\n")
        current_section = None
        current_content: List[str] = []

        section_mapping = {
            "analysis": "## Analysis",
            "strategy": "## Strategy",
            "implementation": "## Implementation",
            "testing": "## Testing",
            "documentation": "## Documentation",
            "code_changes": "## Code Changes",
            "risk_assessment": "## Risk Assessment",
            "metrics": "## Metrics",
            "scorecard": "## Scorecard",
        }

        for line in lines:
            # Check for section headers
            matched_section = None
            for key, header in section_mapping.items():
                if line.strip().startswith(header):
                    # Save previous section if exists
                    if current_section:
                        sections[current_section] = "\n".join(current_content).strip()
                    current_section = key
                    current_content = []
                    matched_section = key
                    break

            if not matched_section and current_section:
                current_content.append(line)

        # Save last section
        if current_section:
            sections[current_section] = "\n".join(current_content).strip()

        # Try to parse scorecard as JSON
        if sections.get("scorecard"):
            try:
                # Extract JSON block if wrapped in code fence
                scorecard_text = sections["scorecard"]
                if "```json" in scorecard_text:
                    scorecard_text = scorecard_text.split("```json")[1].split("```")[0]
                elif "```" in scorecard_text:
                    scorecard_text = scorecard_text.split("```")[1].split("```")[0]

                sections["scorecard"] = json.loads(scorecard_text.strip())
            except (json.JSONDecodeError, IndexError) as e:
                logger.warning(f"Failed to parse scorecard JSON: {e}")
                sections["scorecard"] = {}

        return sections

    def _format_context_for_llm(self, context: AgentContext) -> str:
        """
        Format agent context into LLM-friendly text.

        Creates a readable representation of all context information for
        inclusion in LLM prompts.

        Args:
            context: Agent execution context

        Returns:
            Formatted context string
        """
        parts: List[str] = []

        if context.goal:
            parts.append(f"GOAL:\n{context.goal}")

        if context.instructions:
            parts.append(f"INSTRUCTIONS:\n{context.instructions}")

        if context.behavior_spec:
            parts.append(f"BEHAVIOR SPECIFICATION:\n{context.behavior_spec}")

        if context.touches:
            parts.append("FILES TO TOUCH:\n- " + "\n- ".join(context.touches))

        if context.dependencies:
            parts.append(
                "DEPENDENCIES:\n- " + "\n- ".join(context.dependencies)
            )

        if context.review_keynotes:
            parts.append(
                "REVIEW KEYNOTES:\n- "
                + "\n- ".join(context.review_keynotes)
            )

        if context.prior_output:
            parts.append(f"PRIOR OUTPUT:\n{context.prior_output}")

        if context.error_output:
            parts.append(f"ERROR TO FIX:\n{context.error_output}")

        if context.memory_context:
            memory_parts = [
                f"{k}: {v}" for k, v in context.memory_context.items()
            ]
            parts.append("MEMORY CONTEXT:\n" + "\n".join(memory_parts))

        return "\n\n".join(parts)

    def _log_interaction(
        self, context: AgentContext, result: AgentResult
    ) -> None:
        """
        Log agent interaction for memory and debugging.

        Records execution details including timestamps, token usage,
        files changed, and commands run for audit trail and memory
        retrieval.

        Args:
            context: Agent execution context
            result: Agent result
        """
        timestamp = datetime.now().isoformat()
        interaction_log = {
            "timestamp": timestamp,
            "agent_id": self.agent_id,
            "goal": context.goal,
            "tokens_used": result.tokens_used,
            "duration": result.duration,
            "files_changed": result.files_changed,
            "commands_run": result.commands_run,
        }

        logger.info(
            f"Agent {self.agent_id} interaction: "
            f"{result.tokens_used} tokens, {result.duration:.2f}s"
        )
