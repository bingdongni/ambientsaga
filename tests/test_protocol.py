"""
Tests for protocol modules — reputation, emergent economy, social norms, language emergence.
"""

import pytest
from unittest.mock import MagicMock, patch
from collections import defaultdict


class TestReputationNetwork:
    """Tests for ReputationNetwork - gossip-based reputation propagation."""

    @pytest.fixture
    def mock_world(self):
        """Create a mock world."""
        world = MagicMock()
        world.get_agent = MagicMock(return_value=MagicMock(wealth=100.0))
        return world

    @pytest.fixture
    def reputation_network(self, mock_world):
        """Create a ReputationNetwork instance."""
        from ambientsaga.protocol.reputation import ReputationNetwork
        return ReputationNetwork(mock_world)

    def test_initialization(self, reputation_network):
        """Test reputation network initialization."""
        assert reputation_network.world is not None
        assert len(reputation_network._views) == 0
        assert len(reputation_network._transmission_log) == 0
        assert len(reputation_network._gossip_cache) == 0

    def test_observe_positive_behavior(self, reputation_network):
        """Test observing positive behavior."""
        reputation_network.observe(
            observer_id="agent1",
            target_id="agent2",
            behavior="helped",
            valence=0.8,
            tick=100,
        )

        score, confidence = reputation_network.get_reputation("agent1", "agent2")
        assert score > 0  # Score should be positive for positive behavior
        assert confidence > 0  # Confidence should be positive after observation

    def test_observe_negative_behavior(self, reputation_network):
        """Test observing negative behavior."""
        reputation_network.observe(
            observer_id="agent1",
            target_id="agent2",
            behavior="defrauded",
            valence=-0.9,
            tick=100,
        )

        score, confidence = reputation_network.get_reputation("agent1", "agent2")
        assert score < 0  # Score should be negative for negative behavior
        assert confidence > 0  # Confidence should be positive after observation

    def test_observe_valence_clamping(self, reputation_network):
        """Test that valence is clamped to [-1, 1]."""
        # Test upper bound
        reputation_network.observe(
            observer_id="agent1",
            target_id="agent2",
            behavior="helped",
            valence=1.5,  # Should be clamped to 1.0
            tick=100,
        )

        score, confidence = reputation_network.get_reputation("agent1", "agent2")
        assert score <= 1.0

        # Test lower bound
        reputation_network.observe(
            observer_id="agent3",
            target_id="agent4",
            behavior="defrauded",
            valence=-1.5,  # Should be clamped to -1.0
            tick=101,
        )

        score, confidence = reputation_network.get_reputation("agent3", "agent4")
        assert score >= -1.0

    def test_get_reputation_no_data(self, reputation_network):
        """Test get_reputation with no data."""
        score, confidence = reputation_network.get_reputation("unknown1", "unknown2")
        assert score == 0.0
        assert confidence == 0.0

    def test_get_all_reputations(self, reputation_network):
        """Test get_all_reputations."""
        reputation_network.observe("agent1", "agent2", "helped", 0.5, 100)
        reputation_network.observe("agent1", "agent3", "helped", 0.7, 101)

        all_reps = reputation_network.get_all_reputations("agent1")
        assert len(all_reps) == 2
        assert "agent2" in all_reps
        assert "agent3" in all_reps

    def test_spread_gossip(self, reputation_network):
        """Test gossip spreading."""
        # Agent1 observes Agent2 positively
        reputation_network.observe("agent1", "agent2", "helped", 0.8, 100)

        # Get initial state
        score, confidence = reputation_network.get_reputation("agent1", "agent2")
        assert score > 0

        # Agent1 and Agent2 gossip - should not crash
        reputation_network.spread(tick=101, gossip_agents=["agent1", "agent2"])

    def test_spread_no_gossip_partners(self, reputation_network):
        """Test spread with no or single gossip partner."""
        reputation_network.spread(tick=100, gossip_agents=[])
        reputation_network.spread(tick=100, gossip_agents=["agent1"])

        # Should not crash

    def test_get_social_network(self, reputation_network):
        """Test getting social network."""
        reputation_network.observe("agent1", "agent2", "helped", 0.5, 100)
        reputation_network.observe("agent1", "agent3", "helped", 0.6, 101)

        network = reputation_network.get_social_network("agent1", depth=1)
        assert isinstance(network, dict)

    def test_get_social_network_depth(self, reputation_network):
        """Test social network with different depths."""
        reputation_network.observe("agent1", "agent2", "helped", 0.5, 100)
        reputation_network.observe("agent2", "agent3", "helped", 0.6, 101)
        reputation_network.observe("agent3", "agent4", "helped", 0.7, 102)

        network_depth1 = reputation_network.get_social_network("agent1", depth=1)
        network_depth2 = reputation_network.get_social_network("agent1", depth=2)

        assert isinstance(network_depth1, dict)
        assert isinstance(network_depth2, dict)

    def test_get_most_trusted(self, reputation_network):
        """Test getting most trusted agents."""
        reputation_network.observe("agent1", "agent2", "helped", 0.5, 100)
        reputation_network.observe("agent1", "agent3", "helped", 0.8, 101)
        reputation_network.observe("agent1", "agent4", "helped", 0.3, 102)

        most_trusted = reputation_network.get_most_trusted("agent1", limit=3)
        assert isinstance(most_trusted, list)
        assert len(most_trusted) >= 1

    def test_reputation_view_update(self, reputation_network):
        """Test ReputationView update mechanism."""
        from ambientsaga.protocol.reputation import ReputationView, ReputationObservation

        view = ReputationView(score=0.0, confidence=0.0)

        obs = ReputationObservation(
            observer_id="agent1",
            target_id="agent2",
            behavior="helped",
            valence=0.5,
            confidence=1.0,
            tick=100,
        )

        view.update(obs)

        assert view.score > 0
        assert view.confidence > 0
        assert len(view.observations) == 1

    def test_reputation_view_update_decay(self, reputation_network):
        """Test that repeated updates decay old confidence."""
        from ambientsaga.protocol.reputation import ReputationView, ReputationObservation

        view = ReputationView(score=0.5, confidence=0.8)

        obs1 = ReputationObservation(
            observer_id="agent1",
            target_id="agent2",
            behavior="helped",
            valence=0.3,
            confidence=1.0,
            tick=100,
        )

        view.update(obs1, decay=0.5)
        confidence_after = view.confidence

        obs2 = ReputationObservation(
            observer_id="agent1",
            target_id="agent2",
            behavior="helped",
            valence=0.4,
            confidence=1.0,
            tick=101,
        )

        view.update(obs2, decay=0.5)

        # Should have more observations
        assert len(view.observations) == 2


