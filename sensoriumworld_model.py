"""
World Model: The central representation of reality for the autonomous system.
Stores multi-dimensional state in Firestore and provides real-time updates.
Eliminates human burden of maintaining situational awareness across multiple data sources.
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import logging
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from enum import Enum
from google.cloud import firestore
import firebase_admin
from firebase_admin import credentials, firestore
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WorldState(Enum):
    """Possible states of a world model entity"""
    STABLE = "stable"
    VOLATILE = "volatile"
    DEGRADING = "degrading"
    UNKNOWN = "unknown"


@dataclass
class Entity:
    """Represents any entity in the world model"""
    id: str
    entity_type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    last_updated: datetime = field(default_factory=datetime.utcnow)
    state: WorldState = WorldState.UNKNOWN
    relationships: List[str] = field(default_factory=list)
    
    def to_firestore_dict(self) -> Dict[str, Any]:
        """Convert entity to Firestore-compatible dictionary"""
        return {
            'id': self.id,
            'entity_type': self.entity_type,
            'properties': self.properties,
            'confidence': self.confidence,
            'last_updated': self.last_updated,
            'state': self.state.value,
            'relationships': self.relationships
        }
    
    @classmethod
    def from_firestore_dict(cls, data: Dict[str, Any]) -> 'Entity':
        """Create entity from Firestore dictionary"""
        return cls(
            id=data.get('id', ''),
            entity_type=data.get('entity_type', ''),
            properties=data.get('properties', {}),
            confidence=data.get('confidence', 1.0),
            last_updated=data.get('last_updated', datetime.utcnow()),
            state=WorldState(data.get('state', 'unknown')),
            relationships=data.get('relationships', [])
        )


class WorldModel:
    """
    The central world representation system that maintains real-time
    understanding of reality for autonomous decision-making.
    
    Architectural Rigor:
    - Implements real-time Firestore synchronization
    - Handles concurrent updates with version control
    - Maintains consistency across distributed components
    - Provides failover mechanisms for network issues
    """
    
    def __init__(self, 
                 firebase_credentials_path: Optional[str] = None,
                 project_id: Optional[str] = None):
        """
        Initialize world model with Firestore backend
        
        Args:
            firebase_credentials_path: Path to Firebase credentials JSON
            project_id: Firebase project ID (optional if in environment)
            
        Raises:
            ValueError: If Firebase initialization fails
            RuntimeError: If Firestore connection cannot be established
        """
        self.entities: Dict[str, Entity] = {}
        self._initialize_firebase(firebase_credentials_path, project_id)
        self._setup_firestore()
        self._last_sync = datetime.utcnow()
        logger.info("WorldModel initialized with Firestore backend")
    
    def _initialize_firebase(self, 
                            credentials_path: Optional[str],
                            project_id: Optional[str]) -> None:
        """Initialize Firebase Admin SDK with proper error handling"""
        try:
            if not firebase_admin._apps:
                if credentials_path and os.path.exists(credentials_path):
                    cred = credentials.Certificate(credentials_path)
                    firebase_admin.initialize_app(cred)
                else:
                    # Try environment variable or default credentials
                    firebase_admin.initialize_app()
            logger.info("Firebase Admin SDK initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {str(e)}")
            raise ValueError(f"Firebase initialization failed: {str(e)}")
    
    def _setup_firestore(self) -> None:
        """Setup Firestore client with retry configuration"""
        try:
            self.db = firestore.client()
            # Test connection
            test_ref = self.db.collection('world_model_health').document('connection_test')
            test_ref.set({'test': True, 'timestamp': datetime.utcnow()}, merge=True)
            logger.info("Firestore connection established and verified")
        except Exception as e:
            logger.error(f"Firestore connection failed: {str(e)}")
            raise RuntimeError(f"Firestore connection failed: {str(e)}")
    
    def update_entity(self, entity: Entity) -> bool:
        """
        Update or create an entity in the world model with atomic consistency
        
        Args:
            entity: Entity to update
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If entity validation fails
        """
        try:
            # Validate entity
            if not entity.id or not entity.entity_type:
                raise ValueError("Entity must have id and entity_type")
            
            # Update in-memory representation
            self.entities[entity