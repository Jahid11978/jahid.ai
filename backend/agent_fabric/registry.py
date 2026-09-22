from __future__ import annotations
from dataclasses import replace
from .models import Agent, AgentGroup

class AgentRegistry:
    def __init__(self):
        """Initialize an empty registry of agents and groups."""
        self._agents={}; self._groups={}
    def register_agent(self, agent: Agent):
        """Register and return an agent, replacing one with the same ID.

        Raises ``ValueError`` when ``max_concurrency`` is less than one.
        """
        if agent.max_concurrency < 1: raise ValueError("max_concurrency must be >= 1")
        self._agents[agent.id]=agent; return agent
    def register_group(self, group: AgentGroup):
        """Register a group and assign its ID to each referenced agent.

        Raises ``ValueError`` if a referenced agent is not registered.
        """
        missing=[x for x in group.agent_ids if x not in self._agents]
        if missing: raise ValueError(f"unknown agents: {missing}")
        self._groups[group.id]=group
        for aid in group.agent_ids: self._agents[aid]=replace(self._agents[aid],group_id=group.id)
        return group
    def get_agent(self, agent_id):
        """Return the agent identified by ``agent_id``."""
        return self._agents[agent_id]
    def get_group(self, group_id):
        """Return the agent group identified by ``group_id``."""
        return self._groups[group_id]
    def agents(self):
        """Return all registered agents in registration order."""
        return tuple(self._agents.values())
    def groups(self):
        """Return all registered groups in registration order."""
        return tuple(self._groups.values())
    def route(self, capability, group_id=None):
        """Return the highest-capacity enabled agent for a capability.

        When ``group_id`` is provided, limit routing to that enabled group.
        Raises ``KeyError`` for an unknown group and ``LookupError`` when the
        group is disabled or no eligible agent provides the capability.
        """
        if group_id is not None and not self.get_group(group_id).enabled: raise LookupError(f"disabled group: {group_id}")
        candidates=self._agents.values() if group_id is None else (self._agents[x] for x in self.get_group(group_id).agent_ids)
        matches=[a for a in candidates if a.enabled and capability in a.capabilities]
        if not matches: raise LookupError(f"no enabled agent for capability: {capability}")
        return sorted(matches,key=lambda a:(a.max_concurrency,a.id),reverse=True)[0]
