"""
swarm module initialization
"""

from swarm.config import settings
from swarm.orchestrator import register_agent, AGENT_REGISTRY, discover_and_load_agents
