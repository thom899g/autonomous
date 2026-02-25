"""
Sensorium: The Autonomous World Modeling System
Core 1 of the Cognitive Liberation Engine
Eliminates human cognitive toil in data synthesis and reality modeling
"""

from .world_model import WorldModel
from .data_ingestors import DataIngestor, FirestoreIngestor, APIStreamIngestor
from .perception_engine import PerceptionEngine

__version__ = "1.0.0"
__all__ = ["WorldModel", "DataIngestor", "FirestoreIngestor", "APIStreamIngestor", "PerceptionEngine"]