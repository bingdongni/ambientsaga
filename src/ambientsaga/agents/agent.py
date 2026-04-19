"""
Agent — core agent model with full cognitive architecture.

An Agent is an autonomous entity with:
- Identity (name, tier, position)
- Attributes (health, personality, skills)
- Memory (episodic, semantic, procedural)
- Emotions (with dynamics and contagion)
- Beliefs (with Bayesian updating)
- Perceptual system (signal processing)
- Deliberation system (decision routing)
- Social relationships
- Economic state
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np

from ambientsaga.agents.core import AgentTier
from ambientsaga.types import TerrainType

# === Ultimate Emergence: Agent Humanity Layer ===
from ambientsaga.emergence.humanity_layer import (
    AgentHumanityLayer,
    EmotionType,
)
from ambientsaga.types import (
    AgentAttributes,
    Decision,
    DecisionType,
    EntityID,
    Inventory,
    Pos2D,
    Relationship,
    ResourceType,
    Signal,
)

if TYPE_CHECKING:
    from ambientsaga.world.signal_bus import SignalSubscription
    from ambientsaga.world.state import World


@dataclass
class CognitiveBelief:
    """A cognitive belief with proposition, evidence, and confidence."""
    proposition: str
    confidence: float  # 0.0-1.0
    source_tick: int
    evidence: tuple[str, ...] = ()
    counter_evidence: tuple[str, ...] = ()
    last_updated_tick: int = 0

    def update(
        self,
        new_evidence: str,
        confirms: bool,
        strength: float,
        current_tick: int,
    ) -> CognitiveBelief:
        """Update belief with new evidence (Bayesian-inspired)."""
        if confirms:
            new_confidence = min(1.0, self.confidence + strength * (1 - self.confidence))
            new_evidence_list = list(self.evidence) + [new_evidence]
            new_counter = self.counter_evidence
        else:
            new_confidence = max(0.0, self.confidence - strength * self.confidence)
            new_evidence_list = list(self.evidence)
            new_counter = list(self.counter_evidence) + [new_evidence]

        return CognitiveBelief(
            proposition=self.proposition,
            confidence=new_confidence,
            source_tick=self.source_tick,
            evidence=tuple(new_evidence_list),
            counter_evidence=tuple(new_counter),
            last_updated_tick=current_tick,
        )


def _default_agent_attributes() -> AgentAttributes:
    """Create a default AgentAttributes instance."""
    from ambientsaga.types import Attribute
    attrs = frozenset([
        (Attribute.STRENGTH, 0.5),
        (Attribute.INTELLIGENCE, 0.5),
        (Attribute.CHARISMA, 0.5),
        (Attribute.WISDOM, 0.5),
        (Attribute.DEXTERITY, 0.5),
        (Attribute.ENDURANCE, 0.5),
        (Attribute.PERCEPTION, 0.5),
        (Attribute.CREATIVITY, 0.5),
        (Attribute.PATIENCE, 0.5),
        (Attribute.COURAGE, 0.5),
        (Attribute.JUST, 0.5),
        (Attribute.GREED, 0.5),
        (Attribute.COMPASSION, 0.5),
        (Attribute.PRIDE, 0.5),
        (Attribute.ENVY, 0.5),
        (Attribute.TEMPERANCE, 0.5),
    ])
    return AgentAttributes(
        name="Unknown",
        age=25 * 360,
        gender="unknown",
        attributes=attrs,
        culture_id="default",
        native_language="common",
        appearance="ordinary",
        personality_summary="average",
        backstory="A mysterious figure.",
        talents=frozenset(),
        flaws=frozenset(),
        ambition="survive",
        fear="unknown",
    )


@dataclass
class Agent:
    """
    A single agent in the simulation.

    Each agent has a complete cognitive architecture including
    perception, memory, emotion, deliberation, and action systems.
    """

    entity_id: EntityID
    name: str
    position: Pos2D
    tier: AgentTier = AgentTier.L3_BACKGROUND
    attributes: AgentAttributes = field(default_factory=_default_agent_attributes)

    # Cognitive state
    health: float = 1.0
    energy: float = 1.0  # 0-1, depletes with activity
    hunger: float = 0.0  # 0=no hunger, 1=starving
    thirst: float = 0.0

    # Inventory
    inventory: Inventory = field(default_factory=Inventory)
    wealth: float = 100.0  # Currency holdings

    # Personality (HEXACO model)
    honesty_humility: float = 0.5  # 0-1
    emotionality: float = 0.5
    extraversion: float = 0.5
    agreeableness: float = 0.5
    conscientiousness: float = 0.5
    openness: float = 0.5

    # Social
    relationships: dict[EntityID, Relationship] = field(default_factory=dict)
    organization_ids: list[EntityID] = field(default_factory=list)
    reputation: float = 0.0  # -1 to 1

    # Language emergence: agent's personal vocabulary
    known_signals: dict[str, str] = field(default_factory=dict)  # signal -> meaning

    # Beliefs
    beliefs: list[CognitiveBelief] = field(default_factory=list)

    # Decision state
    current_goal: str | None = None
    goal_priority: float = 0.0
    last_decision_tick: int = -1
    last_perception_tick: int = -1

    # Perception
    _perception_radius: float = 5.0
    _subscription: SignalSubscription | None = field(default=None, repr=False)
    _pending_signals: list[Signal] = field(default_factory=list)

    # Memory (simple circular buffer)
    _episodic_memory: list[dict[str, Any]] = field(default_factory=list)
    _max_episodic: int = 50

    # Skills
    skills: dict[str, float] = field(default_factory=lambda: {
        "strength": 0.5,
        "intelligence": 0.5,
        "charisma": 0.5,
        "crafting": 0.5,
        "agriculture": 0.5,
        "combat": 0.5,
        "trading": 0.5,
        "diplomacy": 0.5,
    })

    # Cached state
    _cached_str: str = ""

    # === Ultimate Emergence: Agent Humanity Layer ===
    # Lazy-initialized human characteristics
    _humanity_layer: AgentHumanityLayer | None = None

    def __post_init__(self) -> None:
        if not self.entity_id:
            raise ValueError("entity_id is required")
        if not self.name:
            self.name = f"Agent_{self.entity_id[:8]}"

    # -------------------------------------------------------------------------
    # Basic Properties
    # -------------------------------------------------------------------------

    @property
    def is_alive(self) -> bool:
        return self.health > 0.0

    @property
    def is_hungry(self) -> bool:
        return self.hunger > 0.5

    @property
    def is_thirsty(self) -> bool:
        return self.thirst > 0.5

    @property
    def perception_radius(self) -> float:
        return self._perception_radius

    @property
    def x(self) -> int:
        return self.position.x

    @property
    def y(self) -> int:
        return self.position.y

    @property
    def humanity(self) -> AgentHumanityLayer:
        """Get or create the Agent Humanity Layer (lazy initialization)."""
        if self._humanity_layer is None:
            self._humanity_layer = AgentHumanityLayer(self)
        return self._humanity_layer

    # -------------------------------------------------------------------------
    # Memory
    # -------------------------------------------------------------------------

    def remember(
        self,
        event_type: str,
        data: dict[str, Any],
        importance: float = 0.5,
        tick: int = 0,
    ) -> None:
        """Record an episodic memory."""
        memory = {
            "tick": tick,
            "type": event_type,
            "data": data,
            "importance": importance,
            "time": time.time(),
        }
        self._episodic_memory.append(memory)
        if len(self._episodic_memory) > self._max_episodic:
            self._evict_memory()

    def _evict_memory(self) -> None:
        """Evict least important memory when buffer is full."""
        if not self._episodic_memory:
            return
        # Remove oldest low-importance memory
        self._episodic_memory.sort(key=lambda m: (m["importance"], m["tick"]))
        self._episodic_memory.pop(0)

    def recall_recent(self, n: int = 10) -> list[dict[str, Any]]:
        """Get the N most recent memories."""
        sorted_mem = sorted(self._episodic_memory, key=lambda m: m["tick"], reverse=True)
        return sorted_mem[:n]

    def recall_by_type(self, event_type: str) -> list[dict[str, Any]]:
        """Get memories of a specific type."""
        return [m for m in self._episodic_memory if m["type"] == event_type]

    # -------------------------------------------------------------------------
    # Perception
    # -------------------------------------------------------------------------

    def perceive(self, signal: Signal) -> None:
        """Process an incoming signal."""
        self._pending_signals.append(signal)
        self.last_perception_tick = signal.duration  # Approximation

    def get_pending_signals(self) -> list[Signal]:
        """Get and clear pending signals."""
        signals = list(self._pending_signals)
        self._pending_signals.clear()
        return signals

    def update_perception_radius(self, radius: float) -> None:
        """Update the perception radius (called by tier system)."""
        self._perception_radius = radius

    # -------------------------------------------------------------------------
    # Decision Making
    # -------------------------------------------------------------------------

    def decide_action(
        self, tick: int, world: World
    ) -> Decision | None:
        """Decide what action to take."""
        if not self.is_alive:
            return None

        # Update needs
        self._update_needs(tick)

        # Determine highest priority need
        action = self._select_action(tick, world)
        return action

    def _update_needs(self, tick: int) -> None:
        """Update need levels (hunger, thirst, energy)."""
        # Basic need decay
        self.hunger = min(1.0, self.hunger + 0.001)
        self.thirst = min(1.0, self.thirst + 0.002)
        self.energy = max(0.0, self.energy - 0.0005)

        # === Ultimate Emergence: Emotional effects on needs ===
        # Stress from unmet needs affects emotional state
        if self.hunger > 0.5:
            self.humanity.stress_level = min(1.0, self.humanity.stress_level + 0.01)
            if self.hunger > 0.7:
                self.humanity.affect(EmotionType.FEAR, 0.1)
        if self.thirst > 0.5:
            self.humanity.stress_level = min(1.0, self.humanity.stress_level + 0.015)
        if self.energy < 0.3:
            self.humanity.affect(EmotionType.SADNESS, 0.05)

        # Critical needs override everything (considering human irrationality)
        if self.hunger > 0.8:
            # Human irrationality: some agents panic when hungry
            irrational = self.humanity.calculate_current_irrationality()
            if irrational > 0.3:
                self.current_goal = "panic_flee" if random.random() < 0.2 else "seek_food"
            else:
                self.current_goal = "seek_food"
            self.goal_priority = self.hunger
        elif self.thirst > 0.8:
            self.current_goal = "seek_water"
            self.goal_priority = self.thirst
        elif self.energy < 0.2:
            self.current_goal = "rest"
            self.goal_priority = 1.0 - self.energy
        else:
            self.current_goal = None
            self.goal_priority = 0.0

        # Update humanity layer state
        if self._humanity_layer is not None:
            self._humanity_layer.update(tick)

    def _select_action(
        self, tick: int, world: World
    ) -> Decision | None:
        """Select the best action based on current state."""
        goal = self.current_goal or "wander"
        goal = goal.lower()

        if goal == "seek_food":
            return self._action_seek_food(tick, world)
        elif goal == "seek_water":
            return self._action_seek_water(tick, world)
        elif goal == "rest":
            return self._action_rest(tick)
        elif goal == "wander":
            return self._action_wander(tick, world)
        elif goal == "socialize":
            return self._action_socialize(tick, world)
        elif goal == "trade":
            return self._action_trade(tick, world)
        elif goal == "work":
            return self._action_work(tick, world)
        elif goal == "explore":
            return self._action_explore(tick, world)
        else:
            return self._action_wander(tick, world)

    def _action_seek_food(self, tick: int, world: World) -> Decision:
        """Seek food."""
        # Find nearest food
        nearest_food: Pos2D | None = None
        min_dist = float("inf")

        for x in range(
            max(0, self.x - 20), min(world._config.world.width, self.x + 20)
        ):
            for y in range(
                max(0, self.y - 20), min(world._config.world.height, self.y + 20)
            ):
                terrain = world.get_terrain(x, y)
                if terrain in (
                    TerrainType.GRASSLAND, TerrainType.SAVANNA,
                    TerrainType.TROPICAL_FOREST, TerrainType.TEMPERATE_FOREST
                ):
                    dist = ((x - self.x) ** 2 + (y - self.y) ** 2) ** 0.5
                    if dist < min_dist:
                        min_dist = dist
                        nearest_food = Pos2D(x, y)

        if nearest_food and min_dist < self._perception_radius:
            # Move toward food
            self.remember("seek_food", {"target": (nearest_food.x, nearest_food.y)}, 0.8, tick)
            return Decision(
                tick=tick,
                agent_id=self.entity_id,
                decision_type=DecisionType.SEEK_FOOD,
                target_pos=nearest_food,
                expected_utility=self.hunger,
                algorithm="heuristic",
            )

        # No food nearby, wander
        return self._action_wander(tick, world)

    def _action_seek_water(self, tick: int, world: World) -> Decision:
        """Seek water."""
        for x in range(
            max(0, self.x - 20), min(world._config.world.width, self.x + 20)
        ):
            for y in range(
                max(0, self.y - 20), min(world._config.world.height, self.y + 20)
            ):
                terrain = world.get_terrain(x, y)
                if terrain.is_water:
                    self.remember("seek_water", {"found": (x, y)}, 0.9, tick)
                    return Decision(
                        tick=tick,
                        agent_id=self.entity_id,
                        decision_type=DecisionType.SEEK_WATER,
                        target_pos=Pos2D(x, y),
                        expected_utility=self.thirst,
                        algorithm="heuristic",
                    )

        return self._action_wander(tick, world)

    def _action_rest(self, tick: int) -> Decision:
        """Rest to recover energy."""
        self.energy = min(1.0, self.energy + 0.1)
        return Decision(
            tick=tick,
            agent_id=self.entity_id,
            decision_type=DecisionType.REST,
            expected_utility=0.5,
            algorithm="rule",
        )

    def _action_wander(self, tick: int, world: World) -> Decision:
        """Random movement."""
        # Move to adjacent walkable tile
        dx = world._rng.integers(-1, 2)
        dy = world._rng.integers(-1, 2)
        new_x = max(0, min(world._config.world.width - 1, self.x + dx))
        new_y = max(0, min(world._config.world.height - 1, self.y + dy))

        new_pos = Pos2D(new_x, new_y)
        terrain = world.get_terrain(new_x, new_y)

        if terrain.is_passable:
            self.remember("wander", {"from": (self.x, self.y), "to": (new_x, new_y)}, 0.1, tick)
            return Decision(
                tick=tick,
                agent_id=self.entity_id,
                decision_type=DecisionType.MOVE_TO,
                target_pos=new_pos,
                expected_utility=0.1,
                algorithm="random",
            )

        return Decision(
            tick=tick,
            agent_id=self.entity_id,
            decision_type=DecisionType.REST,
            expected_utility=0.1,
            algorithm="rule",
        )

    def _action_socialize(self, tick: int, world: World) -> Decision:
        """Try to interact with nearby agents."""
        nearby = list(world.get_agents_near(self.position, 3.0))
        if nearby:
            other, dist = nearby[0]
            return Decision(
                tick=tick,
                agent_id=self.entity_id,
                decision_type=DecisionType.SOCIALIZE,
                target_id=other.entity_id,
                expected_utility=0.3,
                algorithm="heuristic",
            )
        return self._action_wander(tick, world)

    def _action_trade(self, tick: int, world: World) -> Decision:
        """Attempt to trade."""
        return Decision(
            tick=tick,
            agent_id=self.entity_id,
            decision_type=DecisionType.TRADE,
            expected_utility=0.2,
            algorithm="market",
        )

    def _action_work(self, tick: int, world: World) -> Decision:
        """Do productive work."""
        skill = max(self.skills, key=lambda s: self.skills[s])
        self.remember("work", {"skill": skill, "level": self.skills[skill]}, 0.3, tick)
        return Decision(
            tick=tick,
            agent_id=self.entity_id,
            decision_type=DecisionType.WORK,
            expected_utility=0.3,
            algorithm="skill_based",
        )

    def _action_explore(self, tick: int, world: World) -> Decision:
        """Explore the world."""
        # Move toward unexplored area
        return Decision(
            tick=tick,
            agent_id=self.entity_id,
            decision_type=DecisionType.EXPLORE,
            expected_utility=0.2,
            algorithm="frontier",
        )

    # -------------------------------------------------------------------------
    # Action Execution
    # -------------------------------------------------------------------------

    def execute_action(self, decision: Decision, world: World) -> None:
        """Execute a decision."""
        if decision is None:
            return

        self.last_decision_tick = decision.tick

        if decision.decision_type == DecisionType.MOVE_TO and decision.target_pos:
            world.move_agent(self.entity_id, decision.target_pos)

        elif decision.decision_type == DecisionType.SEEK_FOOD:
            if decision.target_pos:
                self._consume_food(world)
            self.hunger = max(0.0, self.hunger - 0.3)

        elif decision.decision_type == DecisionType.SEEK_WATER:
            if decision.target_pos:
                self._consume_water(world)
            self.thirst = max(0.0, self.thirst - 0.4)

        elif decision.decision_type == DecisionType.SOCIALIZE:
            if decision.target_id:
                self._socialize(decision.target_id, world)

        elif decision.decision_type == DecisionType.WORK:
            self._do_work(world)

        elif decision.decision_type == DecisionType.TRADE:
            self._do_trade(world)

    def _consume_food(self, world: World) -> None:
        """Consume food at current location."""
        terrain = world.get_terrain(self.x, self.y)
        if terrain in (
            TerrainType.GRASSLAND, TerrainType.SAVANNA, TerrainType.TROPICAL_FOREST
        ):
            self.inventory.add(ResourceType.FRUIT, 1.0)

    def _consume_water(self, world: World) -> None:
        """Consume water at current location."""
        terrain = world.get_terrain(self.x, self.y)
        if terrain.is_water:
            self.thirst = 0.0

    def _socialize(self, other_id: EntityID, world: World) -> None:
        """Interact with another agent."""
        world.set_relationship(
            self.entity_id,
            other_id,
            trust=self.agreeableness * 0.1,
        )
        self.remember(
            "socialize",
            {"with": other_id, "trust_delta": self.agreeableness * 0.1},
            0.4,
            world.tick,
        )

    def _do_work(self, world: World) -> None:
        """Perform productive work."""
        # Add some wealth based on skills
        skill_level = sum(self.skills.values()) / len(self.skills)
        earnings = skill_level * 2.0
        self.wealth += earnings
        self.energy = max(0.0, self.energy - 0.02)

    def _do_trade(self, world: World) -> None:
        """Attempt to trade."""
        # Simple trade logic
        if self.inventory.total_weight() > 20:
            self.wealth += 5.0

    # -------------------------------------------------------------------------
    # Aging and Lifecycle
    # -------------------------------------------------------------------------

    def age(self, ticks: int = 1) -> None:
        """Age the agent."""
        self.attributes = self.attributes.age_ticks(ticks)
        self.health = max(0.0, self.health - 0.00001 * ticks)

        # Mortality risk increases with age
        if self.attributes.age > 60 * 360:  # 60 years
            mortality = 0.0001 * (self.attributes.age - 60 * 360) / (40 * 360)
            self.health = max(0.0, self.health - mortality)

    # -------------------------------------------------------------------------
    # Belief Update
    # -------------------------------------------------------------------------

    def update_belief(
        self,
        proposition: str,
        evidence: str,
        confirms: bool,
        strength: float,
        tick: int,
    ) -> None:
        """Update a belief with new evidence."""
        existing = next((b for b in self.beliefs if b.proposition == proposition), None)

        if existing:
            # Update existing belief
            idx = self.beliefs.index(existing)
            self.beliefs[idx] = existing.update(
                evidence, confirms, strength, tick
            )
        else:
            # Create new belief
            belief = CognitiveBelief(
                proposition=proposition,
                confidence=0.5 if confirms else 0.3,
                source_tick=tick,
                evidence=(evidence,),
                counter_evidence=() if confirms else (evidence,),
                last_updated_tick=tick,
            )
            self.beliefs.append(belief)

    # -------------------------------------------------------------------------
    # String Representation
    # -------------------------------------------------------------------------

    def __str__(self) -> str:
        return f"Agent({self.name}, tier={self.tier.name}, pos=({self.x}, {self.y}), health={self.health:.2f})"

    def __repr__(self) -> str:
        return (
            f"Agent(id={self.entity_id[:8]}, tier={self.tier.name}, "
            f"pos=({self.x}, {self.y}), health={self.health:.2f}, "
            f"wealth={self.wealth:.1f}, tier={self.tier.name})"
        )


# ---------------------------------------------------------------------------
# Agent Factory
# ---------------------------------------------------------------------------


class AgentFactory:
    """
    Factory for creating agents with consistent initialization.

    Responsible for:
    - Generating agent names
    - Distributing initial attributes
    - Setting up cognitive systems
    - Registering with the world
    """

    NAMES_FIRST = [
        "Aldric", "Brynn", "Cedric", "Diana", "Elena", "Fenris", "Gwendolyn", "Hector",
        "Isolde", "Jasper", "Kira", "Lysander", "Mira", "Nolan", "Ophelia", "Pyrus",
        "Quinn", "Rowena", "Silas", "Thalia", "Uri", "Vesper", "Wren", "Xander",
        "Yara", "Zephyr", "Aria", "Bodhi", "Calla", "Dorian", "Eira", "Florian",
    ]

    NAMES_SECOND = [
        "of the Mountain", "of the River", "of the Valley", "of the Shore",
        "the Wanderer", "the Builder", "the Hunter", "the Healer", "the Smith",
        "the Trader", "the Scholar", "the Warrior", "the Farmer", "the Shepherd",
    ]

    def __init__(self, world: World) -> None:
        self.world = world
        self._name_used: set[str] = set()
        self._agent_index = 0

    def create_agent(
        self,
        tier: AgentTier,
        position: Pos2D | None = None,
        name: str | None = None,
        seed: int | None = None,
    ) -> Agent:
        """Create a new agent with the given tier."""
        rng = np.random.Generator(np.random.PCG64(seed or self._agent_index))
        self._agent_index += 1

        # Generate entity ID
        from ambientsaga.types import new_entity_id
        entity_id = new_entity_id()

        # Generate or use provided name
        if name is None:
            name = self._generate_name(rng)

        # Determine position
        if position is None:
            position = self._find_suitable_position(rng)

        # Generate attributes
        from ambientsaga.types import Attribute
        attrs_list = [
            (Attribute.STRENGTH, rng.uniform(0.3, 0.8)),
            (Attribute.INTELLIGENCE, rng.uniform(0.3, 0.8)),
            (Attribute.CHARISMA, rng.uniform(0.3, 0.8)),
            (Attribute.WISDOM, rng.uniform(0.3, 0.8)),
            (Attribute.DEXTERITY, rng.uniform(0.3, 0.8)),
            (Attribute.ENDURANCE, rng.uniform(0.3, 0.8)),
            (Attribute.PERCEPTION, rng.uniform(0.3, 0.8)),
            (Attribute.CREATIVITY, rng.uniform(0.3, 0.8)),
            (Attribute.PATIENCE, rng.uniform(0.3, 0.8)),
            (Attribute.COURAGE, rng.uniform(0.3, 0.8)),
            (Attribute.JUST, rng.uniform(0.3, 0.8)),
            (Attribute.GREED, rng.uniform(0.3, 0.8)),
            (Attribute.COMPASSION, rng.uniform(0.3, 0.8)),
            (Attribute.PRIDE, rng.uniform(0.3, 0.8)),
            (Attribute.ENVY, rng.uniform(0.3, 0.8)),
            (Attribute.TEMPERANCE, rng.uniform(0.3, 0.8)),
        ]
        age_ticks = rng.integers(18 * 360, 60 * 360)
        gender = rng.choice(["male", "female", "other"])
        cultures = ["nomadic", "agricultural", "trading", "warrior", "spiritual"]
        languages = ["common", "ancient", "tribal", "merchant"]
        appearance_templates = [
            "weathered skin and calloused hands",
            "tall and lean with sharp features",
            "short and sturdy with a warm smile",
            "pale and thin with piercing eyes",
            "broad-shouldered with sun-darkened skin",
        ]
        personality_templates = [
            "cautious and pragmatic",
            "bold and ambitious",
            "peaceful and introspective",
            "curious and quick-witted",
            "loyal and protective",
        ]
        talent_options = ["hunting", "crafting", "healing", "trading", "farming", "fighting", "storytelling", "music"]
        flaw_options = ["greed", "pride", "envy", "wrath", "laziness", "cowardice", "cruelty", "impulsiveness"]
        ambition_options = ["wealth", "power", "knowledge", "peace", "legacy", "freedom", "belonging"]
        fear_options = ["death", "isolation", "failure", "rejection", "darkness", "loss"]
        attrs = AgentAttributes(
            name=name,
            age=age_ticks,
            gender=gender,
            attributes=frozenset(attrs_list),
            culture_id=rng.choice(cultures),
            native_language=rng.choice(languages),
            appearance=rng.choice(appearance_templates),
            personality_summary=rng.choice(personality_templates),
            backstory=f"{name} grew up in a {rng.choice(cultures)} community.",
            talents=frozenset(rng.choice(talent_options, size=min(3, len(talent_options)), replace=False)),
            flaws=frozenset(rng.choice(flaw_options, size=min(2, len(flaw_options)), replace=False)),
            ambition=rng.choice(ambition_options),
            fear=rng.choice(fear_options),
        )

        # Create agent
        agent = Agent(
            entity_id=entity_id,
            name=name,
            position=position,
            tier=tier,
            attributes=attrs,
            honesty_humility=rng.uniform(0.3, 0.8),
            emotionality=rng.uniform(0.3, 0.8),
            extraversion=rng.uniform(0.3, 0.8),
            agreeableness=rng.uniform(0.3, 0.8),
            conscientiousness=rng.uniform(0.3, 0.8),
            openness=rng.uniform(0.3, 0.8),
            _perception_radius=self._get_tier_radius(tier),
        )

        # Set initial wealth
        agent.wealth = rng.uniform(50.0, 200.0)

        # Initialize skills based on tier
        self._initialize_skills(agent, rng, tier)

        return agent

    def spawn_population(
        self,
        n: int,
        tier_distribution: dict[int, int] | None = None,
    ) -> list[Agent]:
        """
        Spawn a population of agents.

        Args:
            n: Total number of agents
            tier_distribution: Dict mapping tier (1-4) to count.
                              If None, uses config defaults.
        """
        if tier_distribution is None:
            cfg = self.world._config.agents
            tier_distribution = {
                AgentTier.L1_CORE: cfg.tier1_count,
                AgentTier.L2_FUNCTIONAL: cfg.tier2_count,
                AgentTier.L3_BACKGROUND: cfg.tier3_count,
            }

        agents: list[Agent] = []

        for tier, count in tier_distribution.items():
            for _ in range(count):
                agent = self.create_agent(tier)
                agents.append(agent)
                self.world.register_agent(agent)

        return agents

    def _generate_name(self, rng: np.random.Generator) -> str:
        """Generate a unique name."""
        for _ in range(100):
            first = rng.choice(self.NAMES_FIRST)
            second = rng.choice(self.NAMES_SECOND)
            name = f"{first} {second}"
            if name not in self._name_used:
                self._name_used.add(name)
                return name
        # Fallback
        return f"Agent_{rng.integers(10000, 99999)}"

    def _find_suitable_position(self, rng: np.random.Generator) -> Pos2D:
        """Find a suitable spawn position on land."""
        w = self.world._config.world.width
        h = self.world._config.world.height

        for _ in range(1000):
            x = rng.integers(0, w)
            y = rng.integers(0, h)
            if self.world.is_passable(x, y):
                return Pos2D(x, y)

        # Fallback
        return Pos2D(w // 2, h // 2)

    def _get_tier_radius(self, tier: AgentTier) -> float:
        """Get default perception radius for a tier."""
        cfg = self.world._config.agents
        if tier == AgentTier.L1_CORE:
            return cfg.max_perception_radius_tier1
        elif tier == AgentTier.L2_FUNCTIONAL:
            return cfg.max_perception_radius_tier2
        elif tier == AgentTier.L3_BACKGROUND:
            return cfg.max_perception_radius_tier3
        else:
            return 1.0

    def _initialize_skills(
        self, agent: Agent, rng: np.random.Generator, tier: AgentTier
    ) -> None:
        """Initialize skills based on tier and randomness."""
        # Map tier to numeric for bonus calculation
        tier_order = {
            AgentTier.L1_CORE: 3,
            AgentTier.L2_FUNCTIONAL: 2,
            AgentTier.L3_BACKGROUND: 1,
        }
        tier_num = tier_order.get(tier, 2)
        tier_bonus = (tier_num - 2) * 0.05
        for skill in agent.skills:
            agent.skills[skill] = rng.uniform(0.3, 0.7) + tier_bonus

