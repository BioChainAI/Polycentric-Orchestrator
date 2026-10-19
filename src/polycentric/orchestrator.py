"""Polycentric ingress + policy + clock gate + shared spatial snapshot reference."""
import time
from shdccp_core.envelope import verify_dev_hmac, validate_tile_hex, digest_hex
from .governance import ScenePolicy
from .memory import CentralManifoldMemory
from .manifold import Manifold
from .frames import FrameRegistry

class AdmissionError(ValueError): pass

class PolycentricOrchestrator:
    def __init__(self, *, scene_policy=None, clock_ns=None):
        self.policy=scene_policy or ScenePolicy()
        self.clock_ns=clock_ns
        self.agent_keys={}
        self.last_sequence={}
        self.seen_events=set()
        self.memory=CentralManifoldMemory()
        self.manifold=Manifold()
        self.frames=FrameRegistry()
        self.quarantine=[]
    def register_dev_agent(self, agent_id, key):
        if not isinstance(key,bytes) or len(key)<16: raise ValueError('dev key must be >=16 bytes')
        self.agent_keys[agent_id]=key
    def register_frame(self, frame_id, matrix, translation, approved_by):
        self.frames.register(frame_id,matrix,translation,approved_by)
    def handshake(self,agent_id):
        if agent_id not in self.agent_keys: raise AdmissionError('unregistered_agent')
        now=time.time_ns() if self.clock_ns is None else self.clock_ns
        return {'protocol':'SHDCCP-EINSTEIN-1','schema_version':'1.0.0',
                'accepted':True,'registry_epoch':1,'orchestrator_time_ns':now,
                'spatial_frames':list(self.frames.names),
                'purpose_scopes':list(self.policy.permitted_purposes),
                'geometric_tick_ns':25_000_000,'geometric_tick_is_clock_sync':False}
    def admit(self,event):
        def reject(reason):
            self.quarantine.append({'event_id':event.get('event_id'),'reason':reason})
            raise AdmissionError(reason)
        agent=event.get('agent_id')
        if agent not in self.agent_keys: reject('unregistered_agent')
        if not verify_dev_hmac(event,self.agent_keys[agent]): reject('dev_mac_invalid')
        bare={k:v for k,v in event.items() if k not in ('event_id','dev_mac')}
        if event.get('event_id')!=digest_hex(bare): reject('event_digest_mismatch')
        if event['event_id'] in self.seen_events: reject('duplicate_event')
        seq=event.get('seq')
        if not isinstance(seq,int) or seq<=self.last_sequence.get(agent,0): reject('sequence_replay')
        if event.get('protocol_id')!='SHDCCP-EINSTEIN-1': reject('protocol_incompatible')
        try: fields=validate_tile_hex(event.get('tile_hex'))
        except (ValueError,TypeError): reject('invalid_tile')
        if fields['form_id']!=3: reject('reference_only_accepts_form3')
        if event.get('time',{}).get('cycle_step')!=fields['cycle_step']:
            reject('cycle_step_mismatch')
        if not isinstance(event.get('point'),list) or len(event['point'])!=3 or any(not isinstance(v,int) for v in event['point']):
            reject('invalid_coordinate')
        ok,reason=self.policy.authorize(event,self.frames.names)
        if not ok: reject(reason)
        now=time.time_ns() if self.clock_ns is None else self.clock_ns
        if abs(event['time']['epoch_ns']-now)>self.policy.max_clock_skew_ns:
            reject('clock_skew')
        if not event.get('evidence_hash'): reject('evidence_required')
        normalized=dict(event)
        normalized['world_point'],normalized['frame_calibration_digest']=self.frames.normalize(event['frame_id'],tuple(event['point']))
        self.last_sequence[agent]=seq
        self.seen_events.add(event['event_id'])
        chain_root=self.memory.append(normalized)
        self.manifold.ingest(normalized)
        return {'admitted':True,'event_id':event['event_id'],'memory_root':chain_root,
                'status':'observation_recorded_not_truth_certified'}
    def snapshot(self, scene_id):
        result=self.manifold.snapshot(scene_id)
        result['memory_root']=self.memory.chain[-1]['hash'] if self.memory.chain else None
        result['source_event_count']=len(self.memory.events)
        result['governance']='evidence-based; no automatic actuation or global truth claims'
        return result
