"""Explicit registered integer-isometry calibration of agent-local cubic coordinates.
Frame registration is orchestrator-administered in this reference; production requires
signed calibration evidence, versioning, expiry and uncertainty covariance.
"""
from shdccp_core.envelope import digest_hex
I=((1,0,0),(0,1,0),(0,0,1))
class FrameRegistry:
    def __init__(self):
        self.transforms={'world':{'R':I,'t':(0,0,0),'approved_by':'bootstrap'}}
    def register(self, frame_id, R, t, approved_by):
        if not approved_by or not isinstance(frame_id,str) or not frame_id:
            raise ValueError('frame identity and approver are mandatory')
        if len(R)!=3 or any(len(row)!=3 for row in R) or len(t)!=3:
            raise ValueError('expected 3x3 matrix and 3-vector translation')
        if any(type(v) is not int or v not in (-1,0,1) for row in R for v in row):
            raise ValueError('integer orthogonal matrix only')
        if any(sum(R[i][k]*R[j][k] for k in range(3)) != int(i==j) for i in range(3) for j in range(3)):
            raise ValueError('matrix not orthogonal')
        if any(type(v) is not int for v in t):
            raise ValueError('integer translation required')
        self.transforms[frame_id]={'R':tuple(map(tuple,R)),'t':tuple(t),'approved_by':approved_by}
    def normalize(self,frame_id,p):
        if frame_id not in self.transforms: raise ValueError('frame unknown')
        tf=self.transforms[frame_id];R=tf['R'];t=tf['t']
        world=tuple(sum(R[i][j]*p[j] for j in range(3))+t[i] for i in range(3))
        return world,digest_hex(tf)
    @property
    def names(self):return tuple(sorted(self.transforms))
