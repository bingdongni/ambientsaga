"""Emergence and Protocol tests — tests for emergence systems and protocol interactions."""

from __future__ import annotations

import pytest
import asyncio
import random

from ambientsaga.config import Config
from ambientsaga.types import Pos2D, EntityID
from ambientsaga.world.state import World
from ambientsaga.agents.agent import Agent
from ambientsaga.agents.core import AgentTier
from ambientsaga.protocol.interaction import (
    MetaProtocol, Trace, Exchange, BASIC_SIGNALS, CONTENT_TYPES
)
from ambientsaga.emergence.butterfly_effects import (
    ButterflyEffectSystem, ButterflyTrace, CausalMagnitude, SensitivityLevel
)
from ambientsaga.emergence.institutional_emergence import (
    InstitutionalEmergenceEngine, EmergentLaw, EmergentGovernment, InstitutionType
)
from ambientsaga.emergence.full_domain_coupling import (
    FullDomainCouplingEngine, Domain, DomainState, ScientificLaw
)


class TestMetaProtocol:
    """MetaProtocol tests."""

    @pytest.fixture
    def world(self):
        """Create a test world."""
        config = Config()
        world = World(config)
        world._initialize()
        return world

    @pytest.fixture
    def protocol(self, world):
        """Create a test protocol."""
        return MetaProtocol(world)

    @pytest.fixture
    def agent(self, world):
        """Create a test agent."""
        agent = Agent(
            entity_id="test_agent_001",
            name="Test Agent",
            position=Pos2D(x=100.0, y=100.0),
            tier=AgentTier.L2_FUNCTIONAL,
        )
        world.register_agent(agent)
        return agent

    def test_protocol_initialization(self, protocol):
        """Test protocol initialization."""
        assert protocol.world is not None
        assert len(protocol._traces) == 0
        assert len(protocol._exchange_history) == 0
        assert len(protocol._signal_registry) > 0  # Pre-seeded with BASIC_SIGNALS

    def test_basic_signals_exist(self, protocol):
        """Test that basic signals are registered."""
        for signal in BASIC_SIGNALS:
            assert signal in protocol._signal_registry

    def test_add_trace(self, protocol, agent):
        """Test adding a trace."""
        trace = Trace(
            trace_id="test_trace_001",
            tick=0,
            actor_id=agent.entity_id,
            receiver_id="test_receiver",
            signal="help",
            content={"type": "resource_transfer", "resource": "food", "amount": 10},
            interpretation="Offering help",
            mutual=False,
            position=agent.position,
        )
        protocol.add_trace(trace)

        assert len(protocol._traces) == 1
        assert len(protocol._pending_traces) == 1
        assert protocol._signal_registry["help"] == 1

    def test_deliberate_returns_dict(self, protocol, agent):
        """Test that deliberate always returns a dict."""
        agent.position = Pos2D(x=100.0, y=100.0)
        decision = protocol.deliberate(agent, tick=0)

        assert isinstance(decision, dict)
        assert "goal" in decision
        assert "priority" in decision

    def test_exchange_history(self, protocol):
        """Test exchange history."""
        history = protocol.get_exchange_history(lookback=100)
        assert isinstance(history, list)


