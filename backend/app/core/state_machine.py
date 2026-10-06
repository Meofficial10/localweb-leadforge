"""Lead state machine.

States and the allowed transitions from the App Flow section:

discovered       -> enriched, rejected
enriched         -> profiled, no_contact
profiled         -> ready (internal; we transition to demo_ready only after build)
demo_ready       -> queued_email, queued_call, rejected
queued_email     -> contacted
queued_call      -> contacted
contacted        -> followup_sent, replied, opted_out, bounced
followup_sent    -> replied, closed_no_response, opted_out
replied          -> interested, not_interested, opted_out
interested       -> won, lost
opted_out        -> (terminal)
closed_no_response-> (terminal)
no_contact       -> (terminal)
rejected         -> (terminal)
bounced          -> (terminal, retryable via enrich)
won / lost       -> (terminal)

Every transition is validated; invalid transitions raise StateTransitionError.
"""
from __future__ import annotations


class StateTransitionError(Exception):
    pass


# Allowed transitions
TRANSITIONS: dict[str, set[str]] = {
    "discovered": {"enriched", "rejected"},
    "enriched": {"profiled", "no_contact"},
    "profiled": {"demo_ready"},
    "demo_ready": {"queued_email", "queued_call", "rejected"},
    "queued_email": {"contacted"},
    "queued_call": {"contacted"},
    "contacted": {"followup_sent", "replied", "opted_out", "bounced"},
    "followup_sent": {"replied", "closed_no_response", "opted_out"},
    "replied": {"interested", "not_interested", "opted_out"},
    "interested": {"won", "lost"},
    "opted_out": set(),
    "closed_no_response": set(),
    "no_contact": set(),
    "rejected": set(),
    "bounced": {"enriched"},  # allow re-enrichment of a dead contact
    "won": set(),
    "lost": set(),
}

TERMINAL_STATES = {"opted_out", "closed_no_response", "no_contact", "rejected", "won", "lost"}


def can_transition(current: str, target: str) -> bool:
    return target in TRANSITIONS.get(current, set())


def transition(current: str, target: str) -> str:
    """Validate and return the new state; raises if invalid."""
    if not can_transition(current, target):
        raise StateTransitionError(
            f"Invalid state transition: {current!r} -> {target!r}"
        )
    return target