class TestEmergentEconomy:
    """Tests for EmergentEconomy - economics from exchange history."""

    @pytest.fixture
    def mock_world(self):
        """Create a mock world."""
        world = MagicMock()
        world.get_agent = MagicMock(return_value=MagicMock(wealth=100.0))
        return world

    @pytest.fixture
    def emergent_economy(self, mock_world):
        """Create an EmergentEconomy instance."""
        from ambientsaga.protocol.emergent_econ import EmergentEconomy
        return EmergentEconomy(mock_world)

    def test_initialization(self, emergent_economy):
        """Test emergent economy initialization."""
        assert emergent_economy.world is not None
        assert len(emergent_economy._exchange_history) == 0
        assert len(emergent_economy._resource_values) == 0
        assert len(emergent_economy._trade_patterns) == 0
        assert len(emergent_economy._emergent_markets) == 0

    def test_get_resource_value_no_history(self, emergent_economy):
        """Test get_resource_value with no exchange history."""
        value = emergent_economy.get_resource_value("food")
        assert value == 1.0  # Default value

    def test_get_resource_value_no_agents(self, emergent_economy):
        """Test get_resource_value with no matching agents."""
        # Create mock exchange without giver
        emergent_economy.world.get_agent = MagicMock(return_value=None)
        value = emergent_economy.get_resource_value("food", agent_id="unknown")
        assert value == 1.0  # Default value

    def test_detect_trade_patterns_empty(self, emergent_economy):
        """Test detect_trade_patterns with no exchanges."""
        patterns = emergent_economy.detect_trade_patterns()
        assert isinstance(patterns, list)

    def test_detect_markets_empty(self, emergent_economy):
        """Test detect_markets with no exchanges."""
        markets = emergent_economy.detect_markets()
        assert isinstance(markets, list)

    def test_detect_currency_empty(self, emergent_economy):
        """Test detect_currency with no exchanges."""
        currency = emergent_economy.detect_currency()
        assert isinstance(currency, list)

    def test_get_specialization_empty(self, emergent_economy):
        """Test get_specialization with no exchanges."""
        spec = emergent_economy.get_specialization()
        assert isinstance(spec, dict)

    def test_get_specialization_for_agent(self, emergent_economy):
        """Test get_specialization for specific agent."""
        spec = emergent_economy.get_specialization(agent_id="unknown")
        assert isinstance(spec, dict)

    def test_get_wealth_ranking_empty(self, emergent_economy):
        """Test get_wealth_ranking with no exchanges."""
        ranking = emergent_economy.get_wealth_ranking()
        assert isinstance(ranking, list)

    def test_get_aggregate_stats(self, emergent_economy):
        """Test get_aggregate_stats."""
        stats = emergent_economy.get_aggregate_stats()
        assert isinstance(stats, dict)

    def test_trade_pattern_is_stable(self, emergent_economy):
        """Test TradePattern.is_stable property."""
        from ambientsaga.protocol.emergent_econ import TradePattern

        # Unstable pattern
        unstable = TradePattern(
            resource_given="food",
            resource_received="stone",
            count=3,
            avg_ratio=0.5,
            participants={"agent1"},
            volatility=0.6,
        )
        assert not unstable.is_stable

        # Stable pattern
        stable = TradePattern(
            resource_given="food",
            resource_received="stone",
            count=10,
            avg_ratio=0.5,
            participants={"agent1", "agent2", "agent3"},
            volatility=0.3,
        )
        assert stable.is_stable

    def test_emergent_market_participant_count(self, emergent_economy):
        """Test EmergentMarket.participant_count property."""
        from ambientsaga.protocol.emergent_econ import EmergentMarket

        market = EmergentMarket(
            resource="food",
            trade_partners=["agent1", "agent2", "agent3"],
            detected_at_tick=100,
            avg_transaction_size=5.0,
            total_volume=100.0,
            price_trend=[1.0, 1.1, 1.2],
        )

        assert market.participant_count == 3