class TestButterflyEffectSystem:
    """ButterflyEffectSystem tests."""

    @pytest.fixture
    def world(self):
        """Create a test world."""
        config = Config()
        world = World(config)
        world._initialize()
        return world

    @pytest.fixture
    def butterfly_system(self, world):
        """Create a butterfly effect system."""
        return ButterflyEffectSystem(world)

    def test_initialization(self, butterfly_system):
        """Test butterfly system initialization."""
        assert butterfly_system.world is not None
        assert len(butterfly_system.traces) == 0
        assert len(butterfly_system.branch_points) == 0
        assert len(butterfly_system.amplifiers) > 0

    def test_record_micro_event(self, butterfly_system):
        """Test recording a micro event."""
        trace_id = butterfly_system.record_micro_event(
            agent_id="test_agent",
            action="help_neighbor",
            magnitude=0.5,
            context={"domain": "social"}
        )

        assert trace_id is not None
        assert trace_id in butterfly_system.traces

    def test_causal_magnitude_levels(self):
        """Test causal magnitude enum."""
        assert CausalMagnitude.NEGLIGIBLE.value == 0.01
        assert CausalMagnitude.CATASTROPHIC.value == 5.0
        assert CausalMagnitude.APOCALYPTIC.value == 10.0

    def test_sensitivity_levels(self):
        """Test sensitivity level enum."""
        assert SensitivityLevel.STABLE is not None
        assert SensitivityLevel.CRITICAL is not None

    def test_get_statistics(self, butterfly_system):
        """Test statistics retrieval."""
        butterfly_system.record_micro_event(
            agent_id="test_agent",
            action="help",
            magnitude=0.5,
            context={"domain": "social"}
        )

        stats = butterfly_system.get_statistics()
        assert "total_traces" in stats
        assert "active_traces" in stats
        assert "global_sensitivity" in stats

    def test_get_major_events(self, butterfly_system):
        """Test getting major events."""
        butterfly_system.record_micro_event(
            agent_id="test_agent",
            action="major_event",
            magnitude=2.0,
            context={"domain": "social"}
        )

        major_events = butterfly_system.get_major_events(lookback=100)
        assert isinstance(major_events, list)

    def test_historical_recording(self, butterfly_system):
        """Test historical recording."""
        butterfly_system.record_to_timeline(
            tick=0,
            event={"type": "test_event", "data": "test"}
        )
        assert len(butterfly_system.historical_timeline) == 1

    def test_anchor_historical_state(self, butterfly_system):
        """Test anchoring historical state."""
        anchor = butterfly_system.anchor_historical_state(tick=0)
        assert anchor is not None
        assert "tick" in anchor
        assert "agent_count" in anchor

    def test_get_historical_narrative(self, butterfly_system):
        """Test getting historical narrative."""
        narrative = butterfly_system.get_historical_narrative(start_tick=0, end_tick=100)
        assert isinstance(narrative, str)

    def test_export_history(self, butterfly_system):
        """Test history export."""
        export = butterfly_system.export_history(format="dict")
        assert isinstance(export, dict)
        assert "current_tick" in export
        assert "timeline" in export

        json_export = butterfly_system.export_history(format="json")
        assert isinstance(json_export, str)


class TestInstitutionalEmergence:
    """InstitutionalEmergenceEngine tests."""

    @pytest.fixture
    def world(self):
        """Create a test world."""
        config = Config()
        world = World(config)
        world._initialize()
        return world

    @pytest.fixture
    def engine(self, world):
        """Create an institutional emergence engine."""
        return InstitutionalEmergenceEngine(world)

    def test_initialization(self, engine):
        """Test engine initialization."""
        assert engine.world is not None
        assert len(engine.emergent_laws) == 0
        assert len(engine.emergent_governments) == 0
        assert len(engine.emergent_religions) == 0

    def test_record_violation(self, engine):
        """Test recording violations."""
        engine.record_violation(
            agent_id="test_agent",
            violation_type="theft",
            tick=0
        )
        assert len(engine.behavior_history) > 0

    def test_record_crisis_event(self, engine):
        """Test recording crisis events."""
        engine.record_crisis_event(
            event_type="plague",
            severity=3.0,
            tick=0,
            casualties=50
        )
        assert len(engine.behavior_history) > 0

    def test_update(self, engine):
        """Test update loop."""
        engine.update(tick=0)
        assert engine.tick_count == 0


class TestFullDomainCoupling:
    """FullDomainCouplingEngine tests."""

    @pytest.fixture
    def world(self):
        """Create a test world."""
        config = Config()
        world = World(config)
        world._initialize()
        return world

    @pytest.fixture
    def domain_engine(self, world):
        """Create a domain coupling engine."""
        return FullDomainCouplingEngine(world)

    def test_initialization(self, domain_engine):
        """Test engine initialization."""
        assert domain_engine.world is not None
        assert len(domain_engine.domain_states) > 0
        assert len(domain_engine.laws) > 0
        assert len(domain_engine.coupling_rules) > 0

    def test_domains_exist(self, domain_engine):
        """Test that all domains are initialized."""
        expected_domains = [
            Domain.PHYSICS, Domain.CHEMISTRY, Domain.BIOLOGY,
            Domain.ECOLOGY, Domain.ECONOMICS, Domain.POLITICS
        ]
        for domain in expected_domains:
            assert domain in domain_engine.domain_states

    def test_update_domain_state(self, domain_engine):
        """Test updating domain state."""
        domain_engine.update_domain_state(Domain.ECONOMICS, "trade_volume", 100.0)
        assert "trade_volume" in domain_engine.domain_states[Domain.ECONOMICS].values

    def test_evaluate_laws(self, domain_engine):
        """Test evaluating scientific laws."""
        for domain, laws in domain_engine.laws.items():
            for law in laws:
                result = law.evaluate({})
                assert "success" in result

    def test_process_delayed_couplings(self, domain_engine):
        """Test processing delayed couplings."""
        domain_engine.process_delayed_couplings()
        # Should not raise


