# AmbientSaga 境世

> Decentralized Perception-Driven Multi-Agent Simulation Engine for Social-Ecological Co-Evolution

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![Documentation](https://img.shields.io/badge/docs-in%20progress-orange)](https://docs.ambientsaga.dev)

**AmbientSaga** is a civilization-scale multi-agent simulation engine that runs thousands of AI agents in a richly modeled natural and social world. It combines the depth of social science with the scale of complex systems research.

**Author**: bingdongni

## Core Philosophy

Three paradigm rules govern every agent in AmbientSaga:

1. **No Global Access** — Agents never read global world state; their only input is locally perceived ambient signals
2. **No Centralized Dispatch** — Agents act autonomously from their own mental model plus local signals
3. **Physical Signal Constraints** — All signals follow propagation range, intensity decay, and duration rules

## Key Features

### Natural World Systems
- Geological subsystem (tectonic plates, erosion, soil formation, mineral deposits)
- Hydrological subsystem (完整水循环, rivers, groundwater, water quality)
- Atmospheric subsystem (temperature, precipitation, wind, climate zones, El Nino)
- Ecological subsystem (food webs, biogeochemical cycles, succession, keystone species)
- Disaster subsystem (earthquakes, volcanic eruptions, floods, droughts, plagues, wildfires)

### Social World Systems
- Individual psychology (Maslow needs, HEXACO personality, emotion dynamics, cognitive biases)
- Social networks (multi-dimensional relationships, trust propagation, network structure)
- Organizations (families, clans, guilds, religions, governments, corporations)
- Institutions (property rights, law, contracts, enforcement mechanisms)
- Economy (production, markets, prices, money, trade, inequality emergence)
- Politics (governance, authority, elections, policy, conflict resolution)
- Culture (belief systems, religion, language evolution, art, knowledge accumulation)

### Agent Architecture
- **L1 Core** (50-80): Full LLM reasoning, real-time decisions, leaders and innovators
- **L2 Functional** (500-1000): Periodic reasoning with memory, routine operations
- **L3 Background** (10k-50k): Lightweight models, behavior-driven, population dynamics
- **L4 Ecological** (100k+): Rule-based, zero LLM cost, ecosystem balance

### Research Platform
- 12+ core quantitative metrics (Gini, polarization, cultural diversity, etc.)
- Causal tracing from any phenomenon to its origin event
- Experiment framework with controlled variables
- Reproducible datasets (short to 1000+ simulated years)

## Architecture

```
AmbientSaga/
├── ambientsaga/
│   ├── world/          # Core simulation engine
│   │   ├── state.py    # World state management
│   │   ├── chunk.py    # Spatial chunking (LOD)
│   │   ├── tick.py     # Time advancement
│   │   ├── signal_bus.py # Event-driven signal routing
│   │   └── events.py   # Event definitions
│   ├── natural/        # Natural world systems
│   │   ├── terrain.py   # Geological + terrain generation
│   │   ├── climate.py   # Atmospheric simulation
│   │   ├── water.py     # Hydrological simulation
│   │   ├── ecology.py   # Ecosystem + biogeochemical cycles
│   │   └── disaster.py  # Natural disaster modeling
│   ├── agents/         # Agent systems
│   │   ├── agent.py    # Agent core model
│   │   ├── tier.py     # Tier management
│   │   ├── cognition/  # Cognitive models
│   │   ├── perception/ # Signal processing
│   │   └── deliberation/ # Decision routing
│   ├── social/         # Social systems
│   ├── economy/        # Economic systems
│   ├── politics/       # Political systems
│   ├── culture/        # Cultural systems
│   ├── research/       # Research tools
│   └── visualization/  # Rendering
└── tests/             # Test suite
```

## Installation

```bash
# Clone the repository
git clone https://github.com/bingdongni/ambientsaga.git
cd ambientsaga

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install with all dependencies
pip install -e ".[all]"

# Run a demo simulation
python -m ambientsaga run --ticks 1000 --agents 5000 --world river_valley
```

## Quick Start

```python
from ambientsaga import World, Config
from ambientsaga.agents import AgentFactory
from ambientsaga.natural import TerrainGenerator
from ambientsaga.visualization import CanvasRenderer

# Create world configuration
config = Config(
    world_size=(512, 512),
    num_agents=5000,
    tick_rate=1.0,  # 1 tick = 1 second real time
    seed=42,
)

# Initialize world
world = World(config)
terrain_gen = TerrainGenerator(config)
world.natural_world.terrain = terrain_gen.generate()
world.natural_world.initialize()

# Spawn agents
factory = AgentFactory(world)
factory.spawn_population(n=5000, tier_distribution={1: 50, 2: 500, 3: 4450})

# Run simulation
renderer = CanvasRenderer(world)
for tick in range(10000):
    world.tick()
    if tick % 100 == 0:
        renderer.render()

print(world.research.get_summary())
```

## Research Usage

```python
from ambientsaga.research import MetricsCollector, ExperimentRunner

# Collect metrics across simulation
collector = MetricsCollector(world)
collector.start()

# Run with experimental conditions
runner = ExperimentRunner(world)
runner.set_condition(tax_rate=0.15, property_regime="communal")
results = runner.run(duration=50000)

# Analyze results
print(results.gini_coefficient_over_time())
print(results.opinion_polarization_index())
print(results.cultural_diversity_map())
```

## Development

```bash
# Run tests
pytest tests/ -v --cov=src/ambientsaga

# Type checking
mypy src/ambientsaga/

# Linting
ruff check src/ambientsaga/

# Format code
ruff format src/ambientsaga/
```

## Academic Impact

AmbientSaga enables research across multiple disciplines:

- **Sociology**: Social stratification, group polarization, institutional emergence
- **Economics**: Division of labor, market formation, inequality dynamics
- **Political Science**: Authority emergence, conflict resolution, policy effects
- **Anthropology**: Cultural transmission, language evolution, religion formation
- **Ecology**: Human-environment coupling, resource dynamics, ecosystem engineering
- **Cognitive Science**: Collective memory, belief propagation, social cognition
- **Complex Systems**: Phase transitions, emergence, scaling laws
- **AI Safety**: Multi-agent alignment, group dynamics, value drift

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

---

*"We do not simulate agents. We simulate worlds."*
