"""
Cognitive Architecture - Agent deliberation and reasoning system.

Provides tiered cognitive capabilities:
- L1_CORE: Full LLM-powered deliberation with memory, reflection, and planning
- L2_FUNCTIONAL: Sophisticated rule-based with emotional state and social awareness
- L3_BACKGROUND: Reactive behavior with habit memory

The cognitive loop:
1. PERCEIVE: Gather sensory input from environment
2. REMEMBER: Retrieve relevant memories
3. DELIBERATE: Form goals and evaluate options
4. PLAN: Create action sequences
5. ACT: Execute the chosen action
6. REFLECT: Update memories and emotional state
"""

from __future__ import annotations

import time
import json
import asyncio
import hashlib
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING
from enum import Enum
import random

if TYPE_CHECKING:
    from ambientsaga.agents.agent import Agent
    from ambientsaga.world.state import World


# ============================================================================
# Cognitive State Types
# ============================================================================

class EmotionalState(Enum):
    """Agent emotional states."""
    CALM = "calm"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    FEARFUL = "fearful"
    HOPEFUL = "hopeful"
    CURIOUS = "curious"
    LONELY = "lonely"
    EXCITED = "excited"
    CONTENT = "content"


class DeliberationMode(Enum):
    """Mode of agent deliberation."""
    REACTIVE = "reactive"        # Immediate response to stimulus
    DELIBERATE = "deliberate"    # Goal-directed planning
    REFLECTIVE = "reflective"    # Thinking about thinking
    NARRATIVE = "narrative"       # Story-driven action


@dataclass
class CognitiveContext:
    """Complete context for agent cognition."""
    # What the agent perceives
    nearby_agents: list[dict] = field(default_factory=list)
    nearby_resources: list[dict] = field(default_factory=list)
    terrain_type: str = "unknown"
    temperature: float = 15.0
    humidity: float = 0.5
    vegetation: float = 0.0
    elevation: float = 0.0

    # Social context
    social_density: float = 0.0  # How many others nearby
    threat_level: float = 0.0      # Danger assessment
    opportunity_level: float = 0.0  # Resource abundance

    # Temporal context
    time_of_day: str = "day"
    season: str = "spring"
    year: int = 0


@dataclass
class Goal:
    """An active goal an agent is pursuing."""
    goal_id: str
    description: str
    priority: float = 0.5  # 0-1
    progress: float = 0.0  # 0-1
    created_tick: int = 0
    plan_steps: list[str] = field(default_factory=list)
    plan_index: int = 0
    abandoned: bool = False
    parent_goal_id: str | None = None

    def is_complete(self) -> bool:
        return self.progress >= 1.0 or self.abandoned

    def advance_plan(self) -> str | None:
        """Get the next step in the plan."""
        if self.plan_index < len(self.plan_steps):
            step = self.plan_steps[self.plan_index]
            self.plan_index += 1
            return step
        return None


@dataclass
class MemoryEntry:
    """A memory entry with rich metadata."""
    tick: int
    content: str
    memory_type: str = "episodic"  # episodic, semantic, procedural
    emotional_valence: float = 0.0  # -1 negative to +1 positive
    importance: float = 0.5  # 0-1
    vividness: float = 1.0  # fades over time
    entities: list[str] = field(default_factory=list)  # other agents involved
    location: tuple[int, int] | None = None
    tags: list[str] = field(default_factory=list)

    def decay(self, ticks: int = 1) -> None:
        """Apply memory decay over time."""
        decay_factor = 0.995 ** ticks
        self.vividness *= decay_factor
        self.importance = max(0.0, self.importance - 0.001 * ticks)


@dataclass
class SocialPerception:
    """What an agent perceives about another agent."""
    agent_id: str
    agent_name: str
    distance: float
    relationship_trust: float = 0.0
    relationship_affiliation: float = 0.0
    body_language: str = "neutral"  # aggressive, fearful, friendly, neutral
    expressed_emotion: EmotionalState = EmotionalState.CALM
    known_for: list[str] = field(default_factory=list)  # reputation markers
    org_memberships: list[str] = field(default_factory=list)


