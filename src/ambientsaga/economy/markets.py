"""
Market system — economic exchange and price formation.

Models:
- Supply and demand
- Price formation and adjustment
- Trade matching
- Regional markets
- Currency and wealth distribution
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from ambientsaga.config import EconomyConfig
from ambientsaga.types import EntityID, Pos2D, ResourceType, Transaction

if TYPE_CHECKING:
    from ambientsaga.world.state import World


@dataclass
class Market:
    """A local market for goods exchange."""

    market_id: str
    position: Pos2D
    region_name: str = ""

    def __post_init__(self) -> None:
        self.prices: dict[ResourceType, float] = {}
        self.supply: dict[ResourceType, float] = {}
        self.demand: dict[ResourceType, float] = {}
        self.volume: dict[ResourceType, float] = {}  # Trade volume this tick
        self.transactions: list[Transaction] = []

        # Initialize prices
        for rt in ResourceType:
            if rt.value > 0:
                self.prices[rt] = self._base_price(rt)

    def _base_price(self, resource: ResourceType) -> float:
        """Get base price for a resource type."""
        base_prices = {
            ResourceType.FOOD: 1.0,
            ResourceType.WATER: 0.5,
            ResourceType.WOOD: 2.0,
            ResourceType.STONE: 1.5,
            ResourceType.TOOLS: 10.0,
            ResourceType.WEAPONS: 20.0,
            ResourceType.CLOTHING: 8.0,
            ResourceType.COPPER: 15.0,
            ResourceType.IRON: 25.0,
            ResourceType.GOLD: 100.0,
        }
        return base_prices.get(resource, 5.0)


class MarketSystem:
    """
    Economic market simulation.

    Key features:
    - Regional markets with local prices
    - Supply-demand price adjustment
    - Trade matching between agents
    - Wealth tracking and Gini calculation
    """

    def __init__(
        self, config: EconomyConfig, world: World, seed: int = 42
    ) -> None:
        self.config = config
        self.world = world
        self._rng = np.random.Generator(np.random.PCG64(seed))

        # Markets
        self._markets: dict[str, Market] = {}
        self._create_regional_markets()

        # Global statistics
        self._total_transactions = 0
        self._total_trade_volume = 0.0
        self._price_history: list[dict[ResourceType, float]] = []

    def _create_regional_markets(self) -> None:
        """Create regional markets across the world."""
        w = self.world._config.world.width
        h = self.world._config.world.height
        num_regions = 16

        # Divide world into grid regions
        cols = int(num_regions ** 0.5)
        rows = cols
        region_w = w // cols
        region_h = h // rows

        idx = 0
        for r in range(rows):
            for c in range(cols):
                cx = c * region_w + region_w // 2
                cy = r * region_h + region_h // 2
                region_name = f"Region_{idx}"
                market = Market(
                    market_id=f"market_{c}_{r}",
                    position=Pos2D(cx, cy),
                    region_name=region_name,
                )
                self._markets[market.market_id] = market
                idx += 1

    def update(self, tick: int) -> None:
        """Update markets for the current tick."""
        # Process trades
        self._process_trades(tick)

        # Update prices based on supply/demand
        self._adjust_prices()

        # Record price history
        if tick % 100 == 0:
            self._record_prices()

    def _process_trades(self, tick: int) -> None:
        """Process trade requests from agents."""
        # Simple trade matching: find buyer-seller pairs
        for market in self._markets.values():
            for resource, price in list(market.prices.items()):
                # Simple: random trade probability
                if self._rng.random() < 0.001:  # 0.1% chance per tick per resource
                    buyer_id = self._find_buyer(market)
                    seller_id = self._find_seller(market, resource)

                    if buyer_id and seller_id:
                        buyer = self.world.get_agent(buyer_id)
                        seller = self.world.get_agent(seller_id)

                        if buyer and seller:
                            quantity = self._rng.uniform(1, 10)
                            total_price = price * quantity

                            if buyer.wealth >= total_price:
                                # Execute trade
                                buyer.wealth -= total_price
                                seller.wealth += total_price * (1.0 - self.config.trade_transaction_cost)

                                tx = Transaction(
                                    tick=tick,
                                    buyer_id=buyer_id,
                                    seller_id=seller_id,
                                    resource=resource,
                                    quantity=quantity,
                                    unit_price=price,
                                    total_value=total_price,
                                )
                                market.transactions.append(tx)
                                self._total_transactions += 1
                                self._total_trade_volume += total_price

                                # Update market supply/demand
                                market.supply[resource] = max(0, market.supply.get(resource, 0) - quantity)
                                market.demand[resource] = max(0, market.demand.get(resource, 0) + quantity)

    def _find_buyer(self, market: Market) -> EntityID | None:
        """Find a potential buyer near a market."""
        x, y = market.position.x, market.position.y
        for agent, _dist in self.world.get_agents_near(Pos2D(x, y), 20.0):
            if agent.wealth > 10.0 and self._rng.random() < 0.01:
                return agent.entity_id
        return None

    def _find_seller(self, market: Market, resource: ResourceType) -> EntityID | None:
        """Find a potential seller of a resource near a market."""
        x, y = market.position.x, market.position.y
        for agent, _dist in self.world.get_agents_near(Pos2D(x, y), 20.0):
            if agent.inventory.has(resource):
                if self._rng.random() < 0.01:
                    return agent.entity_id
        return None

    def _adjust_prices(self) -> None:
        """Adjust prices based on supply and demand."""
        for market in self._markets.values():
            for resource in market.prices:
                supply = market.supply.get(resource, 100.0)
                demand = market.demand.get(resource, 50.0)

                if supply > 0 and demand > 0:
                    # Price adjusts toward equilibrium
                    ratio = demand / supply
                    adjustment = self.config.price_adjustment_speed * (ratio - 1.0)
                    market.prices[resource] *= (1.0 + adjustment)

                    # Keep prices within reasonable bounds
                    market.prices[resource] = max(0.1, min(1000.0, market.prices[resource]))

                # Decay supply and demand
                market.supply[resource] *= 0.99
                market.demand[resource] *= 0.99

    def _record_prices(self) -> None:
        """Record current prices for historical tracking."""
        # Record average prices across all markets
        avg_prices: dict[ResourceType, float] = {}
        for market in self._markets.values():
            for resource, price in market.prices.items():
                if resource not in avg_prices:
                    avg_prices[resource] = []
                avg_prices[resource].append(price)

        self._price_history.append({
            r: sum(ps) / len(ps) for r, ps in avg_prices.items() if ps
        })

    def get_market(self, market_id: str) -> Market | None:
        """Get a market by ID."""
        return self._markets.get(market_id)

    def get_market_near(self, pos: Pos2D) -> Market | None:
        """Get the nearest market to a position."""
        nearest = None
        min_dist = float("inf")
        for market in self._markets.values():
            dist = pos.euclidean_distance(market.position)
            if dist < min_dist:
                min_dist = dist
                nearest = market
        return nearest

    def compute_gini(self) -> float:
        """Compute the Gini coefficient of wealth distribution."""
        wealths = [a.wealth for a in self.world.get_all_agents() if a.is_alive]
        if not wealths:
            return 0.0

        wealths = sorted(wealths)
        n = len(wealths)
        mean = sum(wealths) / n

        if mean == 0:
            return 0.0

        # Gini = sum(|xi - xj|) / (2 * n^2 * mean)
        total_diff = 0.0
        for i in range(n):
            total_diff += abs(wealths[i] - mean) * n - 2 * sum(wealths[:i])

        return total_diff / (n * n * mean)

    def get_stats(self) -> dict:
        """Get economic statistics."""
        return {
            "total_markets": len(self._markets),
            "total_transactions": self._total_transactions,
            "total_trade_volume": self._total_trade_volume,
            "gini_coefficient": self.compute_gini(),
            "price_history_length": len(self._price_history),
        }
