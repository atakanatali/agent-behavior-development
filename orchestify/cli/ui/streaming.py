"""Rich streaming display for agent execution."""
import time
from typing import Optional
from rich.console import Console
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.spinner import Spinner

console = Console()


class AgentStreamDisplay:
    """Live display for streaming agent output."""

    def __init__(self):
        self.current_agent: Optional[str] = None
        self.current_phase: Optional[str] = None
        self.agent_outputs: dict = {}
        self.status_log: list = []

    def _build_layout(self) -> Layout:
        """Build the Rich layout."""
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=5),
        )
        layout["body"].split_row(
            Layout(name="agents", ratio=1),
            Layout(name="output", ratio=2),
        )
        return layout

    def _render_header(self) -> Panel:
        """Render header panel."""
        phase_text = self.current_phase or "Idle"
        agent_text = self.current_agent or "None"
        return Panel(
            f"[bold cyan]Phase:[/bold cyan] {phase_text}  |  "
            f"[bold yellow]Agent:[/bold yellow] {agent_text}",
            style="cyan",
        )

    def _render_agents_panel(self) -> Panel:
        """Render agents status panel."""
        table = Table(show_header=True, header_style="bold cyan", box=None)
        table.add_column("Agent", style="cyan")
        table.add_column("Status", style="green")

        statuses = {
            "tpm": "pending",
            "architect": "pending",
            "engineer": "pending",
            "reviewer": "pending",
            "qa": "pending",
        }

        for agent_id, status in statuses.items():
            icon = {"running": "[yellow]...[/yellow]", "done": "[green]OK[/green]",
                    "failed": "[red]X[/red]", "pending": "[dim]--[/dim]"}.get(status, "[dim]--[/dim]")
            table.add_row(agent_id, icon)

        return Panel(table, title="Agents", border_style="cyan")

    def _render_output(self) -> Panel:
        """Render current output panel."""
        if self.current_agent and self.current_agent in self.agent_outputs:
            output = self.agent_outputs[self.current_agent][-2000:]
        else:
            output = "[dim]Waiting for agent output...[/dim]"
        return Panel(output, title="Output", border_style="green")

    def _render_footer(self) -> Panel:
        """Render log footer."""
        recent = self.status_log[-5:] if self.status_log else ["[dim]No activity yet[/dim]"]
        return Panel("\n".join(recent), title="Log", border_style="dim")

    def update(self, agent_id: str, phase: str, text: str) -> None:
        """Update display state."""
        self.current_agent = agent_id
        self.current_phase = phase
        if agent_id not in self.agent_outputs:
            self.agent_outputs[agent_id] = ""
        self.agent_outputs[agent_id] += text

    def log(self, message: str) -> None:
        """Add a log entry."""
        ts = time.strftime("%H:%M:%S")
        self.status_log.append(f"[dim]{ts}[/dim] {message}")


class PipelineDisplay:
    """Simple pipeline progress display."""

    PHASES = ["TPM", "Architect", "Engineer", "Reviewer", "QA", "Complete"]

    def __init__(self):
        self.current_phase_idx = 0
        self.issue_progress = (0, 0)

    def render(self) -> Panel:
        """Render the pipeline progress."""
        parts = []
        for i, phase in enumerate(self.PHASES):
            if i < self.current_phase_idx:
                parts.append(f"[green]{phase}[/green]")
            elif i == self.current_phase_idx:
                parts.append(f"[bold yellow]> {phase}[/bold yellow]")
            else:
                parts.append(f"[dim]{phase}[/dim]")

        pipeline_str = " -> ".join(parts)

        issues_done, issues_total = self.issue_progress
        progress = f"Issues: {issues_done}/{issues_total}" if issues_total > 0 else ""

        return Panel(
            f"{pipeline_str}\n{progress}",
            title="Pipeline Progress",
            border_style="cyan",
        )

    def advance(self):
        """Move to next phase."""
        if self.current_phase_idx < len(self.PHASES) - 1:
            self.current_phase_idx += 1
