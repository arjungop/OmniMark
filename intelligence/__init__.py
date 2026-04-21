"""
The OmniMark Intelligence Layer

Not prompt engineering. Actual AI that:
- Scores accounts based on learned patterns
- Detects what signals lead to deals
- Predicts best outreach strategy per persona
- Learns from every outcome
"""

from .ai_brain import (
    AIBrain,
    AccountScoringEngine,
    PatternDetectionEngine,
    StrategyPredictionEngine,
    ProactiveIntelligenceEngine
)

__all__ = [
    'AIBrain',
    'AccountScoringEngine',
    'PatternDetectionEngine',
    'StrategyPredictionEngine',
    'ProactiveIntelligenceEngine'
]
