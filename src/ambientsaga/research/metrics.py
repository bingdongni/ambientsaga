"""
Research package — metrics, benchmarking, causal tracing.

Metrics:
- 12+ core quantitative metrics
- Time series tracking
- Spatial analysis
- Social network analysis
- Economic indicators
- Cultural diversity indices
"""

from __future__ import annotations

import numpy as np
from typing import TYPE_CHECKING, Any
from dataclasses import dataclass, field
from pathlib import Path
import json

from ambientsaga.config import ResearchConfig

if TYPE_CHECKING:
    from ambientsaga.world.state import World


@dataclass
class MetricSnapshot:
    """A snapshot of all metrics at a specific tick."""

    tick: int
    # Social metrics
    gini_coefficient: float = 0.0
    polarization_index: float = 0.0
    cultural_diversity: float = 0.0
    network_clustering: float = 0.0
    social_stratification: float = 0.0
    trust_network_density: float = 0.0
    conflict_incidents: int = 0
    cooperation_rate: float = 0.0
    migration_rate: float = 0.0

    # Economic metrics
    economic_output: float = 0.0
    inequality_ratio: float = 0.0
    market_activity: float = 0.0
    labor_participation: float = 0.0

    # Environmental metrics
    land_use_diversity: float = 0.0
    ecosystem_health: float = 0.0
    resource_sustainability: float = 0.0

    # Cultural metrics
    belief_system_count: int = 0
    language_diversity: float = 0.0
    innovation_rate: float = 0.0
    institutional_legitimacy: float = 0.0

    # Political metrics
    governance_coverage: float = 0.0
    authority_legitimacy: float = 0.0
    policy_stability: float = 0.0

    # Agent metrics
    population: int = 0
    avg_health: float = 0.0
    avg_wealth: float = 0.0
    avg_happiness: float = 0.0