class TestAgentIntegration:
    """Agent integration tests."""

    @pytest.fixture
    def world(self):
        """Create a test world."""
        config = Config()
        world = World(config)
        world._initialize()
        return world

    @pytest.fixture
    def agent(self, world):
        """Create a test agent."""
        agent = Agent(
            entity_id="test_agent_001",
            name="Test Agent",
            position=Pos2D(x=100.0, y=100.0),
            tier=AgentTier.L1_CORE,
        )
        world.register_agent(agent)
        return agent

    def test_agent_has_humanity_layer(self, agent):
        """Test that agent can access humanity layer."""
        humanity = agent.humanity
        assert humanity is not None

    def test_agent_needs_update(self, agent):
        """Test agent needs update."""
        agent.hunger = 0.5
        agent._update_needs(tick=0)
        # Should not raise


class TestWorldIntegration:
    """World integration tests."""

    @pytest.fixture
    def world(self):
        """Create a test world."""
        config = Config()
        world = World(config)
        world._initialize()
        return world

    @pytest.fixture
    def agent(self, world):
        """Create and register a test agent."""
        agent = Agent(
            entity_id="test_agent_001",
            name="Test Agent",
            position=Pos2D(x=100.0, y=100.0),
            tier=AgentTier.L2_FUNCTIONAL,
        )
        world.register_agent(agent)
        return agent

    def test_world_has_protocol(self, world):
        """Test that world has protocol system."""
        assert world._protocol is not None

    def test_world_has_emergence_systems(self, world):
        """Test that world has all emergence systems."""
        assert world._butterfly_effect is not None
        assert world._domain_coupling is not None
        assert world._institutional_emergence is not None

    def test_world_tick(self, world):
        """Test world tick."""
        world.tick_once()
        assert world.tick >= 0

    def test_world_tick_with_agents(self, world, agent):
        """Test world tick with agents."""
        agent.position = Pos2D(x=100.0, y=100.0)
        world.tick_once()
        # Should not raise

    def test_propagate_disaster_effects(self, world):
        """Test disaster effect propagation."""
        # Create a mock disaster
        class MockDisaster:
            disaster_id = "test_disaster"
            disaster_type = "plague"
            magnitude = 2.0
            casualties = 20
            narrative = "A plague occurred"

        world._propagate_disaster_effects(MockDisaster(), tick=0)
        # Should not raise