class TestEmergentNorms:
    """Tests for EmergentNorms - social norms from interaction patterns."""

    @pytest.fixture
    def mock_world(self):
        """Create a mock world."""
        world = MagicMock()
        # Mock the protocol with traces
        world._protocol = MagicMock()
        world._protocol._traces = []
        return world

    @pytest.fixture
    def emergent_norms(self, mock_world):
        """Create an EmergentNorms instance."""
        from ambientsaga.protocol.social_norms import EmergentNorms
        return EmergentNorms(mock_world)

    def test_initialization(self, emergent_norms):
        """Test emergent norms initialization."""
        assert emergent_norms.world is not None
        assert len(emergent_norms._norms) == 0
        assert len(emergent_norms._institutions) == 0
        assert emergent_norms._norm_counter == 0
        assert emergent_norms._inst_counter == 0

    def test_analyze_traces_no_history(self, emergent_norms, mock_world):
        """Test analyze_traces with no traces."""
        mock_world._protocol._traces = []
        norms = emergent_norms.analyze_traces(tick=100)
        assert isinstance(norms, list)

    def test_analyze_traces_insufficient_data(self, emergent_norms, mock_world):
        """Test analyze_traces with insufficient data."""
        # Add a few traces but not enough to trigger norm detection
        mock_world._protocol._traces = [
            MagicMock(signal="help", accepted=True, actor_id="a1", receiver_id="a2",
                     content={})
            for _ in range(10)
        ]
        norms = emergent_norms.analyze_traces(tick=100)
        # Should not detect norms with insufficient data
        assert isinstance(norms, list)

    def test_get_active_norms(self, emergent_norms):
        """Test getting active norms."""
        norms = emergent_norms.get_active_norms()
        assert isinstance(norms, list)

    def test_get_institutions(self, emergent_norms):
        """Test getting institutions."""
        institutions = emergent_norms.get_institutions()
        assert isinstance(institutions, list)

    def test_apply_norm_influence_no_norms(self, emergent_norms):
        """Test applying norm influence when no norms exist."""
        agent = MagicMock()
        trace = MagicMock()
        result = emergent_norms.apply_norm_influence(agent, trace)
        assert isinstance(result, dict)

    def test_get_summary(self, emergent_norms):
        """Test getting summary."""
        summary = emergent_norms.get_summary()
        assert isinstance(summary, dict)
        assert "norms" in summary or "active_norms" in summary

    def test_norm_is_active(self, emergent_norms):
        """Test Norm.is_active property."""
        from ambientsaga.protocol.social_norms import Norm

        # Active norm
        active_norm = Norm(
            norm_id="norm1",
            name="test_norm",
            description="test",
            trigger_pattern="help",
            count=10,
            participating_agents={"agent1", "agent2"},
            strength=0.5,
            first_emerged=100,
            last_observed=150,
            norm_type="reciprocity",
        )
        assert active_norm.is_active

        # Inactive norm
        inactive_norm = Norm(
            norm_id="norm2",
            name="test_norm2",
            description="test",
            trigger_pattern="help",
            count=10,
            participating_agents={"agent1"},
            strength=0.2,
            first_emerged=100,
            last_observed=150,
            norm_type="reciprocity",
        )
        assert not inactive_norm.is_active

    def test_institution_properties(self, emergent_norms):
        """Test Institution properties."""
        from ambientsaga.protocol.social_norms import Institution

        inst = Institution(
            institution_id="inst1",
            name="test_inst",
            type="leadership",
            founding_tick=100,
            members={"agent1", "agent2"},
            rules=["rule1", "rule2"],
            stability=0.7,
            norm_id="norm1",
        )

        assert inst.institution_id == "inst1"
        assert inst.type == "leadership"
        assert len(inst.members) == 2