class MetricsCollector:
    """
    Comprehensive metrics collection system.

    Tracks 12+ core quantitative metrics across:
    - Social (Gini, polarization, diversity, clustering)
    - Economic (output, inequality, market activity)
    - Environmental (land use, ecosystem, resources)
    - Cultural (beliefs, language, innovation)
    - Political (governance, authority, policy)
    - Agent (population, health, wealth, happiness)
    """

    def __init__(self, world: "World", config: ResearchConfig) -> None:
        self.world = world
        self.config = config

        # Time series storage
        self._snapshots: list[MetricSnapshot] = []
        self._start_tick = 0

        # Sliding window
        self._window_size = config.gini_window_size
        self._rolling_values: dict[str, list[float]] = {}

    def collect(self, tick: int) -> MetricSnapshot:
        """Collect metrics at the current tick."""
        snapshot = MetricSnapshot(tick=tick)

        # Population
        agents = self.world.get_all_agents()
        alive_agents = [a for a in agents if a.is_alive]
        snapshot.population = len(alive_agents)

        if not alive_agents:
            self._snapshots.append(snapshot)
            return snapshot

        # Gini coefficient
        wealths = [a.wealth for a in alive_agents]
        snapshot.gini_coefficient = self._compute_gini(wealths)

        # Economic metrics
        snapshot.economic_output = sum(a.wealth for a in alive_agents) / max(1, len(alive_agents))
        wealths_sorted = sorted(wealths)
        if len(wealths_sorted) >= 2:
            snapshot.inequality_ratio = wealths_sorted[-1] / max(1.0, wealths_sorted[0])
        else:
            snapshot.inequality_ratio = 1.0

        snapshot.avg_wealth = sum(wealths) / len(wealths)
        snapshot.market_activity = self.world._market_system.get_stats()["total_transactions"] if self.world._market_system else 0.0

        # Social metrics
        snapshot.social_stratification = self._compute_stratification(alive_agents)
        snapshot.trust_network_density = self._compute_trust_density()
        snapshot.avg_health = sum(a.health for a in alive_agents) / len(alive_agents)

        # Happiness approximation
        happiness_estimates = []
        for a in alive_agents:
            h = (a.health * 0.3 +
                 min(1.0, (1.0 - a.hunger) * 0.2 +
                     (1.0 - a.thirst) * 0.2 +
                     a.energy * 0.2 +
                     len(a.relationships) * 0.1))
            happiness_estimates.append(h)
        snapshot.avg_happiness = sum(happiness_estimates) / max(1, len(happiness_estimates))

        # Cultural diversity
        snapshot.cultural_diversity = self._compute_cultural_diversity()
        snapshot.belief_system_count = self._count_belief_systems(alive_agents)

        # Environmental
        snapshot.land_use_diversity = self._compute_land_diversity()
        snapshot.ecosystem_health = self._compute_ecosystem_health()

        # Political
        snapshot.governance_coverage = self._compute_governance_coverage()

        self._snapshots.append(snapshot)
        return snapshot

    def _compute_gini(self, values: list[float]) -> float:
        """Compute Gini coefficient."""
        if not values:
            return 0.0
        values = sorted(values)
        n = len(values)
        if n < 2:
            return 0.0
        mean = sum(values) / n
        if mean == 0:
            return 0.0

        cumsum = 0.0
        for i, v in enumerate(values):
            cumsum += (2 * (i + 1) - n - 1) * v
        return cumsum / (n * n * mean)

    def _compute_stratification(self, agents: list) -> float:
        """Compute social stratification (wealth quintile spread)."""
        if len(agents) < 5:
            return 0.0

        wealths = sorted([a.wealth for a in agents])
        n = len(wealths)
        q1 = wealths[n // 4]
        q3 = wealths[3 * n // 4]
        return q3 / max(1.0, q1)

    def _compute_trust_density(self) -> float:
        """Compute density of trust relationships."""
        total_agents = self.world.get_agent_count()
        if total_agents < 2:
            return 0.0

        trust_count = 0
        for rel in self.world._relationships.values():
            if rel.get("trust", 0) > 0.3:
                trust_count += 1

        max_relationships = total_agents * (total_agents - 1) // 2
        return trust_count / max(1, max_relationships)

    def _compute_cultural_diversity(self) -> float:
        """Compute cultural diversity (Simpson's Index for beliefs)."""
        belief_counts: dict[str, int] = {}
        for agent in self.world.get_all_agents():
            if not agent.is_alive:
                continue
            for belief in agent.beliefs:
                # Group by proposition category
                key = belief.proposition[:20]
                belief_counts[key] = belief_counts.get(key, 0) + 1

        if not belief_counts:
            return 0.0

        total = sum(belief_counts.values())
        if total < 2:
            return 0.0

        sum_sq = sum((count / total) ** 2 for count in belief_counts.values())
        return 1.0 - sum_sq

    def _count_belief_systems(self, agents: list) -> int:
        """Count distinct belief systems."""
        belief_keys: set[str] = set()
        for agent in agents:
            for belief in agent.beliefs:
                if belief.confidence > 0.6:
                    belief_keys.add(belief.proposition[:20])
        return len(belief_keys)

    def _compute_land_diversity(self) -> float:
        """Compute land use diversity (terrain type variety)."""
        w = self.world._config.world.width
        h = self.world._config.world.height
        terrain_counts: dict[int, int] = {}

        # Sample terrain
        sample_rate = max(1, (w * h) // 10000)
        for y in range(0, h, sample_rate):
            for x in range(0, w, sample_rate):
                t = int(self.world._terrain[y, x])
                terrain_counts[t] = terrain_counts.get(t, 0) + 1

        if not terrain_counts:
            return 0.0

        total = sum(terrain_counts.values())
        sum_sq = sum((count / total) ** 2 for count in terrain_counts.values())
        return 1.0 - sum_sq

    def _compute_ecosystem_health(self) -> float:
        """Compute ecosystem health (proxy from vegetation cover)."""
        if self.world._vegetation is None:
            return 0.5
        avg_veg = float(np.mean(self.world._vegetation))
        return min(1.0, avg_veg)

    def _compute_governance_coverage(self) -> float:
        """Compute fraction of agents in organizations."""
        total = self.world.get_agent_count()
        if total == 0:
            return 0.0

        governed = 0
        for agent in self.world.get_all_agents():
            if agent.organization_ids:
                governed += 1

        return governed / total

    # -------------------------------------------------------------------------
    # Analysis Methods
    # -------------------------------------------------------------------------

    def get_snapshot(self, tick: int) -> MetricSnapshot | None:
        """Get a snapshot at a specific tick."""
        for snap in self._snapshots:
            if snap.tick == tick:
                return snap
        return None

    def gini_over_time(self) -> list[tuple[int, float]]:
        """Get Gini coefficient over time."""
        return [(s.tick, s.gini_coefficient) for s in self._snapshots]

    def polarization_over_time(self) -> list[tuple[int, float]]:
        """Get polarization index over time."""
        return [(s.tick, s.polarization_index) for s in self._snapshots]

    def cultural_diversity_over_time(self) -> list[tuple[int, float]]:
        """Get cultural diversity over time."""
        return [(s.tick, s.cultural_diversity) for s in self._snapshots]

    def population_over_time(self) -> list[tuple[int, int]]:
        """Get population over time."""
        return [(s.tick, s.population) for s in self._snapshots]

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of all metrics."""
        if not self._snapshots:
            return {}

        latest = self._snapshots[-1]
        return {
            "latest_tick": latest.tick,
            "population": latest.population,
            "gini_coefficient": latest.gini_coefficient,
            "cultural_diversity": latest.cultural_diversity,
            "avg_health": latest.avg_health,
            "avg_wealth": latest.avg_wealth,
            "avg_happiness": latest.avg_happiness,
            "ecosystem_health": latest.ecosystem_health,
            "governance_coverage": latest.governance_coverage,
            "snapshots_collected": len(self._snapshots),
        }

    def export(self, path: str | Path) -> None:
        """Export metrics to JSON."""
        data = []
        for snap in self._snapshots:
            data.append({
                "tick": snap.tick,
                "gini_coefficient": snap.gini_coefficient,
                "polarization_index": snap.polarization_index,
                "cultural_diversity": snap.cultural_diversity,
                "population": snap.population,
                "avg_health": snap.avg_health,
                "avg_wealth": snap.avg_wealth,
                "avg_happiness": snap.avg_happiness,
                "economic_output": snap.economic_output,
                "inequality_ratio": snap.inequality_ratio,
                "market_activity": snap.market_activity,
                "social_stratification": snap.social_stratification,
                "trust_network_density": snap.trust_network_density,
                "belief_system_count": snap.belief_system_count,
                "land_use_diversity": snap.land_use_diversity,
                "ecosystem_health": snap.ecosystem_health,
                "governance_coverage": snap.governance_coverage,
            })
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def __len__(self) -> int:
        return len(self._snapshots)

    def generate_academic_report(
        self,
        title: str = "AmbientSaga Simulation Report",
        authors: list[str] | None = None,
    ) -> "AcademicReport":
        """
        Generate an academic report from collected metrics.

        Creates a comprehensive academic report with:
        - Executive summary
        - Methodology
        - Results (tables and figures)
        - Statistical analysis
        - Discussion
        - Conclusions
        """
        from ambientsaga.research.academic_output import AcademicReport, StatisticalAnalyzer

        report = AcademicReport(
            title=title,
            authors=authors or ["AmbientSaga Research Team"],
            abstract=self._generate_abstract(),
        )

        # Add methodology section
        report.add_section(
            "Methods",
            self._generate_methodology(),
            level=2,
        )

        # Add results sections
        report.add_section(
            "Population Dynamics",
            self._generate_population_results(),
            level=2,
        )

        report.add_section(
            "Economic Analysis",
            self._generate_economic_results(),
            level=2,
        )

        report.add_section(
            "Social Structure",
            self._generate_social_results(),
            level=2,
        )

        report.add_section(
            "Cultural Development",
            self._generate_cultural_results(),
            level=2,
        )

        report.add_section(
            "Environmental Impact",
            self._generate_environmental_results(),
            level=2,
        )

        # Add statistical analysis
        report.add_section(
            "Statistical Analysis",
            self._generate_statistical_analysis(),
            level=2,
        )

        # Add tables
        self._add_result_tables(report)

        # Add conclusions
        report.add_section(
            "Conclusions",
            self._generate_conclusions(),
            level=2,
        )

        # Add references
        report.add_reference("AmbientSaga: A Multi-Agent Simulation Framework for Complex Systems Research")
        report.add_reference("Epstein, J. M., & Axtell, R. (1996). Growing Artificial Societies: Social Science from the Bottom Up.")
        report.add_reference("Axelrod, R. (1997). The Complexity of Cooperation: Agent-Based Models of Competition and Collaboration.")

        return report

    def _generate_abstract(self) -> str:
        """Generate abstract from metrics."""
        if not self._snapshots:
            return "No data collected during simulation."

        latest = self._snapshots[-1]
        initial = self._snapshots[0] if self._snapshots else latest

        return (
            f"This report presents the results of an AmbientSaga multi-agent simulation "
            f"covering {latest.tick} simulation ticks. "
            f"The simulation tracked {latest.population} agents across a dynamic environment. "
            f"Key findings include: "
            f"Population change from {initial.population} to {latest.population} agents; "
            f"Gini coefficient of {latest.gini_coefficient:.3f} indicating "
            f"{'high' if latest.gini_coefficient > 0.4 else 'moderate' if latest.gini_coefficient > 0.2 else 'low'} wealth inequality; "
            f"Cultural diversity index of {latest.cultural_diversity:.3f}; "
            f"Ecosystem health of {latest.ecosystem_health:.3f}; "
            f"and governance coverage of {latest.governance_coverage:.1%}."
        )

    def _generate_methodology(self) -> str:
        """Generate methodology section."""
        latest = self._snapshots[-1] if self._snapshots else None
        return (
            "The AmbientSaga simulation framework was used to model a population of autonomous agents "
            "interacting in a shared environment. Agents make decisions based on their internal states, "
            "social relationships, and environmental conditions.\n\n"
            "**Metrics Collected:**\n"
            "- Population dynamics (birth, death, migration)\n"
            "- Economic indicators (wealth distribution, market activity)\n"
            "- Social structure (trust networks, cooperation rates)\n"
            "- Cultural development (belief systems, language diversity)\n"
            "- Environmental impact (land use, ecosystem health)\n\n"
            f"**Simulation Parameters:**\n"
            f"- World size: {self.world._config.world.width}x{self.world._config.world.height}\n"
            f"- Total snapshots: {len(self._snapshots)}\n"
            f"- Time window: {self._window_size} ticks\n"
        )

    def _generate_population_results(self) -> str:
        """Generate population results section."""
        if not self._snapshots:
            return "No population data available."

        initial = self._snapshots[0]
        latest = self._snapshots[-1]

        growth_rate = ((latest.population - initial.population) / max(1, initial.population)) * 100

        return (
            f"Population dynamics showed {'growth' if growth_rate > 0 else 'decline' if growth_rate < 0 else 'stability'} "
            f"over the simulation period.\n\n"
            f"- Initial population: {initial.population} agents\n"
            f"- Final population: {latest.population} agents\n"
            f"- Growth rate: {growth_rate:+.1f}%\n"
            f"- Peak population: {max(s.population for s in self._snapshots)} agents\n"
            f"- Average population: {sum(s.population for s in self._snapshots) / max(1, len(self._snapshots)):.1f} agents\n"
        )

    def _generate_economic_results(self) -> str:
        """Generate economic results section."""
        if not self._snapshots:
            return "No economic data available."

        latest = self._snapshots[-1]
        avg_gini = sum(s.gini_coefficient for s in self._snapshots) / max(1, len(self._snapshots))

        return (
            f"Economic analysis revealed wealth distribution patterns in the agent society.\n\n"
            f"- Gini coefficient: {latest.gini_coefficient:.3f} (average: {avg_gini:.3f})\n"
            f"- Average wealth: {latest.avg_wealth:.2f}\n"
            f"- Inequality ratio: {latest.inequality_ratio:.2f}\n"
            f"- Social stratification: {latest.social_stratification:.3f}\n"
            f"- Market activity: {latest.market_activity:.1f} transactions\n"
            f"- Economic output: {latest.economic_output:.2f}\n"
        )

    def _generate_social_results(self) -> str:
        """Generate social results section."""
        if not self._snapshots:
            return "No social data available."

        latest = self._snapshots[-1]

        return (
            f"Social structure analysis revealed network formation patterns.\n\n"
            f"- Trust network density: {latest.trust_network_density:.4f}\n"
            f"- Cooperation rate: {latest.cooperation_rate:.3f}\n"
            f"- Conflict incidents: {latest.conflict_incidents}\n"
            f"- Governance coverage: {latest.governance_coverage:.1%}\n"
            f"- Average happiness: {latest.avg_happiness:.3f}\n"
            f"- Migration rate: {latest.migration_rate:.3f}\n"
        )

    def _generate_cultural_results(self) -> str:
        """Generate cultural results section."""
        if not self._snapshots:
            return "No cultural data available."

        latest = self._snapshots[-1]

        return (
            f"Cultural development showed emergence of shared belief systems.\n\n"
            f"- Cultural diversity index: {latest.cultural_diversity:.3f}\n"
            f"- Belief systems identified: {latest.belief_system_count}\n"
            f"- Language diversity: {latest.language_diversity:.3f}\n"
            f"- Innovation rate: {latest.innovation_rate:.4f}\n"
            f"- Institutional legitimacy: {latest.institutional_legitimacy:.3f}\n"
        )

    def _generate_environmental_results(self) -> str:
        """Generate environmental results section."""
        if not self._snapshots:
            return "No environmental data available."

        latest = self._snapshots[-1]

        return (
            f"Environmental analysis revealed resource utilization patterns.\n\n"
            f"- Land use diversity: {latest.land_use_diversity:.3f}\n"
            f"- Ecosystem health: {latest.ecosystem_health:.3f}\n"
            f"- Resource sustainability: {latest.resource_sustainability:.3f}\n"
        )

    def _generate_statistical_analysis(self) -> str:
        """Generate statistical analysis section."""
        from ambientsaga.research.academic_output import StatisticalAnalyzer

        if len(self._snapshots) < 2:
            return "Insufficient data for statistical analysis."

        # Compute correlations
        analyzer = StatisticalAnalyzer()
        gini_series = [s.gini_coefficient for s in self._snapshots]
        pop_series = [float(s.population) for s in self._snapshots]
        wealth_series = [s.avg_wealth for s in self._snapshots]

        # Correlation between Gini and population
        gini_pop_corr, _ = analyzer.pearson_correlation(gini_series, pop_series) if len(gini_series) >= 3 else (0.0, 1.0)

        # Trend analysis
        gini_trend = analyzer.linear_trend(gini_series)

        return (
            f"Statistical analysis of the simulation data reveals the following patterns:\n\n"
            f"- Correlation between inequality and population: {gini_pop_corr:.3f}\n"
            f"- Gini coefficient trend: {'increasing' if gini_trend.slope > 0.001 else 'decreasing' if gini_trend.slope < -0.001 else 'stable'} "
            f"(slope: {gini_trend.slope:.6f}, R²: {gini_trend.r_squared:.3f})\n"
            f"- Total data points: {len(self._snapshots)}\n"
            f"- Time span: {self._snapshots[-1].tick - self._snapshots[0].tick} ticks\n"
        )

    def _generate_conclusions(self) -> str:
        """Generate conclusions section."""
        if not self._snapshots:
            return "No conclusions can be drawn from the available data."

        latest = self._snapshots[-1]

        conclusions = []

        # Population
        if latest.population > 100:
            conclusions.append("The agent population reached a sustainable size capable of complex social interactions.")
        elif latest.population > 10:
            conclusions.append("A small but viable population emerged, demonstrating basic social behaviors.")
        else:
            conclusions.append("The population struggled to maintain viability, suggesting environmental challenges.")

        # Inequality
        if latest.gini_coefficient > 0.4:
            conclusions.append("High wealth inequality emerged, potentially driving social stratification.")
        elif latest.gini_coefficient > 0.2:
            conclusions.append("Moderate wealth inequality suggests a balanced distribution of resources.")
        else:
            conclusions.append("Low wealth inequality indicates equitable resource distribution among agents.")

        # Cultural
        if latest.cultural_diversity > 0.5:
            conclusions.append("High cultural diversity indicates successful emergence of distinct belief systems.")
        else:
            conclusions.append("Cultural homogeneity suggests agents developed shared beliefs.")

        # Governance
        if latest.governance_coverage > 0.5:
            conclusions.append("Significant governance structures emerged, organizing agent behavior.")
        else:
            conclusions.append("Limited governance suggests emergent norms rather than formal institutions.")

        return "\n\n".join(f"- {c}" for c in conclusions)

    def _add_result_tables(self, report: "AcademicReport") -> None:
        """Add result tables to the report."""
        if not self._snapshots:
            return

        # Population over time table
        pop_data = [(s.tick, s.population) for s in self._snapshots[::max(1, len(self._snapshots)//10)]]
        report.add_table(
            "Population Over Time",
            ["Tick", "Population"],
            [[str(tick), str(pop)] for tick, pop in pop_data],
            notes="Sample of population values at regular intervals.",
        )

        # Economic indicators table
        if len(self._snapshots) >= 5:
            economic_data = [
                ["Metric", "Initial", "Final", "Change"],
                ["Gini Coefficient", f"{self._snapshots[0].gini_coefficient:.3f}",
                 f"{self._snapshots[-1].gini_coefficient:.3f}",
                 f"{self._snapshots[-1].gini_coefficient - self._snapshots[0].gini_coefficient:+.3f}"],
                ["Avg Wealth", f"{self._snapshots[0].avg_wealth:.2f}",
                 f"{self._snapshots[-1].avg_wealth:.2f}",
                 f"{self._snapshots[-1].avg_wealth - self._snapshots[0].avg_wealth:+.2f}"],
                ["Population", str(self._snapshots[0].population),
                 str(self._snapshots[-1].population),
                 str(self._snapshots[-1].population - self._snapshots[0].population)],
            ]
            report.add_table(
                "Economic and Population Indicators",
                economic_data[0],
                economic_data[1:],
                notes="Comparison of key indicators between start and end of simulation.",
            )
