"""Simulation Runner for DialGuard campaign scenarios."""

import random
from dialguard.allocator.call_allocator import CallAllocator
from dialguard.dialer.predictive import PredictiveDialer
from dialguard.dialer.progressive import ProgressiveDialer
from dialguard.models.agent import Agent
from dialguard.models.borrower import Borrower
from dialguard.models.call import Call
from dialguard.pacing.engine import PredictivePacingEngine
from dialguard.repository.in_memory import InMemoryRepository
from dialguard.safety.safety_controller import SafetyController
from dialguard.simulation.metrics import SimulationMetrics
from dialguard.state.agent_state import AgentState
from dialguard.state.call_state import CallState
from dialguard.telecom.event_handler import ProviderEventHandler
from dialguard.telecom.events import ProviderCallEvent, TelecomEventType
from dialguard.telecom.flaky_provider import FlakyProvider
from dialguard.telecom.reliable_provider import ReliableProvider


class CampaignSimulator:
    """Discrete-step campaign simulator comparing Progressive vs Predictive dialing."""

    def __init__(
        self,
        num_agents: int = 10,
        num_borrowers: int = 200,
        ticks_per_cycle: int = 1,
    ) -> None:
        self.num_agents = num_agents
        self.num_borrowers = num_borrowers
        self.ticks_per_cycle = ticks_per_cycle

    def _setup_environment(
        self, is_flaky: bool = False
    ) -> tuple[
        InMemoryRepository,
        CallAllocator,
        SafetyController,
        PredictivePacingEngine,
        ProviderEventHandler,
        ReliableProvider | FlakyProvider,
    ]:
        repository = InMemoryRepository()

        # Seed agents
        for i in range(1, self.num_agents + 1):
            agent = Agent(id=f"agent-{i:03d}", state=AgentState.AVAILABLE)
            repository.add_agent(agent)

        # Seed borrowers & queued calls
        for i in range(1, self.num_borrowers + 1):
            borrower = Borrower(id=f"borrower-{i:04d}", name=f"Borrower {i}")
            repository.add_borrower(borrower)
            call = Call(id=f"call-{i:04d}", borrower_id=borrower.id)
            repository.add_call(call)

        allocator = CallAllocator(repository)
        safety_controller = SafetyController()
        pacing_engine = PredictivePacingEngine()
        event_handler = ProviderEventHandler(repository)

        if is_flaky:
            provider = FlakyProvider()
        else:
            provider = ReliableProvider()

        provider.register_listener(event_handler.handle_event)

        return (
            repository,
            allocator,
            safety_controller,
            pacing_engine,
            event_handler,
            provider,
        )

    def run_scenario(
        self,
        scenario_name: str,
        dialer_mode: str,  # "PROGRESSIVE" or "PREDICTIVE"
        answer_rate: float,
        avg_talk_time_cycles: int,
        total_cycles: int = 60,
        dynamic_degradation: bool = False,
    ) -> SimulationMetrics:
        """Run a single simulation scenario for a given dialer mode."""
        (
            repository,
            allocator,
            safety_controller,
            pacing_engine,
            event_handler,
            provider,
        ) = self._setup_environment(is_flaky=dynamic_degradation)

        metrics = SimulationMetrics(
            scenario_name=scenario_name,
            dialer_mode=dialer_mode,
            total_cycles=total_cycles,
        )

        progressive_dialer = ProgressiveDialer(
            repository=repository,
            allocator=allocator,
            safety_controller=safety_controller,
            provider=provider,
        )
        predictive_dialer = PredictiveDialer(
            repository=repository,
            allocator=allocator,
            pacing_engine=pacing_engine,
            safety_controller=safety_controller,
            provider=provider,
        )

        # Track active call durations: {call_id: remaining_cycles}
        active_conversations: dict[str, int] = {}
        # Track wrap-up durations: {agent_id: remaining_cycles}
        active_wrapups: dict[str, int] = {}

        current_answer_rate = answer_rate

        for cycle in range(1, total_cycles + 1):
            # Dynamic conditions handling for Scenario D
            if dynamic_degradation and cycle >= (total_cycles // 2):
                current_answer_rate = 0.15
                if isinstance(provider, FlakyProvider):
                    provider.set_health_score(0.60)

            # 1. Update Agent utilization metrics
            for agent in repository.list_agents():
                metrics.cumulative_agent_total_ticks += 1
                if agent.state == AgentState.CONNECTED:
                    metrics.cumulative_agent_talk_ticks += 1
                elif agent.state == AgentState.AVAILABLE:
                    metrics.cumulative_agent_idle_ticks += 1

            # 2. Advance active wrap-ups
            completed_wrapups: list[str] = []
            for agent_id, rem in list(active_wrapups.items()):
                if rem <= 1:
                    agent = repository.get_agent(agent_id)
                    if agent and agent.state == AgentState.WRAP_UP:
                        agent.transition_to(AgentState.AVAILABLE)
                    completed_wrapups.append(agent_id)
                else:
                    active_wrapups[agent_id] = rem - 1
            for aid in completed_wrapups:
                active_wrapups.pop(aid, None)

            # 3. Advance active conversations
            ended_conversations: list[str] = []
            for call_id, rem in list(active_conversations.items()):
                if rem <= 1:
                    call = repository.get_call(call_id)
                    if call and call.state == CallState.CONNECTED:
                        # Complete call via provider event
                        event_handler.handle_event(
                            ProviderCallEvent(
                                call_id=call.id,
                                event_type=TelecomEventType.COMPLETED,
                            )
                        )
                        metrics.total_calls_completed += 1
                        if call.agent_id:
                            # Start wrap up (1 cycle)
                            active_wrapups[call.agent_id] = 1
                    ended_conversations.append(call_id)
                else:
                    active_conversations[call_id] = rem - 1
            for cid in ended_conversations:
                active_conversations.pop(cid, None)

            # 4. Execute Dialer Cycle
            if dialer_mode == "PROGRESSIVE":
                result = progressive_dialer.execute_cycle()
                dials_attempted = result.initiated_calls
                if (
                    result.requested_calls > 0
                    and result.approved_calls < result.requested_calls
                ):
                    metrics.safety_throttles += 1
                allocated_pairs = result.allocated_pairs
            else:
                pred_result = predictive_dialer.execute_cycle(
                    recent_answer_rate=current_answer_rate,
                    avg_call_duration_seconds=float(avg_talk_time_cycles),
                )
                dials_attempted = pred_result.initiated_calls
                decision = pred_result.safety_decision
                if (
                    decision.requested_calls > 0
                    and decision.approved_calls < decision.requested_calls
                ):
                    metrics.safety_throttles += 1
                if decision.fallback_to_progressive:
                    metrics.progressive_fallbacks += 1
                allocated_pairs = pred_result.allocated_pairs

            metrics.total_dials_attempted += dials_attempted

            # 5. Simulate carrier response only for calls that reached INITIATED state
            for agent, call in allocated_pairs:
                if call.state != CallState.INITIATED:
                    continue

                # Ringing
                event_handler.handle_event(
                    ProviderCallEvent(
                        call_id=call.id,
                        event_type=TelecomEventType.RINGING,
                    )
                )

                # Pickup determination
                will_answer = random.random() < current_answer_rate
                if will_answer:
                    metrics.total_calls_answered += 1
                    event_handler.handle_event(
                        ProviderCallEvent(
                            call_id=call.id,
                            event_type=TelecomEventType.ANSWERED,
                        )
                    )
                    # Duration with small variance
                    duration = max(
                        1, int(random.gauss(avg_talk_time_cycles, 2))
                    )
                    active_conversations[call.id] = duration
                else:
                    metrics.total_calls_failed += 1
                    event_handler.handle_event(
                        ProviderCallEvent(
                            call_id=call.id,
                            event_type=TelecomEventType.FAILED,
                            reason="No answer / busy",
                        )
                    )

        return metrics

    def run_all_scenarios(self) -> list[tuple[SimulationMetrics, SimulationMetrics]]:
        """Run all four benchmark scenarios (A, B, C, D) comparing Progressive vs Predictive."""
        scenarios = [
            ("Scenario A (Low Answer: 20%, Talk: 120s)", 0.20, 6, 60, False),
            ("Scenario B (Moderate Answer: 50%, Talk: 90s)", 0.50, 4, 60, False),
            ("Scenario C (High Answer: 70%, Talk: 180s)", 0.70, 8, 60, False),
            ("Scenario D (Dynamic Shift: 40% -> 15%, Flaky Carrier)", 0.40, 5, 60, True),
        ]

        results: list[tuple[SimulationMetrics, SimulationMetrics]] = []

        for name, ans_rate, talk_cycles, total_cycles, dynamic in scenarios:
            prog_metrics = self.run_scenario(
                scenario_name=name,
                dialer_mode="PROGRESSIVE",
                answer_rate=ans_rate,
                avg_talk_time_cycles=talk_cycles,
                total_cycles=total_cycles,
                dynamic_degradation=dynamic,
            )
            pred_metrics = self.run_scenario(
                scenario_name=name,
                dialer_mode="PREDICTIVE",
                answer_rate=ans_rate,
                avg_talk_time_cycles=talk_cycles,
                total_cycles=total_cycles,
                dynamic_degradation=dynamic,
            )
            results.append((prog_metrics, pred_metrics))

        return results


def print_comparison_tables(
    results: list[tuple[SimulationMetrics, SimulationMetrics]],
) -> None:
    """Pretty-print formatted comparison tables for the simulation scenarios."""
    print("\n" + "=" * 88)
    print("                 DIALGUARD SMARTDIALER SIMULATION RESULTS                 ")
    print("=" * 88)

    for prog, pred in results:
        print(f"\n>> {prog.scenario_name}")
        print("-" * 88)
        print(
            f"{'Metric':<36} | {'Progressive Dialer':<22} | {'Predictive Dialer':<22}"
        )
        print("-" * 88)
        print(
            f"{'Calls Attempted':<36} | {prog.total_dials_attempted:<22} | {pred.total_dials_attempted:<22}"
        )
        print(
            f"{'Calls Answered':<36} | {prog.total_calls_answered:<22} | {pred.total_calls_answered:<22}"
        )
        print(
            f"{'Calls Completed':<36} | {prog.total_calls_completed:<22} | {pred.total_calls_completed:<22}"
        )
        print(
            f"{'Calls Failed / Unanswered':<36} | {prog.total_calls_failed:<22} | {pred.total_calls_failed:<22}"
        )
        print(
            f"{'Agent Utilization (%)':<36} | {prog.agent_utilization_pct:>20.1f}% | {pred.agent_utilization_pct:>20.1f}%"
        )
        print(
            f"{'Safety Throttles / Cap Hits':<36} | {prog.safety_throttles:<22} | {pred.safety_throttles:<22}"
        )
        if pred.progressive_fallbacks > 0:
            print(
                f"{'Progressive Fallback Cycles':<36} | {'N/A':<22} | {pred.progressive_fallbacks:<22}"
            )
        print("-" * 88)


if __name__ == "__main__":
    simulator = CampaignSimulator(num_agents=10, num_borrowers=200)
    results = simulator.run_all_scenarios()
    print_comparison_tables(results)
