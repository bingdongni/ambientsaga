"""
Social Stratification Emergence System.

Handles the emergent formation of social classes and hierarchies from agent interactions:
- Class formation based on wealth, power, knowledge, social capital
- Hierarchy emergence through reputation and influence
- Social mobility mechanisms
- Stratification patterns from agent behaviors
- Elite formation and consolidation
- Social distance and segregation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

import numpy as np

from ambientsaga.types import EntityID

if TYPE_CHECKING:
    pass


class SocialClass(Enum):
    """Emergent social classes."""
    UNDERCLASS = auto()    # Bottom 5%, marginalized
    WORKING = auto()       # 10-20%, laborers
    LOWER_MIDDLE = auto()  # 20-40%, small proprietors
    UPPER_MIDDLE = auto()  # 40-70%, professionals
    ELITE = auto()         # Top 10-30%, powerful
    RULING = auto()        # Top 1-5%, decision makers


@dataclass
class ClassPosition:
    """An agent's position within a class structure."""
    agent_id: EntityID
    class_level: SocialClass
    wealth_score: float = 0.0  # 0-1
    power_score: float = 0.0   # 0-1
    knowledge_score: float = 0.0  # 0-1
    social_capital: float = 0.0    # 0-1
    prestige_score: float = 0.0   # 0-1
    combined_score: float = 0.0   # 0-1, overall class position

    # Mobility indicators
    mobility_direction: str = "stable"  # "up", "down", "stable"
    mobility_rate: float = 0.0  # Rate of change per tick


@dataclass
class HierarchyNode:
    """A node in the emergent social hierarchy."""
    node_id: str
    agent_id: EntityID  # The agent at this position
    position: int  # Position in hierarchy (0 = top)
    level: SocialClass
    subordinates: list[str] = field(default_factory=list)  # subordinate node_ids
    superiors: list[str] = field(default_factory=list)  # superior node_ids
    influence_score: float = 0.0  # How much influence this position has
    control_score: float = 0.0   # How much control over resources


@dataclass
class ClassFormationEvent:
    """An event in class formation history."""
    event_type: str  # "mobility", "class_shift", "elite_formation", "mobility_block"
    tick: int
    agent_id: EntityID
    from_class: SocialClass | None
    to_class: SocialClass | None
    cause: str
    description: str


@dataclass
class StratificationPattern:
    """An emergent pattern of stratification."""
    pattern_id: str
    pattern_type: str  # "wealth_gap", "knowledge_gap", "power_gap", "caste_like", "meritocratic"
    gini_coefficient: float  # 0-1, inequality measure
    top_10_share: float  # Share of resources held by top 10%
    bottom_40_share: float  # Share held by bottom 40%
    mobility_rate: float  # How much mobility exists
    tick_created: int
    description: str = ""


