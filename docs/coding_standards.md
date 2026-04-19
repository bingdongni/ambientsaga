# AmbientSaga Coding Standards

This document outlines the coding standards and conventions for the AmbientSaga project.

## File Organization

```
src/ambientsaga/
├── __init__.py          # Package exports
├── __main__.py          # CLI entry point
├── config.py            # Configuration system
├── types.py             # Core type definitions
├── main.py              # Main class
├── agents/              # Agent system
│   ├── __init__.py
│   ├── core.py          # Base agent
│   ├── agent.py         # Full agent
│   ├── cognition.py     # Cognitive system
│   └── tier.py          # Agent tiers
├── world/               # World system
│   ├── __init__.py
│   ├── state.py         # World state
│   ├── terrain.py      # Terrain generation
│   └── ...
├── science/            # Science framework
├── protocol/            # Emergent protocols
├── scenarios/           # User scenarios
└── visualization/       # Visualization
```

## Import Conventions

### Standard imports order
1. Standard library
2. Third-party libraries
3. Local imports

```python
# standard library
import json
import time
from pathlib import Path
from typing import Any

# third-party
import numpy as np
from dataclasses import dataclass

# local
from ambientsaga.types import EntityID, Pos2D
from ambientsaga.config import Config
```

### TYPE_CHECKING
Use `TYPE_CHECKING` for imports only needed for type hints:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ambientsaga.agents.agent import Agent
```

## Type Hints

### Required for all public methods
```python
# Good
def get_agent(self, entity_id: EntityID) -> "Agent" | None: ...

# Bad - missing type hints
def get_agent(self, entity_id):
    ...
```

### Use union syntax for multiple types
```python
# Python 3.10+
def method(x: int | None) -> str | None: ...

# Alternative for Python 3.9 compatibility
from typing import Optional, Union
def method(x: Optional[int]) -> Optional[str]: ...
```

### Generic types
```python
from typing import Callable, Iterator

def filter_agents(self, func: Callable[[Agent], bool]) -> Iterator[Agent]: ...

def get_all_agents(self) -> list[Agent]: ...
```

## Docstrings

### Required for all public classes and methods

```python
class MyClass:
    """
    Brief description of the class.

    More detailed description if needed.

    Example:
        my_class = MyClass()
        result = my_class.method()
    """

    def my_method(self, param: str, optional: int = 10) -> bool:
        """
        Brief description of what the method does.

        Args:
            param: Description of param
            optional: Description of optional param (default: 10)

        Returns:
            Description of return value

        Raises:
            ValueError: When this exception is raised
        """
        pass
```

### Private methods can have simpler docstrings
```python
def _internal_method(self) -> None:
    """Internal helper method."""
    pass
```

## Naming Conventions

### Variables and Functions
- snake_case for variables and functions
- PascalCase for classes
- SCREAMING_SNAKE_CASE for constants

```python
# Variables
agent_count = 0
world_config = None

# Functions
def get_agent_count() -> int: ...
def save_world_state(path: str) -> None: ...

# Classes
class World:
class SimulationConfig:

# Constants
MAX_AGENTS = 10000
DEFAULT_TICK_RATE = 0.0
```

### Private Members
- Prefix with single underscore for private
- Double underscore triggers name mangling (avoid)

```python
class World:
    def __init__(self) -> None:
        self._config = None  # private
        self.__tick = 0      # name-mangled (avoid)
```

## Dataclasses

### Prefer @dataclass for data containers

```python
from dataclasses import dataclass, field

@dataclass
class AgentStats:
    """Statistics for an agent."""

    health: float = 1.0
    energy: float = 1.0
    wealth: float = 0.0

@dataclass
class WorldConfig:
    """Configuration for world generation."""

    width: int = 512
    height: int = 512
    seed: int | None = None
    options: dict[str, Any] = field(default_factory=dict)
```

## Error Handling

### Use specific exceptions
```python
# Good
raise ValueError(f"Invalid value: {value}")

# Bad
raise Exception(f"Invalid value: {value}")
```

### Consistent error messages
```
"Expected X, got Y"
"Value must be between A and B, got C"
"Entity not found: {id}"
```

## Properties

### Use @property for read-only access
```python
class World:
    @property
    def tick(self) -> int:
        """Current simulation tick."""
        return self._tick_engine.tick

    @property
    def agent_count(self) -> int:
        """Total number of agents."""
        return len(self._agents)
```

## Async Code

### Async functions should return awaitables
```python
async def fetch_data(self, url: str) -> dict[str, Any]:
    """Fetch data from URL."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()
```

## Testing

### Test file naming
```
tests/
├── test_world.py       # Tests for world module
├── test_agent.py        # Tests for agent module
└── test_integration.py # Integration tests
```

### Test class naming
```python
class TestWorld:
    def test_agent_creation(self) -> None:
        ...

    def test_agent_movement(self) -> None:
        ...
```

## Performance

### Use numpy for vectorized operations
```python
# Good
elevation = np.random.random((height, width))

# Bad
for y in range(height):
    for x in range(width):
        elevation[y, x] = random.random()
```

### Use slots for dataclasses with many instances
```python
@dataclass(slots=True)
class Agent:
    entity_id: EntityID
    name: str
    position: Pos2D
```

### Avoid unnecessary object creation
```python
# Good
agents = list(self._agents.values())

# Bad (creates unnecessary intermediate list)
agents = [a for a in self._agents.values()]
```

## Logging

### Use the standard logger
```python
import logging

logger = logging.getLogger(__name__)

def my_method() -> None:
    logger.debug("Detailed debug info")
    logger.info("User-facing info")
    logger.warning("Warning condition")
    logger.error("Error occurred")
```

## Thread Safety

### Document thread safety guarantees
```python
class World:
    """
    Thread Safety:
    All public methods are thread-safe and acquire _lock as needed.
    """

    def get_agent(self, entity_id: EntityID) -> Agent | None:
        """Thread-safe agent access."""
        with self._lock:
            return self._agents.get(entity_id)
```

## Deprecation

### When deprecating code
```python
import warnings

def old_method() -> None:
    """
    Deprecated: Use new_method instead.

    .. deprecated::
        This method will be removed in version 2.0.
        Use :meth:`new_method` instead.
    """
    warnings.warn(
        "old_method is deprecated, use new_method instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return new_method()
```

## Documentation

### Inline comments
- Use sparingly
- Explain WHY, not WHAT
- Don't state the obvious

```python
# Good: explain reasoning
# Use seeded RNG for reproducibility
rng = np.random.Generator(np.random.PCG64(seed))

# Bad: restate the code
# Increment counter
counter += 1
```

### Module docstrings
```python
"""
Module name — brief description.

Longer description of the module's purpose and contents.

Example:
    from ambientsaga.world import World
    world = World(config)
"""
```
