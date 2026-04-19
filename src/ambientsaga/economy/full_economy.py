"""
Economy System - Production, trade, markets, and resource flow.

Features:
- Production chains: resources → materials → goods → services
- Trade networks: local markets, long-distance trade, merchant routes
- Price dynamics: supply/demand, scarcity, quality, transport costs
- Specialization: agents develop skills, trade for other goods
- Wealth accumulation: savings, investment, economic growth

Academic value:
- Emergent economic patterns from agent behavior
- Trade network topology analysis
- Wealth distribution dynamics
- Labor specialization emergence

Engineering value:
- Event-driven market simulation
- Efficient price calculations
- Trade routing optimization
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from collections import defaultdict
from enum import Enum

if TYPE_CHECKING:
    from ambientsaga.agents.agent import Agent
    from ambientsaga.world.state import World


# ============================================================================
# Economic Types
# ============================================================================

class GoodType(Enum):
    """Categories of goods."""
    # Raw materials
    FOOD = "food"
    WATER = "water"
    WOOD = "wood"
    STONE = "stone"
    ORE = "ore"
    HERBS = "herbs"

    # Processed materials
    FLUR = "flour"
    MEAT = "meat"
    LEATHER = "leather"
    CLOTH = "cloth"
    IRON = "iron"
    COPPER = "copper"
    GOLD = "gold"
    MEDICINE = "medicine"

    # Finished goods
    TOOL = "tool"
    WEAPON = "weapon"
    ARMOR = "armor"
    POTTERY = "pottery"
    JEWELRY = "jewelry"
    FURNITURE = "furniture"

    # Services
    TRANSPORT = "transport"
    HEALING = "healing"
    TEACHING = "teaching"
    ENTERTAINMENT = "entertainment"
    PROTECTION = "protection"

    # Currency
    COIN = "coin"


class ProductionSkill(Enum):
    """Skills required for production."""
    GATHERING = "gathering"
    FARMING = "farming"
    HUNTING = "hunting"
    FISHING = "fishing"
    MINING = "mining"
    WOODWORKING = "woodworking"
    STONEMASONRY = "stonemasonry"
    METALWORK = "metalwork"
    LEATHERWORK = "leatherwork"
    WEAVING = "weaving"
    COOKING = "cooking"
    BREWING = "brewing"
    HERBALISM = "herbalism"
    HEALING = "healing"
    CARPENTRY = "carpentry"
    FORGING = "forging"
    JEWELRY_MAKING = "jewelry_making"
    TEACHING = "teaching"
    ENTERTAINMENT = "entertainment"
    LEADERSHIP = "leadership"


@dataclass
class Recipe:
    """A production recipe."""
    name: str
    skill_required: ProductionSkill
    skill_level: float  # 0-1
    inputs: dict[GoodType, float]  # inputs per unit output
    output_quantity: float = 1.0
    base_time: int = 10  # ticks
    quality_modifier: float = 1.0  # based on skill
    description: str = ""

    def get_input_value(self, prices: dict[GoodType, float]) -> float:
        """Calculate input cost."""
        total = 0.0
        for good, qty in self.inputs.items():
            total += qty * prices.get(good, 1.0)
        return total


# ============================================================================
# Production System
# ============================================================================

class ProductionSystem:
    """
    Manages all production in the world.

    Features:
    - Recipe database
    - Skill development
    - Quality modifiers
    - Production efficiency
    """

    # Recipe database
    RECIPES: dict[str, Recipe] = {}

    def __init__(self, world: World):
        self.world = world
        self._setup_recipes()

    def _setup_recipes(self) -> None:
        """Initialize all production recipes."""
        recipes = [
            # Food production
            Recipe("gather_food", ProductionSkill.GATHERING, 0.0,
                   {GoodType.WOOD: 0}, output_quantity=2.0, base_time=5,
                   description="Gather wild food"),
            Recipe("hunt", ProductionSkill.HUNTING, 0.2,
                   {}, output_quantity=3.0, base_time=20,
                   description="Hunt wild game"),
            Recipe("fish", ProductionSkill.FISHING, 0.1,
                   {}, output_quantity=2.5, base_time=15,
                   description="Catch fish"),
            Recipe("cook_meal", ProductionSkill.COOKING, 0.3,
                   {GoodType.FOOD: 1.0}, output_quantity=2.0, base_time=8,
                   description="Cook a meal"),
            Recipe("brew_ale", ProductionSkill.BREWING, 0.4,
                   {GoodType.FOOD: 2.0}, output_quantity=3.0, base_time=30,
                   description="Brew ale"),

            # Wood working
            Recipe("chop_wood", ProductionSkill.WOODWORKING, 0.0,
                   {}, output_quantity=2.0, base_time=10,
                   description="Chop wood"),
            Recipe("carve_wood", ProductionSkill.CARPENTRY, 0.3,
                   {GoodType.WOOD: 1.0}, output_quantity=1.0, base_time=15,
                   description="Carve wooden item"),
            Recipe("build_furniture", ProductionSkill.CARPENTRY, 0.5,
                   {GoodType.WOOD: 3.0}, output_quantity=1.0, base_time=40,
                   description="Build furniture"),

            # Stone working
            Recipe("mine_stone", ProductionSkill.MINING, 0.1,
                   {}, output_quantity=2.0, base_time=15,
                   description="Mine stone"),
            Recipe("carve_stone", ProductionSkill.STONEMASONRY, 0.4,
                   {GoodType.STONE: 1.5}, output_quantity=1.0, base_time=25,
                   description="Carve stone"),
            Recipe("build_wall", ProductionSkill.STONEMASONRY, 0.5,
                   {GoodType.STONE: 5.0}, output_quantity=1.0, base_time=60,
                   description="Build stone wall"),

            # Metal working
            Recipe("mine_ore", ProductionSkill.MINING, 0.3,
                   {}, output_quantity=1.5, base_time=20,
                   description="Mine ore"),
            Recipe("smelt_iron", ProductionSkill.METALWORK, 0.4,
                   {GoodType.ORE: 2.0}, output_quantity=1.0, base_time=30,
                   description="Smelt iron"),
            Recipe("forge_tool", ProductionSkill.FORGING, 0.5,
                   {GoodType.IRON: 1.0}, output_quantity=1.0, base_time=25,
                   description="Forge a tool"),
            Recipe("forge_weapon", ProductionSkill.FORGING, 0.7,
                   {GoodType.IRON: 2.0, GoodType.WOOD: 0.5}, output_quantity=1.0, base_time=40,
                   description="Forge a weapon"),
            Recipe("forge_armor", ProductionSkill.FORGING, 0.8,
                   {GoodType.IRON: 3.0, GoodType.LEATHER: 1.0}, output_quantity=1.0, base_time=60,
                   description="Forge armor"),

            # Leather work
            Recipe("tan_leather", ProductionSkill.LEATHERWORK, 0.3,
                   {GoodType.MEAT: 2.0}, output_quantity=1.0, base_time=20,
                   description="Tan leather"),
            Recipe("make_cloth", ProductionSkill.WEAVING, 0.4,
                   {GoodType.WOOD: 0.5}, output_quantity=2.0, base_time=25,
                   description="Weave cloth"),
            Recipe("tailor_clothes", ProductionSkill.WEAVING, 0.5,
                   {GoodType.CLOTH: 2.0}, output_quantity=1.0, base_time=30,
                   description="Tailor clothing"),

            # Medicine
            Recipe("gather_herbs", ProductionSkill.HERBALISM, 0.1,
                   {}, output_quantity=2.0, base_time=10,
                   description="Gather medicinal herbs"),
            Recipe("make_medicine", ProductionSkill.HERBALISM, 0.5,
                   {GoodType.HERBS: 2.0}, output_quantity=2.0, base_time=20,
                   description="Prepare medicine"),

            # Services
            Recipe("heal", ProductionSkill.HEALING, 0.6,
                   {GoodType.MEDICINE: 0.5}, output_quantity=1.0, base_time=15,
                   description="Provide healing"),
            Recipe("teach", ProductionSkill.TEACHING, 0.5,
                   {}, output_quantity=1.0, base_time=30,
                   description="Teach a skill"),
            Recipe("entertain", ProductionSkill.ENTERTAINMENT, 0.3,
                   {}, output_quantity=1.0, base_time=20,
                   description="Provide entertainment"),
            Recipe("protect", ProductionSkill.LEADERSHIP, 0.4,
                   {}, output_quantity=1.0, base_time=25,
                   description="Provide protection"),

            # Luxury goods
            Recipe("make_jewelry", ProductionSkill.JEWELRY_MAKING, 0.7,
                   {GoodType.GOLD: 1.0, GoodType.STONE: 0.5}, output_quantity=1.0, base_time=45,
                   description="Craft jewelry"),
            Recipe("make_pottery", ProductionSkill.CARPENTRY, 0.3,
                   {GoodType.STONE: 1.0}, output_quantity=2.0, base_time=20,
                   description="Make pottery"),
        ]

        for recipe in recipes:
            self.RECIPES[recipe.name] = recipe

    def can_produce(
        self,
        agent: Agent,
        recipe_name: str,
    ) -> bool:
        """Check if agent can produce using a recipe."""
        recipe = self.RECIPES.get(recipe_name)
        if not recipe:
            return False

        # Check skill level
        skill = agent.skills.get(recipe.skill_required.value, 0.0)
        if skill < recipe.skill_level:
            return False

        # Check inputs
        for good, qty in recipe.inputs.items():
            if agent.inventory.get(good, 0) < qty:
                return False

        return True

    def produce(
        self,
        agent: Agent,
        recipe_name: str,
    ) -> tuple[bool, str]:
        """
        Execute production.

        Returns (success, narrative).
        """
        recipe = self.RECIPES.get(recipe_name)
        if not recipe:
            return False, f"Unknown recipe: {recipe_name}"

        if not self.can_produce(agent, recipe_name):
            return False, "Cannot produce: insufficient skill or materials"

        # Consume inputs
        for good, qty in recipe.inputs.items():
            agent.inventory[good] = agent.inventory.get(good, 0) - qty

        # Calculate quality based on skill
        skill = agent.skills.get(recipe.skill_required.value, 0.0)
        quality = recipe.quality_modifier * (0.5 + skill * 0.5)
        quality = min(1.5, max(0.5, quality))  # Clamp 0.5-1.5

        # Produce output
        output_good = GoodType(recipe_name.split('_')[0].upper())
        # Map recipe to output type
        output_mapping = {
            "gather_food": GoodType.FOOD,
            "hunt": GoodType.MEAT,
            "fish": GoodType.FOOD,
            "cook_meal": GoodType.FOOD,
            "brew_ale": GoodType.FOOD,
            "chop_wood": GoodType.WOOD,
            "carve_wood": GoodType.TOOL,
            "build_furniture": GoodType.FURNITURE,
            "mine_stone": GoodType.STONE,
            "carve_stone": GoodType.POTTERY,
            "build_wall": GoodType.TOOL,
            "mine_ore": GoodType.ORE,
            "smelt_iron": GoodType.IRON,
            "forge_tool": GoodType.TOOL,
            "forge_weapon": GoodType.WEAPON,
            "forge_armor": GoodType.ARMOR,
            "tan_leather": GoodType.LEATHER,
            "make_cloth": GoodType.CLOTH,
            "tailor_clothes": GoodType.CLOTH,
            "gather_herbs": GoodType.HERBS,
            "make_medicine": GoodType.MEDICINE,
            "heal": GoodType.HEALING,
            "teach": GoodType.TEACHING,
            "entertain": GoodType.ENTERTAINMENT,
            "protect": GoodType.PROTECTION,
            "make_jewelry": GoodType.JEWELRY,
            "make_pottery": GoodType.POTTERY,
        }

        output = output_mapping.get(recipe_name, GoodType.FOOD)
        qty = recipe.output_quantity * quality
        agent.inventory[output] = agent.inventory.get(output, 0) + qty

        # Advance skill
        agent.skills[recipe.skill_required.value] = min(
            1.0, skill + 0.01 * quality
        )

        return True, f"Produced {qty:.1f} {output.value}"

    def get_available_recipes(self, agent: Agent) -> list[str]:
        """Get recipes agent can currently produce."""
        return [
            name for name in self.RECIPES
            if self.can_produce(agent, name)
        ]


# ============================================================================
# Market System
# ============================================================================

@dataclass
class MarketListing:
    """A single listing in a market."""
    seller_id: str
    good_type: GoodType
    quantity: float
    unit_price: float
    quality: float = 1.0
    tick_listed: int = 0


@dataclass
class Market:
    """A local market."""
    market_id: str
    name: str
    location_x: int
    location_y: int
    listings: list[MarketListing] = field(default_factory=list)
    trade_volume: dict[GoodType, float] = field(default_factory=dict)

    def get_price(self, good: GoodType) -> float | None:
        """Get average price for a good."""
        relevant = [l for l in self.listings if l.good_type == good]
        if not relevant:
            return None
        return sum(l.unit_price for l in relevant) / len(relevant)

    def add_listing(
        self,
        seller_id: str,
        good: GoodType,
        quantity: float,
        price: float,
        quality: float = 1.0,
        tick: int = 0,
    ) -> None:
        """Add a listing to the market."""
        self.listings.append(MarketListing(
            seller_id=seller_id,
            good_type=good,
            quantity=quantity,
            unit_price=price,
            quality=quality,
            tick_listed=tick,
        ))

    def execute_trade(
        self,
        buyer_id: str,
        listing_index: int,
    ) -> tuple[bool, str]:
        """Execute a trade."""
        if listing_index >= len(self.listings):
            return False, "Invalid listing"

        listing = self.listings[listing_index]
        if listing.quantity <= 0:
            return False, "No quantity available"

        # Execute trade (caller must handle inventory/wealth transfer)
        return True, f"Bought {listing.quantity} {listing.good_type.value} for {listing.unit_price * listing.quantity}"


class MarketSystem:
    """
    Manages all markets and trade.

    Features:
    - Multiple local markets
    - Price discovery
    - Supply/demand dynamics
    - Trade history and statistics
    """

    def __init__(self, world: World):
        self.world = world
        self.markets: dict[str, Market] = {}
        self._global_prices: dict[GoodType, list[float]] = defaultdict(list)

        # Base prices for each good type
        self._base_prices: dict[GoodType, float] = {
            GoodType.FOOD: 1.0,
            GoodType.WATER: 0.5,
            GoodType.WOOD: 1.0,
            GoodType.STONE: 1.0,
            GoodType.ORE: 3.0,
            GoodType.HERBS: 2.0,
            GoodType.FLUR: 2.0,
            GoodType.MEAT: 4.0,
            GoodType.LEATHER: 5.0,
            GoodType.CLOTH: 4.0,
            GoodType.IRON: 8.0,
            GoodType.COPPER: 5.0,
            GoodType.GOLD: 20.0,
            GoodType.MEDICINE: 6.0,
            GoodType.TOOL: 5.0,
            GoodType.WEAPON: 15.0,
            GoodType.ARMOR: 25.0,
            GoodType.POTTERY: 3.0,
            GoodType.JEWELRY: 30.0,
            GoodType.FURNITURE: 10.0,
            GoodType.COIN: 1.0,
        }

    def get_market(
        self,
        x: int,
        y: int,
        create: bool = True,
    ) -> Market | None:
        """Get or create market at location."""
        # Find nearest existing market within range
        search_radius = 50
        for market in self.markets.values():
            dx = market.location_x - x
            dy = market.location_y - y
            if dx * dx + dy * dy < search_radius * search_radius:
                return market

        if create:
            market_id = f"market_{len(self.markets)}"
            market = Market(
                market_id=market_id,
                name=f"Market at ({x}, {y})",
                location_x=x,
                location_y=y,
            )
            self.markets[market_id] = market
            return market

        return None

    def get_price(
        self,
        good: GoodType,
        x: int | None = None,
        y: int | None = None,
    ) -> float:
        """Get current price for a good."""
        # Local market price if location given
        if x is not None and y is not None:
            market = self.get_market(x, y, create=False)
            if market:
                price = market.get_price(good)
                if price:
                    return price

        # Use global average or base price
        if good in self._global_prices and self._global_prices[good]:
            avg = sum(self._global_prices[good]) / len(self._global_prices[good])
            return avg

        return self._base_prices.get(good, 5.0)

    def register_sale(
        self,
        good: GoodType,
        price: float,
        quantity: float,
    ) -> None:
        """Register a sale for price tracking."""
        self._global_prices[good].append(price)

        # Keep only last 1000 prices
        if len(self._global_prices[good]) > 1000:
            self._global_prices[good] = self._global_prices[good][-1000:]

    def list_item(
        self,
        seller_id: str,
        good: GoodType,
        quantity: float,
        price: float,
        x: int,
        y: int,
        quality: float = 1.0,
    ) -> bool:
        """List an item for sale in local market."""
        market = self.get_market(x, y)
        if not market:
            return False

        market.add_listing(
            seller_id=seller_id,
            good=good,
            quantity=quantity,
            price=price,
            quality=quality,
            tick=self.world.tick,
        )
        return True

    def buy_item(
        self,
        buyer_id: str,
        good: GoodType,
        max_price: float,
        quantity: float,
        x: int,
        y: int,
    ) -> tuple[bool, str, float]:
        """
        Try to buy an item from local market.

        Returns (success, narrative, actual_price).
        """
        market = self.get_market(x, y, create=False)
        if not market:
            return False, "No market nearby", 0.0

        # Find best listing (lowest price meeting criteria)
        best_idx = None
        best_price = None

        for idx, listing in enumerate(market.listings):
            if listing.good_type == good and listing.quantity >= quantity:
                if listing.unit_price <= max_price:
                    if best_price is None or listing.unit_price < best_price:
                        best_idx = idx
                        best_price = listing.unit_price

        if best_idx is None:
            return False, f"No {good.value} available within price range", 0.0

        listing = market.listings[best_idx]

        # Update listing
        listing.quantity -= quantity
        if listing.quantity < 0.01:
            market.listings.pop(best_idx)

        # Register sale for price tracking
        self.register_sale(good, listing.unit_price, quantity)

        return True, f"Bought {quantity} {good.value}", listing.unit_price

    def get_trade_summary(self) -> dict[str, Any]:
        """Get trade statistics."""
        total_trades = sum(
            sum(m.trade_volume.values())
            for m in self.markets.values()
        )

        return {
            "total_markets": len(self.markets),
            "total_listings": sum(len(m.listings) for m in self.markets.values()),
            "total_trade_volume": total_trades,
            "tracked_goods": len(self._global_prices),
            "average_prices": {
                good.value: self.get_price(good)
                for good in GoodType
            },
        }


# ============================================================================
# Economic Summary
# ============================================================================

def get_economic_stats(world: World) -> dict[str, Any]:
    """Get economic statistics for the world."""
    if not hasattr(world, '_production_system'):
        return {"status": "not initialized"}

    prod = world._production_system
    market = world._market_system

    return {
        "production": {
            "recipes_available": len(prod.RECIPES),
        },
        "markets": market.get_trade_summary(),
    }