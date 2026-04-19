"""
Science Systems — Unified Scientific Framework

This module unifies all scientific disciplines into a coherent framework:
- Physics: Fundamental forces and matter
- Chemistry: Atomic and molecular interactions
- Biology: Life and living systems
- Ecology: Ecosystems and environment
- And all social sciences emerge from biological systems

Key Design Principles:
1. All sciences emerge from physics
2. Coupling occurs through shared variables and events
3. Changes propagate across disciplinary boundaries
4. The framework is extensible for new disciplines

Coupling Graph:
    Physics
       |
    Chemistry
       |
    Biology
     /    \
Ecology   Social Sciences
    \\       /
   Human Systems
      |
   Economic Systems
      |
   Political Systems
      |
   Cultural Systems
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum


class ScientificDomain(Enum):
    """Scientific domains."""
    PHYSICS = "physics"
    CHEMISTRY = "chemistry"
    BIOLOGY = "biology"
    ECOLOGY = "ecology"
    PSYCHOLOGY = "psychology"
    SOCIOLOGY = "sociology"
    ECONOMICS = "economics"
    POLITICAL_SCIENCE = "political_science"
    LINGUISTICS = "linguistics"
    ANTHROPOLOGY = "anthropology"
    MEDICINE = "medicine"
    ENVIRONMENTAL_SCIENCE = "environmental_science"
    COMPUTATIONAL_SCIENCE = "computational_science"
    STATISTICS = "statistics"
    SYSTEM_SCIENCE = "system_science"
    GENETICS = "genetics"
    ASTRONOMY = "astronomy"
    NEUROSCIENCE = "neuroscience"
    EDUCATION = "education"
    GEOGRAPHY = "geography"
    HISTORY = "history"
    PHILOSOPHY = "philosophy"
    ETHICS = "ethics"
    LAW = "law"
    ARCHAEOLOGY = "archaeology"


@dataclass
class ScientificLaw:
    """A scientific law or principle."""
    law_id: str
    name: str
    domain: ScientificDomain
    description: str

    # The law as a function
    law_function: Callable[..., float]

    # Parameters
    parameters: dict[str, float] = field(default_factory=dict)

    # Couplings to other domains
    coupled_domains: list[ScientificDomain] = field(default_factory=list)
    coupling_strength: dict[str, float] = field(default_factory=dict)

    def apply(self, *args, **kwargs) -> float:
        """Apply the scientific law."""
        try:
            return self.law_function(*args, **kwargs)
        except Exception:
            return 0.0


@dataclass
class CouplingRelation:
    """A coupling relationship between two systems."""
    coupling_id: str
    source_domain: ScientificDomain
    target_domain: ScientificDomain

    # Shared variables
    shared_variables: list[str]

    # Coupling function: how changes propagate
    coupling_function: Callable[[dict], dict]

    # Coupling strength (0-1)
    strength: float = 1.0

    # Delay (ticks before effect manifests)
    delay: int = 0

    def propagate(self, source_state: dict) -> dict:
        """Propagate changes from source to target."""
        result = self.coupling_function(source_state)
        # Apply strength
        for key in result:
            if isinstance(result[key], (int, float)):
                result[key] *= self.strength
        return result


@dataclass
class UnifiedField:
    """A field that spans multiple scientific domains."""
    field_id: str
    name: str
    description: str

    # Values across domains
    values: dict[ScientificDomain, float] = field(default_factory=dict)

    # Rate of change
    rate_of_change: float = 0.0

    def get(self, domain: ScientificDomain) -> float:
        """Get value for a domain."""
        return self.values.get(domain, 0.0)

    def set(self, domain: ScientificDomain, value: float) -> None:
        """Set value for a domain."""
        self.values[domain] = value

    def update(self, dt: float = 1.0) -> None:
        """Update field values."""
        # Apply rate of change
        for domain in self.values:
            self.values[domain] += self.rate_of_change * dt


class ScienceEngine:
    """
    Unified Science Engine.

    Integrates all scientific disciplines into a coherent framework.
    Provides:
    - Scientific laws database
    - Coupling relationships
    - Cross-domain propagation
    - Emergence detection

    The engine maintains consistency across all domains while allowing
    emergent behaviors to arise from interactions.
    """

    def __init__(self, config: dict = None):
        # Handle both dict and ScienceConfig object
        if config is None:
            config = {}
        elif not isinstance(config, dict):
            # It's a ScienceConfig object, extract relevant fields
            config = {
                "physics": {"gravity": getattr(config, 'physics_gravity', -9.81), "temperature": getattr(config, 'physics_temperature', 293.15)},
                "chemistry": {"reaction_rate": getattr(config, 'chemistry_reaction_rate', 1.0)},
                "biology": {"mutation_rate": getattr(config, 'biology_mutation_rate', 0.0001)},
                "ecology": {"trophic_efficiency": getattr(config, 'ecology_trophic_efficiency', 0.1)},
                "coupling_strength": getattr(config, 'coupling_strength', 1.0),
                "enable_physics": getattr(config, 'enable_physics', True),
                "enable_chemistry": getattr(config, 'enable_chemistry', True),
                "enable_biology": getattr(config, 'enable_biology', True),
                "enable_ecology": getattr(config, 'enable_ecology', True),
            }
        self.config = config

        # Sub-engines
        from .biology import BiologyEngine
        from .chemistry import ChemistryEngine
        from .ecology import EcosystemEngine as EcologyEngine
        from .physics import PhysicsEngine

        self.physics = PhysicsEngine(self.config.get("physics") if isinstance(self.config, dict) else None)
        self.chemistry = ChemistryEngine(self.config.get("chemistry") if isinstance(self.config, dict) else None)
        self.biology = BiologyEngine(self.config.get("biology") if isinstance(self.config, dict) else None)
        self.ecology = EcologyEngine(self.config.get("ecology") if isinstance(self.config, dict) else None)

        # Scientific laws
        self.laws: dict[str, ScientificLaw] = {}
        self._register_scientific_laws()

        # Coupling relationships
        self.couplings: list[CouplingRelation] = []
        self._register_couplings()

        # Unified fields
        self.fields: dict[str, UnifiedField] = {}

        # Event bus for cross-domain events
        self.cross_domain_events: list[dict] = []

        # Statistics
        self.tick = 0
        self.domain_interactions: dict[str, int] = {}

    def _register_scientific_laws(self) -> None:
        """Register scientific laws."""

        # Physics laws
        self.laws["F=ma"] = ScientificLaw(
            law_id="F=ma",
            name="Newton's Second Law",
            domain=ScientificDomain.PHYSICS,
            description="Force equals mass times acceleration",
            law_function=lambda m, a: m * a,
            parameters={"G": 6.674e-11},
            coupled_domains=[ScientificDomain.CHEMISTRY],
        )

        self.laws["E=mc^2"] = ScientificLaw(
            law_id="E=mc^2",
            name="Mass-Energy Equivalence",
            domain=ScientificDomain.PHYSICS,
            description="Energy equals mass times speed of light squared",
            law_function=lambda m: m * (299792458 ** 2),
            coupled_domains=[ScientificDomain.CHEMISTRY, ScientificDomain.BIOLOGY],
        )

        self.laws["thermodynamics_2nd"] = ScientificLaw(
            law_id="thermodynamics_2nd",
            name="Second Law of Thermodynamics",
            domain=ScientificDomain.PHYSICS,
            description="Entropy of isolated system never decreases",
            law_function=lambda S1, S2: max(S1, S2),
            coupled_domains=[ScientificDomain.CHEMISTRY, ScientificDomain.BIOLOGY, ScientificDomain.ECOLOGY],
        )

        # Chemistry laws
        self.laws["reaction_rate"] = ScientificLaw(
            law_id="reaction_rate",
            name="Arrhenius Equation",
            domain=ScientificDomain.CHEMISTRY,
            description="Temperature dependence of reaction rate",
            law_function=lambda k0, Ea, T: k0 * math.exp(-Ea / (8.314 * T)),
            coupled_domains=[ScientificDomain.PHYSICS, ScientificDomain.BIOLOGY],
        )

        self.laws["equilibrium"] = ScientificLaw(
            law_id="equilibrium",
            name="Law of Mass Action",
            domain=ScientificDomain.CHEMISTRY,
            description="Equilibrium constant from concentration ratio",
            law_function=lambda products, reactants: products / max(reactants, 0.001),
            coupled_domains=[ScientificDomain.BIOLOGY],
        )

        # Biology laws
        self.laws["population_growth"] = ScientificLaw(
            law_id="population_growth",
            name="Logistic Growth Model",
            domain=ScientificDomain.BIOLOGY,
            description="Population growth with carrying capacity",
            law_function=lambda N, r, K: r * N * (1 - N / K),
            coupled_domains=[ScientificDomain.ECOLOGY, ScientificDomain.SOCIOLOGY],
        )

        self.laws["natural_selection"] = ScientificLaw(
            law_id="natural_selection",
            name="Natural Selection",
            domain=ScientificDomain.BIOLOGY,
            description="Fitter organisms leave more offspring",
            law_function=lambda fitness, selection_pressure: fitness * (1 + selection_pressure),
            coupled_domains=[ScientificDomain.ECOLOGY],
        )

        self.laws["metabolism"] = ScientificLaw(
            law_id="metabolism",
            name="Metabolic Rate Scaling",
            domain=ScientificDomain.BIOLOGY,
            description="Metabolic rate scales with body mass to 3/4 power",
            law_function=lambda mass: mass ** 0.75,
            coupled_domains=[ScientificDomain.PHYSICS, ScientificDomain.ECOLOGY],
        )

        # Ecology laws
        self.laws["trophic_efficiency"] = ScientificLaw(
            law_id="trophic_efficiency",
            name="Trophic Transfer Efficiency",
            domain=ScientificDomain.ECOLOGY,
            description="Only 10% of energy transfers between trophic levels",
            law_function=lambda energy, efficiency: energy * efficiency,
            coupled_domains=[ScientificDomain.BIOLOGY],
        )

        self.laws["carrying_capacity"] = ScientificLaw(
            law_id="carrying_capacity",
            name="Carrying Capacity",
            domain=ScientificDomain.ECOLOGY,
            description="Environment's maximum sustainable population",
            law_function=lambda resources, consumption: resources / max(consumption, 0.001),
            coupled_domains=[ScientificDomain.BIOLOGY, ScientificDomain.SOCIOLOGY],
        )

        # Social science laws (emergent)
        self.laws["utility_maximization"] = ScientificLaw(
            law_id="utility_maximization",
            name="Utility Maximization",
            domain=ScientificDomain.ECONOMICS,
            description="Agents maximize expected utility",
            law_function=lambda utility, cost: utility - cost,
            coupled_domains=[ScientificDomain.BIOLOGY, ScientificDomain.SOCIOLOGY],
        )

        self.laws["supply_demand"] = ScientificLaw(
            law_id="supply_demand",
            name="Supply and Demand",
            domain=ScientificDomain.ECONOMICS,
            description="Price equilibriums from supply and demand",
            law_function=lambda supply, demand: (demand - supply) / max(supply, 0.001),
            coupled_domains=[ScientificDomain.ECOLOGY],
        )

        self.laws["power_distribution"] = ScientificLaw(
            law_id="power_distribution",
            name="Power Law Distribution",
            domain=ScientificDomain.POLITICAL_SCIENCE,
            description="Power often follows Pareto distribution",
            law_function=lambda wealth, exponent: wealth ** exponent,
            coupled_domains=[ScientificDomain.ECONOMICS, ScientificDomain.SOCIOLOGY],
        )

        self.laws["social_learning"] = ScientificLaw(
            law_id="social_learning",
            name="Social Learning Theory",
            domain=ScientificDomain.SOCIOLOGY,
            description="Behavior acquired through observation of others",
            law_function=lambda obs, imitation_rate: obs * imitation_rate,
            coupled_domains=[ScientificDomain.BIOLOGY, ScientificDomain.PSYCHOLOGY],
        )

        # === Additional Physics Laws ===

        self.laws["coulombs_law"] = ScientificLaw(
            law_id="coulombs_law",
            name="Coulomb's Law",
            domain=ScientificDomain.PHYSICS,
            description="Electrostatic force between charged particles",
            law_function=lambda q1, q2, r: (q1 * q2) / max(r ** 2, 0.001),
            parameters={"k": 8.99e9},
            coupled_domains=[ScientificDomain.CHEMISTRY],
        )

        self.laws["ideal_gas"] = ScientificLaw(
            law_id="ideal_gas",
            name="Ideal Gas Law",
            domain=ScientificDomain.PHYSICS,
            description="PV = nRT relationship for ideal gases",
            law_function=lambda P, V, n, R=8.314, T=293.15: P * V - n * R * T,
            coupled_domains=[ScientificDomain.CHEMISTRY, ScientificDomain.BIOLOGY],
        )

        self.laws["wave_equation"] = ScientificLaw(
            law_id="wave_equation",
            name="Wave Equation",
            domain=ScientificDomain.PHYSICS,
            description="Wave propagation speed relationship",
            law_function=lambda freq, wavelength: freq * wavelength,
            coupled_domains=[ScientificDomain.COMPUTATIONAL_SCIENCE],
        )

        self.laws["gravitation"] = ScientificLaw(
            law_id="gravitation",
            name="Newton's Law of Gravitation",
            domain=ScientificDomain.PHYSICS,
            description="Gravitational attraction between masses",
            law_function=lambda m1, m2, r, G=6.674e-11: G * m1 * m2 / max(r ** 2, 0.001),
            coupled_domains=[ScientificDomain.ASTRONOMY],
        )

        self.laws["planck_radiation"] = ScientificLaw(
            law_id="planck_radiation",
            name="Planck's Radiation Law",
            domain=ScientificDomain.PHYSICS,
            description="Blackbody radiation spectrum",
            law_function=lambda T, h=6.626e-34, k=1.381e-23: (2 * h * 3e8**2) / (T**4 * 5.67e-8),
            coupled_domains=[ScientificDomain.ASTRONOMY, ScientificDomain.ENVIRONMENTAL_SCIENCE],
        )

        # === Additional Chemistry Laws ===

        self.laws["nernst_equation"] = ScientificLaw(
            law_id="nernst_equation",
            name="Nernst Equation",
            domain=ScientificDomain.CHEMISTRY,
            description="Electrode potential dependence on concentration",
            law_function=lambda E0, R=8.314, T=293.15, n=1, F=96485: E0 + (R * T / (n * F)),
            coupled_domains=[ScientificDomain.PHYSICS, ScientificDomain.BIOLOGY],
        )

        self.laws["henrys_law"] = ScientificLaw(
            law_id="henrys_law",
            name="Henry's Law",
            domain=ScientificDomain.CHEMISTRY,
            description="Gas solubility in liquid at equilibrium",
            law_function=lambda concentration, pressure, kH: concentration - kH * pressure,
            coupled_domains=[ScientificDomain.ENVIRONMENTAL_SCIENCE],
        )

        self.laws["raoults_law"] = ScientificLaw(
            law_id="raoults_law",
            name="Raoult's Law",
            domain=ScientificDomain.CHEMISTRY,
            description="Vapor pressure lowering of solutions",
            law_function=lambda mole_fraction, vapor_pressure: mole_fraction * vapor_pressure,
            coupled_domains=[ScientificDomain.PHYSICS],
        )

        # === Additional Biology Laws ===

        self.laws["hardy_weinberg"] = ScientificLaw(
            law_id="hardy_weinberg",
            name="Hardy-Weinberg Equilibrium",
            domain=ScientificDomain.BIOLOGY,
            description="Genetic equilibrium in population without evolution",
            law_function=lambda p, q: 2 * p * q,  # heterozygote frequency
            coupled_domains=[ScientificDomain.BIOLOGY],
        )

        self.laws["mendelian_inheritance"] = ScientificLaw(
            law_id="mendelian_inheritance",
            name="Mendel's Laws of Inheritance",
            domain=ScientificDomain.BIOLOGY,
            description="Genetic transmission patterns",
            law_function=lambda parent1, parent2: (parent1 + parent2) / 2,
            coupled_domains=[ScientificDomain.GENETICS],
        )

        self.laws["nerve_impulse"] = ScientificLaw(
            law_id="nerve_impulse",
            name="Nernst Potential",
            domain=ScientificDomain.BIOLOGY,
            description="Resting membrane potential",
            law_function=lambda ion_conc_in, ion_conc_out, z=1, T=310: 61 * math.log10(ion_conc_in / max(ion_conc_out, 0.001)) * z,
            coupled_domains=[ScientificDomain.PHYSICS],
        )

        # === Additional Social Science Laws ===

        self.laws["pareto_distribution"] = ScientificLaw(
            law_id="pareto_distribution",
            name="Pareto Principle",
            domain=ScientificDomain.ECONOMICS,
            description="80% of effects come from 20% of causes",
            law_function=lambda wealth, threshold: math.log(max(wealth, 1)) - math.log(max(threshold, 1)),
            parameters={"alpha": 1.16},
            coupled_domains=[ScientificDomain.SOCIOLOGY, ScientificDomain.POLITICAL_SCIENCE],
        )

        self.laws["laffer_curve"] = ScientificLaw(
            law_id="laffer_curve",
            name="Laffer Curve",
            domain=ScientificDomain.ECONOMICS,
            description="Tax revenue as function of tax rate (inverted U)",
            law_function=lambda tax_rate, max_revenue: 4 * max_revenue * tax_rate * (1 - tax_rate),
            coupled_domains=[ScientificDomain.POLITICAL_SCIENCE],
        )

        self.laws["diffusion_innovation"] = ScientificLaw(
            law_id="diffusion_innovation",
            name="Rogers Diffusion of Innovation",
            domain=ScientificDomain.SOCIOLOGY,
            description="Adoption rate of new innovations follows S-curve",
            law_function=lambda adopters, potential: adopters * (potential - adopters) / potential,
            coupled_domains=[ScientificDomain.ECONOMICS, ScientificDomain.PSYCHOLOGY],
        )

        self.laws["macht_distribution"] = ScientificLaw(
            law_id="macht_distribution",
            name="Weber's Law of Power",
            domain=ScientificDomain.POLITICAL_SCIENCE,
            description="Power distance in social hierarchies",
            law_function=lambda base_power, levels: base_power / (2 ** levels),
            coupled_domains=[ScientificDomain.SOCIOLOGY],
        )

        self.laws["information_entropy"] = ScientificLaw(
            law_id="information_entropy",
            name="Shannon Information Entropy",
            domain=ScientificDomain.COMPUTATIONAL_SCIENCE,
            description="Measure of information uncertainty",
            law_function=lambda probabilities: -sum(p * math.log2(max(p, 1e-10)) for p in probabilities if p > 0),
            coupled_domains=[ScientificDomain.PHYSICS, ScientificDomain.STATISTICS],
        )

        self.laws["zipfs_law"] = ScientificLaw(
            law_id="zipfs_law",
            name="Zipf's Law",
            domain=ScientificDomain.LINGUISTICS,
            description="Frequency of words inversely proportional to rank",
            law_function=lambda rank, constant=10000: constant / max(rank, 1),
            coupled_domains=[ScientificDomain.STATISTICS, ScientificDomain.SOCIOLOGY],
        )

        self.laws["allometric_scaling"] = ScientificLaw(
            law_id="allometric_scaling",
            name="Allometric Scaling",
            domain=ScientificDomain.BIOLOGY,
            description="Body size relationships across species",
            law_function=lambda mass, exponent: mass ** exponent,
            parameters={"exponent": 0.75},
            coupled_domains=[ScientificDomain.ECOLOGY, ScientificDomain.MEDICINE],
        )

        self.laws["doubling_time"] = ScientificLaw(
            law_id="doubling_time",
            name="Rule of 70 (Doubling Time)",
            domain=ScientificDomain.STATISTICS,
            description="Time for exponential growth to double",
            law_function=lambda growth_rate: 70 / max(growth_rate, 0.001),
            coupled_domains=[ScientificDomain.ECONOMICS, ScientificDomain.BIOLOGY],
        )

        self.laws["central_limit"] = ScientificLaw(
            law_id="central_limit",
            name="Central Limit Theorem",
            domain=ScientificDomain.STATISTICS,
            description="Distribution of sample means approaches normal",
            law_function=lambda n, variance: math.sqrt(variance / max(n, 1)),
            coupled_domains=[ScientificDomain.SYSTEM_SCIENCE],
        )

        self.laws["dunning_kruger"] = ScientificLaw(
            law_id="dunning_kruger",
            name="Dunning-Kruger Effect",
            domain=ScientificDomain.PSYCHOLOGY,
            description="Low competence overestimates ability",
            law_function=lambda competence, exp=2: min(1.0, competence ** exp + 0.1),
            coupled_domains=[ScientificDomain.SOCIOLOGY, ScientificDomain.EDUCATION],
        )

        self.laws["groupthink"] = ScientificLaw(
            law_id="groupthink",
            name="Groupthink Model",
            domain=ScientificDomain.PSYCHOLOGY,
            description="Cohesion reduces critical evaluation",
            law_function=lambda cohesion, stress: cohesion * stress / max(cohesion + stress, 0.1),
            coupled_domains=[ScientificDomain.POLITICAL_SCIENCE, ScientificDomain.SYSTEM_SCIENCE],
        )

    def _register_couplings(self) -> None:
        """Register cross-domain couplings."""

        # Physics -> Chemistry: Temperature affects reaction rates
        self.couplings.append(CouplingRelation(
            coupling_id="physics_chemistry_temp",
            source_domain=ScientificDomain.PHYSICS,
            target_domain=ScientificDomain.CHEMISTRY,
            shared_variables=["temperature", "pressure", "energy"],
            coupling_function=lambda s: {
                "temperature": s.get("temperature", 293.15),
                "pressure": s.get("pressure", 101325.0),
                "reaction_rate_factor": s.get("temperature", 293.15) / 293.15,
            },
            strength=1.0,
            delay=0,
        ))

        # Chemistry -> Biology: Metabolism from chemical reactions
        self.couplings.append(CouplingRelation(
            coupling_id="chemistry_biology_metabolism",
            source_domain=ScientificDomain.CHEMISTRY,
            target_domain=ScientificDomain.BIOLOGY,
            shared_variables=["energy", "nutrients", "atp"],
            coupling_function=lambda s: {
                "metabolic_rate": s.get("energy", 100.0) * 0.01,
                "atp_available": s.get("atp", 100.0),
            },
            strength=1.0,
            delay=1,
        ))

        # Biology -> Ecology: Population dynamics affect ecosystems
        self.couplings.append(CouplingRelation(
            coupling_id="biology_ecology_population",
            source_domain=ScientificDomain.BIOLOGY,
            target_domain=ScientificDomain.ECOLOGY,
            shared_variables=["population", "biomass", "fitness"],
            coupling_function=lambda s: {
                "population_density": s.get("population", 100) / 1000,
                "biomass_flux": s.get("biomass", 100.0) * 0.1,
                "selection_pressure": 1 - s.get("fitness", 0.5),
            },
            strength=1.0,
            delay=10,
        ))

        # Ecology -> Biology: Resource availability affects fitness
        self.couplings.append(CouplingRelation(
            coupling_id="ecology_biology_resources",
            source_domain=ScientificDomain.ECOLOGY,
            target_domain=ScientificDomain.BIOLOGY,
            shared_variables=["carrying_capacity", "resource_availability", "competition"],
            coupling_function=lambda s: {
                "survival_probability": min(1.0, s.get("carrying_capacity", 1000) / 1000),
                "competition_intensity": s.get("competition", 0.0),
            },
            strength=0.8,
            delay=5,
        ))

        # Ecology -> Economics: Ecosystem services have economic value
        self.couplings.append(CouplingRelation(
            coupling_id="ecology_economics",
            source_domain=ScientificDomain.ECOLOGY,
            target_domain=ScientificDomain.ECONOMICS,
            shared_variables=["primary_productivity", "biodiversity", "resources"],
            coupling_function=lambda s: {
                "natural_capital": s.get("primary_productivity", 1000) * s.get("biodiversity", 0.5),
                "resource_value": s.get("resources", 100.0) * 0.01,
            },
            strength=0.5,
            delay=20,
        ))

        # Biology -> Social: Human behavior emerges from biology
        self.couplings.append(CouplingRelation(
            coupling_id="biology_social",
            source_domain=ScientificDomain.BIOLOGY,
            target_domain=ScientificDomain.SOCIOLOGY,
            shared_variables=["intelligence", "social_behavior", "reproduction"],
            coupling_function=lambda s: {
                "social_learning_rate": s.get("intelligence", 0.5) * 0.1,
                "group_size": min(150, int(s.get("population", 100) * 0.3)),
            },
            strength=0.7,
            delay=50,
        ))

        # Economics -> Social: Economic inequality affects social structure
        self.couplings.append(CouplingRelation(
            coupling_id="economics_social",
            source_domain=ScientificDomain.ECONOMICS,
            target_domain=ScientificDomain.SOCIOLOGY,
            shared_variables=["wealth", "inequality", "mobility"],
            coupling_function=lambda s: {
                "gini_coefficient": s.get("inequality", 0.3),
                "social_mobility": s.get("mobility", 0.5),
            },
            strength=0.6,
            delay=30,
        ))

        # Social -> Political: Social structures influence politics
        self.couplings.append(CouplingRelation(
            coupling_id="social_political",
            source_domain=ScientificDomain.SOCIOLOGY,
            target_domain=ScientificDomain.POLITICAL_SCIENCE,
            shared_variables=["power", "institutions", "norms"],
            coupling_function=lambda s: {
                "institutional_strength": s.get("institutions", 0.5),
                "norm_adherence": s.get("norms", 0.7),
            },
            strength=0.5,
            delay=50,
        ))

    def update(self, tick: int, dt: float = 1.0) -> dict:
        """Update all scientific systems with coupling."""
        self.tick = tick
        all_events = {}

        # Update each domain
        physics_stats = self.physics.get_statistics()
        self._propagate_state("physics", physics_stats)

        chemistry_stats = self.chemistry.get_statistics()
        self._propagate_state("chemistry", chemistry_stats)

        biology_stats = self.biology.get_statistics()
        self._propagate_state("biology", biology_stats)

        ecology_stats = self.ecology.get_statistics()
        self._propagate_state("ecology", ecology_stats)

        # Propagate across domains
        self._propagate_cross_domain(tick, dt)

        # Record events
        all_events = {
            "physics": physics_stats,
            "chemistry": chemistry_stats,
            "biology": biology_stats,
            "ecology": ecology_stats,
        }

        return all_events

    def _propagate_state(self, domain: str, state: dict) -> None:
        """Propagate state changes within domain."""
        for coupling in self.couplings:
            if coupling.source_domain.value == domain:
                self.cross_domain_events.append({
                    "tick": self.tick,
                    "source": domain,
                    "state": state,
                    "coupling": coupling.coupling_id,
                })

    def _propagate_cross_domain(self, tick: int, dt: float) -> None:
        """Propagate changes across domains via couplings."""
        # Group events by coupling
        events_by_coupling: dict[str, list[dict]] = {}
        for event in self.cross_domain_events:
            coupling_id = event["coupling"]
            if coupling_id not in events_by_coupling:
                events_by_coupling[coupling_id] = []
            events_by_coupling[coupling_id].append(event)

        # Process each coupling
        for coupling in self.couplings:
            if coupling.coupling_id not in events_by_coupling:
                continue

            events = events_by_coupling[coupling.coupling_id]
            if not events:
                continue

            # Get latest event from source
            latest = max(events, key=lambda e: e["tick"])
            source_state = latest["state"]

            # Apply coupling
            if coupling.delay == 0 or (self.tick - latest["tick"]) >= coupling.delay:
                target_state = coupling.propagate(source_state)

                # Apply to target domain
                self._apply_to_target(coupling.target_domain, target_state)

                # Track interaction
                key = f"{coupling.source_domain.value}->{coupling.target_domain.value}"
                self.domain_interactions[key] = self.domain_interactions.get(key, 0) + 1

    def _apply_to_target(self, domain: ScientificDomain, state: dict) -> None:
        """Apply state changes to target domain."""
        domain_name = domain.value

        if domain_name == "physics":
            # Apply to physics engine
            pass
        elif domain_name == "chemistry":
            # Apply to chemistry engine
            pass
        elif domain_name == "biology":
            # Apply to biology engine
            pass
        elif domain_name == "ecology":
            # Apply to ecology engine
            pass

    def apply_law(self, law_id: str, *args, **kwargs) -> float:
        """Apply a scientific law."""
        law = self.laws.get(law_id)
        if not law:
            return 0.0
        return law.apply(*args, **kwargs)

    def get_coupling_strength(self, source: ScientificDomain, target: ScientificDomain) -> float:
        """Get coupling strength between two domains."""
        for coupling in self.couplings:
            if coupling.source_domain == source and coupling.target_domain == target:
                return coupling.strength
        return 0.0

    def create_unified_field(self, field_id: str, name: str, description: str) -> UnifiedField:
        """Create a new unified field."""
        field = UnifiedField(
            field_id=field_id,
            name=name,
            description=description,
        )
        self.fields[field_id] = field
        return field

    def get_statistics(self) -> dict:
        """Get comprehensive statistics."""
        return {
            "tick": self.tick,
            "domains": {
                "physics": self.physics.get_statistics(),
                "chemistry": self.chemistry.get_statistics(),
                "biology": self.biology.get_statistics(),
                "ecology": self.ecology.get_statistics(),
            },
            "laws": len(self.laws),
            "couplings": len(self.couplings),
            "cross_domain_interactions": self.domain_interactions,
            "unified_fields": len(self.fields),
        }


# =============================================================================
# Emergence Monitor
# =============================================================================

class EmergenceMonitor:
    """
    Monitors for emergent phenomena across domains.

    Detects:
    - Novel behaviors at domain boundaries
    - Cross-domain patterns
    - System-level properties
    - Emergent institutions
    """

    def __init__(self):
        self.observations: list[dict] = []
        self.emergent_patterns: list[dict] = []

    def observe(self, tick: int, domain: str, observation: dict) -> None:
        """Record an observation."""
        self.observations.append({
            "tick": tick,
            "domain": domain,
            "observation": observation,
        })

        # Check for patterns
        self._check_patterns(tick)

    def _check_patterns(self, tick: int) -> None:
        """Check for emergent patterns."""
        # Check recent observations
        recent = [o for o in self.observations if o["tick"] > tick - 100]

        # Group by domain
        by_domain: dict[str, list] = {}
        for obs in recent:
            domain = obs["domain"]
            if domain not in by_domain:
                by_domain[domain] = []
            by_domain[domain].append(obs)

        # Check for cross-domain patterns
        if len(by_domain) >= 2:
            self._detect_cross_domain_emergence(tick, by_domain)

    def _detect_cross_domain_emergence(
        self,
        tick: int,
        by_domain: dict[str, list],
    ) -> None:
        """Detect emergence at domain boundaries."""
        # This is a simplified detection
        # In a full implementation, would use more sophisticated methods
        domains = list(by_domain.keys())

        for i, d1 in enumerate(domains):
            for d2 in domains[i + 1:]:
                # Check if there's interaction evidence
                # (simplified - real implementation would be more sophisticated)
                pattern = {
                    "tick": tick,
                    "type": "cross_domain",
                    "domains": [d1, d2],
                    "description": f"Interaction between {d1} and {d2}",
                }
                self.emergent_patterns.append(pattern)
