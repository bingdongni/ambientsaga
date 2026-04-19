"""
Emergent Economics — economics arise from exchange history, not predefined markets.

Instead of a MarketSystem with fixed prices and trading rules, this module
analyzes the pattern of exchanges and extracts:
- Resource values (emergent prices)
- Trade patterns (emergent markets)
- Specialization (emergent professions)
- Currency (emergent medium of exchange)
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ambientsaga.protocol.interaction import Exchange


@dataclass
class TradePattern:
    """A recurring exchange pattern detected in history."""
    resource_given: str
    resource_received: str
    count: int
    avg_ratio: float        # given/received ratio
    participants: set[str]  # agents who engaged in this pattern
    volatility: float       # how variable is the ratio

    @property
    def is_stable(self) -> bool:
        return self.count >= 5 and self.volatility < 0.5


@dataclass
class EmergentMarket:
    """A market-like pattern detected from exchange history."""
    resource: str
    trade_partners: list[str]  # agents who trade this resource
    detected_at_tick: int
    avg_transaction_size: float
    total_volume: float
    price_trend: list[float]    # Recent prices over time

    @property
    def participant_count(self) -> int:
        return len(self.trade_partners)


class EmergentEconomy:
    """
    No predefined prices, no predefined markets. Economy emerges from exchange patterns.
    """

    def __init__(self, world) -> None:
        self.world = world
        self._exchange_history: list[Exchange] = []
        self._max_exchanges = 200_000

        # Computed caches (refreshed periodically)
        self._resource_values: dict[str, float] = {}  # resource -> avg value
        self._trade_patterns: list[TradePattern] = []
        self._emergent_markets: list[EmergentMarket] = []
        self._currency_candidates: dict[str, float] = {}  # resource -> currency_score
        self._specialization: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        # agent_id -> {resource_type: production_score}

        # Wealth tracking
        self._wealth_history: dict[str, list[float]] = defaultdict(list)

    def process_exchange(self, exchange: Exchange) -> None:
        """Process a new exchange and update economic state."""
        self._exchange_history.append(exchange)
        if len(self._exchange_history) > self._max_exchanges:
            self._exchange_history = self._exchange_history[-self._max_exchanges // 2:]

        # Update specialization tracking
        for resource, amount in exchange.given.items():
            self._specialization[exchange.giver_id][resource] += amount
        for resource, amount in exchange.received.items():
            # Receiving resources might indicate consumption need
            pass

        # Track wealth
        giver_wealth = getattr(self.world.get_agent(exchange.giver_id), 'wealth', 100.0) if self.world.get_agent(exchange.giver_id) else 100.0
        self._wealth_history[exchange.giver_id].append(giver_wealth)
        if len(self._wealth_history[exchange.giver_id]) > 100:
            self._wealth_history[exchange.giver_id] = self._wealth_history[exchange.giver_id][-100:]

    def get_resource_value(self, resource: str, agent_id: str | None = None,
                          lookback: int = 500) -> float:
        """
        Get the emergent value of a resource.
        Value is computed from exchange history: how much of other resources
        does one unit of this resource typically buy?
        """
        recent = self._exchange_history[-lookback:]
        if not recent:
            return 1.0  # Default value

        # Find exchanges involving this resource
        relevant = [e for e in recent if resource in e.given or resource in e.received]
        if not relevant:
            return self._resource_values.get(resource, 1.0)

        # Calculate implied exchange ratios
        ratios = []
        for e in relevant:
            if resource in e.given:
                given_amt = e.given[resource]
                received_amt = sum(v for k, v in e.received.items() if k != "gratitude")
                if received_amt > 0 and given_amt > 0:
                    # How many units of other resources per unit of this resource
                    ratios.append(received_amt / given_amt)
            elif resource in e.received:
                received_amt = e.received[resource]
                given_amt = sum(v for k, v in e.given.items() if k != "gratitude")
                if received_amt > 0 and given_amt > 0:
                    ratios.append(received_amt / given_amt)

        if ratios:
            avg = sum(ratios) / len(ratios)
            # Update cache
            self._resource_values[resource] = avg
            return avg
        return self._resource_values.get(resource, 1.0)

    def detect_trade_patterns(self, lookback: int = 1000) -> list[TradePattern]:
        """
        Detect recurring exchange patterns. When the same two resources are
        exchanged repeatedly between agents at similar ratios, a "market" pattern
        emerges.
        """
        recent = self._exchange_history[-lookback:]
        patterns: dict[tuple[str, str], list[Exchange]] = defaultdict(list)

        for e in recent:
            for rg in e.given:
                if rg == "gratitude":
                    continue
                for rr in e.received:
                    if rr == "gratitude":
                        continue
                    key = (rg, rr)
                    patterns[key].append(e)

        results = []
        for (rg, rr), exchanges in patterns.items():
            if len(exchanges) < 3:
                continue

            # Calculate ratio
            ratios = []
            participants = set()
            for e in exchanges:
                given_amt = e.given.get(rg, 0)
                received_amt = e.received.get(rr, 0)
                if given_amt > 0 and received_amt > 0:
                    ratios.append(received_amt / given_amt)
                    participants.add(e.giver_id)
                    participants.add(e.receiver_id)

            if len(ratios) < 3:
                continue

            avg_ratio = sum(ratios) / len(ratios)
            variance = sum((r - avg_ratio) ** 2 for r in ratios) / len(ratios)
            volatility = variance ** 0.5 / max(avg_ratio, 0.001)

            results.append(TradePattern(
                resource_given=rg,
                resource_received=rr,
                count=len(exchanges),
                avg_ratio=avg_ratio,
                participants=participants,
                volatility=volatility,
            ))

        # Sort by stability and count
        results.sort(key=lambda p: (-p.count, p.volatility))
        self._trade_patterns = results[:20]
        return self._trade_patterns

    def detect_markets(self, lookback: int = 500) -> list[EmergentMarket]:
        """
        Detect market-like patterns: resources being traded by multiple agents
        with some regularity.
        """
        recent = self._exchange_history[-lookback:]
        resource_participants: dict[str, set[str]] = defaultdict(set)
        resource_volumes: dict[str, list[float]] = defaultdict(list)

        for e in recent:
            for resource, amount in e.given.items():
                if resource != "gratitude":
                    resource_participants[resource].add(e.giver_id)
                    resource_participants[resource].add(e.receiver_id)
                    resource_volumes[resource].append(amount)
            for resource, amount in e.received.items():
                if resource != "gratitude":
                    resource_participants[resource].add(e.giver_id)
                    resource_participants[resource].add(e.receiver_id)

        markets = []
        for resource, participants in resource_participants.items():
            if len(participants) >= 3:
                volumes = resource_volumes.get(resource, [1.0])
                markets.append(EmergentMarket(
                    resource=resource,
                    trade_partners=list(participants)[:20],
                    detected_at_tick=self.world.tick,
                    avg_transaction_size=sum(volumes) / len(volumes),
                    total_volume=sum(volumes),
                    price_trend=[self.get_resource_value(resource)],
                ))

        markets.sort(key=lambda m: -m.total_volume)
        self._emergent_markets = markets[:10]
        return self._emergent_markets

    def detect_currency(self, lookback: int = 1000) -> list[tuple[str, float]]:
        """
        Detect which resources function as currency (medium of exchange).
        A resource becomes currency-like when it's frequently used to
        measure value in exchanges.
        """
        recent = self._exchange_history[-lookback:]
        if len(recent) < 10:
            return []

        # Count how often each resource appears in exchanges
        resource_frequency: dict[str, int] = defaultdict(int)
        for e in recent:
            for r in e.given:
                if r != "gratitude":
                    resource_frequency[r] += 1
            for r in e.received:
                if r != "gratitude":
                    resource_frequency[r] += 1

        # Score by how evenly distributed its usage is
        currency_scores = {}
        for resource, freq in resource_frequency.items():
            if freq < 5:
                continue
            # Currency should appear in many different exchanges
            unique_exchanges = len(set(
                e.trace_id for e in recent
                if resource in e.given or resource in e.received
            ))
            # Currency should appear in diverse pairs
            pairs = set()
            for e in recent:
                if resource in e.given:
                    pairs.add(resource + "_vs_" + "_".join(k for k in e.received if k != "gratitude"))
                elif resource in e.received:
                    pairs.add("_".join(k for k in e.given if k != "gratitude") + "_vs_" + resource)
            pair_diversity = len(pairs)
            score = (freq / len(recent)) * (unique_exchanges / len(recent)) * min(pair_diversity / 3, 1.0)
            currency_scores[resource] = score

        ranked = sorted(currency_scores.items(), key=lambda x: -x[1])[:5]
        self._currency_candidates = dict(ranked)
        return ranked

    def get_specialization(self, agent_id: str | None = None) -> dict:
        """Get specialization data for an agent or all agents."""
        if agent_id:
            return dict(self._specialization.get(agent_id, {}))
        # Return top specializations across all agents
        all_specs: dict[str, list[tuple[str, float]]] = defaultdict(list)
        for aid, specs in self._specialization.items():
            for resource, amount in specs.items():
                all_specs[resource].append((aid, amount))
        result = {}
        for resource, items in all_specs.items():
            items.sort(key=lambda x: -x[1])
            result[resource] = [(aid, amt) for aid, amt in items[:5]]
        return result

    def get_wealth_ranking(self, limit: int = 10) -> list[tuple[str, float]]:
        """Get wealth ranking based on current agent wealth."""
        rankings = []
        for agent_id in self._wealth_history:
            agent = self.world.get_agent(agent_id)
            if agent:
                wealth = getattr(agent, 'wealth', 100.0)
                rankings.append((agent.name, wealth))
        return sorted(rankings, key=lambda x: -x[1])[:limit]

    def get_aggregate_stats(self) -> dict:
        """Get aggregate economic statistics."""
        if not self._exchange_history:
            return {
                "total_exchanges": 0,
                "active_agents": 0,
                "emergent_markets": 0,
                "trade_patterns": 0,
                "currency_candidates": [],
            }
        return {
            "total_exchanges": len(self._exchange_history),
            "active_agents": len(set(e.giver_id for e in self._exchange_history[-500:])
                                | set(e.receiver_id for e in self._exchange_history[-500:])),
            "emergent_markets": len(self._emergent_markets),
            "trade_patterns": len(self._trade_patterns),
            "currency_candidates": self.detect_currency(200),
            "top_markets": [(m.resource, m.total_volume) for m in self._emergent_markets[:5]],
            "wealthiest": self.get_wealth_ranking(5),
        }
