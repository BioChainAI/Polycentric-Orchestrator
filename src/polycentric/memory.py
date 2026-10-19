"""Content-addressed append chain for accepted events; no decentralized consensus."""
from shdccp_core.envelope import digest_hex
class CentralManifoldMemory:
    def __init__(self): self.events=[];self.chain=[]
    def append(self,event):
        self.events.append(dict(event))
        prior=self.chain[-1]['hash'] if self.chain else 'GENESIS'
        entry={'prior':prior,'event_id':event['event_id'],'scene_id':event['scene_id']}
        entry['hash']=digest_hex(entry)
        self.chain.append(entry)
        return entry['hash']
    def verify(self):
        prior='GENESIS'
        if len(self.events)!=len(self.chain): return False
        for event,entry in zip(self.events,self.chain):
            if entry['prior']!=prior or entry['event_id']!=event['event_id']: return False
            if entry['hash']!=digest_hex({k:v for k,v in entry.items() if k!='hash'}): return False
            prior=entry['hash']
        return True