# ============================================================================
# LLM Integration
# ============================================================================

class LLMDeliberator:
    """
    LLM-powered deliberation system for L1_CORE agents.

    Uses a structured prompting approach that:
    1. Builds rich context from agent state + memories + environment
    2. Calls LLM for goal formation and action planning
    3. Caches results and uses fallback for rate limiting

    Falls back to sophisticated rule-based reasoning when LLM is unavailable.
    Supports both sync and async operation via AsyncLLMQueue.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-20250514",
        batch_size: int = 10,
        use_async: bool = True,
    ):
        self.api_key = api_key
        self.model = model
        self.batch_size = batch_size
        self._call_count = 0
        self._total_tokens = 0
        self._last_call_time = 0.0
        self._rate_limit_calls_per_minute = 60
        self._cache: dict[str, dict] = {}

        # Async queue for scalable LLM calls
        self._async_queue = None
        if use_async and api_key:
            try:
                from ambientsaga.agents.llm_queue import AsyncLLMQueue
                self._async_queue = AsyncLLMQueue(
                    api_key=api_key,
                    model=model,
                    calls_per_minute=60,
                    num_workers=4,
                )
            except ImportError:
                pass

        # Prompt templates
        self._system_prompt = """You are an agent in a simulated world. Think deeply about your decisions. Consider:
1. Your current needs (hunger, thirst, safety, belonging, esteem)
2. Your personality and values
3. Your relationships with others
4. Your goals and plans
5. The current situation and environment

