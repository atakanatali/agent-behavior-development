"""
Workflow State Machine for ABD orchestration engine.

Manages the development workflow state transitions using the transitions library.
Tracks cycles (review and QA) and persists state via StateManager.
"""

import logging
from enum import Enum
from typing import Any, Callable, Dict, Optional

from transitions import Machine, MachineError

from orchestify.core.state import StateManager

logger = logging.getLogger(__name__)


class WorkflowState(str, Enum):
    """Enumeration of all possible workflow states."""

    INIT = "init"
    TPM_GATHERING = "tpm_gathering"
    TPM_CREATING_ISSUES = "tpm_creating_issues"
    ARCHITECT_REVIEWING = "architect_reviewing"
    ARCHITECT_DISTRIBUTING = "architect_distributing"
    ENGINEER_DEVELOPING = "engineer_developing"
    REVIEWER_REVIEWING = "reviewer_reviewing"
    ENGINEER_FIXING_REVIEW = "engineer_fixing_review"
    QA_TESTING = "qa_testing"
    ENGINEER_FIXING_QA = "engineer_fixing_qa"
    ARCHITECT_FINAL_REVIEW = "architect_final_review"
    MERGING = "merging"
    NEXT_ISSUE = "next_issue"
    EPIC_COMPLETE = "epic_complete"
    ESCALATED = "escalated"
    ERROR = "error"


