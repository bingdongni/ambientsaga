"""
Tick Engine — simulation time advancement system.

Manages the simulation clock with support for:
- Variable tick rates
- Pause/resume
- Time acceleration and deceleration
- Season and year tracking
- Deterministic replay
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Iterator


@dataclass
class TickState:
    """Immutable state at a specific tick."""

    tick: int
    season_index: int  # 0=SPRING, 1=SUMMER, 2=AUTUMN, 3=WINTER
    year: int
    day: int
    tick_in_day: int  # Ticks since midnight
    is_paused: bool
    time_scale: float  # Multiplier for tick rate


class TickEngine:
    """
    Manages simulation time and tick execution.

    The tick engine provides:
    - Precise tick counting
    - Real-time pacing control
    - Season and calendar tracking
    - Pause/resume/seek functionality
    - Deterministic tick ordering

    Architecture:
    Each tick is divided into phases that run in order:
    1. PHASE_WORLD_UPDATE — Update world state (weather, resources, etc.)
    2. PHASE_ECOLOGY — Process ecological systems
    3. PHASE_AGENT_PERCEPTION — Agents perceive signals
    4. PHASE_AGENT_DECISION — Agents make decisions
    5. PHASE_AGENT_ACTION — Agents execute actions
    6. PHASE_SOCIAL — Process social interactions
    7. PHASE_ECONOMY — Process economic transactions
    8. PHASE_DISASTERS — Process natural disasters
    9. PHASE_HISTORY — Record historical events
    10. PHASE_METRICS — Collect metrics
    """

    TICK_PHASES = [
        "WORLD_UPDATE",
        "ECOLOGY",
        "AGENT_PERCEPTION",
        "AGENT_DECISION",
        "AGENT_ACTION",
        "SOCIAL",
        "ECONOMY",
        "POLITICAL",
        "CULTURE",
        "DISASTERS",
        "HISTORY",
        "METRICS",
        "EMERGENCE_SYSTEMS",  # NEW: Run enhanced emergence and causal systems
    ]

    TICKS_PER_DAY = 1  # 1 tick = 1 day (default)
    TICKS_PER_SEASON = 360  # 360 days per season
    DAYS_PER_YEAR = TICKS_PER_SEASON * 4  # 1440 days
    HOURS_PER_DAY = 24

    def __init__(
        self,
        tick_rate: float = 1.0,
        start_tick: int = 0,
    ) -> None:
        self._tick = start_tick
        self._tick_rate = tick_rate
        self._time_scale = 1.0
        self._is_paused = False
        self._is_running = False
        self._auto_terminate_at: int | None = None

        # Phase callbacks: phase_name -> list of callbacks
        self._phase_callbacks: dict[str, list[Callable[[int], None]]] = {
            phase: [] for phase in self.TICK_PHASES
        }

        # Performance tracking
        self._tick_durations: dict[str, list[float]] = {
            phase: [] for phase in self.TICK_PHASES
        }
        self._last_real_time = time.monotonic()
        self._total_real_time_elapsed = 0.0

        # Deterministic mode
        self._deterministic = False
        self._deterministic_rng_state: dict | None = None

    # -------------------------------------------------------------------------
    # Time Properties
    # -------------------------------------------------------------------------

    @property
    def tick(self) -> int:
        return self._tick

    @tick.setter
    def tick(self, value: int) -> None:
        """Set the current tick (use seek() for normal operations)."""
        if value < 0:
            raise ValueError("tick must be non-negative")
        self._tick = value

    @property
    def year(self) -> int:
        return self._tick // self.DAYS_PER_YEAR

    @property
    def day(self) -> int:
        return self._tick % self.DAYS_PER_YEAR

    @property
    def season_index(self) -> int:
        return (self._tick % self.DAYS_PER_YEAR) // self.TICKS_PER_SEASON

    @property
    def tick_in_day(self) -> int:
        return self._tick % self.HOURS_PER_DAY

    @property
    def season(self) -> str:
        seasons = ["SPRING", "SUMMER", "AUTUMN", "WINTER"]
        return seasons[self.season_index]

    @property
    def tick_rate(self) -> float:
        return self._tick_rate

    @property
    def time_scale(self) -> float:
        return self._time_scale

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    @property
    def is_running(self) -> bool:
        return self._is_running

    # -------------------------------------------------------------------------
    # Control Methods
    # -------------------------------------------------------------------------

    def pause(self) -> None:
        """Pause the simulation."""
        self._is_paused = True

    def resume(self) -> None:
        """Resume the simulation."""
        self._is_paused = False

    def toggle_pause(self) -> bool:
        """Toggle pause state. Returns new pause state."""
        self._is_paused = not self._is_paused
        return self._is_paused

    def set_time_scale(self, scale: float) -> None:
        """Set the time scale multiplier (0.0 = pause, >1.0 = fast)."""
        if scale < 0:
            raise ValueError(f"time_scale must be non-negative, got {scale}")
        self._time_scale = scale
        if scale == 0:
            self._is_paused = True

    def set_tick_rate(self, rate: float) -> None:
        """Set the target tick rate (ticks per second, 0 = unlimited/no sleep)."""
        if rate < 0:
            raise ValueError(f"tick_rate must be non-negative, got {rate}")
        self._tick_rate = rate

    def seek(self, tick: int) -> None:
        """Jump to a specific tick (not all systems support this)."""
        if tick < 0:
            raise ValueError(f"tick must be non-negative, got {tick}")
        self._tick = tick

    def set_auto_terminate(self, tick: int | None) -> None:
        """Set the tick at which simulation auto-terminates."""
        self._auto_terminate_at = tick

    def enable_deterministic(self) -> None:
        """Enable deterministic mode (for reproducible experiments)."""
        self._deterministic = True

    def disable_deterministic(self) -> None:
        """Disable deterministic mode."""
        self._deterministic = False

    # -------------------------------------------------------------------------
    # Phase Management
    # -------------------------------------------------------------------------

    def register_phase_callback(
        self,
        phase: str,
        callback: Callable[[int], None],
    ) -> None:
        """Register a callback for a specific phase."""
        if phase not in self._phase_callbacks:
            raise ValueError(f"Unknown phase: {phase}. Available: {self.TICK_PHASES}")
        self._phase_callbacks[phase].append(callback)

    def unregister_phase_callback(
        self,
        phase: str,
        callback: Callable[[int], None],
    ) -> None:
        """Remove a phase callback."""
        if phase in self._phase_callbacks:
            try:
                self._phase_callbacks[phase].remove(callback)
            except ValueError:
                pass

    def get_state(self) -> TickState:
        """Get current tick state."""
        return TickState(
            tick=self._tick,
            season_index=self.season_index,
            year=self.year,
            day=self.day,
            tick_in_day=self.tick_in_day,
            is_paused=self._is_paused,
            time_scale=self._time_scale,
        )

    # -------------------------------------------------------------------------
    # Main Tick Loop
    # -------------------------------------------------------------------------

    def tick_once(self) -> bool:
        """
        Execute one tick of simulation.

        Returns True if tick was executed, False if paused or terminated.
        """
        if self._is_paused:
            return False

        if (
            self._auto_terminate_at is not None
            and self._tick >= self._auto_terminate_at
        ):
            self._is_running = False
            return False

        real_start = time.monotonic()

        # Execute each phase in order
        for phase in self.TICK_PHASES:
            phase_start = time.monotonic()

            for callback in self._phase_callbacks.get(phase, []):
                try:
                    callback(self._tick)
                except Exception:
                    # Log but don't stop the simulation
                    pass

            phase_duration = time.monotonic() - phase_start
            self._tick_durations[phase].append(phase_duration)

            # Keep last 100 durations per phase
            if len(self._tick_durations[phase]) > 100:
                self._tick_durations[phase] = self._tick_durations[phase][-100:]

        self._tick += 1

        # Real time management
        real_elapsed = time.monotonic() - real_start
        self._total_real_time_elapsed += real_elapsed

        # Sleep to maintain tick rate (if not in benchmark mode)
        if self._tick_rate > 0 and self._time_scale > 0:
            target_interval = self._time_scale / self._tick_rate
            if real_elapsed < target_interval:
                time.sleep(target_interval - real_elapsed)

        self._last_real_time = time.monotonic()
        return True

    def run(
        self,
        max_ticks: int | None = None,
        progress_callback: Callable[[int, TickState], None] | None = None,
    ) -> int:
        """
        Run the simulation loop.

        Returns the final tick number.
        """
        self._is_running = True
        self._is_paused = False
        terminate_at = max_ticks if max_ticks else self._auto_terminate_at

        while self._is_running:
            if terminate_at is not None and self._tick >= terminate_at:
                break

            executed = self.tick_once()
            if executed and progress_callback is not None:
                progress_callback(self._tick, self.get_state())

        self._is_running = False
        return self._tick

    def stop(self) -> None:
        """Stop the simulation loop."""
        self._is_running = False

    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------

    def get_performance_stats(self) -> dict:
        """Get tick performance statistics."""
        stats = {}
        for phase, durations in self._tick_durations.items():
            if durations:
                stats[phase] = {
                    "mean_ms": sum(durations) / len(durations) * 1000,
                    "max_ms": max(durations) * 1000,
                    "min_ms": min(durations) * 1000,
                    "count": len(durations),
                }
        return {
            "total_ticks": self._tick,
            "total_real_time_s": self._total_real_time_elapsed,
            "avg_tick_rate": (
                self._tick / self._total_real_time_elapsed
                if self._total_real_time_elapsed > 0
                else 0
            ),
            "phases": stats,
        }

    def get_calendar_string(self) -> str:
        """Get human-readable calendar string."""
        return (
            f"Year {self.year}, {self.season}, Day {self.day % self.TICKS_PER_SEASON + 1}"
        )

    def __repr__(self) -> str:
        return (
            f"TickEngine(tick={self._tick}, year={self.year}, "
            f"season={self.season}, rate={self._tick_rate} t/s)"
        )
