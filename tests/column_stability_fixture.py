"""Independent source values for a synthetic 800 mm square concrete section."""
from column_demand_fixture import DesignBank


class StiffnessBank(DesignBank):
    def __init__(self):
        super().__init__()
        self.call('PropFrame.GetSectProps','frame_section','RECT_SYNTHETIC',
            'Area As2 As3 Torsion I22 I33 S22 S33 Z22 Z33 R22 R33 pRetVal',
            [.64,.533333333333,.533333333333,.0577067,.03413333333333333,.03413333333333333,
             .085333333333,.085333333333,.128,.128,.2309401076758503,.2309401076758503,0])
        self.call('PropMaterial.GetMPIsotropic','material','CONCRETE_SYNTHETIC',
            'E U A G pRetVal',[34000000,.2,.00001,14166666.666666666,0])

    def set_static_vector(self,vector):
        self.combos['SUM']=(0,[(0,'G',1)])
        for rows in self.forces.values():
            for row in rows:
                if row[4] in ('G','SUM'): row[7:]=list(vector)

    def unequal_rectangle(self):
        # T2=.6 m, T3=.8 m. I22=.0256 m4; I33=.0144 m4.
        self.calls[('PropFrame.GetRectangle','frame_section','RECT_SYNTHETIC')]['raw_response'][2:4]=[.8,.6]
        props=self.calls[('PropFrame.GetSectProps','frame_section','RECT_SYNTHETIC')]['raw_response']
        props[0]=.48; props[4:6]=[.0256,.0144]; props[10:12]=[.2309401076758503,.17320508075688773]