class TestAgentHumanityLayer:
    """AgentHumanityLayer comprehensive tests."""

    @pytest.fixture
    def world(self):
        """Create a test world."""
        config = Config()
        world = World(config)
        world._initialize()
        return world

    @pytest.fixture
    def agent(self, world):
        """Create a test agent."""
        agent = Agent(
            entity_id="humanity_test_agent",
            name="Humanity Test Agent",
            position=Pos2D(x=100.0, y=100.0),
            tier=AgentTier.L2_FUNCTIONAL,
        )
        world.register_agent(agent)
        return agent

    def test_humanity_layer_initialization(self, agent):
        """Test humanity layer initializes correctly."""
        humanity = agent.humanity
        assert humanity is not None
        assert humanity.emotions is not None
        assert hasattr(humanity, 'biases')
        assert hasattr(humanity, 'prejudice')
        assert hasattr(humanity, 'trust')
        assert hasattr(humanity, 'temporal')
        assert hasattr(humanity, 'irrationality')

    def test_emotion_affect(self, agent):
        """Test applying emotions to agent."""
        from ambientsaga.emergence.humanity_layer import EmotionType
        humanity = agent.humanity
        humanity.affect(EmotionType.JOY, 0.5)
        assert humanity.emotions.joy > 0.0

        humanity.affect(EmotionType.ANGER, 0.3)
        assert humanity.emotions.anger > 0.0

    def test_emotion_types(self, agent):
        """Test emotion types that exist in EmotionState."""
        from ambientsaga.emergence.humanity_layer import EmotionType
        humanity = agent.humanity

        # Only test emotions that exist in EmotionState
        existing_emotions = [
            EmotionType.JOY, EmotionType.SADNESS, EmotionType.ANGER,
            EmotionType.FEAR, EmotionType.DISGUST, EmotionType.SURPRISE,
            EmotionType.TRUST, EmotionType.ANTICIPATION, EmotionType.LOVE,
            EmotionType.REMORSE
        ]

        for emotion in existing_emotions:
            humanity.affect(emotion, 0.1)
            # Should not raise

    def test_emotion_state_to_dict(self, agent):
        """Test emotion state serialization."""
        from ambientsaga.emergence.humanity_layer import EmotionType
        humanity = agent.humanity
        humanity.affect(EmotionType.JOY, 0.5)
        humanity.affect(EmotionType.SADNESS, 0.2)

        state = humanity.emotions.to_dict()
        assert "joy" in state
        assert "sadness" in state
        assert "valence" in state
        assert "arousal" in state

    def test_stress_level(self, agent):
        """Test stress level management."""
        humanity = agent.humanity
        initial_stress = humanity.stress_level

        humanity.stress_level = min(1.0, initial_stress + 0.2)
        assert humanity.stress_level > initial_stress

        humanity.stress_level = max(0.0, humanity.stress_level - 0.1)
        assert humanity.stress_level < initial_stress + 0.2

    def test_mood_calculation(self, agent):
        """Test mood calculation from emotions."""
        from ambientsaga.emergence.humanity_layer import EmotionType
        humanity = agent.humanity
        humanity.affect(EmotionType.JOY, 0.8)
        humanity.affect(EmotionType.SADNESS, 0.1)

        mood = humanity.get_mood()
        assert isinstance(mood, float)

    def test_cognitive_biases_loss_aversion(self, agent):
        """Test loss aversion bias."""
        humanity = agent.humanity
        biases = humanity.biases

        result = biases.apply_loss_aversion(gain=10.0, loss=10.0)
        # Loss has 2.25x weight, so result should be negative
        assert result < 0

    def test_cognitive_biases_confirmation(self, agent):
        """Test confirmation bias."""
        humanity = agent.humanity
        biases = humanity.biases

        evidence = {"supports_belief": True}
        weight = biases.apply_confirmation_bias(evidence, "belief")
        assert 0 <= weight <= 1

    def test_trust_network_record_interaction(self, agent):
        """Test recording trust interactions."""
        humanity = agent.humanity
        tn = humanity.trust

        initial_trust = tn.get_trust("other_agent")
        tn.record_interaction("other_agent", cooperation=True, tick=0)
        new_trust = tn.get_trust("other_agent")

        assert new_trust > initial_trust

    def test_trust_network_betrayal(self, agent):
        """Test betrayal detection."""
        humanity = agent.humanity
        tn = humanity.trust

        # Record multiple betrayals to lower trust
        for _ in range(5):
            tn.record_interaction("enemy_agent", cooperation=False, tick=0)

        # Should have higher chance to betray now
        will_betray = tn.should_betray("enemy_agent", potential_gain=10.0, tick=100)
        assert isinstance(will_betray, bool)

    def test_trust_network_forgiveness(self, agent):
        """Test forgiveness mechanism."""
        humanity = agent.humanity
        tn = humanity.trust

        # Record betrayal
        tn.record_interaction("test_agent", cooperation=False, tick=0)

        # Should sometimes forgive
        will_forgive = tn.should_forgive("test_agent")
        assert isinstance(will_forgive, bool)

    def test_temporal_preference_evaluate_options(self, agent):
        """Test evaluating temporal options."""
        humanity = agent.humanity
        tp = humanity.temporal

        options = [(10.0, 0.0), (5.0, 20.0), (0.0, 50.0)]
        idx, utility = tp.evaluate_options(options)

        assert 0 <= idx < len(options)
        assert isinstance(utility, float)

    def test_temporal_preference_present_value(self, agent):
        """Test present value calculation."""
        humanity = agent.humanity
        tp = humanity.temporal

        present = tp.get_present_value(future_value=100.0, delay=10)
        assert present < 100.0  # Discounted

    def test_irrationality_under_stress(self, agent):
        """Test irrationality changes under different stress levels."""
        humanity = agent.humanity

        # Low stress
        humanity.stress_level = 0.0
        humanity.fatigue = 0.0
        low_irrational = humanity.calculate_current_irrationality()

        # High stress
        humanity.stress_level = 0.9
        humanity.fatigue = 0.9
        high_irrational = humanity.calculate_current_irrationality()

        assert high_irrational >= low_irrational

    def test_irrationality_decision_modification(self, agent):
        """Test irrationality modifies decisions."""
        humanity = agent.humanity

        decision = {"goal": "gather", "priority": 0.8}
        modified = humanity.make_decision_with_irrationality([decision])

        assert isinstance(modified, dict)
        assert "goal" in modified

    def test_emotional_infection(self, agent):
        """Test emotional contagion between agents."""
        from ambientsaga.emergence.humanity_layer import EmotionType
        humanity = agent.humanity

        # Set high joy
        humanity.affect(EmotionType.JOY, 0.9)

        # Simulate receiving emotional contagion
        nearby_emotions = {
            "joy": 0.8,
            "sadness": 0.1
        }

        humanity.receive_emotional_contagion(nearby_emotions)
        # Should increase own emotions slightly
        assert humanity.emotions.joy >= 0.9

    def test_fatigue_accumulation(self, agent):
        """Test fatigue accumulation."""
        humanity = agent.humanity

        initial_fatigue = humanity.fatigue
        humanity.fatigue = min(1.0, humanity.fatigue + 0.1)
        assert humanity.fatigue > initial_fatigue