Be thoughtful, consistent, and true to your character's personality. Your decisions should feel like a real person would make them."""

    async def start_async(self) -> None:
        """Start the async LLM queue."""
        if self._async_queue:
            await self._async_queue.start()

    async def stop_async(self) -> None:
        """Stop the async LLM queue."""
        if self._async_queue:
            await self._async_queue.stop()

    @property
    def has_async(self) -> bool:
        """Check if async queue is available."""
        return self._async_queue is not None

    def can_call_llm(self) -> bool:
        """Check if we can make an LLM call (rate limiting)."""
        if not self.api_key:
            return False
        if self._async_queue:
            return self._async_queue.can_call_llm()
        now = time.time()
        if now - self._last_call_time < 60.0:
            return self._call_count < self._rate_limit_calls_per_minute
        self._call_count = 0
        return True

    async def deliberate(
        self,
        agent: "Agent",
        context: CognitiveContext,
        world: "World",
    ) -> dict[str, Any]:
        """
        Deliberate about what to do.

        Returns dict with:
        - action: the chosen action
        - goal: the goal being pursued
        - reasoning: explanation of the decision
        - emotional_state: resulting emotional state
        """
        # Build rich context
        rich_context = self._build_context(agent, context, world)

        # Check cache
        cache_key = self._get_cache_key(agent, context)
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Try async LLM queue if available
        if self._async_queue and self.can_call_llm():
            try:
                from ambientsaga.agents.llm_queue import LLMTask, Priority
                task = LLMTask(
                    task_id=f"{agent.entity_id}_{world.tick}",
                    agent_id=agent.entity_id,
                    prompt=self._build_llm_prompt(agent, rich_context),
                    context=rich_context,
                    priority=Priority.HIGH,
                )
                result = await self._async_queue.submit(task)
                if result and result.success:
                    self._call_count += 1
                    self._total_tokens += result.tokens_used
                    parsed = self._parse_llm_response(result.content)
                    self._cache[cache_key] = parsed
                    return parsed
            except Exception:
                pass  # Fall through to sync LLM or rule-based

        # Try sync LLM if available
        if self.can_call_llm():
            try:
                result = await self._call_llm(agent, rich_context)
                self._cache[cache_key] = result
                return result
            except Exception:
                pass  # Fall through to rule-based

        # Fall back to sophisticated rule-based reasoning
        return self._rule_based_deliberate(agent, rich_context, world)

    def _build_context(
        self,
        agent: "Agent",
        context: CognitiveContext,
        world: "World",
    ) -> dict[str, Any]:
        """Build a rich context dictionary for deliberation."""
        # Get recent memories
        memories = getattr(agent, '_cognitive_memories', [])
        recent_memories = sorted(memories, key=lambda m: m.tick, reverse=True)[:10]
        memory_summary = "\n".join([
            f"[Tick {m.tick}] {m.content} (emotion: {m.emotional_valence:.1f})"
            for m in recent_memories
        ]) if recent_memories else "No recent memories."

        # Get active goals
        goals = getattr(agent, '_cognitive_goals', [])
        goal_summary = "\n".join([
            f"- {g.description} (priority: {g.priority:.2f}, progress: {g.progress:.1%})"
            for g in goals if not g.is_complete()
        ]) if goals else "No active goals."

        # Get relationships
        rels = world._relationships
        nearby_ids = [n["agent_id"] for n in context.nearby_agents]
        rel_summary = []
        for aid in nearby_ids:
            key = (min(agent.entity_id, aid), max(agent.entity_id, aid))
            if key in rels:
                r = rels[key]
                other_name = next((n["agent_name"] for n in context.nearby_agents if n["agent_id"] == aid), aid[:8])
                rel_summary.append(f"- {other_name}: trust={r['trust']:.1f}, affiliation={r['affiliation']:.1f}")

        return {
            "agent_name": agent.name,
            "agent_id": agent.entity_id,
            "tier": agent.tier.value,
            "age": agent.attributes.age,
            "gender": agent.attributes.gender,
            "personality_summary": agent.attributes.personality_summary,
            "backstory": agent.attributes.backstory,
            "ambition": agent.attributes.ambition,
            "fear": agent.attributes.fear,
            "talents": list(agent.attributes.talents),
            "flaws": list(agent.attributes.flaws),
            "wealth": agent.wealth,
            "health": agent.health,
            "energy": agent.energy,
            "hunger": agent.hunger,
            "thirst": agent.thirst,
            # HEXACO personality
            "honesty_humility": agent.honesty_humility,
            "emotionality": agent.emotionality,
            "extraversion": agent.extraversion,
            "agreeableness": agent.agreeableness,
            "conscientiousness": agent.conscientiousness,
            "openness": agent.openness,
            # Memory
            "recent_memories": memory_summary,
            "active_goals": goal_summary,
            # Context
            "terrain": context.terrain_type,
            "temperature": context.temperature,
            "vegetation": context.vegetation,
            "season": context.season,
            "social_density": context.social_density,
            # Nearby agents
            "nearby_agents": [
                f"{n['agent_name']} ({n['distance']:.0f}m away, trust={n['relationship_trust']:.1f})"
                for n in context.nearby_agents[:5]
            ],
            "relationships": rel_summary[:5],
            # Skills
            "skills": dict(agent.skills),
            "tick": world.tick,
            "year": world.year,
            "season": world.season,
        }

    def _get_cache_key(self, agent: "Agent", context: CognitiveContext) -> str:
        """Generate a cache key for deliberation results."""
        # Include relevant state in cache key
        tick = getattr(agent, '_last_decision_tick', 0)
        state = (
            f"{agent.entity_id}:"
            f"{int(agent.hunger * 10)}:"
            f"{int(agent.thirst * 10)}:"
            f"{int(agent.energy * 10)}:"
            f"{context.terrain_type}:"
            f"{len(context.nearby_agents)}:"
            f"{tick % 10}"
        )
        return hashlib.md5(state.encode()).hexdigest()

    def _build_llm_prompt(self, agent: "Agent", context: dict[str, Any]) -> str:
        """Build a prompt for the LLM."""
        return f"""You are {context.get('agent_name', 'an agent')} in a simulated world.

Your personality: {context.get('personality_summary', 'balanced')}
Your backstory: {context.get('backstory', 'ordinary')}
Your ambitions: {context.get('ambition', 'survive and thrive')}

Current state:
- Health: {context.get('health', 0.5):.0%}
- Energy: {context.get('energy', 0.5):.0%}
- Hunger: {context.get('hunger', 0.5):.0%}
- Thirst: {context.get('thirst', 0.5):.0%}
- Wealth: {context.get('wealth', 0):.0f}
- Social connections: {context.get('social_connections', 0)}

Nearby agents: {context.get('nearby_summary', 'none')}
Nearby resources: {context.get('resource_summary', 'none')}

Recent memories:
{context.get('memory_summary', 'No memories.')}

Active goals:
{context.get('goal_summary', 'None.')}

What should you do? Respond with JSON:
{{"decision": "...", "goal": "...", "reasoning": "...", "priority": 0.0-1.0}}
"""

    def _parse_llm_response(self, content: str | None) -> dict[str, Any]:
        """Parse LLM response into structured format."""
        if not content:
            return {
                "decision": "wait",
                "goal": "observe",
                "reasoning": "No response from LLM",
                "priority": 0.5,
            }

        try:
            # Try to parse as JSON
            import re
            json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return {
                    "decision": data.get("decision", "wait"),
                    "goal": data.get("goal", "observe"),
                    "reasoning": data.get("reasoning", ""),
                    "priority": float(data.get("priority", 0.5)),
                    "using_llm": True,
                }
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

        # Fallback: extract decision from text
        return {
            "decision": self._extract_decision(content),
            "goal": "llm_derived",
            "reasoning": content[:200],
            "priority": 0.5,
            "using_llm": True,
        }

    def _extract_decision(self, text: str) -> str:
        """Extract a decision from free-text LLM response."""
        text_lower = text.lower()

        # Map keywords to decisions
        keywords = {
            "gather": ["gather", "collect", "find food", "find resource"],
            "rest": ["rest", "sleep", "recover", "relax"],
            "explore": ["explore", "wander", "travel", "move"],
            "socialize": ["talk", "interact", "social", "meet"],
            "trade": ["trade", "exchange", "barter", "buy", "sell"],
            "help": ["help", "assist", "support", "give"],
            "attack": ["attack", "fight", "confront", "aggress"],
            "flee": ["flee", "run", "escape", "hide"],
        }

        for decision, words in keywords.items():
            for word in words:
                if word in text_lower:
                    return decision

        return "wait"

    async def _call_llm(
        self,
        agent: "Agent",
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Call the LLM API for deliberation."""
        import anthropic

        client = anthropic.Anthropic(api_key=self.api_key)

        context_str = json.dumps(context, indent=2, ensure_ascii=False)

        prompt = f"""You are {context['agent_name']}, a person in a simulated world.

Your personality: {context['personality_summary']}
Your backstory: {context['backstory']}
Your ambitions: {context['ambition']}
What you fear: {context['fear']}
Your talents: {', '.join(context['talents'])}
Your flaws: {', '.join(context['flaws'])}

Current state:
- Health: {context['health']:.0%}
- Energy: {context['energy']:.0%}
- Hunger: {context['hunger']:.0%}
- Thirst: {context['thirst']:.0%}
- Wealth: {context['wealth']:.0f}
- Age: {context['age']} years
- Season: {context['season']}

Current environment:
- Terrain: {context['terrain']}
- Temperature: {context['temperature']:.1f}°C
- Vegetation: {context['vegetation']:.0%}
- Social density: {context['social_density']:.0%}

Nearby people: {', '.join(context['nearby_agents']) if context['nearby_agents'] else 'No one nearby'}

Your recent memories:
{context['recent_memories']}

Your active goals:
{context['active_goals']}

Based on all this information, what should {context['agent_name']} do? Consider their personality, needs, goals, and relationships.

Respond in JSON format:
{{
    "action": "specific action name",
    "goal": "what goal this serves",
    "reasoning": "why this action makes sense given personality and situation",
    "emotional_state": "resulting emotion after this decision",
    "narrative": "a 1-2 sentence atmospheric description of what happens"
}}

Choose actions from: gather_food, find_water, rest, move_to_location, socialize, trade, craft, explore, fight, flee, forage, share_food, tell_story, teach_skill, ask_for_help, form_group, create_art, perform_ritual, share_knowledge, trade_item, craft_item, settle_dispute, lead_group, follow, wait, contemplate

The action should feel authentic to the character's personality. Make interesting choices - not just survival.
"""

        response = client.messages.create(
            model=self.model,
            max_tokens=300,
            system=self._system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )

        self._call_count += 1
        self._last_call_time = time.time()
        self._total_tokens += response.usage.input_tokens + response.usage.output_tokens

        # Parse response
        try:
            text = response.content[0].text
            # Try to extract JSON
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            result = json.loads(text.strip())
            return {
                "action": result.get("action", "idle"),
                "goal": result.get("goal", "survive"),
                "reasoning": result.get("reasoning", ""),
                "emotional_state": result.get("emotional_state", "calm"),
                "narrative": result.get("narrative", ""),
                "using_llm": True,
            }
        except (json.JSONDecodeError, IndexError):
            return self._rule_based_deliberate(
                agent, context, None
            )

    def _rule_based_deliberate(
        self,
        agent: "Agent",
        context: dict[str, Any],
        world: "World | None",
    ) -> dict[str, Any]:
        """
        Sophisticated rule-based deliberation fallback.

        Uses personality, needs, relationships, and context to make decisions.
        """
        # Need urgency assessment
        hunger = context.get("hunger", 0.0)
        thirst = context.get("thirst", 0.0)
        energy = context.get("energy", 1.0)
        health = context.get("health", 1.0)

        # Personality modifiers
        extraversion = context.get("extraversion", 0.5)
        agreeableness = context.get("agreeableness", 0.5)
        conscientiousness = context.get("conscientiousness", 0.5)
        openness = context.get("openness", 0.5)
        emotionality = context.get("emotionality", 0.5)

        rng = random.Random(agent.entity_id + str(context.get("tick", 0)))

        # Priority: survival first
        if hunger > 0.85:
            action = "gather_food"
            goal = "survive_hunger"
            reasoning = f"Very hungry ({hunger:.0%}), must find food."
            emotional = "anxious"
            narrative = f"{context['agent_name']}'s stomach growls. The search for sustenance begins."

        elif thirst > 0.85:
            action = "find_water"
            goal = "survive_thirst"
            reasoning = f"Very thirsty ({thirst:.0%}), must find water."
            emotional = "desperate"
            narrative = f"{context['agent_name']}'s throat burns with thirst. Water must be found."

        elif health < 0.3:
            action = "rest"
            goal = "recover_health"
            reasoning = f"Badly wounded ({health:.0%}), must rest and recover."
            emotional = "vulnerable"
            narrative = f"{context['agent_name']}'s wounds ache. Rest is necessary."

        elif energy < 0.2:
            action = "rest"
            goal = "restore_energy"
            reasoning = f"Exhausted ({energy:.0%}), must rest."
            emotional = "tired"
            narrative = f"{context['agent_name']}'s body demands rest."

        # Social opportunities
        elif context.get("nearby_agents") and extraversion > 0.5 and rng.random() < extraversion * 0.4:
            nearby = context["nearby_agents"]
            target = rng.choice(nearby)
            if agreeableness > 0.5:
                action = "socialize"
                goal = "build_relationship"
                reasoning = f"Social opportunity with {target['agent_name']}, high extraversion."
                emotional = "warm"
                narrative = f"{context['agent_name']} approaches {target['agent_name']}, seeking connection."

        # Trade opportunity
        elif context.get("wealth", 0) > 200 and rng.random() < 0.15:
            action = "trade"
            goal = "economic_gain"
            reasoning = "Has surplus wealth, good time to trade."
            emotional = "opportunistic"
            narrative = f"{context['agent_name']} considers a trade opportunity."

        # Crafting opportunity
        elif rng.random() < conscientiousness * 0.2:
            skill = rng.choice(list(context.get("skills", {}).keys()))
            action = "craft"
            goal = "build_skill"
            reasoning = f"Time to practice {skill} skill, conscientiousness drives productive work."
            emotional = "satisfied"
            narrative = f"{context['agent_name']} settles into the work of crafting."

        # Exploration (openness)
        elif rng.random() < openness * 0.1:
            action = "explore"
            goal = "discover"
            reasoning = "Curiosity drives exploration of the unknown."
            emotional = "curious"
            narrative = f"{context['agent_name']} feels the pull of the horizon, seeking new places."

        # Idle / contemplate
        else:
            if emotionality > 0.6:
                action = "contemplate"
                goal = "process_experience"
                reasoning = "Reflecting on recent experiences, emotional processing."
                emotional = "melancholic"
                narrative = f"{context['agent_name']} sits in quiet contemplation."
            else:
                action = "wait"
                goal = "observe"
                reasoning = "No urgent needs, simply observing the world."
                emotional = "content"
                narrative = f"{context['agent_name']} watches the world go by, content."

        return {
            "action": action,
            "goal": goal,
            "reasoning": reasoning,
            "emotional_state": emotional,
            "narrative": narrative,
            "using_llm": False,
        }

    def get_stats(self) -> dict[str, Any]:
        """Get deliberation statistics."""
        return {
            "total_calls": self._call_count,
            "total_tokens": self._total_tokens,
            "cache_size": len(self._cache),
        }


# ============================================================================
# Cognitive Manager - Coordinates all agent cognition
# ============================================================================

class CognitiveManager:
    """
    Manages cognitive processing for all agents.

    Coordinates:
    - Perception gathering
    - Memory management
    - Deliberation
    - Emotional state
    - Goal management
    """

    def __init__(self, llm_api_key: str | None = None):
        self.deliberator = LLMDeliberator(api_key=llm_api_key)
        self._deliberation_count = 0
        self._llm_call_count = 0

    def build_context(
        self,
        agent: "Agent",
        world: "World",
        tick: int,
    ) -> CognitiveContext:
        """Build a complete cognitive context for an agent."""
        # Gather nearby agents
        nearby_agents = []
        for other, dist in world.get_agents_near(agent.position, agent.perception_radius):
            if other.entity_id == agent.entity_id or not other.is_alive:
                continue
            rel = world.get_relationship(agent.entity_id, other.entity_id)
            nearby_agents.append(SocialPerception(
                agent_id=other.entity_id,
                agent_name=other.name,
                distance=dist,
                relationship_trust=rel.get("trust", 0.0) if rel else 0.0,
                relationship_affiliation=rel.get("affiliation", 0.0) if rel else 0.0,
            ))

        # Get terrain and environmental data
        terrain = world.get_terrain(agent.x, agent.y)
        temperature = world.get_temperature(agent.x, agent.y)
        humidity = world.get_humidity(agent.x, agent.y)
        vegetation = world.get_vegetation(agent.x, agent.y)
        elevation = world.get_elevation(agent.x, agent.y)

        # Social density
        social_density = len(nearby_agents) / max(1, agent.perception_radius ** 2 * 0.1)

        # Threat assessment (based on hostile relationships nearby)
        threat = 0.0
        for n in nearby_agents:
            if n.relationship_trust < -0.3:
                threat += abs(n.relationship_trust)

        # Opportunity (based on vegetation + nearby resources)
        opportunity = vegetation * 0.5 + (1 - threat) * 0.5

        # Populate nearby resources from terrain analysis
        nearby_resources = []
        radius = int(agent.perception_radius)
        if radius > 0:
            # Count terrain types in nearby cells
            terrain_counts: dict[str, int] = {}
            vegetation_total = 0.0
            water_count = 0
            x, y = int(agent.x), int(agent.y)
            world_width = getattr(world, '_terrain', None)
            if world_width is not None:
                world_width = world_width.shape[1]
                world_height = world_width.shape[0] if hasattr(world_width, 'shape') else world_width
            else:
                world_width = 256
                world_height = 256

            sample_step = max(1, radius // 5)  # Sample every N cells for performance
            for dy in range(-radius, radius + 1, sample_step):
                for dx in range(-radius, radius + 1, sample_step):
                    wx = (x + dx) % world_width
                    wy = (y + dy) % world_height
                    try:
                        nearby_terrain = world.get_terrain(wx, wy)
                        terrain_name = nearby_terrain.name
                        terrain_counts[terrain_name] = terrain_counts.get(terrain_name, 0) + 1
                        if nearby_terrain.is_water:
                            water_count += 1
                        vegetation_total += world.get_vegetation(wx, wy)
                    except Exception:
                        pass

            # Map terrain to resources and calculate abundance
            terrain_resource_map = {
                "FOREST": "wood",
                "DENSE_FOREST": "wood",
                "RAINFOREST": "wood",
                "GRASSLAND": "food",
                "SAVANNA": "food",
                "PLAINS": "food",
                "SCRUBLAND": "herbs",
                "HILLS": "stone",
                "MOUNTAINS": "stone",
                "HIGHLANDS": "stone",
                "DESERT": "clay",
                "DESERT_SCRUB": "clay",
                "WETLAND": "fish",
                "MARSH": "fish",
                "BEACH": "salt",
                "COAST": "fish",
                "OCEAN": "fish",
                "LAKE": "fish",
                "RIVER": "fish",
            }

            total_cells = max(1, sum(terrain_counts.values()))
            for terrain_name, count in terrain_counts.items():
                resource = terrain_resource_map.get(terrain_name, "materials")
                abundance = count / total_cells
                nearby_resources.append({
                    "type": resource,
                    "abundance": round(abundance, 3),
                    "terrain": terrain_name,
                })

            # Add water availability
            if water_count > 0:
                nearby_resources.append({
                    "type": "fresh_water",
                    "abundance": round(water_count / total_cells, 3),
                    "terrain": "water",
                })

            # Add average vegetation as a general food indicator
            if vegetation_total > 0:
                nearby_resources.append({
                    "type": "foraging",
                    "abundance": round(vegetation_total / max(1, total_cells), 3),
                    "terrain": "vegetation",
                })

        return CognitiveContext(
            nearby_agents=[
                {
                    "agent_id": n.agent_id,
                    "agent_name": n.agent_name,
                    "distance": n.distance,
                    "relationship_trust": n.relationship_trust,
                    "relationship_affiliation": n.relationship_affiliation,
                }
                for n in nearby_agents
            ],
            nearby_resources=nearby_resources,
            terrain_type=terrain.name,
            temperature=temperature,
            humidity=humidity,
            vegetation=vegetation,
            elevation=elevation,
            social_density=social_density,
            threat_level=min(1.0, threat),
            opportunity_level=min(1.0, opportunity),
            season=world.season,
            year=world.year,
        )

    async def think(
        self,
        agent: "Agent",
        context: CognitiveContext,
        world: "World",
    ) -> dict[str, Any]:
        """
        Main cognitive process for an agent.

        Returns deliberation result with action, goal, reasoning, narrative.
        """
        self._deliberation_count += 1

        # Build deliberation context
        deliberation_context = self.deliberator._build_context(agent, context, world)

        # Deliberate
        result = await self.deliberator.deliberate(agent, context, world)

        if result.get("using_llm"):
            self._llm_call_count += 1

        return result

    def remember(
        self,
        agent: "Agent",
        event_type: str,
        content: str,
        tick: int,
        emotional_valence: float = 0.0,
        importance: float = 0.5,
    ) -> None:
        """Add a memory to an agent's cognitive memory."""
        if not hasattr(agent, '_cognitive_memories'):
            agent._cognitive_memories = []

        memories = agent._cognitive_memories
        memories.append(MemoryEntry(
            tick=tick,
            content=content,
            memory_type="episodic",
            emotional_valence=emotional_valence,
            importance=importance,
            location=(agent.x, agent.y),
        ))

        # Consolidate if too many
        if len(memories) > 100:
            # Sort by (importance * vividness)
            memories.sort(key=lambda m: m.importance * getattr(m, 'vividness', 1.0), reverse=True)
            memories[:50] = memories  # Keep top half

    def get_stats(self) -> dict[str, Any]:
        """Get cognitive processing statistics."""
        return {
            "deliberations": self._deliberation_count,
            "llm_calls": self._llm_call_count,
            "deliberator_stats": self.deliberator.get_stats(),
        }
