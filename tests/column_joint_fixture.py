"""Synthetic two-storey column and four orthogonal beams, with native catalogs."""
from copy import deepcopy
from hashlib import sha256
import json
import math

from column_bank_fixture import encoded
from column_stability_fixture import StiffnessBank


class JointBank(StiffnessBank):
    def __init__(self):
        super().__init__()
        self.calls = {k:v for k,v in self.calls.items() if k[1]!='point'}
        self.frame_names = list(self.members)
        self.point_names = []
        for name,xyz in [('P0',(0,0,0)),('P1',(0,0,4)),('P2',(0,0,8)),
                         ('PX+',(5,0,4)),('PX-',(-5,0,4)),('PY+',(0,5,4)),('PY-',(0,-5,4))]:
            self.point(name,xyz)
        for name,i,j in ((self.members[0],'P0','P1'),(self.members[1],'P1','P2')):
            self.frame(name,i,j,1,'RECT_SYNTHETIC',[0,1,0,0,0,1,1,0,0])
        self.call('PropFrame.GetRectangle','frame_section','BEAM_SYNTHETIC',
            'FileName MatProp T3 T2 Color notes GUID pRetVal',['','CONCRETE_SYNTHETIC',.7,.6,0,'','',0])
        self.call('PropFrame.GetRebarBeam','beam_section','BEAM_SYNTHETIC',
            'MatPropLong MatPropConfine CoverTop CoverBot TopLeftArea TopRightArea BotLeftArea BotRightArea pRetVal',
            ['STEEL_SYNTHETIC','TIE_STEEL_SYNTHETIC',.06,.06,0,0,0,0,0])
        for name,i,j,matrix in [('BX+','P1','PX+',[1,0,0,0,0,-1,0,1,0]),
            ('BX-','PX-','P1',[1,0,0,0,0,-1,0,1,0]),
            ('BY+','P1','PY+',[0,0,1,1,0,0,0,1,0]),('BY-','PY-','P1',[0,0,1,1,0,0,0,1,0])]:
            self.frame(name,i,j,2,'BEAM_SYNTHETIC',matrix)

    def point(self,name,xyz):
        if name not in self.point_names: self.point_names.append(name)
        self.call('PointObj.GetCoordCartesian','point',name,'X Y Z pRetVal',list(xyz)+[0])
        self.calls[('PointObj.GetCoordCartesian','point',name)]['args']=[name,0.0,0.0,0.0,'Global']
        self.call('PointObj.GetRestraint','point',name,'Value pRetVal',[[False]*6,0])

    def frame(self,name,i,j,orientation,section,matrix):
        if name not in self.frame_names: self.frame_names.append(name)
        self.call('FrameObj.GetPoints','frame',name,'Point1 Point2 pRetVal',[i,j,0])
        self.call('FrameObj.GetDesignOrientation','frame',name,'DesignOrientation pRetVal',[orientation,0])
        self.call('FrameObj.GetSection','frame',name,'PropName SAuto pRetVal',[section,'',0])
        self.call('FrameObj.GetTransformationMatrix','frame',name,'Value pRetVal',[matrix,0])
        self.calls[('FrameObj.GetTransformationMatrix','frame',name)]['args']=[name,[],True]

    def reverse(self,name):
        ends=self.calls[('FrameObj.GetPoints','frame',name)]['raw_response']
        ends[:2]=ends[1::-1]
        matrix=self.calls[('FrameObj.GetTransformationMatrix','frame',name)]['raw_response'][0]
        for i in (0,2,3,5,6,8):matrix[i]=-matrix[i]

    def rotate_global(self,degrees):
        c,s=math.cos(math.radians(degrees)),math.sin(math.radians(degrees))
        for key,call in self.calls.items():
            if key[0]=='PointObj.GetCoordCartesian':
                xyz=call['raw_response'];x,y=xyz[:2];xyz[:2]=[c*x-s*y,s*x+c*y]
            if key[0]=='FrameObj.GetTransformationMatrix':
                m=call['raw_response'][0];a,b=m[:3],m[3:6]
                m[:3]=[c*x-s*y for x,y in zip(a,b)];m[3:6]=[s*x+c*y for x,y in zip(a,b)]

    def unequal_rotated_lower(self):
        name=self.members[0];section='LOWER_RECT_SYNTHETIC'
        self.calls[('FrameObj.GetSection','frame',name)]['raw_response'][0]=section
        self.calls[('FrameObj.GetTransformationMatrix','frame',name)]['raw_response'][0]=[0,0,-1,0,1,0,1,0,0]
        for api,kind in [('PropFrame.GetRectangle','frame_section'),('PropFrame.GetRebarColumn','column_section'),
                         ('PropFrame.GetSectProps','frame_section')]:
            value=deepcopy(self.calls[(api,kind,'RECT_SYNTHETIC')])
            self.call(api,kind,section,' '.join(value['output_names']),value['raw_response'])
        self.calls[('PropFrame.GetRectangle','frame_section',section)]['raw_response'][3]=.6
        props=self.calls[('PropFrame.GetSectProps','frame_section',section)]['raw_response']
        props[0]=.48;props[4:6]=[.0144,.0256];props[10:12]=[.17320508075688773,.2309401076758503]
        self.calls[('PropMaterial.GetORebar_1','material','TIE_STEEL_SYNTHETIC')]['raw_response'][0]=500000

    def files(self):
        for api,kind,names in [('FrameObj.GetNameList','frames',self.frame_names),('PointObj.GetNameList','points',self.point_names)]:
            self.call(api,kind,None,'NumberNames MyName pRetVal',[len(names),list(names),0])
            self.calls[(api,kind,None)]['entity']={'kind':kind}
        files=super().files()
        catalog=json.loads(files['catalogs.json'])
        catalog['names'].update(frames=self.frame_names,points=self.point_names)
        catalog['catalog_complete'].update(frames=True,points=True)
        files['catalogs.json']=encoded(catalog)
        files['archive-manifest.json']=encoded({'schema':'tbdy.full-bank.archive-manifest.v1',
            'files':{name:{'sha256':sha256(raw).hexdigest(),'bytes':len(raw)} for name,raw in files.items() if name!='archive-manifest.json'}})
        return files