class TestButterflyEffectPropagation:
    """Butterfly effect propagation and alternative history tests."""

    @pytest.fixture
    def world(self):
        """Create a test world."""
        config = Config()
        world = World(config)
        world._initialize()
        return world

    @pytest.fixture
    def butterfly_system(self, world):
        """Create a butterfly effect system."""
        return ButterflyEffectSystem(world)

    def test_causal_chain_propagation(self, butterfly_system):
        """Test causal chain propagation to new domains."""
        trace_id = butterfly_system.record_micro_event(
            agent_id="test_agent",
            action="help",
            magnitude=0.5,
            context={"domain": "social"}
        )

        assert trace_id is not None
        trace = butterfly_system.traces[trace_id]

        # Propagate to new domain
        butterfly_system.propagate_causal_chain(
            trace_id=trace_id,
            new_domain="economics",
            new_agent="receiver_1",
            delay=5
        )

        assert len(trace.causal_chain) == 2
        assert "economics" in trace.affected_domains

    def test_causal_amplification(self, butterfly_system):
        """Test causal magnitude amplification."""
        trace_id = butterfly_system.record_micro_event(
            agent_id="test_agent",
            action="major_event",
            magnitude=1.0,
            context={"domain": "social"}
        )

        trace = butterfly_system.traces[trace_id]
        initial_magnitude = trace.current_magnitude

        # Amplify
        trace.amplify(1.5)

        assert trace.current_magnitude > initial_magnitude

    def test_branch_point_creation(self, butterfly_system):
        """Test branch point creation for significant events."""
        # Record a major event
        trace_id = butterfly_system.record_micro_event(
            agent_id="test_leader",
            action="death",
            magnitude=5.0,
            context={"domain": "social", "magnitude": 2.0, "target_tier": 1}
        )

        trace = butterfly_system.traces[trace_id]
        assert trace.branch_point
        assert trace.branch_id is not None
        assert trace.branch_id in butterfly_system.branch_points

    def test_alternative_history_trigger(self, butterfly_system):
        """Test alternative history triggering."""
        # Set to chaotic sensitivity
        butterfly_system.global_sensitivity = SensitivityLevel.CHAOTIC
        butterfly_system.chaos_accumulator = 60.0

        # Should have chance to trigger
        triggered = butterfly_system.should_trigger_alternative_history()
        assert isinstance(triggered, bool)

    def test_global_sensitivity_update(self, butterfly_system):
        """Test global sensitivity updates based on events."""
        initial_sensitivity = butterfly_system.global_sensitivity

        # Record multiple events to increase chaos
        for _ in range(10):
            butterfly_system.record_micro_event(
                agent_id="test_agent",
                action="test",
                magnitude=2.0,
                context={"domain": "social"}
            )

        assert butterfly_system.chaos_accumulator > 0

    def test_trace_irreversibility(self, butterfly_system):
        """Test marking traces as irreversible."""
        trace_id = butterfly_system.record_micro_event(
            agent_id="test_agent",
            action="catastrophic",
            magnitude=10.0,
            context={"domain": "biology", "affected_agents": 100}
        )

        trace = butterfly_system.traces[trace_id]
        # Catastrophic events might be marked as irreversible
        assert trace.branch_point or trace.current_magnitude > 5.0