class TestLanguageEmergence:
    """Tests for LanguageEmergence - language from shared signal interpretation."""

    @pytest.fixture
    def language_emergence(self):
        """Create a LanguageEmergence instance."""
        from ambientsaga.protocol.language_emergence import LanguageEmergence
        return LanguageEmergence()

    def test_initialization(self, language_emergence):
        """Test language emergence initialization."""
        assert len(language_emergence._vocabulary) == 0
        assert len(language_emergence._agent_signatures) == 0
        assert len(language_emergence._signal_counts) == 0
        assert len(language_emergence._usage_history) == 0

    def test_record_usage(self, language_emergence):
        """Test recording signal usage."""
        language_emergence.record_usage(
            signal="help",
            sender_id="agent1",
            receiver_id="agent2",
            interpreted_meaning="assistance_offered",
            accepted=True,
            tick=100,
            trace_id="trace1",
        )

        assert "help" in language_emergence._vocabulary
        assert "agent1" in language_emergence._agent_signatures

    def test_record_usage_multiple_agents(self, language_emergence):
        """Test recording usage with multiple agents."""
        for i in range(5):
            language_emergence.record_usage(
                signal="help",
                sender_id=f"agent{i}",
                receiver_id=f"agent{i+1}",
                interpreted_meaning="assistance_offered",
                accepted=True,
                tick=100 + i,
                trace_id=f"trace{i}",
            )

        assert language_emergence._vocabulary["help"]["assistance_offered"] == 5

    def test_record_usage_different_meanings(self, language_emergence):
        """Test recording same signal with different meanings."""
        language_emergence.record_usage(
            signal="help",
            sender_id="agent1",
            receiver_id="agent2",
            interpreted_meaning="assistance_offered",
            accepted=True,
            tick=100,
            trace_id="trace1",
        )
        language_emergence.record_usage(
            signal="help",
            sender_id="agent3",
            receiver_id="agent4",
            interpreted_meaning="request_for_help",
            accepted=True,
            tick=101,
            trace_id="trace2",
        )

        assert len(language_emergence._vocabulary["help"]) == 2

    def test_get_shared_signals_empty(self, language_emergence):
        """Test get_shared_signals with no usage."""
        shared = language_emergence.get_shared_signals(threshold=0.5)
        assert len(shared) == 0

    def test_get_shared_signals_threshold(self, language_emergence):
        """Test get_shared_signals with threshold."""
        # Record many usages of the same signal
        for i in range(100):
            language_emergence.record_usage(
                signal="help",
                sender_id=f"agent{i}",
                receiver_id=f"agent{i+1}",
                interpreted_meaning="assistance",
                accepted=True,
                tick=100 + i,
                trace_id=f"trace{i}",
            )

        shared = language_emergence.get_shared_signals(threshold=0.5)
        assert "help" in shared

    def test_get_agent_signals(self, language_emergence):
        """Test getting agent's signals."""
        language_emergence.record_usage(
            signal="help",
            sender_id="agent1",
            receiver_id="agent2",
            interpreted_meaning="assistance",
            accepted=True,
            tick=100,
            trace_id="trace1",
        )
        language_emergence.record_usage(
            signal="gift",
            sender_id="agent1",
            receiver_id="agent3",
            interpreted_meaning="sharing",
            accepted=True,
            tick=101,
            trace_id="trace2",
        )

        # Check that agent1's signals are recorded
        assert "help" in language_emergence._agent_signatures.get("agent1", {})
        assert "gift" in language_emergence._agent_signatures.get("agent1", {})

    def test_invent_signal(self, language_emergence):
        """Test inventing a new signal."""
        signal = language_emergence.invent_signal(
            agent_id="agent1",
            meaning="new_concept",
            tick=100,
        )

        # Signal should be created
        assert signal is not None

    def test_invent_signal_imitation(self, language_emergence):
        """Test that invention often results in imitation."""
        # Add an existing signal
        for i in range(10):
            language_emergence.record_usage(
                signal="help",
                sender_id=f"agent{i}",
                receiver_id=f"agent{i+1}",
                interpreted_meaning="assistance",
                accepted=True,
                tick=100 + i,
                trace_id=f"trace{i}",
            )

        # Invent signal - should often imitate existing
        signal = language_emergence.invent_signal(
            agent_id="agent_new",
            meaning="assistance",
            tick=200,
        )

        # Most of the time it should return "help"
        # (75% chance to imitate based on the code)

    def test_get_vocabulary_stats(self, language_emergence):
        """Test getting vocabulary statistics."""
        language_emergence.record_usage(
            signal="help",
            sender_id="agent1",
            receiver_id="agent2",
            interpreted_meaning="assistance",
            accepted=True,
            tick=100,
            trace_id="trace1",
        )
        language_emergence.record_usage(
            signal="gift",
            sender_id="agent1",
            receiver_id="agent2",
            interpreted_meaning="sharing",
            accepted=True,
            tick=101,
            trace_id="trace2",
        )

        stats = language_emergence.get_vocabulary_stats()
        assert "total_signals" in stats
        assert "total_usages" in stats
        assert stats["total_signals"] == 2

    def test_get_signal_evolution(self, language_emergence):
        """Test getting signal evolution."""
        language_emergence.record_usage(
            signal="help",
            sender_id="agent1",
            receiver_id="agent2",
            interpreted_meaning="assistance",
            accepted=True,
            tick=100,
            trace_id="trace1",
        )

        evolution = language_emergence.get_signal_evolution("help")
        assert isinstance(evolution, list)
