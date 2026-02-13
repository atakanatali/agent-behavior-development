"""
Data models for the orchestify database layer.

Lightweight dataclasses that map to database rows.
"""
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional


def _now() -> str:
    return datetime.utcnow().isoformat()


@dataclass
class SprintRow:
    sprint_id: str
    status: str = "created"
    prompt: Optional[str] = None
    epic_id: Optional[str] = None
    issues_total: int = 0
    issues_done: int = 0
    pid: Optional[int] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=_now)
    started_at: Optional[str] = None
    paused_at: Optional[str] = None
    completed_at: Optional[str] = None
    updated_at: str = field(default_factory=_now)
    id: Optional[int] = None


@dataclass
class EpicRow:
    epic_id: str
    sprint_id: Optional[str] = None
    status: str = "pending"
    metadata: Optional[str] = None  # JSON
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    id: Optional[int] = None


@dataclass
class IssueRow:
    issue_number: int
    epic_id: str
    sprint_id: Optional[str] = None
    status: str = "pending"
    assigned_agent: Optional[str] = None
    branch_name: Optional[str] = None
    pr_number: Optional[int] = None
    review_cycles: int = 0
    qa_cycles: int = 0
    self_fix_attempts: int = 0
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    id: Optional[int] = None


@dataclass
class CycleRow:
    issue_id: int
    cycle_number: int
    agent_from: str
    agent_to: str
    action: str
    result: Optional[str] = None
    timestamp: str = field(default_factory=_now)
    id: Optional[int] = None


@dataclass
class AgentMessageRow:
    sprint_id: str
    agent_id: str
    message_type: str  # log, output, error, warning, communication, checkpoint
    content: str
    epic_id: Optional[str] = None
    issue_id: Optional[int] = None
    level: Optional[str] = "INFO"
    related_agent: Optional[str] = None
    metadata: Optional[str] = None  # JSON
    timestamp: str = field(default_factory=_now)
    id: Optional[int] = None


@dataclass
class AgentLogRow:
    sprint_id: str
    agent_id: str
    event: str
    level: str = "INFO"
    data: Optional[str] = None  # JSON
    timestamp: str = field(default_factory=_now)
    id: Optional[int] = None


@dataclass
class ScorecardRow:
    issue_id: int
    agent_id: str
    scope_control: int = 0
    behavior_fidelity: int = 0
    evidence_orientation: int = 0
    actionability: int = 0
    risk_awareness: int = 0
    total: int = 0
    interpretation: Optional[str] = None  # promote/recycle/anti-pattern
    created_at: str = field(default_factory=_now)
    id: Optional[int] = None


@dataclass
class RecyclePatternRow:
    issue_id: int
    pattern_type: str  # kept, reused, banned
    pattern_value: str
    applied_by: Optional[str] = None
    applied_at: str = field(default_factory=_now)
    id: Optional[int] = None