class TestInstitutionalEmergenceDetailed:
    """Detailed institutional emergence tests."""

    @pytest.fixture
    def world(self):
        """Create a test world."""
        config = Config()
        world = World(config)
        world._initialize()
        return world

    @pytest.fixture
    def engine(self, world):
        """Create an institutional emergence engine."""
        return InstitutionalEmergenceEngine(world)

    def test_law_emergence(self, engine):
        """Test emergent law creation."""
        # Record multiple violations
        for i in range(5):
            engine.record_violation(
                agent_id=f"violator_{i}",
                violation_type="theft",
                tick=i
            )

        # Check if law emerges
        engine.update(tick=10)

        # Should have tracked the pattern
        assert len(engine.behavior_history) > 0

    def test_government_emergence(self, engine):
        """Test government structure emergence."""
        # Record crisis events
        engine.record_crisis_event(
            event_type="resource_war",
            severity=3.0,
            tick=0,
            casualties=100
        )

        engine.update(tick=10)

        # Should track the crisis
        assert len(engine.behavior_history) > 0

    def test_religion_emergence(self, engine):
        """Test religious institution emergence."""
        # Record shared narratives
        for i in range(10):
            engine.record_violation(
                agent_id=f"believer_{i}",
                violation_type="ritual",
                tick=i
            )

        engine.update(tick=20)

        assert len(engine.behavior_history) > 0

    def test_institution_type_transitions(self, engine):
        """Test institution type transitions."""
        from ambientsaga.emergence.institutional_emergence import InstitutionType

        # Check all institution types exist
        assert InstitutionType.LAW is not None
        assert InstitutionType.GOVERNMENT is not None
        assert InstitutionType.RELIGION is not None
        assert InstitutionType.CLASS is not None
        assert InstitutionType.ORGANIZATION is not None
        assert InstitutionType.CULTURE is not None

    def test_behavior_pattern_detection(self, engine):
        """Test detecting behavior patterns."""
        # Record similar behaviors
        for _ in range(20):
            engine.record_violation(
                agent_id="repeat_offender",
                violation_type="theft",
                tick=0
            )

        # Pattern should be detected
        theft_violations = [
            v for v in engine.behavior_history
            if v.get("violation_type") == "theft"
        ]
        assert len(theft_violations) >= 10


class TestFullDomainCouplingDetailed:
    """Detailed domain coupling tests."""

    @pytest.fixture
    def world(self):
        """Create a test world."""
        config = Config()
        world = World(config)
        world._initialize()
        return world

    @pytest.fixture
    def domain_engine(self, world):
        """Create a domain coupling engine."""
        return FullDomainCouplingEngine(world)

    def test_cross_domain_coupling(self, domain_engine):
        """Test cross-domain coupling effects."""
        from ambientsaga.emergence.full_domain_coupling import Domain

        # Physics affects Chemistry
        domain_engine.update_domain_state(Domain.PHYSICS, "temperature", 1000.0)

        # Physics state should have temperature
        physics_state = domain_engine.domain_states[Domain.PHYSICS]
        assert "temperature" in physics_state.values

    def test_coupling_delay(self, domain_engine):
        """Test processing delayed couplings."""
        # The delayed couplings are pre-defined in initialization
        # Just test that processing doesn't raise
        domain_engine.process_delayed_couplings()
        # Should not raise

    def test_domain_states(self, domain_engine):
        """Test domain state updates."""
        from ambientsaga.emergence.full_domain_coupling import Domain

        # Update multiple domains
        domain_engine.update_domain_state(Domain.ECONOMICS, "trade_volume", 100.0)
        domain_engine.update_domain_state(Domain.ECOLOGY, "population", 5000.0)

        # Should have tracked the updates
        eco_state = domain_engine.domain_states[Domain.ECONOMICS]
        assert "trade_volume" in eco_state.values

    def test_evaluate_laws(self, domain_engine):
        """Test evaluating scientific laws."""
        for domain, laws in domain_engine.laws.items():
            for law in laws:
                result = law.evaluate({})
                assert "success" in result

    def test_process_delayed_couplings(self, domain_engine):
        """Test processing delayed couplings."""
        domain_engine.process_delayed_couplings()
        # Should not raise


