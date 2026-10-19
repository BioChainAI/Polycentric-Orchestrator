"""The Mind's Eye is a multi-perspective, replayable scene graph, not one agent's truth."""
from shdccp_core.geometry import triple_quad, cubic_address
from manifold_projection.projector import scene_points, lod_group

class Manifold:
    def __init__(self, *, voxel_edge=4):
        self.scenes={}
        self.voxel_edge=voxel_edge
    def ingest(self,event):
        scene=self.scenes.setdefault(event['scene_id'],{})
        # Preserve all perspectives in event history; scene displays the latest per agent.
        prior=scene.get(event['agent_id'])
        if prior is None or event['seq']>prior['seq']:
            scene[event['agent_id']]=event
    def snapshot(self,scene_id):
        perspective=self.scenes.get(scene_id,{})
        positions={k:tuple(v.get('world_point',v['point'])) for k,v in perspective.items()}
        ordered=sorted(positions)
        triad=triple_quad(*(positions[x] for x in ordered[:3])) if len(ordered)>=3 else None
        clocks=[int(v['time']['epoch_ns']) for v in perspective.values()]
        spread=(max(clocks)-min(clocks)) if clocks else 0
        # Reference temporal coincidence gate: physical clock uncertainties + one 40-Hz tick.
        uncertainty=max((int(v['time']['uncertainty_ns']) for v in perspective.values()),default=0)
        temporally_aligned=(spread <= 25_000_000 + 2*uncertainty)
        data={
            'scene_id':scene_id,'perspectives':len(perspective),
            'frames':sorted({v['frame_id'] for v in perspective.values()}),
            'views':{k:v['view'] for k,v in sorted(perspective.items())},
            'spatial':scene_points(positions),
            'lod_cubes':lod_group(list(positions.values()),self.voxel_edge),
            'temporal_spread_ns':spread,
            'temporally_aligned':temporally_aligned,
            'geometric_alignment_status':'registered-frame-and-clock-window' if temporally_aligned else 'temporal-alignment-insufficient',
            'tqf_triad':{'agent_ids':ordered[:3],**triad} if triad else None,
            'claims':{k:v['claim'] for k,v in sorted(perspective.items())},
            'evidence_hashes':{k:v['evidence_hash'] for k,v in sorted(perspective.items())},
            'calibrations':{k:v.get('frame_calibration_digest') for k,v in sorted(perspective.items())}
        }
        return data
