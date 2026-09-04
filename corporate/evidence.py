from hashlib import sha256
class EvidenceCore:
 def register(self,case_id,paths):return [{"case_id":case_id,"name":p.name,"path":str(p),"sha256":sha256(p.read_bytes()).hexdigest()} for p in paths]
