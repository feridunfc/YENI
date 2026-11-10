"""Synthetic beam source bank with exact endpoint areas and mixed controls."""
from column_kinematics_fixture import KinematicsBank

TABLE='Concrete Beam Design Summary - TS 500-2000(R2018)'
FIELDS='Story Label UniqueName DesignSect Station Status AsTopCombo AsMinTop AsTop AsBotCombo AsMinBot AsBot TLngCombo TLngRebar totTopRebar totBotRebar WarnMsg ErrMsg'.split()


class BeamBank(KinematicsBank):
    def __init__(self):
        super().__init__();self.beam_rows=[];self.beam_units={k:'m2' for k in ('AsMinTop','AsTop','AsMinBot','AsBot','TLngRebar','totTopRebar','totBotRebar')}
        self.beam_units['Station']='m'
        for beam in ('BX+','BX-','BY+','BY-'):
            self.call('FrameObj.GetEndLengthOffset','frame',beam,'AutoOffset Length1 Length2 RZ pRetVal',[True,.25,.25,0,0])
            self.forces[beam]=[]
            for station in (.25,2.5,4.75):
                for case in ('G','SUM','RS_SUM'):
                    self.forces[beam].append([beam,station,beam+'-E',station,case,
                        'Max' if case=='RS_SUM' else 'Single Value',0,-25,10,0,0,0,45])
                self.beam_rows.append(dict(zip(FIELDS,['SYNTHETIC_STORY',beam,beam,'BEAM_SYNTHETIC',str(station),
                    'No Message','SUM','.0004','.0009','RS_SUM','.0003','.0005','SUM','.0006',
                    '.0012','.0008','No Message','No Message'])))

    def files(self):
        self.table(TABLE,FIELDS,self.beam_rows,self.beam_units)
        return super().files()