class SocialStratificationSystem:
    """
    Manages emergent social stratification and class formation.

    This system handles:
    1. Calculating agent class positions based on multiple factors
    2. Forming emergent hierarchies from power relationships
    3. Tracking social mobility over time
    4. Detecting stratification patterns
    5. Modeling elite formation and consolidation
    6. Social distance and segregation emergence
    """

    def __init__(self, seed: int = 42):
        self._rng = np.random.Generator(np.random.PCG64(seed))

        # Agent class positions
        self._class_positions: dict[EntityID, ClassPosition] = {}

        # Hierarchy nodes
        self._hierarchy_nodes: dict[str, HierarchyNode] = {}
        self._next_node_id = 0

        # Class formation history
        self._class_history: list[ClassFormationEvent] = []

        # Stratification patterns
        self._patterns: list[StratificationPattern] = []
        self._next_pattern_id = 0

        # Class boundaries (percentages)
        self._class_thresholds = {
            SocialClass.UNDERCLASS: 0.05,
            SocialClass.WORKING: 0.20,
            SocialClass.LOWER_MIDDLE: 0.40,
            SocialClass.UPPER_MIDDLE: 0.70,
            SocialClass.ELITE: 0.95,
            SocialClass.RULING: 1.00,
        }

        # Statistics
        self._stats = {
            "total_mobility_events": 0,
            "upward_mobility": 0,
            "downward_mobility": 0,
            "class_fluidity": 0.0,
        }

    def calculate_class_position(
        self,
        agent_id: EntityID,
        wealth: float,
        power: float,
        knowledge: float,
        social_capital: float,
        prestige: float,
    ) -> ClassPosition:
        """
        Calculate an agent's class position based on multiple factors.

        Args:
            agent_id: The agent's ID
            wealth: Agent's wealth (0-1 normalized)
            power: Agent's power/authority (0-1)
            knowledge: Agent's knowledge/education (0-1)
            social_capital: Agent's social connections (0-1)
            prestige: Agent's reputation/prestige (0-1)

        Returns:
            The agent's class position
        """
        # Normalize inputs to 0-1
        wealth = max(0.0, min(1.0, wealth))
        power = max(0.0, min(1.0, power))
        knowledge = max(0.0, min(1.0, knowledge))
        social_capital = max(0.0, min(1.0, social_capital))
        prestige = max(0.0, min(1.0, prestige))

        # Weighted combination for overall score
        # Power and wealth are weighted more heavily
        combined_score = (
            wealth * 0.30 +
            power * 0.25 +
            knowledge * 0.20 +
            social_capital * 0.15 +
            prestige * 0.10
        )

        # Determine class based on combined score
        class_level = self._score_to_class(combined_score)

        position = ClassPosition(
            agent_id=agent_id,
            class_level=class_level,
            wealth_score=wealth,
            power_score=power,
            knowledge_score=knowledge,
            social_capital=social_capital,
            prestige_score=prestige,
            combined_score=combined_score,
        )

        # Update mobility if we have previous position
        if agent_id in self._class_positions:
            old_position = self._class_positions[agent_id]
            position.mobility_direction = self._get_mobility_direction(
                old_position.combined_score, combined_score
            )

        self._class_positions[agent_id] = position
        return position

    def _score_to_class(self, score: float) -> SocialClass:
        """Convert a combined score to a social class."""
        if score < self._class_thresholds[SocialClass.UNDERCLASS]:
            return SocialClass.UNDERCLASS
        elif score < self._class_thresholds[SocialClass.WORKING]:
            return SocialClass.WORKING
        elif score < self._class_thresholds[SocialClass.LOWER_MIDDLE]:
            return SocialClass.LOWER_MIDDLE
        elif score < self._class_thresholds[SocialClass.UPPER_MIDDLE]:
            return SocialClass.UPPER_MIDDLE
        elif score < self._class_thresholds[SocialClass.ELITE]:
            return SocialClass.ELITE
        else:
            return SocialClass.RULING

    def _get_mobility_direction(self, old_score: float, new_score: float) -> str:
        """Determine the direction of social mobility."""
        diff = new_score - old_score
        if abs(diff) < 0.01:
            return "stable"
        elif diff > 0:
            return "up"
        else:
            return "down"

    def record_mobility_event(
        self,
        agent_id: EntityID,
        from_class: SocialClass | None,
        to_class: SocialClass,
        cause: str,
        tick: int,
    ) -> None:
        """Record a social mobility event."""
        event = ClassFormationEvent(
            event_type="mobility",
            tick=tick,
            agent_id=agent_id,
            from_class=from_class,
            to_class=to_class,
            cause=cause,
            description=f"Agent {agent_id} moved from {from_class.name if from_class else 'N/A'} to {to_class.name}",
        )
        self._class_history.append(event)
        self._stats["total_mobility_events"] += 1

        if event.from_class and event.to_class:
            if self._class_to_level(event.from_class) < self._class_to_level(event.to_class):
                self._stats["upward_mobility"] += 1
            elif self._class_to_level(event.from_class) > self._class_to_level(event.to_class):
                self._stats["downward_mobility"] += 1

    def _class_to_level(self, social_class: SocialClass) -> int:
        """Convert class to numeric level (higher = more privileged)."""
        levels = {
            SocialClass.UNDERCLASS: 0,
            SocialClass.WORKING: 1,
            SocialClass.LOWER_MIDDLE: 2,
            SocialClass.UPPER_MIDDLE: 3,
            SocialClass.ELITE: 4,
            SocialClass.RULING: 5,
        }
        return levels.get(social_class, 0)

    def create_hierarchy_node(
        self,
        agent_id: EntityID,
        position: int,
        level: SocialClass,
    ) -> HierarchyNode:
        """Create a node in the social hierarchy."""
        node_id = f"node_{self._next_node_id}"
        self._next_node_id += 1

        node = HierarchyNode(
            node_id=node_id,
            agent_id=agent_id,
            position=position,
            level=level,
        )

        self._hierarchy_nodes[node_id] = node
        return node

    def build_hierarchy_from_positions(self) -> None:
        """Build hierarchy nodes from current class positions."""
        # Sort agents by combined score
        sorted_agents = sorted(
            self._class_positions.items(),
            key=lambda x: x[1].combined_score,
            reverse=True
        )

        # Create hierarchy nodes
        for rank, (agent_id, position) in enumerate(sorted_agents):
            node = self.create_hierarchy_node(
                agent_id=agent_id,
                position=rank,
                level=position.class_level,
            )
            node.influence_score = position.power_score * 0.7 + position.prestige_score * 0.3
            node.control_score = position.wealth_score * 0.6 + position.power_score * 0.4

    def calculate_gini_coefficient(self, attribute: str = "combined_score") -> float:
        """
        Calculate the Gini coefficient for inequality in an attribute.

        Returns:
            Gini coefficient (0 = perfect equality, 1 = perfect inequality)
        """
        scores = [
            pos.combined_score for pos in self._class_positions.values()
        ]

        if not scores:
            return 0.0

        n = len(scores)
        sorted_scores = sorted(scores)

        # Calculate Gini
        cumsum = 0.0
        for i, score in enumerate(sorted_scores):
            cumsum += (2 * i + 1 - n) * score

        gini = cumsum / (n * sum(sorted_scores)) if sum(sorted_scores) > 0 else 0.0
        return max(0.0, min(1.0, gini))

    def calculate_top_share(self, attribute: str = "combined_score", top_percent: float = 0.1) -> float:
        """Calculate the share of total attribute held by top X%."""
        if not self._class_positions:
            return 0.0

        scores = [getattr(pos, attribute) for pos in self._class_positions.values()]
        total = sum(scores)
        if total == 0:
            return 0.0

        n = len(scores)
        k = max(1, int(n * top_percent))
        top_k = sorted(scores, reverse=True)[:k]

        return sum(top_k) / total

    def detect_stratification_pattern(
        self,
        tick: int,
        pattern_type: str = "wealth_gap",
    ) -> StratificationPattern:
        """Detect an emergent stratification pattern."""
        gini = self.calculate_gini_coefficient()
        top_10 = self.calculate_top_share(top_percent=0.1)
        bottom_40 = self.calculate_top_share(top_percent=0.4)

        # Calculate mobility rate
        recent_events = [
            e for e in self._class_history
            if tick - e.tick < 100
        ]
        mobility_rate = len(recent_events) / max(1, len(self._class_positions)) if self._class_positions else 0.0

        # Determine pattern type based on metrics
        if gini > 0.5 and top_10 > 0.5:
            pattern_type = "caste_like"
            description = "Highly unequal, rigid stratification"
        elif gini > 0.4 and mobility_rate < 0.1:
            pattern_type = "elite_domination"
            description = "Elite consolidation of resources"
        elif gini < 0.3 and mobility_rate > 0.3:
            pattern_type = "meritocratic"
            description = "High mobility, low inequality"
        elif gini > 0.3 and gini < 0.5:
            pattern_type = "middle_class"
            description = "Moderate inequality with substantial middle class"
        else:
            description = f"Inequality: Gini={gini:.2f}, Top10%={top_10:.2f}, Mobility={mobility_rate:.2f}"

        pattern = StratificationPattern(
            pattern_id=f"pattern_{self._next_pattern_id}",
            pattern_type=pattern_type,
            gini_coefficient=gini,
            top_10_share=top_10,
            bottom_40_share=bottom_40,
            mobility_rate=mobility_rate,
            tick_created=tick,
            description=description,
        )

        self._patterns.append(pattern)
        self._next_pattern_id += 1

        return pattern

    def get_class_distribution(self) -> dict[str, int]:
        """Get the current distribution of agents across classes."""
        distribution = {cls.name: 0 for cls in SocialClass}

        for position in self._class_positions.values():
            distribution[position.class_level.name] += 1

        return distribution

    def get_elite_agents(self, top_percent: float = 0.1) -> list[EntityID]:
        """Get the top X% of agents by combined score."""
        if not self._class_positions:
            return []

        n = max(1, int(len(self._class_positions) * top_percent))
        sorted_agents = sorted(
            self._class_positions.items(),
            key=lambda x: x[1].combined_score,
            reverse=True
        )

        return [agent_id for agent_id, _ in sorted_agents[:n]]

    def get_social_distance(
        self,
        agent_a: EntityID,
        agent_b: EntityID,
    ) -> float:
        """Calculate social distance between two agents (0 = same class, 1 = opposite)."""
        pos_a = self._class_positions.get(agent_a)
        pos_b = self._class_positions.get(agent_b)

        if not pos_a or not pos_b:
            return 0.5  # Unknown distance

        # Distance based on class difference
        class_diff = abs(
            self._class_to_level(pos_a.class_level) -
            self._class_to_level(pos_b.class_level)
        ) / 5.0  # Normalize to 0-1

        # Distance based on score difference
        score_diff = abs(pos_a.combined_score - pos_b.combined_score)

        return (class_diff * 0.6 + score_diff * 0.4)

    def update(self, tick: int) -> None:
        """Update the stratification system each tick."""
        # Update class positions for all agents
        # This would be called from World._phase_agent_decision or similar

        # Calculate mobility statistics
        recent_events = [
            e for e in self._class_history
            if tick - e.tick < 50
        ]

        if self._class_positions:
            self._stats["class_fluidity"] = len(recent_events) / len(self._class_positions)

        # Detect new patterns periodically
        if tick % 100 == 0 and self._class_positions:
            self.detect_stratification_pattern(tick)

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about social stratification."""
        distribution = self.get_class_distribution()
        total_agents = len(self._class_positions)

        return {
            "total_agents": total_agents,
            "class_distribution": distribution,
            "gini_coefficient": self.calculate_gini_coefficient(),
            "top_10_share": self.calculate_top_share(top_percent=0.1),
            "bottom_40_share": self.calculate_top_share(top_percent=0.4),
            "mobility_events": {
                "total": self._stats["total_mobility_events"],
                "upward": self._stats["upward_mobility"],
                "downward": self._stats["downward_mobility"],
                "class_fluidity": self._stats["class_fluidity"],
            },
            "elite_agents": len(self.get_elite_agents()),
            "patterns_detected": len(self._patterns),
            "current_pattern": self._patterns[-1].pattern_type if self._patterns else "none",
        }
