"""Provider Event Handler for mapping carrier events to domain state machines safely."""

import logging
import threading
from dialguard.exceptions import InvalidStateTransitionError, TerminalStateError
from dialguard.models.agent import Agent
from dialguard.models.call import Call
from dialguard.repository.in_memory import InMemoryRepository
from dialguard.state.agent_state import AgentState
from dialguard.state.call_state import CallState
from dialguard.telecom.events import ProviderCallEvent, TelecomEventType

logger = logging.getLogger(__name__)


class ProviderEventHandler:
    """Processes incoming telecom events, synchronizing Call and Agent states safely.

    Design Decisions (Prototype Choices):
    - In-memory event deduplication set tracking processed event_ids.
    - Milestone tracking to prevent reprocessing identical (call_id, event_type) transitions.
    - Out-of-order and terminal protection: Late events on terminal calls are safely discarded.
    """

    def __init__(self, repository: InMemoryRepository) -> None:
        self.repository = repository
        self._lock = threading.RLock()
        self._processed_event_ids: set[str] = set()
        self._processed_milestones: set[tuple[str, TelecomEventType]] = set()

    def handle_event(self, event: ProviderCallEvent) -> bool:
        """Process an incoming provider call event idempotently and safely.

        Returns True if the event caused a state transition; False if ignored/deduplicated.
        """
        with self._lock:
            # 1. Deduplication by unique event_id
            if event.event_id in self._processed_event_ids:
                logger.warning(
                    "Duplicate event_id '%s' received for call '%s'. Ignoring.",
                    event.event_id,
                    event.call_id,
                )
                return False

            self._processed_event_ids.add(event.event_id)

            # 2. Retrieve Call from repository
            call = self.repository.get_call(event.call_id)
            if call is None:
                logger.error(
                    "Received event for non-existent call_id '%s'. Event: %s",
                    event.call_id,
                    event.event_type,
                )
                return False

            # 3. Check if call is already in a terminal state
            if call.is_terminal:
                logger.info(
                    "Call '%s' is already in terminal state '%s'. Discarding out-of-order event '%s'.",
                    call.id,
                    call.state,
                    event.event_type,
                )
                return False

            # 4. Deduplication by milestone (prevent re-applying identical state)
            milestone = (event.call_id, event.event_type)
            if milestone in self._processed_milestones:
                logger.info(
                    "Duplicate milestone '%s' for call '%s'. Ignoring.",
                    event.event_type,
                    event.call_id,
                )
                return False

            # 5. Map event to CallState & AgentState transitions
            success = self._apply_event_transition(call, event)
            if success:
                self._processed_milestones.add(milestone)
            return success

    def _apply_event_transition(
        self, call: Call, event: ProviderCallEvent
    ) -> bool:
        """Apply state transition based on telecom event type."""
        agent = (
            self.repository.get_agent(call.agent_id) if call.agent_id else None
        )

        try:
            match event.event_type:
                case TelecomEventType.INITIATED:
                    if call.can_transition_to(CallState.INITIATED):
                        call.transition_to(CallState.INITIATED)
                        if agent and agent.can_transition_to(
                            AgentState.DIALING
                        ):
                            agent.transition_to(AgentState.DIALING)
                        return True
                    else:
                        logger.warning(
                            "Cannot transition call '%s' from '%s' to INITIATED",
                            call.id,
                            call.state,
                        )
                        return False

                case TelecomEventType.RINGING:
                    if call.can_transition_to(CallState.RINGING):
                        call.transition_to(CallState.RINGING)
                        return True
                    else:
                        logger.warning(
                            "Out-of-order or invalid RINGING for call '%s' in state '%s'",
                            call.id,
                            call.state,
                        )
                        return False

                case TelecomEventType.ANSWERED:
                    if call.can_transition_to(CallState.ANSWERED):
                        call.transition_to(CallState.ANSWERED)
                        # Bridge to CONNECTED if agent assigned
                        if agent and call.can_transition_to(
                            CallState.CONNECTED
                        ):
                            call.transition_to(CallState.CONNECTED)
                            if agent.can_transition_to(AgentState.CONNECTED):
                                agent.transition_to(AgentState.CONNECTED)
                        return True
                    else:
                        logger.warning(
                            "Cannot transition call '%s' from '%s' to ANSWERED",
                            call.id,
                            call.state,
                        )
                        return False

                case TelecomEventType.COMPLETED:
                    if call.can_transition_to(CallState.COMPLETED):
                        call.transition_to(CallState.COMPLETED)
                        if agent and agent.can_transition_to(
                            AgentState.WRAP_UP
                        ):
                            agent.transition_to(AgentState.WRAP_UP)
                        return True
                    else:
                        logger.warning(
                            "Cannot complete call '%s' in state '%s'",
                            call.id,
                            call.state,
                        )
                        return False

                case TelecomEventType.FAILED | TelecomEventType.TIMEOUT:
                    if call.can_transition_to(CallState.FAILED):
                        call.transition_to(CallState.FAILED)
                        if agent:
                            if agent.can_transition_to(AgentState.AVAILABLE):
                                agent.transition_to(AgentState.AVAILABLE)
                            elif agent.can_transition_to(AgentState.WRAP_UP):
                                agent.transition_to(AgentState.WRAP_UP)
                        return True
                    else:
                        logger.warning(
                            "Cannot fail call '%s' in state '%s'",
                            call.id,
                            call.state,
                        )
                        return False

                case _:
                    logger.error(
                        "Unhandled event type '%s' for call '%s'",
                        event.event_type,
                        call.id,
                    )
                    return False

        except (InvalidStateTransitionError, TerminalStateError) as e:
            logger.error("State transition error during event handling: %s", e)
            return False
