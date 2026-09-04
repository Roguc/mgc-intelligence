class OrganizationRegistry:
 def __init__(self):self._units={}
 def register(self,unit):self._units[unit.unit_id]=unit
 def get(self,unit_id):return self._units[unit_id]
 def all(self):return list(self._units.values())
class AgentRegistry:
 def __init__(self):self._agents={}
 def register(self,agent):self._agents[agent.agent_id]=agent
 def get(self,agent_id):return self._agents[agent_id]
 def for_capabilities(self,terms):
  sought=' '.join(terms).casefold();return [a for a in self._agents.values() if any(x.casefold() in sought for x in a.capabilities)]
 def all(self):return list(self._agents.values())
class MissionRegistry:
 def __init__(self):self._missions={}
 def register(self,mission):self._missions[mission.mission_id]=mission;return mission
 def get(self,mission_id):return self._missions[mission_id]
