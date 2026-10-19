"""Purpose-bound federation admission. A policy check is not a judgment of truth."""
from dataclasses import dataclass

@dataclass(frozen=True)
class ScenePolicy:
    permitted_purposes:tuple=('scene_alignment',)
    required_consent:str='spatial_share'
    allowed_frames:tuple=('world',)
    max_clock_uncertainty_ns:int=10_000_000
    max_clock_skew_ns:int=1_000_000_000
    require_human_for_actions:bool=True
    def authorize(self,observation,known_frames=None):
        if observation.get('purpose') not in self.permitted_purposes:
            return False,'purpose_denied'
        if self.required_consent not in observation.get('consent_scopes',[]):
            return False,'consent_missing'
        if observation.get('frame_id') not in (known_frames or self.allowed_frames):
            return False,'unknown_frame_transform'
        t=observation.get('time',{})
        if not isinstance(t.get('uncertainty_ns'),int) or t['uncertainty_ns'] > self.max_clock_uncertainty_ns or t['uncertainty_ns']<0:
            return False,'clock_uncertainty'
        return True,'policy_admitted'
