"""
Agent core - the foundation of individual agents in the simulation.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ambientsaga.types import EntityID, Pos2D, ResourceType, Tick


# Agent Tier - determines processing strategy
class AgentTier(Enum):
    """Agent processing tier - determines how agent decisions are made.

    Tier hierarchy (highest to lowest capability):
    - L1_CORE: Full LLM reasoning, few agents
    - L2_FUNCTIONAL: Hybrid: embedding + occasional LLM
    - L3_BACKGROUND: Rule-based, most agents
    - L4_ECOLOGICAL: Rule-based population dynamics, background processes
    """

    L1_CORE = "l1_core"           # Full LLM reasoning, few agents
    L2_FUNCTIONAL = "l2_functional"  # Hybrid: embedding + occasional LLM
    L3_BACKGROUND = "l3_background"  # Rule-based, most agents
    L4_ECOLOGICAL = "l4_ecological"  # Rule-based population dynamics

    @property
    def is_llm_capable(self) -> bool:
        """Whether this tier has LLM reasoning capability."""
        return self in {AgentTier.L1_CORE, AgentTier.L2_FUNCTIONAL}

    @property
    def processing_priority(self) -> int:
        """Processing priority (lower = higher priority)."""
        return {
            AgentTier.L1_CORE: 0,
            AgentTier.L2_FUNCTIONAL: 1,
            AgentTier.L3_BACKGROUND: 2,
            AgentTier.L4_ECOLOGICAL: 3,
        }[self]


# Agent State
class AgentState(Enum):
    """Current state of an agent."""
    ALIVE = "alive"
    DEAD = "dead"
    SLEEPING = "sleeping"
    TRAVELING = "traveling"
    WORKING = "working"
    SOCIALIZING = "socializing"
    CELEBRATING = "celebrating"
    MOURNING = "mourning"


@dataclass
class PersonalityTraits:
    """Big Five personality traits plus additional dimensions."""
    # Big Five
    openness: float = 0.5        # 0-1, curiosity/creativity
    conscientiousness: float = 0.5  # 0-1, organization/discipline
    extraversion: float = 0.5   # 0-1, sociability
    agreeableness: float = 0.5  # 0-1, cooperation/compassion
    neuroticism: float = 0.5   # 0-1, emotional stability (inverted: high = stable)

    # Additional
    dominance: float = 0.5      # 0-1, leadership/assertiveness
    religiosity: float = 0.5    # 0-1, spiritual orientation
    materialism: float = 0.5   # 0-1, value on possessions
    risk_tolerance: float = 0.5  # 0-1, willingness to take risks
    patience: float = 0.5       # 0-1, delayed gratification

    def to_dict(self) -> dict[str, float]:
        return {
            "openness": self.openness,
            "conscientiousness": self.conscientiousness,
            "extraversion": self.extraversion,
            "agreeableness": self.agreeableness,
            "neuroticism": self.neuroticism,
            "dominance": self.dominance,
            "religiosity": self.religiosity,
            "materialism": self.materialism,
            "risk_tolerance": self.risk_tolerance,
            "patience": self.patience,
        }


@dataclass
class Goal:
    """A goal that an agent is pursuing."""
    goal_id: str
    description: str
    priority: float = 0.5  # 0-1
    progress: float = 0.0  # 0-1
    deadline: Tick | None = None
    parent_goal: str | None = None
    sub_goals: list[str] = field(default_factory=list)
    abandoned: bool = False

    def update(self, progress_delta: float) -> None:
        self.progress = min(1.0, self.progress + progress_delta)


@dataclass
class MemoryEntry:
    """A single memory entry."""
    tick: Tick
    content: str
    memory_type: str  # "episodic", "semantic", "procedural"
    emotional_valence: float = 0.0  # -1 (negative) to +1 (positive)
    importance: float = 0.5  # 0-1, how memorable
    location: Pos2D | None = None
    entities_involved: list[EntityID] = field(default_factory=list)
    vividness: float = 1.0  # 0-1, fades over time

    def decay(self, factor: float = 0.01) -> None:
        """Apply memory decay."""
        self.vividness = max(0, self.vividness - factor)
        self.importance = max(0, self.importance - factor * 0.5)


@dataclass
class AgentMemory:
    """
    Multi-layered memory system for agents.
    Simulates the way humans store and retrieve memories.
    """
    episodic: list[MemoryEntry] = field(default_factory=list)  # Personal experiences
    semantic: list[MemoryEntry] = field(default_factory=list)  # World knowledge
    procedural: list[MemoryEntry] = field(default_factory=list)  # Skills and habits
    emotional_tags: dict[str, float] = field(default_factory=dict)  # Emotional associations

    max_episodic: int = 500
    max_semantic: int = 1000
    max_procedural: int = 200

    def add_memory(self, entry: MemoryEntry) -> None:
        """Add a memory entry."""
        if entry.memory_type == "episodic":
            self.episodic.append(entry)
            if len(self.episodic) > self.max_episodic:
                self._consolidate_episodic()
        elif entry.memory_type == "semantic":
            self.semantic.append(entry)
            if len(self.semantic) > self.max_semantic:
                self.semantic = self.semantic[-self.max_semantic:]
        elif entry.memory_type == "procedural":
            self.procedural.append(entry)
            if len(self.procedural) > self.max_procedural:
                self.procedural = self.procedural[-self.max_procedural:]

    def _consolidate_episodic(self) -> None:
        """Consolidate episodic memories - keep important ones, compress others."""
        # Sort by (vividness * importance)
        scored = sorted(
            self.episodic,
            key=lambda m: m.vividness * m.importance,
            reverse=True
        )
        # Keep top half
        self.episodic = scored[:self.max_episodic // 2]
        # Compress remaining into semantic summaries
        for entry in scored[self.max_episodic // 2:]:
            entry.content = f"[Memory fragment] {entry.content[:50]}..."
            entry.vividness *= 0.3
            self.episodic.append(entry)

    def decay_memories(self, tick: Tick) -> None:
        """Apply time-based decay to all memories."""
        for entry in self.episodic:
            entry.decay()
        # Remove faded memories
        self.episodic = [m for m in self.episodic if m.vividness > 0.05]
        self.semantic = [m for m in self.semantic if m.importance > 0.05]

    def recall_recent(self, count: int = 10) -> list[MemoryEntry]:
        """Recall recent episodic memories."""
        return sorted(self.episodic, key=lambda m: m.tick, reverse=True)[:count]

    def recall_emotional(self, valence_threshold: float = 0.5) -> list[MemoryEntry]:
        """Recall emotionally significant memories."""
        return [
            m for m in self.episodic
            if abs(m.emotional_valence) >= valence_threshold
        ]

    def get_fragments(self, count: int = 5) -> list[str]:
        """Get fragmented memory snippets (for atmospheric storytelling)."""
        # Return low-vividness fragments for a dreamlike quality
        fragments = [m for m in self.episodic if 0.1 < m.vividness < 0.4]
        if len(fragments) < count:
            fragments = [m for m in self.episodic if m.vividness < 0.6]
        fragments = sorted(fragments, key=lambda m: m.tick, reverse=True)
        return [f"[{m.tick}] ...{m.content}..." for m in fragments[:count]]


@dataclass
class AgentProfile:
    """Complete profile of an agent."""
    agent_id: EntityID
    name: str
    age: int = 25
    gender: str = "unknown"
    tier: AgentTier = AgentTier.L3_BACKGROUND

    # Physical
    position: Pos2D = Pos2D(0, 0)
    home_position: Pos2D = Pos2D(0, 0)

    # Personality
    personality: PersonalityTraits = field(default_factory=PersonalityTraits)

    # Culture and identity
    culture: str = "default"
    language: str = "common"
    beliefs: list[str] = field(default_factory=list)
    values: list[str] = field(default_factory=list)

    # Needs (Maslow-inspired)
    needs: dict[str, float] = field(default_factory=lambda: {
        "physiological": 0.7,
        "safety": 0.7,
        "belonging": 0.7,
        "esteem": 0.7,
        "self_actualization": 0.5,
    })

    # Resources
    resources: dict[ResourceType, float] = field(default_factory=dict)
    skills: dict[str, float] = field(default_factory=lambda: {
        "gathering": 0.3,
        "crafting": 0.3,
        "social": 0.3,
        "combat": 0.1,
        "exploration": 0.3,
    })

    # Relationships (entity_id -> relationship strength -1 to 1)
    relationships: dict[EntityID, float] = field(default_factory=dict)

    # Goals
    goals: list[Goal] = field(default_factory=list)

    # Narrative
    title: str = ""  # e.g., "the wanderer", "the healer"
    reputation: float = 0.5  # 0-1, how others see them
    known_for: list[str] = field(default_factory=list)  # Things they're known for

    # Life events (for narrative)
    birth_tick: Tick = 0
    last_action_tick: Tick = 0

    def apply_needs_decay(self) -> None:
        """Apply basic needs decay over time."""
        self.needs["physiological"] = max(0, self.needs["physiological"] - 0.01)
        self.needs["safety"] = max(0, self.needs["safety"] - 0.005)
        self.needs["belonging"] = max(0, self.needs["belonging"] - 0.003)
        self.needs["esteem"] = max(0, self.needs["esteem"] - 0.002)
        self.needs["self_actualization"] = max(0, self.needs["self_actualization"] - 0.001)

    def get_dominant_need(self) -> str:
        """Get the most urgent unsatisfied need."""
        urgent = [(v, k) for k, v in self.needs.items() if v < 0.6]
        if urgent:
            urgent.sort()
            return urgent[0][1]
        return "self_actualization"

    def get_active_goal(self) -> Goal | None:
        """Get the highest priority active goal."""
        active = [g for g in self.goals if not g.abandoned]
        if active:
            return max(active, key=lambda g: g.priority)
        return None


@dataclass
class ActionResult:
    """Result of an agent action."""
    action_type: str
    success: bool
    tick: Tick
    target: EntityID | None = None
    position: Pos2D | None = None
    resources_changed: dict[ResourceType, float] = field(default_factory=dict)
    message: str = ""
    alive: bool = True
    priority: int = 10  # Scheduling priority for next tick
    events: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class SocialBond:
    """A social bond between two agents."""
    agent_a: EntityID
    agent_b: EntityID
    bond_type: str  # "friend", "family", "rival", "romantic", "professional"
    strength: float = 0.5  # 0-1
    last_interaction: Tick = 0
    interactions: int = 0


class Agent(ABC):
    """
    Abstract base class for all agents in the simulation.
    Each agent has a profile, memory, and the ability to take actions.
    """

    def __init__(self, profile: AgentProfile):
        self.profile = profile
        self.memory = AgentMemory()
        self._last_tick_processed: Tick = 0

    @property
    def id(self) -> EntityID:
        return self.profile.agent_id

    @property
    def position(self) -> Pos2D:
        return self.profile.position

    @property
    def tier(self) -> AgentTier:
        return self.profile.tier

    @abstractmethod
    async def think(self, tick: Tick, context: dict[str, Any]) -> ActionResult:
        """
        Core thinking process - decide what to do.
        Subclasses implement different thinking strategies.
        """
        pass

    @abstractmethod
    async def act(self, action: ActionResult, tick: Tick) -> None:
        """
        Execute the decided action.
        """
        pass

    async def tick(self, tick: Tick, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Main agent tick - think and act.
        Returns a dict with results for the simulation engine.
        """
        if context is None:
            context = {}

        self.profile.apply_needs_decay()
        self.memory.decay_memories(tick)

        # Think
        result = await self.think(tick, context)

        # Act
        if result.success and result.alive:
            await self.act(result, tick)

        self.profile.last_action_tick = tick
        self._last_tick_processed = tick

        # Record in memory
        self._record_action(result)

        return {
            "alive": result.alive,
            "action": result.action_type,
            "success": result.success,
            "priority": result.priority,
        }

    def _record_action(self, result: ActionResult) -> None:
        """Record an action in memory."""
        if result.success:
            valence = 0.1
        else:
            valence = -0.1

        entry = MemoryEntry(
            tick=result.tick,
            content=f"{result.action_type}: {result.message}",
            memory_type="episodic",
            emotional_valence=valence,
            importance=0.3,
            position=result.position,
        )
        self.memory.add_memory(entry)

    def add_goal(self, description: str, priority: float = 0.5) -> Goal:
        """Add a new goal."""
        goal = Goal(
            goal_id=str(uuid.uuid4()),
            description=description,
            priority=priority,
        )
        self.profile.goals.append(goal)
        return goal

    def set_belief(self, belief: str) -> None:
        """Set a belief."""
        if belief not in self.profile.beliefs:
            self.profile.beliefs.append(belief)

    def get_memory_summary(self, max_entries: int = 20) -> str:
        """Get a text summary of recent memories."""
        recent = self.memory.recall_recent(max_entries)
        if not recent:
            return "No significant memories."

        lines = []
        for m in recent:
            lines.append(f"[Tick {m.tick}] {m.content}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Serialize agent to dict."""
        return {
            "agent_id": str(self.profile.agent_id),
            "name": self.profile.name,
            "age": self.profile.age,
            "position": {"x": self.profile.position.x, "y": self.profile.position.y},
            "tier": self.profile.tier.value,
            "state": self.profile.needs,
            "goals": [g.description for g in self.profile.goals[:5]],
            "memory_count": len(self.memory.episodic),
            "relationships": len(self.profile.relationships),
        }


class RuleBasedAgent(Agent):
    """Rule-based agent - uses simple rules for decision making."""

    def __init__(self, profile: AgentProfile):
        super().__init__(profile)
        self.profile.tier = AgentTier.L3_BACKGROUND

    async def think(self, tick: Tick, context: dict[str, Any]) -> ActionResult:
        """Simple rule-based decision making."""
        # Priority: satisfy most urgent need
        dominant_need = self.profile.get_dominant_need()

        if dominant_need == "physiological":
            # Look for food/water
            return ActionResult(
                action_type="gather",
                success=True,
                tick=tick,
                message=f"Gathering resources for {dominant_need}",
            )
        elif dominant_need == "safety":
            return ActionResult(
                action_type="seek_shelter",
                success=True,
                tick=tick,
                message="Seeking safety",
            )
        elif dominant_need == "belonging":
            return ActionResult(
                action_type="socialize",
                success=True,
                tick=tick,
                message="Seeking social connection",
            )
        elif dominant_need == "esteem":
            return ActionResult(
                action_type="work",
                success=True,
                tick=tick,
                message="Working to build reputation",
            )
        else:
            return ActionResult(
                action_type="explore",
                success=True,
                tick=tick,
                message="Exploring and growing",
            )

    async def act(self, action: ActionResult, tick: Tick) -> None:
        """Execute the action."""
        # Simple implementation - in full version, this would interact with world
        if action.action_type == "gather":
            self.profile.needs["physiological"] = min(1.0, self.profile.needs["physiological"] + 0.1)
        elif action.action_type == "socialize":
            self.profile.needs["belonging"] = min(1.0, self.profile.needs["belonging"] + 0.1)
        elif action.action_type == "work":
            self.profile.needs["esteem"] = min(1.0, self.profile.needs["esteem"] + 0.05)


class LLMGuidedAgent(Agent):
    """
    LLM-guided agent - uses language model for decision making.
    This is the premium tier for key characters.
    """

    def __init__(self, profile: AgentProfile, llm_config: dict[str, Any] | None = None):
        super().__init__(profile)
        self.profile.tier = AgentTier.L1_CORE
        self.llm_config = llm_config or {}

    async def think(self, tick: Tick, context: dict[str, Any]) -> ActionResult:
        """
        LLM-powered decision making.
        In production, this would call the LLM API.
        For now, falls back to rule-based with richer context.
        """
        # Build rich context for LLM
        prompt_context = self._build_llm_context(tick, context)

        # In production: call LLM API here
        # For now, use enhanced rule-based reasoning
        return await self._llm_fallback_think(prompt_context, tick)

    def _build_llm_context(self, tick: Tick, context: dict[str, Any]) -> dict[str, Any]:
        """Build rich context for LLM decision making."""
        memory_summary = self.get_memory_summary(10)
        active_goal = self.profile.get_active_goal()

        return {
            "agent": self.profile,
            "memory_summary": memory_summary,
            "active_goal": active_goal.description if active_goal else "None",
            "needs": self.profile.needs,
            "tick": tick,
            "world_state": context.get("world_state", {}),
            "nearby_agents": context.get("nearby_agents", []),
        }

    async def _llm_fallback_think(self, context: dict[str, Any], tick: Tick) -> ActionResult:
        """Fallback reasoning when LLM is not available."""
        dominant_need = self.profile.get_dominant_need()
        self.memory.get_fragments(3)

        # Build atmospheric action descriptions
        action_map = {
            "physiological": "forage",
            "safety": "fortify",
            "belonging": "connect",
            "esteem": "create",
            "self_actualization": "reflect",
        }

        action_type = action_map.get(dominant_need, "wander")

        messages = {
            "forage": "Scouring the land for sustenance, driven by hunger.",
            "fortify": "Strengthening defenses, wary of unseen dangers.",
            "connect": "Seeking the warmth of companionship.",
            "create": "Building something meaningful to leave a mark.",
            "reflect": "Pondering the deeper questions of existence.",
            "wander": "Drifting through the world, open to whatever comes.",
        }

        return ActionResult(
            action_type=action_type,
            success=True,
            tick=tick,
            message=messages.get(action_type, "Moving forward."),
        )

    async def act(self, action: ActionResult, tick: Tick) -> None:
        """Execute the action with atmospheric storytelling."""
        # Add richer memory entries for LLM-guided agents
        entry = MemoryEntry(
            tick=tick,
            content=f"{action.message}",
            memory_type="episodic",
            emotional_valence=0.1,
            importance=0.5,
            position=self.profile.position,
            vividness=0.8,
        )
        self.memory.add_memory(entry)


class AgentRegistry:
    """Registry for managing all agents in the simulation."""

    def __init__(self, max_agents: int = 100000):
        self.max_agents = max_agents
        self._agents: dict[EntityID, Agent] = {}
        self._position_index: dict[Pos2D, EntityID] = {}
        self._tier_counts: dict[AgentTier, int] = dict.fromkeys(AgentTier, 0)

    def register(self, agent: Agent) -> bool:
        """Register a new agent."""
        if len(self._agents) >= self.max_agents:
            return False
        if agent.id in self._agents:
            return False

        self._agents[agent.id] = agent
        self._position_index[agent.position] = agent.id
        self._tier_counts[agent.tier] = self._tier_counts.get(agent.tier, 0) + 1
        return True

    def unregister(self, agent_id: EntityID) -> None:
        """Unregister an agent."""
        agent = self._agents.pop(agent_id, None)
        if agent:
            self._position_index.pop(agent.position, None)
            self._tier_counts[agent.tier] = max(0, self._tier_counts.get(agent.tier, 1) - 1)

    def get_agent(self, agent_id: EntityID) -> Agent | None:
        """Get an agent by ID."""
        return self._agents.get(agent_id)

    def update_position(self, agent_id: EntityID, new_pos: Pos2D) -> None:
        """Update an agent's position in the spatial index."""
        agent = self._agents.get(agent_id)
        if agent:
            old_pos = agent.profile.position
            if old_pos in self._position_index and self._position_index[old_pos] == agent_id:
                del self._position_index[old_pos]
            self._position_index[new_pos] = agent_id
            agent.profile.position = new_pos

    def list_all_agents(self) -> list[EntityID]:
        """List all agent IDs."""
        return list(self._agents.keys())

    def count(self) -> int:
        """Get total agent count."""
        return len(self._agents)

    def count_by_tier(self, tier: AgentTier) -> int:
        """Get agent count by tier."""
        return self._tier_counts.get(tier, 0)

    def get_agents_near(self, pos: Pos2D, radius: int) -> list[Agent]:
        """Get agents within radius of a position."""
        results = []
        for agent in self._agents.values():
            dx = agent.position.x - pos.x
            dy = agent.position.y - pos.y
            if dx * dx + dy * dy <= radius * radius:
                results.append(agent)
        return results

    def get_all_agents(self) -> list[Agent]:
        """Get all agents."""
        return list(self._agents.values())

    def get_stats(self) -> dict[str, Any]:
        """Get registry statistics."""
        return {
            "total": self.count(),
            "by_tier": dict(self._tier_counts),
            "max": self.max_agents,
        }
