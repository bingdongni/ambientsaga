# AmbientSaga

Large-scale AI agent simulation system with emergent social structures.

## Project Overview

AmbientSaga simulates thousands of AI agents in a world where social structures, economies, and cultures emerge from micro-interactions without preset institutions.

- **10K agents**: ~21 ticks/s (stable, low variance)
- **100 agents**: ~4300 ticks/s
- **Web visualization**: WebSocket on port 8765

## Quick Start

```bash
# Run simulation (requires Python 3.11+)
PYTHONPATH="E:/PROJECT/src" python -m ambientsaga run --ticks 500 --agents 10000

# With visualization
PYTHONPATH="E:/PROJECT/src" python -m ambientsaga run --ticks 500 --agents 10000 --visualize

# With LLM deliberation
ANTHROPIC_API_KEY="your_key" PYTHONPATH="E:/PROJECT/src" python -m ambientsaga run
```

## Architecture

### Core Modules

| Module | Purpose |
|--------|---------|
| `agents/` | Agent system (core.py, agent.py, cognition.py, tier.py) |
| `world/` | World engine (terrain, climate, ecology, state) |
| `protocol/` | Emergent interaction protocols |
| `evolution/` | Self-evolution system (genome, variation, selection) |
| `science/` | Unified science framework (physics, chemistry, biology, ecology) |
| `visualization/` | Web-based visualization |
| `research/` | Metrics and academic output tools |

### Agent Tiers

- **L1_CORE** (10%): Full cognitive capabilities, LLM deliberation
- **L2_FUNCTIONAL** (10%): Rule-based reasoning
- **L3_BACKGROUND** (80%): Simple reactive behavior

### Key Classes

- `Agent` (agents/agent.py): Main agent class with cognition, memory, beliefs
- `World` (world/state.py): Simulation world with terrain, climate, agents
- `ScienceEngine` (science/systems.py): Unified science with cross-domain coupling

## Key Design Decisions

### Emergent vs Hardcoded

- **Emergent**: Social norms, economic patterns, language, organizations
- **Hardcoded**: Terrain generation, basic needs, physics laws

### Performance Optimizations

- Hash-based sampling for L1 agent decision load
- Chunk-based spatial indexing (chunk_size=16)
- Binary serialization with msgspec
- Asynchronous LLM queue for L1 deliberation

### Science Framework

Physics → Chemistry → Biology → Ecology → Economics

All domains coupled via:
- Temperature affects reaction rates
- Metabolism affects organism energy
- Resources affect economic value

## Running Tests

```bash
# Basic import test
PYTHONPATH="E:/PROJECT/src" python -c "from ambientsaga import main"

# Science module test
PYTHONPATH="E:/PROJECT/src" python -c "
from ambientsaga.science import ScienceEngine
s = ScienceEngine()
print(f'Engines: {len(s.engines)}, Laws: {len(s.scientific_laws)}')
"
```

## Known Limitations

- Python 3.9 compatible (no `|` union syntax in type hints)
- WebSocket requires `websockets` library (fallback to polling if missing)
- LLM deliberation requires `ANTHROPIC_API_KEY` environment variable

## File Organization

```
src/ambientsaga/
├── __main__.py          # CLI entry point
├── main.py             # AmbientSaga main class
├── config.py           # Configuration system
├── types.py            # Core type definitions
├── agents/
│   ├── core.py         # Base agent class
│   ├── agent.py        # Full cognitive agent
│   ├── cognition.py    # Cognitive architecture
│   ├── tier.py         # Agent tier definitions
│   └── llm_queue.py    # Async LLM queue
├── world/
│   ├── state.py        # World state management
│   ├── terrain.py      # Terrain generation
│   ├── climate.py      # Climate simulation
│   ├── ecology.py      # Ecological simulation
│   └── ...
├── protocol/           # Emergent protocols
├── evolution/          # Self-evolution engine
├── science/            # Science framework
├── visualization/     # Web visualization
└── research/          # Metrics and analysis
```
