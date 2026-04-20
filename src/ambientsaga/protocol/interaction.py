"""
Emergent Protocol System — open-ended multi-agent interaction framework.

This module provides the foundation for all emergent behavior in AmbientSaga.
Instead of predefined behaviors, organizations, or markets, complex social
phenomena emerge from repeated agent-to-agent interactions.

Core concepts:
- Trace: Every interaction creates an atomic record
- Exchange: Resource transfers that emerge into economics
- MetaProtocol: Open-ended decision-making based on memory/relationships
- Emergence: Complex patterns (markets, language, institutions) arise from traces
"""

from __future__ import annotations

import random
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ambientsaga.types import Pos2D

if TYPE_CHECKING:
    from ambientsaga.agents.agent import Agent
    from ambientsaga.agents.cognition import CognitiveManager

# Basic signal vocabulary for bootstrapping
BASIC_SIGNALS = {
    "help",      # Offering assistance
    "request",   # Asking for help
    "offer",     # Proposing exchange
    "gift",      # Voluntary transfer
    "threat",    # Coercive message
    "promise",   # Commitment to future action
    "accept",    # Agreement to terms
    "reject",    # Refusal
    "inform",    # Sharing information
    "ask",       # Seeking information
}

# Content types that agents can create
CONTENT_TYPES = {
    "resource_transfer",  # {resource, amount}
    "promise",            # {what, when}
    "statement",          # {claim, evidence}
    "ask",                # {question, context}
    "declare",            # {intention, target}
    "gossip",             # {about, content}
    "agreement",          # {terms}
    "declaration",        # {type, details}
}

def _gen_trace_id() -> str:
    return uuid.uuid4().hex[:16]


@dataclass
class Trace:
    """
    Atomic record of a single agent-to-agent interaction.
    This is the fundamental unit from which all emergence arises.
    """
    trace_id: str
    tick: int
    actor_id: str          # Who initiated
    receiver_id: str       # Who received (empty = broadcast)
    signal: str            # Arbitrary signal string
    content: dict          # Open content dict
    interpretation: str    # Actor's intended meaning
    mutual: bool           # Was this a two-way exchange?
    position: Pos2D
    accepted: bool = False  # Did receiver accept?
    cost: dict = field(default_factory=dict)   # Resources actor spent
    benefit: dict = field(default_factory=dict) # Resources actor received
    secondary_traces: list = field(default_factory=list)  # Sub-interactions
    language_shared: float = 0.0  # 0-1, how shared is the signal?

    @property
    def is_broadcast(self) -> bool:
        return not bool(self.receiver_id)

    def __repr__(self) -> str:
        return f"Trace({self.signal[:20]} a={self.actor_id[:8]} r={self.receiver_id[:8] if self.receiver_id else '?'} t={self.tick})"


@dataclass
class Exchange:
    """
    Record of a resource exchange between two agents.
    Economics emerge from patterns in these exchanges.
    """
    trace_id: str
    giver_id: str
    receiver_id: str
    given: dict        # {resource: amount}
    received: dict     # {resource: amount}
    terms: str         # Human-readable description
    is_voluntary: bool
    tick: int
    # Computed fields (emerge from exchange history)
    debt: float = 0.0
    reciprocity_score: float = 0.0
    transaction_count: int = 1

    @property
    def net_flow(self) -> dict:
        """Net resource flow (received - given) for giver"""
        result = defaultdict(float)
        for r, a in self.received.items():
            result[r] += a
        for r, a in self.given.items():
            result[r] -= a
        return dict(result)


