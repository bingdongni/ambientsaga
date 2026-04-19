"""
Emergent Protocol System — fusion of interaction, reputation, economics, language, and norms.

Submodules:
- interaction: MetaProtocol, Trace, Exchange
- reputation: ReputationNetwork
- emergent_econ: EmergentEconomy
- language_emergence: LanguageEmergence
- social_norms: EmergentNorms
"""

from ambientsaga.protocol.emergent_econ import EmergentEconomy, EmergentMarket, TradePattern
from ambientsaga.protocol.interaction import (
    BASIC_SIGNALS,
    CONTENT_TYPES,
    Exchange,
    MetaProtocol,
    Trace,
)
from ambientsaga.protocol.language_emergence import LanguageEmergence, SignalUsage
from ambientsaga.protocol.reputation import ReputationNetwork, ReputationObservation, ReputationView
from ambientsaga.protocol.social_norms import EmergentNorms, Institution, Norm

__all__ = [
    "MetaProtocol", "Trace", "Exchange", "BASIC_SIGNALS", "CONTENT_TYPES",
    "ReputationNetwork", "ReputationObservation", "ReputationView",
    "EmergentEconomy", "TradePattern", "EmergentMarket",
    "LanguageEmergence", "SignalUsage",
    "EmergentNorms", "Norm", "Institution",
]
