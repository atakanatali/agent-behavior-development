"""
ABD Orchestration Engine.

Orchestrates the full pipeline: TPM → Architect → Issue Loop → Complete.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from orchestify.core.state import StateManager, EpicStatus, IssueStatus
from orchestify.utils.logger import get_logger


logger = get_logger(__name__)


class OrchestrifyEngine:
    """
    Main orchestration engine for ABD workflow.

    Manages the full pipeline from planning through completion.
    """

    def __init__(
        self,
        config: Dict[str, Any],
        state_manager: StateManager,
        provider_registry: Dict[str, Any],
        memory_client: Optional[Any] = None,
    ):
        """
        Initialize orchestration engine.

        Args:
            config: Engine configuration
            state_manager: State persistence manager
            provider_registry: Registry of LLM providers
            memory_client: Optional memory client
        """
        self.config = config
        self.state_manager = state_manager
        self.provider_registry = provider_registry
        self.memory_client = memory_client
        self.agents = {}
        self.logger = get_logger(__name__)

    def register_agent(self, agent_id: str, agent: Any) -> None:
        """
        Register an agent for use in orchestration.

        Args:
            agent_id: Agent identifier
            agent: Agent instance
        """
        self.agents[agent_id] = agent
        self.logger.info(f"Registered agent: {agent_id}")

    async def run_full_pipeline(
        self,
        plan_file: Optional[Path] = None,
        prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run full ABD pipeline.

        Executes: TPM → Architect → Issue Loop → Complete

        Args:
            plan_file: Optional path to plan file
            prompt: Optional initial prompt

        Returns:
            Pipeline results
        """
        self.logger.info("Starting full ABD pipeline")

        try:
            # Phase 1: TPM
            tpm_result = await self.run_phase("tpm", input_text=prompt or "")
            if not tpm_result.get("success"):
                self.logger.error("TPM phase failed")
                return {"success": False, "error": "TPM phase failed"}

            epic_id = tpm_result.get("epic_id")
            self.logger.info(f"TPM generated epic: {epic_id}")

            # Phase 2: Architect
            architect_result = await self.run_phase("architect", epic_id=epic_id)
            if not architect_result.get("success"):
                self.logger.error("Architect phase failed")
                return {"success": False, "error": "Architect phase failed"}

            self.logger.info(f"Architect phase complete for epic {epic_id}")

            # Phase 3: Issue Loop
            issues_result = await self._run_issue_loop(epic_id)
            if not issues_result.get("success"):
                self.logger.error("Issue loop failed")
                return {"success": False, "error": "Issue loop failed"}

            # Phase 4: Complete
            complete_result = await self.run_phase("complete", epic_id=epic_id)

            return {
                "success": True,
                "epic_id": epic_id,
                "tpm_result": tpm_result,
                "architect_result": architect_result,
                "issues_result": issues_result,
                "complete_result": complete_result,
            }

        except Exception as e:
            self.logger.error(f"Pipeline error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def run_phase(self, phase: str, **kwargs) -> Dict[str, Any]:
        """
        Run a specific pipeline phase.

        Args:
            phase: Phase name (tpm, architect, issue_loop, complete)
            **kwargs: Phase-specific arguments

        Returns:
            Phase result
        """
        self.logger.info(f"Running phase: {phase}")

        try:
            if phase == "tpm":
                return await self._run_tpm(kwargs.get("input_text", ""))
            elif phase == "architect":
                return await self._run_architect(kwargs.get("epic_id"))
            elif phase == "issue_loop":
                return await self._run_issue_loop(kwargs.get("epic_id"))
            elif phase == "complete":
                return await self._run_complete(kwargs.get("epic_id"))
            else:
                raise ValueError(f"Unknown phase: {phase}")

        except Exception as e:
            self.logger.error(f"Phase {phase} error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def _run_tpm(self, input_text: str) -> Dict[str, Any]:
        """
        Execute TPM (Task Planning Model) agent.

        Args:
            input_text: Input prompt

        Returns:
            TPM result with epic_id
        """
        self.logger.info("Executing TPM agent")

        if "tpm" not in self.agents:
            self.logger.error("TPM agent not registered")
            return {"success": False, "error": "TPM agent not found"}

        try:
            tpm_agent = self.agents["tpm"]
            # TPM execution would be implemented by the agent
            # This is a placeholder
            return {
                "success": True,
                "epic_id": "epic-001",
                "plan": "Epic plan from TPM",
            }
        except Exception as e:
            self.logger.error(f"TPM execution error: {e}")
            return {"success": False, "error": str(e)}

    async def _run_architect(self, epic_id: str) -> Dict[str, Any]:
        """
        Execute Architect agent for epic planning.

        Args:
            epic_id: Epic identifier

        Returns:
            Architect result
        """
        self.logger.info(f"Executing Architect for epic {epic_id}")

        if "architect" not in self.agents:
            self.logger.error("Architect agent not registered")
            return {"success": False, "error": "Architect agent not found"}

        try:
            self.state_manager.create_epic(epic_id)
            architect_agent = self.agents["architect"]
            # Architect execution would be implemented by the agent
            return {
                "success": True,
                "epic_id": epic_id,
                "issues": [],
            }
        except Exception as e:
            self.logger.error(f"Architect execution error: {e}")
            return {"success": False, "error": str(e)}

    async def _run_issue_loop(self, epic_id: str) -> Dict[str, Any]:
        """
        Run the main issue processing loop.

        Args:
            epic_id: Epic identifier

        Returns:
            Issue loop result
        """
        self.logger.info(f"Starting issue loop for epic {epic_id}")

        issues_processed = 0
        issues_failed = 0

        try:
            while True:
                next_issue = self.state_manager.get_next_issue(epic_id)
                if not next_issue:
                    break

                self.logger.info(
                    f"Processing issue {next_issue.issue_number} in epic {epic_id}"
                )

                # Run issue cycle: Engineer -> Reviewer -> QA -> Architect
                result = await self._run_issue_cycle(epic_id, next_issue.issue_number)

                if result.get("success"):
                    issues_processed += 1
                else:
                    issues_failed += 1
                    # Check if escalation needed
                    if result.get("escalate"):
                        await self._escalate(
                            epic_id,
                            next_issue.issue_number,
                            result.get("reason", "Unknown"),
                        )

            return {
                "success": issues_failed == 0,
                "issues_processed": issues_processed,
                "issues_failed": issues_failed,
            }

        except Exception as e:
            self.logger.error(f"Issue loop error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def _run_issue_cycle(
        self, epic_id: str, issue_number: int
    ) -> Dict[str, Any]:
        """
        Run full cycle for one issue: Engineer -> Reviewer -> QA -> Architect.

        Args:
            epic_id: Epic identifier
            issue_number: GitHub issue number

        Returns:
            Cycle result
        """
        self.logger.info(f"Starting cycle for issue {issue_number}")

        issue = self.state_manager.update_issue(
            epic_id,
            issue_number,
            {"status": IssueStatus.IN_PROGRESS}
        )

        try:
            # Engineer phase
            engineer_result = await self._run_engineer(epic_id, issue_number)
            if not engineer_result.get("success"):
                self.logger.warning(f"Engineer phase failed for issue {issue_number}")
                return {"success": False, "escalate": True, "reason": "Engineer phase failed"}

            pr_number = engineer_result.get("pr_number")

            # Reviewer phase
            reviewer_result = await self._run_reviewer(epic_id, issue_number, pr_number)
            if not reviewer_result.get("success"):
                self.logger.warning(f"Reviewer phase failed for issue {issue_number}")
                return {"success": False, "escalate": True, "reason": "Reviewer phase failed"}

            # QA phase
            qa_result = await self._run_qa(epic_id, issue_number, pr_number)
            if not qa_result.get("success"):
                self.logger.warning(f"QA phase failed for issue {issue_number}")
                return {"success": False, "escalate": True, "reason": "QA phase failed"}

            # Architect final review and merge
            final_result = await self._run_architect_final(epic_id, issue_number, pr_number)
            if not final_result.get("success"):
                self.logger.warning(f"Architect final phase failed for issue {issue_number}")
                return {"success": False, "escalate": True, "reason": "Architect final phase failed"}

            # Mark issue as done
            self.state_manager.update_issue(
                epic_id,
                issue_number,
                {"status": IssueStatus.DONE}
            )

            return {
                "success": True,
                "issue_number": issue_number,
                "pr_number": pr_number,
            }

        except Exception as e:
            self.logger.error(f"Issue cycle error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def _run_engineer(self, epic_id: str, issue_number: int) -> Dict[str, Any]:
        """
        Execute Engineer agent with self-fix loop.

        Args:
            epic_id: Epic identifier
            issue_number: GitHub issue number

        Returns:
            Engineer result
        """
        self.logger.info(f"Executing Engineer for issue {issue_number}")

        if "engineer" not in self.agents:
            self.logger.error("Engineer agent not registered")
            return {"success": False, "error": "Engineer agent not found"}

        max_self_fixes = self.config.get("max_self_fixes", 3)
        attempt = 0

        try:
            while attempt < max_self_fixes:
                engineer_agent = self.agents["engineer"]
                # Engineer execution would be implemented by the agent
                attempt += 1

                # Placeholder result
                return {
                    "success": True,
                    "issue_number": issue_number,
                    "pr_number": 123,
                    "self_fix_attempts": attempt,
                }

            return {"success": False, "error": f"Failed after {max_self_fixes} attempts"}

        except Exception as e:
            self.logger.error(f"Engineer execution error: {e}")
            return {"success": False, "error": str(e)}

    async def _run_reviewer(
        self, epic_id: str, issue_number: int, pr_number: int
    ) -> Dict[str, Any]:
        """
        Execute Reviewer agent.

        Args:
            epic_id: Epic identifier
            issue_number: GitHub issue number
            pr_number: Pull request number

        Returns:
            Reviewer result
        """
        self.logger.info(f"Executing Reviewer for PR {pr_number}")

        if "reviewer" not in self.agents:
            self.logger.error("Reviewer agent not registered")
            return {"success": False, "error": "Reviewer agent not found"}

        try:
            issue = self.state_manager.update_issue(
                epic_id,
                issue_number,
                {
                    "status": IssueStatus.REVIEW,
                    "pr_number": pr_number,
                }
            )

            reviewer_agent = self.agents["reviewer"]
            # Reviewer execution would be implemented by the agent

            issue.review_cycles += 1
            self.state_manager.update_issue(
                epic_id,
                issue_number,
                {"review_cycles": issue.review_cycles}
            )

            return {
                "success": True,
                "issue_number": issue_number,
                "pr_number": pr_number,
                "review_cycles": issue.review_cycles,
            }

        except Exception as e:
            self.logger.error(f"Reviewer execution error: {e}")
            return {"success": False, "error": str(e)}

    async def _run_qa(
        self, epic_id: str, issue_number: int, pr_number: int
    ) -> Dict[str, Any]:
        """
        Execute QA agent.

        Args:
            epic_id: Epic identifier
            issue_number: GitHub issue number
            pr_number: Pull request number

        Returns:
            QA result
        """
        self.logger.info(f"Executing QA for PR {pr_number}")

        if "qa" not in self.agents:
            self.logger.error("QA agent not registered")
            return {"success": False, "error": "QA agent not found"}

        try:
            issue = self.state_manager.update_issue(
                epic_id,
                issue_number,
                {
                    "status": IssueStatus.QA,
                    "pr_number": pr_number,
                }
            )

            qa_agent = self.agents["qa"]
            # QA execution would be implemented by the agent

            issue.qa_cycles += 1
            self.state_manager.update_issue(
                epic_id,
                issue_number,
                {"qa_cycles": issue.qa_cycles}
            )

            return {
                "success": True,
                "issue_number": issue_number,
                "pr_number": pr_number,
                "qa_cycles": issue.qa_cycles,
            }

        except Exception as e:
            self.logger.error(f"QA execution error: {e}")
            return {"success": False, "error": str(e)}

    async def _run_architect_final(
        self, epic_id: str, issue_number: int, pr_number: int
    ) -> Dict[str, Any]:
        """
        Execute Architect final review and merge.

        Args:
            epic_id: Epic identifier
            issue_number: GitHub issue number
            pr_number: Pull request number

        Returns:
            Final result
        """
        self.logger.info(f"Executing Architect final review for PR {pr_number}")

        if "architect" not in self.agents:
            self.logger.error("Architect agent not registered")
            return {"success": False, "error": "Architect agent not found"}

        try:
            architect_agent = self.agents["architect"]
            # Architect final execution would be implemented by the agent

            return {
                "success": True,
                "issue_number": issue_number,
                "pr_number": pr_number,
                "merged": True,
            }

        except Exception as e:
            self.logger.error(f"Architect final execution error: {e}")
            return {"success": False, "error": str(e)}

    async def _run_complete(self, epic_id: str) -> Dict[str, Any]:
        """
        Complete the epic.

        Args:
            epic_id: Epic identifier

        Returns:
            Completion result
        """
        self.logger.info(f"Completing epic {epic_id}")

        try:
            if self.state_manager.is_epic_complete(epic_id):
                self.state_manager.update_epic_status(epic_id, EpicStatus.COMPLETE)
                self.logger.info(f"Epic {epic_id} completed successfully")
                return {"success": True, "epic_id": epic_id}
            else:
                self.logger.warning(f"Epic {epic_id} has incomplete issues")
                return {"success": False, "error": "Incomplete issues remain"}

        except Exception as e:
            self.logger.error(f"Complete phase error: {e}")
            return {"success": False, "error": str(e)}

    async def _escalate(
        self, epic_id: str, issue_number: int, reason: str
    ) -> None:
        """
        Escalate issue to user.

        Args:
            epic_id: Epic identifier
            issue_number: GitHub issue number
            reason: Escalation reason
        """
        self.logger.warning(f"Escalating issue {issue_number}: {reason}")
        self.state_manager.update_issue(
            epic_id,
            issue_number,
            {"status": IssueStatus.ESCALATED}
        )
        await self._notify_user(
            f"Issue {issue_number} escalated: {reason}"
        )

    async def _notify_user(self, message: str) -> None:
        """
        Notify user with a message.

        Args:
            message: Message to send
        """
        self.logger.info(f"Notifying user: {message}")
        # Implementation would send notification to user
        pass
