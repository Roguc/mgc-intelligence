class CorporateAPI:
 def __init__(self,platform):self.platform=platform
 def organization(self):return [x.__dict__ for x in self.platform.organizations.all()]
 def agents(self):return [x.__dict__ for x in self.platform.agents.all()]
 def case_state(self,case_id):return self.platform.states[case_id].as_dict()
