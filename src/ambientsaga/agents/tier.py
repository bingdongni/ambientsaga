"""
Tier Manager — manages agent tier transitions and hot-spot upgradation.

This is the core component that implements the multi-tier architecture:
- L1 Core: Full LLM reasoning
- L2 Functional: Periodic LLM with memory
- L3 Background: Lightweight behavior-driven
- L4 Ecological: Rule-based population dynamics

The tier manager handles:
- Agent tier transitions (upgrade/downgrade)
- Hot-spot detection and temporary upgrade triggering
- Per-tier processing budgets
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import TYPE_CHECKING

from ambientsaga.config import AgentConfig
from ambientsaga.types import AgentTier, EntityID, Pos2D

if TYPE_CHECKING:
    from ambientsaga.world.chunk import ChunkManager
    from ambientsaga.world.state import World


class TierManager:
    """
    Manages agent tier assignments and processing.

    Key responsibilities:
    - Track agent tiers
    - Detect hot-spots (conflict zones, settlements, disasters)
    - Trigger temporary upgrades for important events
    - Budget LLM inference costs
    - Coordinate per-tier processing schedules
    """

    def __init__(
        self,
        config: AgentConfig,
        world: World,
        chunk_manager: ChunkManager,
    ) -> None:
        self.config = config
        self.world = world
        self.chunk_manager = chunk_manager

        # Tier registries
        self._tier_agents: dict[AgentTier, set[EntityID]] = defaultdict(set)
        self._agent_tier: dict[EntityID, AgentTier] = {}
        self._agent_base_tier: dict[EntityID, AgentTier] = {}  # Before temporary upgrades
        self._agent_temporary: dict[EntityID, int] = {}  # Remaining ticks of temporary tier

        # Hot-spot tracking
        self._hotspot_chunks: set[tuple[int, int]] = set()
        self._hotspot_tiles: dict[tuple[int, int], float] = {}  # (x,y) -> intensity

        # Processing budgets
        self._llm_budget_tier1 = config.deliberation_budget_tier1
        self._llm_budget_tier2 = config.deliberation_budget_tier2
        self._llm_budget_tier3 = config.deliberation_budget_tier3

        # Statistics
        self._stats = {
            "total_upgrades": 0,
            "total_downgrades": 0,
            "temporary_upgrades": 0,
            "hotspot_triggers": 0,
        }

        # Callbacks for tier change events
        self._tier_change_callbacks: list[Callable[[EntityID, AgentTier, AgentTier], None]] = []

    def register_agent(self, agent_id: EntityID, tier: AgentTier) -> None:
        """Register an agent with an initial tier."""
        self._agent_tier[agent_id] = tier
        self._agent_base_tier[agent_id] = tier
        self._tier_agents[tier].add(agent_id)

    def unregister_agent(self, agent_id: EntityID) -> None:
        """Remove an agent from the tier system."""
        tier = self._agent_tier.pop(agent_id, None)
        if tier is not None:
            self._tier_agents[tier].discard(agent_id)
        self._agent_base_tier.pop(agent_id, None)
        self._agent_temporary.pop(agent_id, None)

    def get_tier(self, agent_id: EntityID) -> AgentTier:
        """Get current tier of an agent."""
        return self._agent_tier.get(agent_id, AgentTier.L3_BACKGROUND)

    def get_base_tier(self, agent_id: EntityID) -> AgentTier:
        """Get base tier (before temporary upgrades)."""
        return self._agent_base_tier.get(agent_id, AgentTier.L3_BACKGROUND)

    def upgrade_tier(
        self, agent_id: EntityID, temporary: bool = False, duration: int = 100
    ) -> AgentTier:
        """
        Upgrade an agent to the next tier.

        If temporary=True, the upgrade lasts for `duration` ticks then reverts.
        """
        current = self.get_tier(agent_id)
        if current.value >= AgentTier.L1_CORE.value:
            return current  # Already at maximum

        new_tier = AgentTier(current.value - 1)  # Upgrade = lower number

        self._set_tier(agent_id, new_tier, temporary, duration)

        if not temporary:
            self._stats["total_upgrades"] += 1
        else:
            self._stats["temporary_upgrades"] += 1

        return new_tier

    def downgrade_tier(self, agent_id: EntityID) -> AgentTier:
        """Downgrade an agent to the next lower tier."""
        current = self.get_tier(agent_id)
        if current.value >= AgentTier.L4_ECOLOGICAL.value:
            return current

        new_tier = AgentTier(current.value + 1)
        self._set_tier(agent_id, new_tier, False, 0)
        self._stats["total_downgrades"] += 1

        return new_tier

    def _set_tier(
        self,
        agent_id: EntityID,
        tier: AgentTier,
        temporary: bool,
        duration: int,
    ) -> None:
        """Set agent tier with callbacks."""
        old_tier = self._agent_tier.get(agent_id)

        if old_tier is not None:
            self._tier_agents[old_tier].discard(agent_id)

        self._agent_tier[agent_id] = tier
        self._tier_agents[tier].add(agent_id)

        if temporary:
            self._agent_temporary[agent_id] = duration
        else:
            self._agent_base_tier[agent_id] = tier
            self._agent_temporary.pop(agent_id, None)

        # Notify callbacks
        if old_tier != tier:
            for callback in self._tier_change_callbacks:
                try:
                    callback(agent_id, old_tier, tier)
                except Exception:
                    pass

    def update(self, tick: int) -> None:
        """
        Update tier system for the current tick.

        Process:
        1. Decay temporary upgrades
        2. Detect hot-spots
        3. Trigger upgrades in hot-spots
        4. Update hotspot intensity map
        """
        # 1. Decay temporary upgrades
        expired: list[EntityID] = []
        for agent_id, remaining in self._agent_temporary.items():
            self._agent_temporary[agent_id] = remaining - 1
            if remaining <= 1:
                expired.append(agent_id)

        for agent_id in expired:
            base_tier = self._agent_base_tier.get(agent_id, AgentTier.L3_BACKGROUND)
            self._set_tier(agent_id, base_tier, False, 0)

        # 2. Detect hot-spots from chunk manager
        self._hotspot_chunks = set(self.chunk_manager.get_hotspot_chunks(threshold=10))

        # 3. Check for event-based triggers
        self._check_event_triggers(tick)

        # 4. Coordinate processing order
        self._coordinate_processing()

    def _check_event_triggers(self, tick: int) -> None:
        """Check for events that should trigger upgrades."""
        # Get recent events
        recent_events = self.world._event_log.get_recent(100)
        for event in recent_events:
            if event.tick < tick - 50:  # Skip old events
                continue

            # Conflict events
            if "conflict" in event.event_type.lower() or "war" in event.event_type.lower():
                if event.position:
                    self._trigger_zone_upgrade(event.position, intensity=0.8)
                    self._stats["hotspot_triggers"] += 1

            # Disaster events
            if event.event_type in (
                "earthquake", "flood", "plague", "volcanic_eruption"
            ):
                if event.position:
                    self._trigger_zone_upgrade(event.position, intensity=0.9)
                    self._stats["hotspot_triggers"] += 1

    def _trigger_zone_upgrade(self, pos: Pos2D, intensity: float) -> None:
        """Trigger upgrades for agents near a position."""
        # Get agents within radius
        radius = 10.0
        for agent, dist in self.world.get_agents_near(pos, radius):
            current_tier = self.get_tier(agent.entity_id)
            if current_tier.value > AgentTier.L2_FUNCTIONAL.value:
                # Only upgrade if not already L1 or L2
                # Probabilistic based on intensity and distance
                upgrade_prob = intensity * (1.0 - dist / radius) * self.config.upgrade_probability
                rng = self.world._rng
                if rng.random() < upgrade_prob:
                    self.upgrade_tier(
                        agent.entity_id,
                        temporary=True,
                        duration=int(50 + intensity * 100),
                    )

    def _coordinate_processing(self) -> None:
        """Determine processing order for the tick."""
        # Priority order: L1 (most important) first, then L2, then L3
        # Within each tier: agents in hot-spots first
        pass  # Actual prioritization done by World.tick()

    def get_agents_by_tier(self, tier: AgentTier) -> set[EntityID]:
        """Get all agent IDs of a specific tier."""
        return self._tier_agents.get(tier, set())

    def get_tier_counts(self) -> dict[str, int]:
        """Get count of agents per tier."""
        return {
            tier.name: len(self._tier_agents.get(tier, set()))
            for tier in AgentTier
        }

    def get_hotspot_count(self) -> int:
        """Get number of active hot-spots."""
        return len(self._hotspot_chunks)

    def get_stats(self) -> dict:
        """Get tier management statistics."""
        return {
            **self._stats,
            "tier_counts": self.get_tier_counts(),
            "hotspot_chunks": len(self._hotspot_chunks),
            "active_temporary_upgrades": len(self._agent_temporary),
        }

    def register_tier_change_callback(
        self, callback: Callable[[EntityID, AgentTier, AgentTier], None]
    ) -> None:
        """Register a callback for tier change events."""
        self._tier_change_callbacks.append(callback)