class MetaProtocol:
    """
    Open-ended interaction system. Agents generate actions based on their
    memory, relationships, and environment — not from a predefined action set.

    Every interaction creates a Trace. Repeated traces create patterns.
    Patterns create expectations. Expectations create norms. Norms create institutions.
    """

    def __init__(self, world, cognitive_manager: CognitiveManager | None = None) -> None:
        self.world = world
        self._cognitive_manager = cognitive_manager
        self._traces: list[Trace] = []
        self._exchange_history: list[Exchange] = []
        # Per-agent exchange index for fast debt lookup: agent_id -> list of exchange indices
        self._agent_exchange_index: dict[str, list[int]] = defaultdict(list)
        self._signal_registry: dict[str, int] = defaultdict(int)  # signal -> use count
        self._pending_traces: list[Trace] = []  # Traces to process this tick
        self._max_traces = 500_000
        self._max_exchanges = 200_000

        # Interaction patterns detected
        self._patterns: dict[str, list[Trace]] = defaultdict(list)
        # Agents who need to respond to traces
        self._pending_responses: dict[str, list[tuple[str, Trace]]] = defaultdict(list)

        # Pre-seed basic signals
        for sig in BASIC_SIGNALS:
            self._signal_registry[sig] = 0

    # -------------------------------------------------------------------------
    # Trace Management
    # -------------------------------------------------------------------------

    def add_trace(self, trace: Trace) -> None:
        """Record a trace and update statistics."""
        self._traces.append(trace)
        self._pending_traces.append(trace)
        self._signal_registry[trace.signal] += 1

        if len(self._traces) > self._max_traces:
            # Keep recent traces, discard oldest
            self._traces = self._traces[-self._max_traces // 2:]

    def get_traces(self, tick: int | None = None, actor_id: str | None = None,
                   signal: str | None = None, limit: int = 100) -> list[Trace]:
        """Query traces with filters."""
        results = self._traces
        if tick is not None:
            results = [t for t in results if t.tick == tick]
        if actor_id is not None:
            results = [t for t in results if t.actor_id == actor_id]
        if signal is not None:
            results = [t for t in results if t.signal == signal]
        return results[-limit:]

    def get_exchange_history(self, agent_id: str | None = None,
                             lookback: int = 1000) -> list[Exchange]:
        """Get exchange history for an agent or globally."""
        hist = self._exchange_history[-lookback:]
        if agent_id:
            hist = [e for e in hist if e.giver_id == agent_id or e.receiver_id == agent_id]
        return hist

    # -------------------------------------------------------------------------
    # Core Interaction Loop
    # -------------------------------------------------------------------------

    def initiate(self, actor: Agent, signal: str, receiver_id: str,
                content: dict, interpretation: str = "") -> Trace:
        """
        Actor initiates an interaction with another agent.
        """
        trace = Trace(
            trace_id=_gen_trace_id(),
            tick=self.world.tick,
            actor_id=actor.entity_id,
            receiver_id=receiver_id,
            signal=signal,
            content=content,
            interpretation=interpretation or signal,
            mutual=False,
            position=actor.position,
        )
        self.add_trace(trace)
        return trace

    def respond(self, trace: Trace, actor: Agent, signal: str,
                content: dict, accepted: bool = False,
                interpretation: str = "") -> Trace:
        """
        Actor responds to a received trace.
        """
        response_trace = Trace(
            trace_id=_gen_trace_id(),
            tick=self.world.tick,
            actor_id=actor.entity_id,
            receiver_id=trace.actor_id,  # Respond to the initiator
            signal=signal,
            content=content,
            interpretation=interpretation or signal,
            mutual=True,
            position=actor.position,
            accepted=accepted,
        )
        # Link response to original
        trace.secondary_traces.append(response_trace.trace_id)
        trace.accepted = accepted

        self.add_trace(response_trace)
        return response_trace

    def interpret(self, actor: Agent, trace: Trace) -> dict:
        """
        Actor interprets a trace based on their memory and relationships.
        Returns interpretation results including trust level, expected behavior, etc.
        """
        rel = actor.relationships.get(trace.actor_id)
        trust = rel.trust if rel else 0.5

        # Check for patterns: has this signal been used successfully before?
        signal_history = [t for t in self._traces[-500:]
                         if t.signal == trace.signal and t.accepted]
        signal_success_rate = len(signal_history) / max(1, self._signal_registry[trace.signal])

        # Check actor's reputation for this signal type
        actor_traces = [t for t in signal_history if t.actor_id == trace.actor_id]
        actor_success_rate = len(actor_traces) / max(1, sum(1 for t in self._traces if t.actor_id == trace.actor_id))

        # Shared language check
        actor_signals = getattr(actor, 'known_signals', {})
        language_match = actor_signals.get(trace.signal, None)

        return {
            "trust": trust,
            "signal_success_rate": signal_success_rate,
            "actor_success_rate": actor_success_rate,
            "language_match": language_match,
            "relationship": rel,
            "should_respond": signal_success_rate > 0.3,
            "interpretation_confidence": (trust + signal_success_rate) / 2,
        }

    def execute(self, trace: Trace) -> tuple[list[Exchange], list[Trace]]:
        """
        Execute a trace's effects: resource transfers, new traces, etc.
        Returns (exchanges, new_traces).
        """
        exchanges: list[Exchange] = []
        new_traces: list[Trace] = []

        content_type = trace.content.get("type", "")

        if content_type == "resource_transfer" and trace.accepted:
            # Execute resource transfer
            exchange = self._execute_resource_transfer(trace)
            if exchange:
                exchanges.append(exchange)
                self._exchange_history.append(exchange)
                # Update per-agent exchange index for fast debt lookup
                idx = len(self._exchange_history) - 1
                self._agent_exchange_index[exchange.giver_id].append(idx)
                self._agent_exchange_index[exchange.receiver_id].append(idx)
                if len(self._exchange_history) > self._max_exchanges:
                    self._exchange_history = self._exchange_history[-self._max_exchanges // 2:]

        elif content_type == "promise" and trace.accepted:
            # Record promise as an active intention for the promisee
            promisee = self.world.get_agent(trace.receiver_id)
            if promisee:
                active_intents = getattr(promisee, 'active_intentions', [])
                active_intents.append({
                    "type": "promise",
                    "from": trace.actor_id,
                    "promise_id": trace.trace_id,
                    "what": trace.content.get("what"),
                    "when": trace.content.get("when", trace.tick + 10),
                    "tick": trace.tick,
                })
                if not hasattr(promisee, 'active_intentions'):
                    promisee.active_intentions = active_intents

        return exchanges, new_traces

    def _execute_resource_transfer(self, trace: Trace) -> Exchange | None:
        """Execute a resource transfer and create an Exchange record."""
        resource = trace.content.get("resource", "food")
        amount = trace.content.get("amount", 1.0)
        giver_id = trace.actor_id
        receiver_id = trace.receiver_id

        giver = self.world.get_agent(giver_id)
        receiver = self.world.get_agent(receiver_id)

        if not giver or not receiver:
            return None

        # Check if giver has enough resources
        giver_wealth = getattr(giver, 'wealth', 100.0)
        if giver_wealth < amount * 0.1:  # Simple check: 10% of amount as "cost"
            return None

        # Update agent wealth
        giver.wealth = max(0, giver_wealth - amount * 0.1)
        receiver.wealth = getattr(receiver, 'wealth', 100.0) + amount * 0.1

        # Update relationships
        rel = giver.relationships.get(receiver_id)
        if rel:
            rel.affection = min(1.0, rel.affection + 0.05)
            rel.interactions_count += 1
            rel.last_interaction_tick = trace.tick
            # Append to history
            history = list(rel.history) if rel.history else []
            history.append(f"{trace.tick}:gift:{amount}")
            rel.history = tuple(history[:20])  # Keep last 20
        else:
            from ambientsaga.types import Relationship
            new_rel = Relationship(
                agent_a=giver_id, agent_b=receiver_id,
                trust=0.5, respect=0.5, affection=0.3,
                history=(), interactions_count=1, last_interaction_tick=trace.tick,
            )
            giver.relationships[receiver_id] = new_rel

        return Exchange(
            trace_id=trace.trace_id,
            giver_id=giver_id,
            receiver_id=receiver_id,
            given={resource: amount},
            received={"gratitude": 1.0},
            terms=f"gift of {amount} {resource}",
            is_voluntary=True,
            tick=trace.tick,
        )

    # -------------------------------------------------------------------------
    # Deliberation — open-ended action generation
    # -------------------------------------------------------------------------

    def deliberate(self, agent: Agent, tick: int) -> dict:
        """
        Agent generates an action based on memory, relationships, and needs.
        This is the UNIFIED decision mechanism - replaces all hardcoded decision trees.

        For L1_CORE agents with cognitive manager, uses LLM deliberation for
        more sophisticated decision-making. Falls back to rule-based deliberation.

        Returns a decision dict with keys:
            signal, receiver_id, content, interpretation, priority, goal, action

        ALWAYS returns a valid decision dict - never returns None.
        """
        # Try LLM deliberation for L1 agents if cognitive manager is available
        if (agent.tier.value == "l1_core" and
            self._cognitive_manager is not None and
            hasattr(self._cognitive_manager.deliberator, 'can_call_llm') and
            self._cognitive_manager.deliberator.can_call_llm()):

            try:
                result = self._llm_deliberate(agent, tick)
                if result:
                    return result
            except Exception:
                pass  # Fall through to rule-based

        # Rule-based deliberation (always returns a valid dict)
        return self._rule_based_deliberate(agent, tick)

    async def deliberate_async(self, agent: Agent, tick: int) -> dict | None:
        """
        Async version of deliberate that can call LLM APIs.
        Use this for L1 agents when async is needed.
        """
        # Try LLM deliberation for L1 agents if cognitive manager is available
        if (agent.tier.value == "l1_core" and
            self._cognitive_manager is not None):

            try:
                # Build cognitive context
                context = self._cognitive_manager.build_context(agent, self.world, tick)

                # Call the cognitive system
                result = await self._cognitive_manager.think(agent, context, self.world)

                if result:
                    # Convert cognitive result to protocol decision
                    return self._cognitive_to_protocol(agent, result, tick)
            except Exception:
                pass  # Fall through to rule-based

        # Fall back to rule-based deliberation
        return self._rule_based_deliberate(agent, tick)

    def _llm_deliberate(self, agent: Agent, tick: int) -> dict | None:
        """
        Use LLM deliberation for decision-making.
        Called synchronously when LLM is cached or available.
        """
        if self._cognitive_manager is None:
            return None

        try:
            context = self._cognitive_manager.build_context(agent, self.world, tick)
            result = self._cognitive_manager.deliberator._rule_based_deliberate(
                agent,
                self._cognitive_manager.deliberator._build_context(agent, context, self.world),
                self.world
            )

            if result:
                return self._cognitive_to_protocol(agent, result, tick)
        except Exception:
            pass

        return None

    def _cognitive_to_protocol(self, agent: Agent, cognitive_result: dict, tick: int) -> dict | None:
        """
        Convert a cognitive deliberation result to a protocol decision.
        Maps LLM-generated actions to protocol signals and content.
        """
        rng = random.Random(tick + hash(agent.entity_id) % 2**31)

        action = cognitive_result.get("action", "idle")
        goal = cognitive_result.get("goal", "")
        reasoning = cognitive_result.get("reasoning", "")

        # Get nearby agents - use larger radius for more social interactions
        cached_nearby = getattr(agent, '_nearby_agents', None)
        if cached_nearby is not None:
            nearby = [a for a, _ in cached_nearby if a.entity_id != agent.entity_id and a.is_alive]
        else:
            nearby = self.world.get_agents_in_radius(agent.position, radius=100)

        agent_wealth = getattr(agent, 'wealth', 100.0)

        # Map cognitive actions to protocol signals
        action_to_signal = {
            "gather_food": None,  # No protocol action needed
            "find_water": None,
            "rest": None,
            "socialize": "inform",
            "trade": "offer",
            "craft": None,
            "explore": None,
            "fight": "threat",
            "flee": None,
            "forage": None,
            "share_food": "help",
            "tell_story": "inform",
            "teach_skill": "inform",
            "ask_for_help": "request",
            "form_group": "declare",
            "create_art": "inform",
            "perform_ritual": "inform",
            "share_knowledge": "inform",
            "trade_item": "offer",
            "craft_item": None,
            "settle_dispute": "inform",
            "lead_group": "declare",
            "follow": None,
            "wait": None,
            "contemplate": None,
        }

        signal = action_to_signal.get(action)
        if signal is None:
            return None  # No protocol action for this action

        # Find a target agent if needed
        receiver_id = ""
        content = {}
        interpretation = reasoning

        if nearby:
            if action in ("socialize", "share_food", "help", "trade", "teach_skill", "tell_story", "share_knowledge"):
                # Interact with a nearby agent
                target = rng.choice(nearby)
                receiver_id = target.entity_id

                if action == "share_food" or action == "help":
                    content = {
                        "type": "resource_transfer",
                        "resource": "food",
                        "amount": min(20.0, agent_wealth * 0.1)
                    }
                elif action in ("trade", "trade_item"):
                    content = {
                        "type": "resource_transfer",
                        "resource": "food",
                        "amount": 5.0,
                        "request": "goods",
                        "request_amount": 5.0
                    }
                elif action in ("tell_story", "share_knowledge", "teach_skill"):
                    content = {
                        "type": "statement",
                        "claim": cognitive_result.get("narrative", reasoning),
                        "evidence": []
                    }
            elif action == "ask_for_help":
                target = rng.choice(nearby)
                receiver_id = target.entity_id
                content = {
                    "type": "ask",
                    "question": f"Could you help me? {reasoning}"
                }
            elif action == "form_group":
                # Broadcast to nearby agents
                if nearby:
                    target = rng.choice(nearby)
                    receiver_id = target.entity_id
                    content = {
                        "type": "declaration",
                        "declaration_type": "form_group",
                        "details": reasoning
                    }
            elif action == "settle_dispute":
                if nearby:
                    target = rng.choice(nearby)
                    receiver_id = target.entity_id
                    content = {
                        "type": "inform",
                        "about": agent.entity_id,
                        "content": f"Addressing dispute: {reasoning}"
                    }

        if not receiver_id:
            return None  # No suitable target

        priority = cognitive_result.get("goal_priority", 0.5)

        return {
            "signal": signal,
            "receiver_id": receiver_id,
            "content": content,
            "interpretation": interpretation,
            "priority": priority,
            "goal": goal,
            "from_llm": True,
        }

    def _rule_based_deliberate(self, agent: Agent, tick: int) -> dict | None:
        """
        Rule-based deliberation with EMERGENT social behavior.

        Creates emergence through:
        1. Emotional decision-making (mood affects choices)
        2. Irrational behaviors (spite, jealousy, revenge, generosity)
        3. Game theory (defect/cooperate/tit-for-tat based on history)
        4. Social norms following/breaking
        5. Cultural influences
        6. Spontaneous conflict and cooperation
        7. SCIENCE MODULATION: Environmental context subtly influences behavior

        Returns a decision dict with keys:
            - signal: protocol signal (optional for local actions)
            - receiver_id: target agent ID (optional)
            - content: interaction content (optional)
            - interpretation: actor's intended meaning
            - priority: decision priority
            - goal: decision goal
            - action: local action string (used when no social interaction)
        """
        rng = random.Random(tick + hash(agent.entity_id) % 2**31)

        # === Get agent state ===
        hunger = getattr(agent, 'hunger', 0.0)
        thirst = getattr(agent, 'thirst', 0.0)
        energy = getattr(agent, 'energy', 1.0)
        agent_wealth = getattr(agent, 'wealth', 100.0)

        # === SCIENCE MODULATION: Get environmental context ===
        env_multiplier = 1.0  # Default - no environmental effect
        scarcity_factor = 0.0  # Resource scarcity (0-1)
        density_factor = 0.0  # Population density pressure (0-1)

        # Get temperature from science engine (if available)
        temperature = 20.0  # Default comfortable temperature
        if self.world._science is not None:
            physics = self.world._science.physics
            if hasattr(physics, 'ambient_temperature'):
                temperature = physics.ambient_temperature
                # Temperature affects behavior slightly
                if temperature < 5 or temperature > 35:
                    env_multiplier = 1.3  # 30% more conflict/violence
                elif temperature < 10 or temperature > 30:
                    env_multiplier = 1.1  # 10% more conflict

        # Calculate resource scarcity based on agent density
        # Higher density means more competition for resources
        total_agents = self.world.get_agent_count()
        if hasattr(self.world, '_config'):
            world_area = self.world._config.world.width * self.world._config.world.height
            # Agents per 100x100 tiles (but world is much larger than 100x100)
            agent_density = total_agents / (world_area / 10000)
            # Scarcity only triggers when VERY crowded (more than 5 agents per 100x100)
            scarcity_factor = min(1.0, max(0.0, (agent_density - 5.0) / 10.0))
            # Density pressure only triggers when VERY crowded (more than 10 agents per 100x100)
            density_factor = min(0.5, max(0.0, (agent_density - 10.0) / 20.0))

        # === Get emotional state (human-like behavior) ===
        emotional_state = getattr(agent, 'emotional_state', None)
        if emotional_state:
            mood = getattr(emotional_state, 'mood', 0.0)
            stress = getattr(emotional_state, 'stress', 0.0)
            frustration = getattr(emotional_state, 'frustration', 0.0)
            social_desire = getattr(emotional_state, 'social_desire', 0.5)
        else:
            mood, stress, frustration, social_desire = 0.0, 0.0, 0.0, 0.5

        # === Get personality traits ===
        personality = getattr(agent, 'personality', None)
        if personality:
            extraversion = getattr(personality, 'extraversion', 0.5)
            agreeableness = getattr(personality, 'agreeableness', 0.5)
            neuroticism = getattr(personality, 'neuroticism', 0.5)
            openness = getattr(personality, 'openness', 0.5)
        else:
            extraversion, agreeableness, neuroticism, openness = 0.5, 0.5, 0.5, 0.5

        # === EMOTIONAL OVERRIDES: Irrational behaviors based on mood ===

        # Environmental stress multiplies existing stress (science modulation)
        effective_stress = stress * env_multiplier

        # STRESS causes irrational actions (amplified by environmental stress)
        if effective_stress > 0.7 and rng.random() < neuroticism * 0.4:
            # Lash out at random nearby agent
            nearby = self._get_nearby_agents(agent, radius=150, max_sample=10)
            if nearby:
                target = rng.choice(nearby)
                stress_action = rng.choice(["threat", "reject", "steal", "accuse"])
                if stress_action == "threat":
                    return {
                        "signal": "threat",
                        "receiver_id": target.entity_id,
                        "content": {"type": "declaration", "declaration_type": "threat",
                                   "details": "Leave me alone!"},
                        "interpretation": f"stressed out, lashing out at {target.name}",
                        "priority": 0.95,
                        "goal": f"threaten:{target.entity_id[:8]}",
                    }
                elif stress_action == "reject":
                    return {
                        "signal": "reject",
                        "receiver_id": target.entity_id,
                        "content": {"type": "statement", "claim": "Go away!", "evidence": []},
                        "interpretation": "rejecting social contact due to stress",
                        "priority": 0.9,
                        "goal": "reject_interaction",
                    }

        # NEGATIVE MOOD causes spiteful behavior
        if mood < -0.3 and rng.random() < abs(mood) * 0.5:
            nearby = self._get_nearby_agents(agent, radius=150, max_sample=10)
            if nearby:
                # Find someone who has been successful (jealousy)
                wealthy_agents = [a for a in nearby if getattr(a, 'wealth', 100) > agent_wealth * 1.5]
                if wealthy_agents:
                    target = rng.choice(wealthy_agents)
                    # Spiteful action: demand resources, threaten, or spread gossip
                    spite_action = rng.choice(["demand", "gossip_about"])
                    if spite_action == "demand":
                        return {
                            "signal": "request",
                            "receiver_id": target.entity_id,
                            "content": {"type": "ask", "question": "Share your wealth with me!"},
                            "interpretation": f"jealous of {target.name}'s wealth",
                            "priority": 0.85,
                            "goal": f"demand_from:{target.entity_id[:8]}",
                        }
                    else:
                        # Gossip about successful agent to damage reputation
                        victim = rng.choice(nearby) if nearby else target
                        return {
                            "signal": "inform",
                            "receiver_id": target.entity_id,
                            "content": {"type": "gossip", "about": victim.entity_id,
                                       "content": "Did you hear? They cheated others!"},
                            "interpretation": f"spreading false gossip about {victim.name}",
                            "priority": 0.8,
                            "goal": f"defame:{victim.entity_id[:8]}",
                        }

        # HIGH FRUSTRATION causes aggressive behavior
        if frustration > 0.6 and rng.random() < frustration * 0.4:
            nearby = self._get_nearby_agents(agent, radius=200, max_sample=15)
            if nearby:
                # Pick a random target for aggression
                target = rng.choice(nearby)
                return {
                    "signal": "threat",
                    "receiver_id": target.entity_id,
                    "content": {"type": "declaration", "declaration_type": "aggression",
                               "details": "You're in my way!"},
                    "interpretation": f"frustrated, threatening {target.name}",
                    "priority": 0.9,
                    "goal": f"aggress:{target.entity_id[:8]}",
                }

        # HIGH OPENNESS + POSITIVE MOOD = creative/innovative behavior
        if openness > 0.7 and mood > 0.3 and rng.random() < 0.3:
            # Try something new - propose a novel interaction
            nearby = self._get_nearby_agents(agent, radius=150, max_sample=10)
            if nearby:
                target = rng.choice(nearby)
                # Invent a new signal
                new_signals = ["ally", "propose_peace", "ritual", "challenge", "bond"]
                novel_signal = rng.choice(new_signals)
                return {
                    "signal": novel_signal,
                    "receiver_id": target.entity_id,
                    "content": {"type": "declaration", "declaration_type": novel_signal,
                               "details": "Let's try something new together!"},
                    "interpretation": f"proposing novel interaction: {novel_signal}",
                    "priority": 0.75,
                    "goal": f"innovate:{novel_signal}",
                }

        # === Check survival needs (REDUCED thresholds for more social interaction) ===
        # Agents can engage in social behavior even when slightly hungry
        if hunger > 0.85:  # Raised threshold from 0.7
            return {
                "signal": None,
                "receiver_id": "",
                "content": {},
                "interpretation": "gathering food",
                "priority": 1.0,
                "goal": "find_food",
                "action": "gather_food",
            }
        if thirst > 0.85:  # Raised threshold from 0.7
            return {
                "signal": None,
                "receiver_id": "",
                "content": {},
                "interpretation": "finding water",
                "priority": 1.0,
                "goal": "find_water",
                "action": "move_to_water",
            }
        if energy < 0.1:  # Raised threshold from 0.2
            return {
                "signal": None,
                "receiver_id": "",
                "content": {},
                "interpretation": "resting",
                "priority": 0.95,
                "goal": "rest",
                "action": "rest",
            }

        # === Get nearby agents (INCREASED radius for more social interaction) ===
        nearby = self._get_nearby_agents(agent, radius=200, max_sample=20)

        # === If no nearby agents, seek social interaction ===
        if not nearby:
            # Social desire increases when alone
            social_desire += 0.1
            if rng.random() < social_desire * 0.5:
                # Actively seek social interaction - move toward agents
                return {
                    "signal": None,
                    "receiver_id": "",
                    "content": {},
                    "interpretation": "seeking social interaction",
                    "priority": 0.5,
                    "goal": "find_agents",
                    "action": "explore_toward_agents",
                }
            else:
                # Random activity with slight exploration bias
                if rng.random() < 0.4:
                    return {
                        "signal": None,
                        "receiver_id": "",
                        "content": {},
                        "interpretation": "exploring",
                        "priority": 0.3,
                        "goal": "explore",
                        "action": "explore",
                    }
                elif rng.random() < 0.6:
                    return {
                        "signal": None,
                        "receiver_id": "",
                        "content": {},
                        "interpretation": "gathering resources",
                        "priority": 0.4,
                        "goal": "gather",
                        "action": "gather_resource",
                    }
                else:
                    return {
                        "signal": None,
                        "receiver_id": "",
                        "content": {},
                        "interpretation": "resting",
                        "priority": 0.2,
                        "goal": "rest",
                        "action": "rest",
                    }

        # === GAME THEORY: Decide strategy based on relationship history ===

        # 1. Check for pending promises/obligations
        pending_intents = getattr(agent, 'active_intentions', [])
        for intent in pending_intents:
            if intent.get("type") == "promise" and intent.get("when", 9999) <= tick:
                return {
                    "signal": "fulfill",
                    "receiver_id": intent["from"],
                    "content": {"type": "resource_transfer", "resource": "food",
                               "amount": 5.0, "promise_id": intent["promise_id"]},
                    "interpretation": f"fulfilling promise to {intent['from']}",
                    "priority": 0.9,
                    "goal": f"fulfill_promise:{intent['promise_id']}",
                }

        # 2. Check relationships for GAME THEORETIC decisions
        for other in nearby:
            rel = agent.relationships.get(other.entity_id)
            if rel:
                trust = rel.trust

                # TIT-FOR-TAT strategy based on trust
                if trust > 0.7 and rng.random() < trust * 0.6:
                    # High trust = cooperate
                    if agent_wealth > 80:
                        return {
                            "signal": "help",
                            "receiver_id": other.entity_id,
                            "content": {"type": "resource_transfer", "resource": "food",
                                       "amount": min(20.0, agent_wealth * 0.15)},
                            "interpretation": f"cooperating with trusted friend {other.name}",
                            "priority": 0.75,
                            "goal": f"cooperate:{other.entity_id[:8]}",
                        }

                # LOW TRUST = DEFECT (potential betrayal)
                if trust < 0.3 and rng.random() < abs(0.3 - trust) * 0.4:
                    # Betrayal or exploitation
                    other_wealth = getattr(other, 'wealth', 100)
                    if other_wealth > agent_wealth:
                        return {
                            "signal": "threat",
                            "receiver_id": other.entity_id,
                            "content": {"type": "declaration", "declaration_type": "extortion",
                                       "details": "Give me resources or else!"},
                            "interpretation": f"exploiting distrusted {other.name}",
                            "priority": 0.8,
                            "goal": f"exploit:{other.entity_id[:8]}",
                        }

                # HISTORY OF CONFLICT = revenge
                conflict_history = [h for h in (rel.history or []) if 'conflict' in h or 'threat' in h]
                if len(conflict_history) >= 2 and rng.random() < 0.4:
                    return {
                        "signal": "threat",
                        "receiver_id": other.entity_id,
                        "content": {"type": "declaration", "declaration_type": "revenge",
                                   "details": "You'll regret crossing me!"},
                        "interpretation": f"seeking revenge on {other.name}",
                        "priority": 0.85,
                        "goal": f"revenge:{other.entity_id[:8]}",
                    }

        # 3. Reciprocity - repay debts (builds social capital)
        debts = self._calculate_debts(agent.entity_id)
        if debts and rng.random() < 0.7:  # Increased probability
            top_debtor = max(debts.items(), key=lambda x: x[1])
            if top_debtor[1] > 0.2:
                debtor_agent = self.world.get_agent(top_debtor[0])
                if debtor_agent and debtor_agent.is_alive:
                    return {
                        "signal": "gift",
                        "receiver_id": top_debtor[0],
                        "content": {"type": "resource_transfer", "resource": "food",
                                   "amount": max(5.0, top_debtor[1] * 1.5)},
                        "interpretation": f"repaying debt to {debtor_agent.name}",
                        "priority": 0.85,
                        "goal": f"repay_debt:{top_debtor[0][:8]}",
                    }

        # 4. Help agents in need (generosity - more likely with high agreeableness)
        agents_in_need = []
        for other in nearby:
            other_wealth = getattr(other, 'wealth', 100.0)
            other_health = getattr(other, 'health', 1.0)
            other_hunger = getattr(other, 'hunger', 0.0)
            if other_health < 0.5 or other_wealth < 50 or other_hunger > 0.7:
                agents_in_need.append(other)

        if agents_in_need and agent_wealth > 70:
            generosity_factor = agreeableness * 0.8 + mood * 0.2
            if rng.random() < generosity_factor:
                other = rng.choice(agents_in_need)
                return {
                    "signal": "help",
                    "receiver_id": other.entity_id,
                    "content": {"type": "resource_transfer", "resource": "food",
                               "amount": min(25.0, agent_wealth * 0.2)},
                    "interpretation": f"generously helping {other.name} who is in need",
                    "priority": 0.7,
                    "goal": f"help:{other.entity_id[:8]}",
                }

        # 5. Trade with surplus agents (mutual benefit)
        agents_with_surplus = [a for a in nearby if getattr(a, 'wealth', 100) > agent_wealth + 30]
        if agents_with_surplus and rng.random() < 0.5:
            other = rng.choice(agents_with_surplus)
            return {
                "signal": "offer",
                "receiver_id": other.entity_id,
                "content": {"type": "resource_transfer", "resource": "food",
                           "amount": 8.0, "request": "food", "request_amount": 15.0},
                "interpretation": f"proposing fair trade with {other.name}",
                "priority": 0.6,
                "goal": f"trade:{other.entity_id[:8]}",
            }

        # 6. RESOURCE SCARCITY → CONFLICT (science → social cascading)
        # When agents are crowded, conflict increases
        if scarcity_factor > 0.3 and rng.random() < scarcity_factor * 0.5:
            others = [a for a in nearby if a.entity_id != agent.entity_id]
            if others:
                # Target wealthy agents during scarcity
                wealthy_others = [a for a in others if getattr(a, 'wealth', 100) > agent_wealth * 1.5]
                if wealthy_others:
                    target = rng.choice(wealthy_others)
                    return {
                        "signal": "threat",
                        "receiver_id": target.entity_id,
                        "content": {"type": "declaration", "declaration_type": "scarcity_conflict",
                                   "details": "Resources are scarce! Give me your share!"},
                        "interpretation": f"scarcity causing conflict with wealthy {target.name}",
                        "priority": 0.8,
                        "goal": f"scarcity_conflict:{target.entity_id[:8]}",
                    }

        # 7. POPULATION DENSITY → COMPETITION (science → social pressure)
        if density_factor > 0.1 and rng.random() < density_factor * 0.4:
            others = [a for a in nearby if a.entity_id != agent.entity_id]
            if others:
                target = rng.choice(others)
                return {
                    "signal": "threat",
                    "receiver_id": target.entity_id,
                    "content": {"type": "declaration", "declaration_type": "competition",
                               "details": "Too crowded! Make room!"},
                    "interpretation": "density pressure causing competition",
                    "priority": 0.7,
                    "goal": "compete",
                }

        # 8. SPONTANEOUS CONFLICT (amplified by environmental stress)
        # Environmental factors increase conflict probability
        conflict_base = neuroticism * 0.15 * env_multiplier + scarcity_factor * 0.1 + density_factor * 0.1
        if rng.random() < conflict_base:
            if not nearby:
                nearby = self._get_nearby_agents(agent, radius=200, max_sample=10)
            if nearby:
                other = rng.choice(nearby)
                conflict_types = ["territorial", "resource", "status", "cultural"]
                conflict = rng.choice(conflict_types)
                return {
                    "signal": "threat",
                    "receiver_id": other.entity_id,
                    "content": {"type": "declaration", "declaration_type": "conflict",
                               "details": f"This is about {conflict}!"},
                    "interpretation": f"starting spontaneous conflict with {other.name}",
                    "priority": 0.75,
                    "goal": f"conflict:{other.entity_id[:8]}",
                }

        # 9. Gossip to build social network
        if rng.random() < 0.5:  # Increased probability
            others = [a for a in nearby if a.entity_id != agent.entity_id]
            if others:
                other = rng.choice(others)
                # Gossip content varies by mood
                if mood > 0.2:
                    gossip_content = "Great weather today! Love this community."
                elif mood < -0.2:
                    gossip_content = "Things could be better around here..."
                else:
                    gossip_content = "Seen any interesting lately?"
                return {
                    "signal": "inform",
                    "receiver_id": other.entity_id,
                    "content": {"type": "gossip", "about": agent.entity_id,
                               "content": gossip_content},
                    "interpretation": "socializing through gossip",
                    "priority": 0.4,
                    "goal": "socialize",
                }

        # 10. Form alliance (high openness + extraversion)
        if openness > 0.6 and extraversion > 0.6 and rng.random() < 0.3:
            others = [a for a in nearby if a.entity_id != agent.entity_id]
            if others:
                other = rng.choice(others)
                return {
                    "signal": "promise",
                    "receiver_id": other.entity_id,
                    "content": {"type": "agreement", "terms": "mutual aid pact",
                               "what": "help each other", "when": tick + 20},
                    "interpretation": f"proposing alliance with {other.name}",
                    "priority": 0.65,
                    "goal": f"ally:{other.entity_id[:8]}",
                }

        # 11. Default: socialize to build relationships
        others = [a for a in nearby if a.entity_id != agent.entity_id]
        if others:
            other = rng.choice(others)
            # Vary the type of social interaction
            social_types = ["inform", "ask", "offer", "gift"]
            signal = rng.choice(social_types)
            if signal == "gift" and agent_wealth > 80:
                content = {"type": "resource_transfer", "resource": "food", "amount": 5.0}
                interpretation = "giving a gift"
            elif signal == "ask":
                content = {"type": "ask", "question": "How are you doing?"}
                interpretation = "asking about wellbeing"
            else:
                content = {"type": "statement", "claim": "Hello!", "evidence": []}
                interpretation = "introducing myself"
            return {
                "signal": signal,
                "receiver_id": other.entity_id,
                "content": content,
                "interpretation": interpretation,
                "priority": 0.35,
                "goal": "socialize",
            }

        # 10. No suitable interaction - explore
        return {
            "signal": None,
            "receiver_id": "",
            "content": {},
            "interpretation": "exploring for opportunities",
            "priority": 0.2,
            "goal": "explore",
            "action": "explore",
        }

    def _get_nearby_agents(self, agent: Agent, radius: float = 200, max_sample: int = 20) -> list:
        """Get nearby agents for deliberation."""
        # Try cached nearby agents first
        cached_nearby = getattr(agent, '_nearby_agents', None)
        if cached_nearby is not None:
            nearby = [a for a, _ in cached_nearby if a.entity_id != agent.entity_id and a.is_alive]
            if len(nearby) > max_sample:
                nearby = [nearby[i] for i in sorted(random.sample(range(len(nearby)), max_sample))]
            return nearby

        # Fallback to world query (returns list of Agent objects)
        nearby = self.world.get_agents_in_radius(agent.position, radius=radius)
        if len(nearby) > max_sample:
            nearby = [nearby[i] for i in sorted(random.sample(range(len(nearby)), max_sample))]
        return nearby

    def _calculate_debts(self, agent_id: str) -> dict[str, float]:
        """
        Calculate outstanding debts for an agent based on exchange history.
        Returns {other_id: debt_amount}.
        Uses per-agent exchange index for O(k) lookup instead of O(n) scan.
        """
        debts: dict[str, float] = defaultdict(float)
        history_len = len(self._exchange_history)
        lookback_start = max(0, history_len - 2000)

        # Use index to directly access agent's exchanges (O(k) instead of O(2000))
        exchange_indices = self._agent_exchange_index.get(agent_id, [])
        for idx in exchange_indices:
            # Only consider exchanges within lookback window
            if idx < lookback_start:
                continue
            ex = self._exchange_history[idx]
            if ex.giver_id == agent_id:
                # Agent gave — other owes
                total_given = sum(ex.given.values())
                total_received = sum(ex.received.values())
                debts[ex.receiver_id] += max(0, total_received - total_given)
            else:
                # Agent received — agent owes
                total_given = sum(ex.given.values())
                total_received = sum(ex.received.values())
                debts[ex.giver_id] += max(0, total_given - total_received)

        return debts

    # -------------------------------------------------------------------------
    # Pattern Detection — from traces to emergence
    # -------------------------------------------------------------------------

    def detect_patterns(self, lookback: int = 500) -> dict:
        """Detect recurring interaction patterns that could become institutions."""
        recent = self._traces[-lookback:]
        if len(recent) < 50:
            return {}

        patterns: dict = {}

        # Group by signal
        by_signal: dict[str, list[Trace]] = defaultdict(list)
        for t in recent:
            by_signal[t.signal].append(t)

        for signal, traces in by_signal.items():
            if len(traces) < 5:
                continue

            # Check acceptance rate
            accepted = sum(1 for t in traces if t.accepted)
            rate = accepted / len(traces)

            # Check consistency of receivers (is this a "role" behavior?)
            receivers = {t.receiver_id for t in traces if t.receiver_id}
            signalers = {t.actor_id for t in traces if t.actor_id}

            patterns[signal] = {
                "count": len(traces),
                "acceptance_rate": rate,
                "unique_receivers": len(receivers),
                "unique_signalers": len(signalers),
                "is_recurring": len(traces) >= 20,
                "is_widely_adopted": len(signalers) >= 10,
            }

        return patterns

    def process_tick(self, tick: int) -> None:
        """Process all pending traces for this tick."""
        tick_traces = [t for t in self._pending_traces if t.tick == tick]
        for trace in tick_traces:
            exchanges, new_traces = self.execute(trace)
            for nt in new_traces:
                self.add_trace(nt)
        self._pending_traces = [t for t in self._pending_traces if t.tick < tick]

    def get_summary(self) -> dict:
        """Get summary statistics for the protocol system."""
        return {
            "total_traces": len(self._traces),
            "total_exchanges": len(self._exchange_history),
            "unique_signals": len(self._signal_registry),
            "top_signals": sorted(self._signal_registry.items(), key=lambda x: -x[1])[:10],
            "patterns": self.detect_patterns(),
        }
