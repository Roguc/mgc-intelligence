from dataclasses import dataclass
@dataclass(frozen=True)
class InferenceRequest: mission_id:str; agent_id:str; prompt:str
@dataclass(frozen=True)
class InferenceResult: text:str; model:str; input_tokens:int=0; output_tokens:int=0; cost_usd:float=0.0
class MockInferenceGateway:
 def __init__(self,replies=None):self.replies=replies or {};self.requests=[]
 def execute(self,request):self.requests.append(request);return InferenceResult(self.replies.get(request.agent_id,"MOCK_INFERENCE_RESULT"),"mock",len(request.prompt.split()),1,0.0)