class TestWorldEmergenceIntegration:
    """Integration tests for all emergence systems working together."""

    @pytest.fixture
    def world(self):
        """Create a test world."""
        config = Config()
        world = World(config)
        world._initialize()
        return world

    def test_all_emergence_systems_initialized(self, world):
        """Test all emergence systems are initialized."""
        assert world._butterfly_effect is not None
        assert world._domain_coupling is not None
        assert world._institutional_emergence is not None

    def test_world_with_agents_ticks(self, world):
        """Test world ticks with all systems running."""
        # Spawn agents
        for i in range(5):
            agent = Agent(
                entity_id=f"integrate_agent_{i}",
                name=f"Agent {i}",
                position=Pos2D(x=100.0 + i * 10, y=100.0 + i * 10),
                tier=AgentTier.L2_FUNCTIONAL,
            )
            world.register_agent(agent)

        # Run ticks
        for _ in range(5):
            world.tick_once()

        # All systems should have processed
        assert world._butterfly_effect is not None

    def test_agent_humanity_in_world_tick(self, world):
        """Test agent humanity layer works during world tick."""
        from ambientsaga.emergence.humanity_layer import EmotionType

        agent = Agent(
            entity_id="hierarchy_agent",
            name="Test Agent",
            position=Pos2D(x=100.0, y=100.0),
            tier=AgentTier.L2_FUNCTIONAL,
        )
        world.register_agent(agent)

        # Access humanity layer
        humanity = agent.humanity
        humanity.affect(EmotionType.JOY, 0.5)

        # Run tick
        world.tick_once()

        # Should not raise and humanity should be accessible
        assert agent.humanity is not None


class TestPerformance:
    """Performance tests."""

    @pytest.fixture
    def world(self):
        """Create a test world."""
        config = Config()
        world = World(config)
        world._initialize()
        return world

    def test_protocol_deliberate_performance(self, world):
        """Test protocol deliberate performance."""
        protocol = world._protocol

        # Create multiple agents
        agents = []
        for i in range(10):
            agent = Agent(
                entity_id=f"perf_agent_{i}",
                name=f"Perf Agent {i}",
                position=Pos2D(x=100.0 + i * 10, y=100.0 + i * 10),
                tier=AgentTier.L2_FUNCTIONAL,
            )
            world.register_agent(agent)
            agents.append(agent)

        # Time deliberation
        import time
        start = time.time()
        for agent in agents:
            protocol.deliberate(agent, tick=0)
        elapsed = time.time() - start

        # Should be fast
        assert elapsed < 1.0  # 10 agents in 1 second

    def test_butterfly_system_performance(self, world):
        """Test butterfly effect system performance."""
        butterfly = world._butterfly_effect

        import time
        start = time.time()

        for i in range(100):
            butterfly.record_micro_event(
                agent_id=f"perf_agent_{i}",
                action="test_action",
                magnitude=0.5,
                context={"domain": "social"}
            )

        elapsed = time.time() - start

        # Should handle 100 events quickly
        assert elapsed < 0.5

    def test_chunk_manager_performance(self, world):
        """Test chunk manager spatial queries."""
        # Spawn many agents
        for i in range(100):
            agent = Agent(
                entity_id=f"chunk_agent_{i}",
                name=f"Chunk Agent {i}",
                position=Pos2D(x=float(i), y=float(i)),
                tier=AgentTier.L3_BACKGROUND,
            )
            world.register_agent(agent)

        import time
        start = time.time()

        for _ in range(100):
            world._chunk_manager.get_agents_in_radius(50.0, 50.0, 20.0)

        elapsed = time.time() - start

        # Should be fast
        assert elapsed < 0.5