class WorkflowManager:
    """
    Manages the ABD development workflow state machine.

    Coordinates state transitions, cycle tracking, and persistence for the
    development workflow. Uses the transitions library for robust state management.

    Attributes:
        state_manager: StateManager instance for persisting workflow state
        config: OrchestrifyConfig instance with orchestration settings
        review_cycle_count: Current review cycle count for current issue
        qa_cycle_count: Current QA cycle count for current issue
        max_review_cycles: Maximum allowed review cycles per issue
        max_qa_cycles: Maximum allowed QA cycles per issue
        current_state: Current workflow state
        _callbacks: Dictionary of registered callbacks for state transitions
    """

    def __init__(self, state_manager: StateManager, config: Any) -> None:
        """
        Initialize the workflow manager.

        Args:
            state_manager: StateManager instance for persisting state
            config: OrchestrifyConfig instance with orchestration settings

        Raises:
            ValueError: If configuration is invalid
        """
        self.state_manager = state_manager
        self.config = config
        self.review_cycle_count = 0
        self.qa_cycle_count = 0
        self.max_review_cycles = config.orchestration.max_review_cycles
        self.max_qa_cycles = config.orchestration.max_qa_cycles

        self.current_state: str = WorkflowState.INIT.value
        self._callbacks: Dict[str, list[Callable]] = {}

        logger.debug(
            f"Initializing WorkflowManager with max_review_cycles="
            f"{self.max_review_cycles}, max_qa_cycles={self.max_qa_cycles}"
        )

        self._setup_state_machine()

    def _setup_state_machine(self) -> None:
        """Set up the transitions-based state machine with all transitions and callbacks."""
        transitions = [
            # TPM flow
            {
                "trigger": "start_gathering",
                "source": WorkflowState.INIT.value,
                "dest": WorkflowState.TPM_GATHERING.value,
            },
            {
                "trigger": "start_issue_creation",
                "source": WorkflowState.TPM_GATHERING.value,
                "dest": WorkflowState.TPM_CREATING_ISSUES.value,
            },
            # Architect flow
            {
                "trigger": "start_architect_review",
                "source": WorkflowState.TPM_CREATING_ISSUES.value,
                "dest": WorkflowState.ARCHITECT_REVIEWING.value,
            },
            {
                "trigger": "start_distribution",
                "source": WorkflowState.ARCHITECT_REVIEWING.value,
                "dest": WorkflowState.ARCHITECT_DISTRIBUTING.value,
            },
            # Engineer development
            {
                "trigger": "start_development",
                "source": [
                    WorkflowState.ARCHITECT_DISTRIBUTING.value,
                    WorkflowState.NEXT_ISSUE.value,
                ],
                "dest": WorkflowState.ENGINEER_DEVELOPING.value,
            },
            # Review cycle
            {
                "trigger": "submit_for_review",
                "source": [
                    WorkflowState.ENGINEER_DEVELOPING.value,
                    WorkflowState.ENGINEER_FIXING_REVIEW.value,
                    WorkflowState.ENGINEER_FIXING_QA.value,
                ],
                "dest": WorkflowState.REVIEWER_REVIEWING.value,
            },
            {
                "trigger": "request_review_changes",
                "source": WorkflowState.REVIEWER_REVIEWING.value,
                "dest": WorkflowState.ENGINEER_FIXING_REVIEW.value,
                "conditions": ["can_review_cycle"],
                "before": ["increment_review_cycle"],
            },
            {
                "trigger": "review_approved",
                "source": WorkflowState.REVIEWER_REVIEWING.value,
                "dest": WorkflowState.QA_TESTING.value,
            },
            # QA cycle
            {
                "trigger": "request_qa_changes",
                "source": WorkflowState.QA_TESTING.value,
                "dest": WorkflowState.ENGINEER_FIXING_QA.value,
                "conditions": ["can_qa_cycle"],
                "before": ["increment_qa_cycle"],
            },
            {
                "trigger": "qa_approved",
                "source": WorkflowState.QA_TESTING.value,
                "dest": WorkflowState.ARCHITECT_FINAL_REVIEW.value,
            },
            # Final approval and merge
            {
                "trigger": "approve_final",
                "source": WorkflowState.ARCHITECT_FINAL_REVIEW.value,
                "dest": WorkflowState.MERGING.value,
            },
            {
                "trigger": "merged",
                "source": WorkflowState.MERGING.value,
                "dest": WorkflowState.NEXT_ISSUE.value,
                "before": ["reset_cycles"],
            },
            {
                "trigger": "all_done",
                "source": WorkflowState.NEXT_ISSUE.value,
                "dest": WorkflowState.EPIC_COMPLETE.value,
            },
            # Escalation and error handling
            {
                "trigger": "escalate",
                "source": "*",
                "dest": WorkflowState.ESCALATED.value,
            },
            {
                "trigger": "error_occurred",
                "source": "*",
                "dest": WorkflowState.ERROR.value,
            },
            # Resume from escalation/error
            {
                "trigger": "resume",
                "source": [WorkflowState.ESCALATED.value, WorkflowState.ERROR.value],
                "dest": WorkflowState.ENGINEER_DEVELOPING.value,
                "before": ["reset_cycles"],
            },
        ]

        self.machine = Machine(
            model=self,
            states=[s.value for s in WorkflowState],
            transitions=transitions,
            initial=WorkflowState.INIT.value,
            send_event=True,
            auto_transitions=False,
        )

        # Register callbacks for state entry
        for state in WorkflowState:
            state_value = state.value
            setattr(
                self,
                f"on_enter_{state_value}",
                self._create_enter_callback(state_value),
            )

        logger.debug("State machine configured successfully")

    def _create_enter_callback(self, state: str) -> Callable:
        """
        Create a callback function for entering a state.

        Args:
            state: The state being entered

        Returns:
            Callback function that logs and persists state
        """

        def callback(event: Any = None) -> None:
            self.current_state = state
            logger.info(f"Entered state: {state}")

        return callback

    def can_review_cycle(self, event: Any = None) -> bool:
        """
        Check if another review cycle is allowed.

        Args:
            event: Transition event (unused but required by transitions library)

        Returns:
            True if review cycle count < max, False otherwise
        """
        result = self.review_cycle_count < self.max_review_cycles
        logger.debug(
            f"can_review_cycle check: {self.review_cycle_count}/"
            f"{self.max_review_cycles} = {result}"
        )
        return result

    def can_qa_cycle(self, event: Any = None) -> bool:
        """
        Check if another QA cycle is allowed.

        Args:
            event: Transition event (unused but required by transitions library)

        Returns:
            True if QA cycle count < max, False otherwise
        """
        result = self.qa_cycle_count < self.max_qa_cycles
        logger.debug(
            f"can_qa_cycle check: {self.qa_cycle_count}/"
            f"{self.max_qa_cycles} = {result}"
        )
        return result

    def increment_review_cycle(self, event: Any = None) -> None:
        """
        Increment the review cycle counter.

        Args:
            event: Transition event (unused but required by transitions library)
        """
        self.review_cycle_count += 1
        logger.debug(f"Incremented review cycle: {self.review_cycle_count}")

    def increment_qa_cycle(self, event: Any = None) -> None:
        """
        Increment the QA cycle counter.

        Args:
            event: Transition event (unused but required by transitions library)
        """
        self.qa_cycle_count += 1
        logger.debug(f"Incremented QA cycle: {self.qa_cycle_count}")

    def reset_cycles(self, event: Any = None) -> None:
        """
        Reset both review and QA cycle counters for next issue.

        Args:
            event: Transition event (unused but required by transitions library)
        """
        self.review_cycle_count = 0
        self.qa_cycle_count = 0
        logger.debug("Reset all cycle counters for next issue")

    def get_current_state(self) -> str:
        """
        Get the current workflow state.

        Returns:
            Current state string
        """
        return self.current_state

    def get_cycle_info(self) -> Dict[str, int]:
        """
        Get current cycle tracking information.

        Returns:
            Dictionary with keys:
                - review_count: Current review cycle count
                - review_max: Maximum review cycles allowed
                - qa_count: Current QA cycle count
                - qa_max: Maximum QA cycles allowed
        """
        return {
            "review_count": self.review_cycle_count,
            "review_max": self.max_review_cycles,
            "qa_count": self.qa_cycle_count,
            "qa_max": self.max_qa_cycles,
        }

    def register_callback(
        self, event_name: str, callback: Callable[..., None]
    ) -> None:
        """
        Register a custom callback for state transitions.

        Args:
            event_name: Event name (e.g., 'before_start_development', 'after_merged')
            callback: Callback function to execute

        Raises:
            ValueError: If event_name is invalid
        """
        if event_name not in self._callbacks:
            self._callbacks[event_name] = []

        self._callbacks[event_name].append(callback)
        logger.debug(f"Registered callback for event: {event_name}")

    def can_transition(self, trigger: str) -> bool:
        """
        Check if a state transition is currently possible.

        Args:
            trigger: Trigger/event name to attempt

        Returns:
            True if transition is valid from current state, False otherwise
        """
        try:
            # Check if trigger exists and if conditions are met
            if not hasattr(self, trigger):
                return False

            # Attempt dry-run by checking state machine configuration
            current = self.get_current_state()
            trigger_config = None

            for trans in self.machine.transitions.get(current, []):
                if trans.trigger == trigger:
                    trigger_config = trans
                    break

            if trigger_config is None:
                return False

            # Check conditions if they exist
            if trigger_config.conditions:
                for condition in trigger_config.conditions:
                    if isinstance(condition, str):
                        if not getattr(self, condition, lambda: False)():
                            return False
                    else:
                        if not condition():
                            return False

            return True
        except Exception as e:
            logger.debug(f"Error checking transition possibility: {e}")
            return False

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize workflow state to dictionary.

        Returns:
            Dictionary representation of current workflow state
        """
        return {
            "current_state": self.current_state,
            "review_cycle_count": self.review_cycle_count,
            "review_cycle_max": self.max_review_cycles,
            "qa_cycle_count": self.qa_cycle_count,
            "qa_cycle_max": self.max_qa_cycles,
        }

    def __str__(self) -> str:
        """Return string representation of workflow state."""
        return (
            f"WorkflowManager(state={self.current_state}, "
            f"review={self.review_cycle_count}/{self.max_review_cycles}, "
            f"qa={self.qa_cycle_count}/{self.max_qa_cycles})"
        )

    def __repr__(self) -> str:
        """Return detailed string representation."""
        return self.__str__()
