"""Asymmetric beam-end area proposals with native unreleased rotations."""
from beam_reference_fixture import BeamBank


class ScenarioBank(BeamBank):
    def __init__(self):
        super().__init__()
        targets={'BX+':(.0016,.0009),'BX-':(.0024,.0012),'BY+':(.0012,.0008),'BY-':(.0018,.0010)}
        for beam in targets:
            self.call('FrameObj.GetReleases','frame',beam,'II JJ StartValue EndValue pRetVal',
                [[False]*6,[False]*6,[0.0]*6,[0.0]*6,0])
        for row in self.beam_rows:
            top,bottom=targets[row['UniqueName']]
            row.update(totTopRebar=str(top),totBotRebar=str(bottom))
