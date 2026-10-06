"""Unit tests for the lead state machine."""
from __future__ import annotations

import pytest

from app.core.state_machine import (
    TERMINAL_STATES,
    StateTransitionError,
    can_transition,
    transition,
)


def test_valid_transitions():
    assert can_transition("discovered", "enriched")
    assert can_transition("enriched", "profiled")
    assert can_transition("profiled", "demo_ready")
    assert can_transition("demo_ready", "queued_email")
    assert can_transition("demo_ready", "queued_call")
    assert can_transition("queued_email", "contacted")
    assert can_transition("contacted", "replied")
    assert can_transition("contacted", "opted_out")
    assert can_transition("contacted", "bounced")
    assert can_transition("replied", "interested")
    assert can_transition("interested", "won")


def test_invalid_transitions_raise():
    with pytest.raises(StateTransitionError):
        transition("discovered", "contacted")  # skip stages
    with pytest.raises(StateTransitionError):
        transition("enriched", "demo_ready")
    with pytest.raises(StateTransitionError):
        transition("queued_email", "interested")
    with pytest.raises(StateTransitionError):
        transition("no_contact", "profiled")


def test_terminal_states_have_no_out():
    for state in TERMINAL_STATES:
        assert can_transition(state, "contacted") is False


def test_opt_out_is_terminal_everywhere_relevant():
    # once opted out, no outgoing transitions exist
    assert not can_transition("opted_out", "contacted")
    assert not can_transition("opted_out", "replied")
