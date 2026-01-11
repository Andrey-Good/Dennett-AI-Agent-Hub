# dennett/config/settings.py
"""
Settings: Configuration for Dennett Core.
"""

class Settings:
    """Global settings for Dennett Core."""
    
    # Database
    DATABASE_PATH = "storage.db"
    
    # API
    API_HOST = "0.0.0.0"
    API_PORT = 8000
    
    # Workers
    AGENT_LEASE_TTL_SEC = 600
    INFERENCE_LEASE_TTL_SEC = 300
    POLL_INTERVAL_SEC = 0.1
    
    # Priority  (base priority коридоры)
    PRIORITY_CHAT = 90
    PRIORITY_MANUAL_RUN = 70
    PRIORITY_INTERNAL_NODE = 50
    PRIORITY_TRIGGER = 30
    
    # Anti-starvation
    AGING_INTERVAL_SEC = 60
    AGING_THRESHOLD_SEC = 300
    AGING_BOOST = 10
    AGING_CAP_COMMUNITY = 65

settings = Settings()
