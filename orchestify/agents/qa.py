"""QA Tester agent for specification and security testing."""

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List

from orchestify.agents.base import ConcreteAgent
from orchestify.core.agent import AgentContext, AgentResult

logger = logging.getLogger(__name__)


@dataclass
class QAResult:
    """Result of QA testing."""

    approved: bool
    spec_findings: List[Dict[str, str]] = field(default_factory=list)
    security_findings: List[Dict[str, str]] = field(default_factory=list)
    overall_assessment: str = ""


class QAAgent(ConcreteAgent):
    """QA agent for testing and validation."""

    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute QA testing."""
        pr_num = 1
        if context.memory_context:
            pr_num = context.memory_context.get("pr_number", 1)

        issue = {
            "number": pr_num,
            "title": context.goal,
            "body": context.behavior_spec,
        }

        result = await self.execute_testing(pr_num, issue)
        status = "PASSED" if result.approved else "FAILED"
        return AgentResult(
            output=f"QA {status}. Spec: {len(result.spec_findings)}, "
            f"Security: {len(result.security_findings)}"
        )

    async def execute_testing(
        self, pr_number: int, issue: Dict
    ) -> QAResult:
        """Execute QA testing."""
        start = time.time()

        try:
            logger.info(f"QA testing PR #{pr_number}")

            diff = issue.get("body", "")

            spec_findings = await self._validate_against_spec(diff, issue)
            security_findings = await self._security_check(diff)

            approved = (
                len(spec_findings) == 0 and len(security_findings) == 0
            )
            assessment = self._generate_assessment(
                spec_findings, security_findings, approved
            )

            await self._post_findings(
                pr_number, spec_findings + security_findings, approved
            )

            result = QAResult(
                approved=approved,
                spec_findings=spec_findings,
                security_findings=security_findings,
                overall_assessment=assessment,
            )

            agent_result = AgentResult(
                output=assessment,
                commands_run=["qa:test"],
                duration=time.time() - start,
            )
            self._log_interaction(
                AgentContext(
                    goal=f"QA PR #{pr_number}",
                    instructions="",
                    behavior_spec="",
                ),
                agent_result,
            )

            return result

        except Exception as e:
            logger.error(f"QA failed: {e}")
            raise RuntimeError(f"QA failed: {e}") from e

    async def _validate_against_spec(
        self, diff: str, issue: Dict
    ) -> List[Dict[str, str]]:
        """Validate against specification."""
        ctx = AgentContext(
            goal="Validate against spec",
            instructions=f"Spec:\n{issue.get('body', '')}\n\nDiff:\n{diff}",
            behavior_spec="Check requirements match",
        )

        response = await self._call_llm(ctx)
        return self._parse_qa_findings(response, "spec")

    async def _security_check(self, diff: str) -> List[Dict[str, str]]:
        """Check security."""
        ctx = AgentContext(
            goal="Security check",
            instructions=f"Diff:\n{diff}",
            behavior_spec="Check: secrets, injection, XSS, auth",
        )

        response = await self._call_llm(ctx)
        return self._parse_qa_findings(response, "security")

    async def _post_findings(
        self,
        pr_number: int,
        findings: List[Dict[str, str]],
        approved: bool,
    ) -> None:
        """Post findings."""
        try:
            from orchestify.github.client import GitHubClient

            token = self.config.get("github_token")
            if not token:
                return

            client = GitHubClient(
                token=token,
                repo_owner=self.config.get("repo_owner"),
                repo_name=self.config.get("repo_name"),
            )

            repo = client.get_repo()
            pr = repo.get_pull(pr_number)

            report = "## QA Report\n"
            if approved:
                report += "✅ All tests passed\n"
            else:
                report += f"❌ {len(findings)} issues\n"

            pr.create_issue_comment(report)
        except Exception as e:
            logger.warning(f"Post failed: {e}")

    def _parse_qa_findings(
        self, response: str, ftype: str
    ) -> List[Dict[str, str]]:
        """Parse findings."""
        findings = []
        for line in response.split("\n"):
            if " - " in line:
                parts = [p.strip() for p in line.split(" - ")]
                if len(parts) >= 2:
                    findings.append(
                        {
                            "type": ftype,
                            "title": parts[0],
                            "message": " - ".join(parts[1:]),
                        }
                    )
        return findings

    def _generate_assessment(
        self,
        spec_findings: List[Dict],
        security_findings: List[Dict],
        approved: bool,
    ) -> str:
        """Generate assessment."""
        status = "✅ PASSED" if approved else "❌ FAILED"
        return (
            f"{status}\nSpec: {len(spec_findings)}, "
            f"Security: {len(security_findings)}"
        )
