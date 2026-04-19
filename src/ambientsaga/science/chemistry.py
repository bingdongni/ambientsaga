"""
Chemistry Engine — Chemical Substances and Reactions

Provides a simplified but principled chemistry simulation:
- Substances: Elements, compounds, molecules
- Reactions: Combustion, oxidation, acid-base, synthesis, decomposition
- Thermochemistry: Enthalpy, entropy, free energy
- Reaction kinetics: Rate laws, catalysts, inhibitors
- Electrochemistry: Redox reactions, batteries

Chemistry emerges from physics (atomic interactions).
Biology emerges from chemistry (molecular systems).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Optional, Callable
from enum import Enum


class ElementType(Enum):
    """Basic chemical elements (simplified periodic table)."""
    # Light elements
    HYDROGEN = "H"
    HELIUM = "He"
    CARBON = "C"
    NITROGEN = "N"
    OXYGEN = "O"
    # Metals
    SODIUM = "Na"
    MAGNESIUM = "Mg"
    IRON = "Fe"
    COPPER = "Cu"
    ZINC = "Zn"
    # Others
    PHOSPHORUS = "P"
    SULFUR = "S"
    CHLORINE = "Cl"
    # Biological
    CALCIUM = "Ca"
    POTASSIUM = "K"
    # Compounds (treated as pseudo-elements for simplicity)
    WATER = "H2O"
    CO2 = "CO2"
    GLUCOSE = "C6H12O6"
    AMINO_ACID = "AA"
    PROTEIN = "PROTEIN"
    DNA = "DNA"
    FAT = "FAT"
    CELL = "CELL"


@dataclass
class Substance:
    """A chemical substance."""
    substance_id: str
    name: str
    formula: str  # Chemical formula
    molecular_mass: float  # g/mol
    state: str = "solid"  # solid, liquid, gas, plasma
    charge: int = 0  # Ionic charge
    polarity: float = 0.5  # 0-1, polarity
    reactivity: float = 0.5  # 0-1, tendency to react

    # Physical properties
    density: float = 1.0  # g/cm^3
    melting_point: float = 273.15  # K
    boiling_point: float = 373.15  # K
    solubility: float = 0.5  # 0-1, in water
    enthalpy: float = 0.0  # kJ/mol, formation enthalpy
    entropy: float = 0.0  # J/(mol·K)

    # Composition
    elements: dict[str, int] = field(default_factory=dict)  # element -> count

    def get_state_at(self, temperature: float) -> str:
        """Get state at given temperature."""
        if temperature < self.melting_point:
            return "solid"
        elif temperature < self.boiling_point:
            return "liquid"
        else:
            return "gas"

    def react_with(self, other: Substance) -> Optional[Reaction]:
        """Check if this substance can react with another."""
        # Simplified reaction rules
        reactions = {
            ("H", "O"): ReactionType.COMBINATION,
            ("C", "O"): ReactionType.COMBUSTION,
            ("HCl", "NaOH"): ReactionType.ACID_BASE,
        }
        key = tuple(sorted([self.formula, other.formula]))
        return reactions.get(key)


@dataclass
class Compound:
    """A chemical compound (combination of substances)."""
    compound_id: str
    name: str
    substances: list[Substance]
    stoichiometry: dict[str, int]  # substance_id -> count
    structure: str = "mixture"  # mixture, solution, suspension, colloid


class ReactionType(Enum):
    """Types of chemical reactions."""
    COMBINATION = "combination"  # A + B -> AB
    DECOMPOSITION = "decomposition"  # AB -> A + B
    COMBUSTION = "combustion"  # Fuel + O2 -> CO2 + H2O
    OXIDATION = "oxidation"  # A + O2 -> AO
    REDUCTION = "reduction"  # AO + H2 -> A + H2O
    ACID_BASE = "acid_base"  # Acid + Base -> Salt + Water
    PRECIPITATION = "precipitation"  # AB + CD -> AD + BC (solid)
    HYDROLYSIS = "hydrolysis"  # AB + H2O -> AH + BOH
    FERMENTATION = "fermentation"  # Glucose -> Ethanol + CO2
    PHOTOSYNTHESIS = "photosynthesis"  # CO2 + H2O -> Glucose + O2
    RESPIRATION = "respiration"  # Glucose + O2 -> CO2 + H2O
    CATALYSIS = "catalysis"  # A + Catalyst -> A* -> A + Catalyst


@dataclass
class Reaction:
    """A chemical reaction."""
    reaction_id: str
    reaction_type: ReactionType

    # Stoichiometry
    reactants: dict[str, int]  # substance_id -> coefficient
    products: dict[str, int]  # substance_id -> coefficient

    # Thermodynamics
    delta_h: float = 0.0  # Enthalpy change (kJ/mol), + = endothermic
    delta_s: float = 0.0  # Entropy change (J/(mol·K))
    activation_energy: float = 0.0  # kJ/mol

    # Kinetics
    rate_constant: float = 1.0  # Reaction rate constant
    catalysts: list[str] = field(default_factory=list)  # substance_ids that catalyze
    inhibitors: list[str] = field(default_factory=list)  # substance_ids that inhibit

    # Equilibrium
    equilibrium_constant: float = 1.0  # K_eq
    reversible: bool = False

    def get_equilibrium(self, temperature: float) -> float:
        """Calculate equilibrium constant at temperature (van't Hoff equation)."""
        if self.delta_h == 0:
            return self.equilibrium_constant
        # ln(K2/K1) = -ΔH/R * (1/T2 - 1/T1)
        R = 8.314  # J/(mol·K)
        K1 = self.equilibrium_constant
        T1 = 298.15  # Reference temperature
        K2 = K1 * math.exp(-self.delta_h * 1000 / R * (1/temperature - 1/T1))
        return K2

    def get_rate(
        self,
        concentrations: dict[str, float],
        temperature: float,
        catalysts_present: set[str] = None,
    ) -> float:
        """Calculate reaction rate."""
        # Check if all reactants are present
        for reactant in self.reactants:
            if reactant not in concentrations:
                return 0.0

        # Base rate from rate law (simplified: rate = k * [A]^a * [B]^b)
        rate = self.rate_constant
        for reactant, coeff in self.reactants.items():
            rate *= (concentrations[reactant] ** coeff)

        # Temperature effect (Arrhenius equation)
        if self.activation_energy > 0:
            R = 8.314
            T_factor = math.exp(-self.activation_energy * 1000 / (R * temperature))
            rate *= T_factor

        # Catalyst effect
        if catalysts_present:
            for catalyst in self.catalysts:
                if catalyst in catalysts_present:
                    rate *= 10  # 10x speedup per catalyst

        # Inhibitor effect
        if catalysts_present:
            for inhibitor in self.inhibitors:
                if inhibitor in catalysts_present:
                    rate *= 0.1  # 10x slowdown per inhibitor

        return rate


@dataclass
class ChemicalSystem:
    """A system containing chemicals."""
    system_id: str
    substances: dict[str, Substance] = field(default_factory=dict)
    reactions: list[Reaction] = field(default_factory=list)
    concentrations: dict[str, float] = field(default_factory=dict)  # substance_id -> mol/L
    temperature: float = 293.15  # K
    pressure: float = 101325.0  # Pa
    volume: float = 1.0  # L
    pH: float = 7.0  # 0-14

    # Environmental
    redox_potential: float = 0.0  # V
    ionic_strength: float = 0.0  # mol/L

    def add_substance(self, substance: Substance, concentration: float = 0.0) -> None:
        """Add a substance to the system."""
        self.substances[substance.substance_id] = substance
        self.concentrations[substance.substance_id] = concentration

    def add_reaction(self, reaction: Reaction) -> None:
        """Add a reaction to the system."""
        self.reactions.append(reaction)

    def get_concentration(self, substance_id: str) -> float:
        """Get concentration of a substance."""
        return self.concentrations.get(substance_id, 0.0)

    def get_total_moles(self, substance_id: str) -> float:
        """Get total moles of a substance."""
        return self.get_concentration(substance_id) * self.volume

    def update_pH(self) -> None:
        """Update pH based on H+ concentration."""
        h_conc = self.get_concentration("H+")
        if h_conc > 0:
            self.pH = -math.log10(h_conc)

    def get_gibbs_energy(self, substance_id: str) -> float:
        """Calculate Gibbs free energy of formation."""
        if substance_id not in self.substances:
            return 0.0
        substance = self.substances[substance_id]
        # G = H - TS (simplified)
        return substance.enthalpy - self.temperature * substance.entropy / 1000


class ChemistryEngine:
    """
    Chemistry simulation engine.

    Provides chemical reactions and transformations.
    Couples with:
    - Physics: Temperature, pressure, energy
    - Biology: Metabolism, nutrients
    - Ecology: Nutrient cycles
    """

    # Pre-defined biological reactions
    BIOLOGICAL_REACTIONS: dict[str, Reaction] = {}

    def __init__(self, config: dict = None):
        self.config = config or {}

        # Substance database
        self.substances: dict[str, Substance] = {}
        self._init_biological_substances()

        # Chemical systems
        self.systems: dict[str, ChemicalSystem] = {}

        # Statistics
        self.total_reactions = 0
        self.reaction_history: list[tuple[int, str, dict]] = []

        # Global chemistry
        self.atmosphere_composition: dict[str, float] = {
            "N2": 0.78,
            "O2": 0.21,
            "CO2": 0.0004,
            "Ar": 0.0093,
            "H2O": 0.0,  # Variable
        }

    def _init_biological_substances(self) -> None:
        """Initialize biological substances."""
        # Water
        water = Substance(
            substance_id="H2O",
            name="Water",
            formula="H2O",
            molecular_mass=18.015,
            state="liquid",
            charge=0,
            polarity=1.0,
            enthalpy=-285.8,
            entropy=69.9,
            elements={"H": 2, "O": 1},
        )
        self.substances["H2O"] = water

        # Glucose
        glucose = Substance(
            substance_id="C6H12O6",
            name="Glucose",
            formula="C6H12O6",
            molecular_mass=180.16,
            state="solid",
            polarity=0.5,
            enthalpy=-1274.5,
            entropy=212.0,
            elements={"C": 6, "H": 12, "O": 6},
        )
        self.substances["C6H12O6"] = glucose

        # CO2
        co2 = Substance(
            substance_id="CO2",
            name="Carbon Dioxide",
            formula="CO2",
            molecular_mass=44.01,
            state="gas",
            polarity=0.0,
            enthalpy=-393.5,
            entropy=213.6,
            elements={"C": 1, "O": 2},
        )
        self.substances["CO2"] = co2

        # O2
        o2 = Substance(
            substance_id="O2",
            name="Oxygen",
            formula="O2",
            molecular_mass=32.00,
            state="gas",
            polarity=0.0,
            enthalpy=0.0,
            entropy=205.0,
            elements={"O": 2},
        )
        self.substances["O2"] = o2

        # N2
        n2 = Substance(
            substance_id="N2",
            name="Nitrogen",
            formula="N2",
            molecular_mass=28.01,
            state="gas",
            polarity=0.0,
            enthalpy=0.0,
            entropy=191.5,
            elements={"N": 2},
        )
        self.substances["N2"] = n2

        # Amino acids (simplified)
        amino = Substance(
            substance_id="AA",
            name="Amino Acid",
            formula="C2H5NO2",
            molecular_mass=75.07,
            state="solid",
            polarity=0.5,
            enthalpy=-500.0,
            entropy=150.0,
        )
        self.substances["AA"] = amino

        # ATP (simplified)
        atp = Substance(
            substance_id="ATP",
            name="Adenosine Triphosphate",
            formula="C10H16N5O13P3",
            molecular_mass=507.18,
            state="solid",
            polarity=0.8,
            enthalpy=-3000.0,
            entropy=500.0,
        )
        self.substances["ATP"] = atp

        # ADP (ATP breakdown product)
        adp = Substance(
            substance_id="ADP",
            name="Adenosine Diphosphate",
            formula="C10H15N5O10P2",
            molecular_mass=427.20,
            state="solid",
            polarity=0.8,
            enthalpy=-2500.0,
            entropy=450.0,
        )
        self.substances["ADP"] = adp

    def get_substance(self, substance_id: str) -> Optional[Substance]:
        """Get a substance by ID."""
        return self.substances.get(substance_id)

    def create_system(self, system_id: str) -> ChemicalSystem:
        """Create a new chemical system."""
        system = ChemicalSystem(system_id=system_id)
        self.systems[system_id] = system
        return system

    def add_reaction(
        self,
        system_id: str,
        reaction_type: ReactionType,
        reactants: dict[str, int],
        products: dict[str, int],
        delta_h: float = 0.0,
        temperature: float = 293.15,
    ) -> Reaction:
        """Add a reaction to a system."""
        if system_id not in self.systems:
            self.create_system(system_id)

        system = self.systems[system_id]
        reaction_id = f"rxn_{len(system.reactions)}"

        reaction = Reaction(
            reaction_id=reaction_id,
            reaction_type=reaction_type,
            reactants=reactants,
            products=products,
            delta_h=delta_h,
            temperature=temperature,
        )

        system.add_reaction(reaction)
        return reaction

    def update(self, tick: int, dt: float = 1.0) -> None:
        """Update chemistry simulation."""
        for system in self.systems.values():
            self._update_system(system, tick, dt)

    def _update_system(self, system: ChemicalSystem, tick: int, dt: float) -> None:
        """Update a chemical system."""
        for reaction in system.reactions:
            # Calculate reaction rate
            rate = reaction.get_rate(
                system.concentrations,
                system.temperature,
            )

            if rate <= 0:
                continue

            # Check if reactants are available
            can_proceed = True
            for reactant, coeff in reaction.reactants.items():
                required = coeff * rate * dt
                available = system.get_concentration(reactant)
                if available < required:
                    can_proceed = False
                    break

            if not can_proceed:
                continue

            # Execute reaction
            for reactant, coeff in reaction.reactants.items():
                system.concentrations[reactant] -= coeff * rate * dt
                if system.concentrations[reactant] < 0:
                    system.concentrations[reactant] = 0

            for product, coeff in reaction.products.items():
                if product not in system.concentrations:
                    system.concentrations[product] = 0
                system.concentrations[product] += coeff * rate * dt

            # Record reaction
            self.total_reactions += 1
            self.reaction_history.append((
                tick,
                reaction.reaction_id,
                {"rate": rate, "temperature": system.temperature}
            ))

            # Update pH
            system.update_pH()

    def photosynthesize(
        self,
        co2: float,
        water: float,
        sunlight_factor: float = 1.0,
    ) -> tuple[float, float, float]:
        """
        Perform photosynthesis: CO2 + H2O -> Glucose + O2

        Returns: (glucose_created, o2_released, energy_stored)
        """
        # Stoichiometry: 6 CO2 + 6 H2O -> C6H12O6 + 6 O2
        # Energy: ~2800 kJ/mol glucose

        max_glucose = min(co2 / 6, water / 6) * sunlight_factor
        glucose = max_glucose
        o2_released = glucose * 6
        co2_consumed = glucose * 6
        water_consumed = glucose * 6
        energy_stored = glucose * 2800  # kJ

        return glucose, o2_released, energy_stored

    def respire(
        self,
        glucose: float,
        oxygen: float,
        efficiency: float = 0.4,
    ) -> tuple[float, float, float]:
        """
        Perform cellular respiration: C6H12O6 + 6 O2 -> 6 CO2 + 6 H2O

        Returns: (co2_produced, water_produced, energy_released)
        """
        # Aerobic respiration: ~2800 kJ/mol glucose, 40% efficiency
        # Net: ~1120 kJ usable energy

        max_cycles = min(glucose, oxygen / 6)
        co2_produced = max_cycles * 6
        water_produced = max_cycles * 6
        energy_released = max_cycles * 2800 * efficiency

        return co2_produced, water_produced, energy_released

    def get_statistics(self) -> dict:
        """Get chemistry statistics."""
        return {
            "substances": len(self.substances),
            "systems": len(self.systems),
            "total_reactions": self.total_reactions,
            "atmosphere_composition": self.atmosphere_composition,
        }


# =============================================================================
# Coupling with other sciences
# =============================================================================

# Chemistry-Biology coupling
METABOLISM_COSTS = {
    "photosynthesis": 0.1,  # Energy cost per unit glucose
    "respiration": 0.4,  # Efficiency of ATP production
    "protein_synthesis": 4.2,  # kJ per gram
    "fat_storage": 39.7,  # kJ per gram
}

# Chemistry-Ecology coupling
NUTRIENT_CYCLES = {
    "carbon": {
        "reservoir": "atmosphere",
        "fluxes": ["photosynthesis", "respiration", "decomposition"],
        " residence_time": 4.0,  # years in atmosphere
    },
    "nitrogen": {
        "reservoir": "atmosphere",
        "fluxes": ["nitrogen_fixation", "denitrification", "assimilation"],
        "residence_time": 10000,  # years
    },
    "phosphorus": {
        "reservoir": "geosphere",
        "fluxes": ["weathering", "uptake", "decomposition"],
        "residence_time": 1000000,  # years
    },
}
