#!/usr/bin/env python3
"""Fixed independent arithmetic for the preserved YENI recipe examples.

This file contains a finite set of hand-check arithmetic and data-contract
fixtures. It is not a solver, check owner, pipeline or ETABS adapter. It never
imports YENI, interprets formula text or closes an engineering check.
Expected values come from GOLDEN_CASES.json. All numeric input contracts and
assertion identities are bound to this reviewed frozen implementation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from math import pi, sqrt, sin, radians, degrees, atan2


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_hash(value) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":"), allow_nan=False)
    return sha256_text(raw)


def oracle_ge_src_001():
    """Integrity and change detection for the three-model package. Independent frozen example only."""
    return {
        'GE-SRC-001-A01': 197+258+261,
        'GE-SRC-001-A02': sha256_text('abc'),
        'GE-SRC-001-A03': sha256_text('abc') != sha256_text('abd'),
    }

def oracle_ge_src_002():
    """Model identity and dimensional unit conversion. Independent frozen example only."""
    return {
        'GE-SRC-002-A01': 471.11*1000,
        'GE-SRC-002-A02': 5.23*1000,
        'GE-SRC-002-A03': 30*30*100,
        'GE-SRC-002-A04': 'IDECAD_TEMPLATE_2STORY_10M_30CM' == 'IDECAD_TEMPLATE_3STORY_9M_40CM',
    }

def oracle_ge_src_003():
    """Force coverage on both sides of an internal joint. Independent frozen example only."""
    expected_keys = [['C-DEMO', 'DX', 'E1/I', 0, 0],
     ['C-DEMO', 'DX', 'E1/J', 1.5, 1.5],
     ['C-DEMO', 'DX', 'E2/I', 1.5, 0],
     ['C-DEMO', 'DX', 'E2/J', 3, 1.5],
     ['C-DEMO', 'DY', 'E1/I', 0, 0],
     ['C-DEMO', 'DY', 'E1/J', 1.5, 1.5],
     ['C-DEMO', 'DY', 'E2/I', 1.5, 0],
     ['C-DEMO', 'DY', 'E2/J', 3, 1.5]]
    observed_missing = [['C-DEMO', 'DX', 'E1/I', 0, 0],
     ['C-DEMO', 'DX', 'E1/J', 1.5, 1.5],
     ['C-DEMO', 'DX', 'E2/I', 1.5, 0],
     ['C-DEMO', 'DX', 'E2/J', 3, 1.5],
     ['C-DEMO', 'DY', 'E1/I', 0, 0],
     ['C-DEMO', 'DY', 'E1/J', 1.5, 1.5],
     ['C-DEMO', 'DY', 'E2/J', 3, 1.5]]
    observed_duplicate = [['C-DEMO', 'DX', 'E1/I', 0, 0],
     ['C-DEMO', 'DX', 'E1/J', 1.5, 1.5],
     ['C-DEMO', 'DX', 'E2/I', 1.5, 0],
     ['C-DEMO', 'DX', 'E2/J', 3, 1.5],
     ['C-DEMO', 'DY', 'E1/I', 0, 0],
     ['C-DEMO', 'DY', 'E1/J', 1.5, 1.5],
     ['C-DEMO', 'DY', 'E2/J', 3, 1.5],
     ['C-DEMO', 'DY', 'E1/J', 1.5, 1.5]]
    return {
        'GE-SRC-003-A01': len(expected_keys),
        'GE-SRC-003-A02': len(observed_missing)/len(expected_keys),
        'GE-SRC-003-A03': len(observed_duplicate),
        'GE-SRC-003-A04': sorted(observed_duplicate)==sorted(expected_keys),
    }

def oracle_ge_src_004():
    """Analysis generation after a PDelta change. Independent frozen example only."""
    target = {'generation': 8, 'model_id': 'M-DEMO', 'pdelta_revision': 'PDELTA-B'}
    old_force = {'generation': 7, 'model_id': 'M-DEMO', 'pdelta_revision': 'PDELTA-A'}
    new_force = {'generation': 8, 'model_id': 'M-DEMO', 'pdelta_revision': 'PDELTA-B'}
    return {
        'GE-SRC-004-A01': old_force==target,
        'GE-SRC-004-A02': new_force==target,
    }

def oracle_ge_src_005():
    """ComboBook and signed force replay. Independent frozen example only."""
    return {
        'GE-SRC-005-A01': 1+0.2*0.508151,
        'GE-SRC-005-A02': (1+0.2*0.508151)*1000+300+40+0.3*30,
        'GE-SRC-005-A03': (1+0.2*0.508151)*20+10+200+0.3*40,
        'GE-SRC-005-A04': (1+0.2*0.508151)*30+5+80+0.3*180,
    }

def oracle_ge_chk_001():
    """Lower concrete-strength bound for C30. Independent frozen example only."""
    return {
        'GE-CHK-001-A01': 30-25,
        'GE-CHK-001-A02': 30>=25,
        'GE-CHK-001-A03': 24>=25,
    }

def oracle_ge_chk_002():
    """Concrete-class range for the selected method. Independent frozen example only."""
    return {
        'GE-CHK-002-A01': 25<=30<=80,
        'GE-CHK-002-A02': 80-30,
        'GE-CHK-002-A03': 25<=90<=80,
    }

def oracle_ge_chk_003():
    """Dimensions of the 300 mm square column. Independent frozen example only."""
    return {
        'GE-CHK-003-A01': min(30*10,30*10),
        'GE-CHK-003-A02': min(300,300)>=300,
        'GE-CHK-003-A03': min(299,300)>=300,
    }

def oracle_ge_chk_004():
    """Seismic axial compression limit. Independent frozen example only."""
    return {
        'GE-CHK-004-A01': 0.4*30*300*300/1000,
        'GE-CHK-004-A02': 848.33/1080,
        'GE-CHK-004-A03': max(0,-200),
    }

def oracle_ge_chk_005():
    """TS 500 axial compression limit. Independent frozen example only."""
    return {
        'GE-CHK-005-A01': 30/1.5,
        'GE-CHK-005-A02': 0.9*(30/1.5)*90000/1000,
        'GE-CHK-005-A03': 1114.48/1620,
        'GE-CHK-005-A04': 1620.1/1620>1,
    }

def oracle_ge_chk_006():
    """Modal mass completeness in both directions. Independent frozen example only."""
    return {
        'GE-CHK-006-A01': sum([0,.92566,0,.07434,0,0]),
        'GE-CHK-006-A02': sum([.92566,0,0,0,.07434,0]),
        'GE-CHK-006-A03': sum([.92566,0,0,0])<.95,
        'GE-CHK-006-A04': sum([.92566,0,0,0]),
    }

def oracle_ge_chk_007():
    """Reported PMM demand and the first reinforcement candidate. Independent frozen example only."""
    return {
        'GE-CHK-007-A01': 4*pi*18**2/4/100,
        'GE-CHK-007-A02': max(abs(2.39),.18),
        'GE-CHK-007-A03': max(abs(1.03),.18),
        'GE-CHK-007-A04': max(abs(.10),.18),
    }

def oracle_ge_chk_009():
    """Longitudinal ratio of four 18 mm bars. Independent frozen example only."""
    return {
        'GE-CHK-009-A01': 4*pi*18**2/4,
        'GE-CHK-009-A02': 4*pi*18**2/4/90000*100,
        'GE-CHK-009-A03': 4*pi*16**2/4/90000,
    }

def oracle_ge_chk_010():
    """From source drift ratio to dimensional storey displacement. Independent frozen example only."""
    return {
        'GE-CHK-010-A01': .001741536505615905*4500,
        'GE-CHK-010-A02': 7*.001741536505615905,
        'GE-CHK-010-A03': 7.836914275271572/3000,
    }

def oracle_ge_chk_011():
    """Design-spectrum corner periods and sample ordinates. Independent frozen example only."""
    return {
        'GE-CHK-011-A01': .2*.1912/.6592,
        'GE-CHK-011-A02': .1912/.6592,
        'GE-CHK-011-A03': .1912/.4,
        'GE-CHK-011-A04': .1912/.4/8,
        'GE-CHK-011-A05': .1912*6/12**2,
    }

def oracle_ge_chk_101():
    """Seismic weight from storey loads. Independent frozen example only."""
    return {
        'GE-CHK-101-A01': 1466.62+.3*176.72,
        'GE-CHK-101-A02': 1396.12+.3*176.72,
        'GE-CHK-101-A03': 1466.62+1396.12+.3*(176.72+176.72),
        'GE-CHK-101-A04': 2968.772/9.80665,
        'GE-CHK-101-A05': 1466.62+1396.12+.6*(176.72+176.72),
    }

def oracle_ge_chk_102():
    """Directional modal period and method-specific period. Independent frozen example only."""
    return {
        'GE-CHK-102-A01': 1/.80077,
        'GE-CHK-102-A02': .1*10**.75,
        'GE-CHK-102-A03': min(1.24879,1.4*.1*10**.75),
        'GE-CHK-102-A04': min(.70,1.4*.1*10**.75),
    }

def oracle_ge_chk_103():
    """Base shear and storey force distribution. Independent frozen example only."""
    return {
        'GE-CHK-103-A01': 2968.78*.1912/(1.4*.1*10**.75)/8,
        'GE-CHK-103-A02': .04*2968.78*.6592,
        'GE-CHK-103-A03': .0075*2*90.13,
        'GE-CHK-103-A04': (90.13-.0075*2*90.13)*1449.14*5/(1519.64*10+1449.14*5),
        'GE-CHK-103-A05': 28.66305367523538+61.4669463247646,
        'GE-CHK-103-A06': max(2968.78*.02,.04*2968.78*.6592),
    }

def oracle_ge_chk_104():
    """Scaling modal base shear. Independent frozen example only."""
    return {
        'GE-CHK-104-A01': max(1,.8*90.13/53.13),
        'GE-CHK-104-A02': (.8*90.13/53.13)*53.13,
        'GE-CHK-104-A03': max(1,.9*90.13/53.13),
    }

def oracle_ge_chk_105():
    """Effective drift and the infill limit. Independent frozen example only."""
    return {
        'GE-CHK-105-A01': .3999*44.91/4500,
        'GE-CHK-105-A02': .3999*67.65/4500,
        'GE-CHK-105-A03': .3999*67.65/4500/.008,
        'GE-CHK-105-A04': .3999*100/4500/.008,
    }

def oracle_ge_chk_106():
    """A1 ratio of maximum to average drift. Independent frozen example only."""
    return {
        'GE-CHK-106-A01': (4.011+3.522)/2,
        'GE-CHK-106-A02': 4.011/((4.011+3.522)/2),
        'GE-CHK-106-A03': 4.011/((4.011+3.522)/2)>1.2,
        'GE-CHK-106-A04': 6/((6+2)/2),
    }

def oracle_ge_chk_107():
    """A2 floor-opening area ratio. Independent frozen example only."""
    return {
        'GE-CHK-107-A01': 91.4449986/3274.4050014,
        'GE-CHK-107-A02': 91.4449986/3274.4050014>1/3,
        'GE-CHK-107-A03': 1200/3274.4050014,
    }

def oracle_ge_chk_108():
    """Dimensional projection limit for A3. Independent frozen example only."""
    return {
        'GE-CHK-108-A01': 4.1/20,
        'GE-CHK-108-A02': 3.1/15,
        'GE-CHK-108-A03': 4.1/20>.2 and 3.1/15>.2,
        'GE-CHK-108-A04': 4/20>.2 and 3.1/15>.2,
    }

def oracle_ge_chk_109():
    """B1 directional effective areas and adjacent-storey ratio. Independent frozen example only."""
    return {
        'GE-CHK-109-A01': 39/38.36,
        'GE-CHK-109-A02': 36.28/35.64,
        'GE-CHK-109-A03': (20+10+.15*40)/48,
    }

def oracle_ge_chk_110():
    """B2 comparison with both adjacent storeys. Independent frozen example only."""
    return {
        'GE-CHK-110-A01': (5.865/5000)/(3.766/5000),
        'GE-CHK-110-A02': (5.865/5000)/(4.816/5000),
        'GE-CHK-110-A03': max(5.865/3.766,5.865/4.816)>2,
        'GE-CHK-110-A04': max(8/3.766,8/4.816),
    }

def oracle_ge_chk_111():
    """B3 support-topology benchmark. Independent frozen example only."""
    return {
        'GE-CHK-111-A01': sqrt((5-5)**2+(0-0)**2+(0-0)**2),
        'GE-CHK-111-A02': sum([1,0]),
        'GE-CHK-111-A03': sqrt((5-0)**2+(0-0)**2+(0-0)**2),
        'GE-CHK-111-A04': sum([1,1]),
    }

def oracle_ge_chk_112():
    """Wall overturning-moment share. Independent frozen example only."""
    return {
        'GE-CHK-112-A01': 2199.1413/18998.915,
        'GE-CHK-112-A02': 2199.1413/18998.915>.4,
        'GE-CHK-112-A03': (.5*18998.915)/18998.915,
    }

def oracle_ge_chk_113():
    """Numerical trace of the second-order indicator. Independent frozen example only."""
    return {
        'GE-CHK-113-A01': .00485*2050.03/(187.26*4.5),
        'GE-CHK-113-A02': .12*3/(.5*8),
        'GE-CHK-113-A03': .00485*2050.03/(187.26*4.5)<=.09,
        'GE-CHK-113-A04': .04*2050.03/(187.26*4.5),
        'GE-CHK-113-A05': .88+(.5*8/3)*(.04*2050.03/(187.26*4.5)),
    }

def oracle_ge_chk_114():
    """Base transfer vector from storey forces. Independent frozen example only."""
    return {
        'GE-CHK-114-A01': 187.2624+55.4117,
        'GE-CHK-114-A02': 7.3*187.2624+2.8*55.4117,
        'GE-CHK-114-A03': 253.7406+75.0828,
        'GE-CHK-114-A04': (7.3-1)*187.2624+(2.8-1)*55.4117,
    }

def oracle_ge_chk_115():
    """S1 minimum eccentricity about both axes. Independent frozen example only."""
    return {
        'GE-CHK-115-A01': 15+0.03*300,
        'GE-CHK-115-A02': 7.43*(15+0.03*300)/1000,
        'GE-CHK-115-A03': [max(abs(2.39),0.17832),max(abs(1.03),0.17832)],
        'GE-CHK-115-A04': max(abs(0.10),7.43*0.024),
    }

def oracle_ge_chk_116():
    """Sway1 slenderness using clear length and exact inertia. Independent frozen example only."""
    return {
        'GE-CHK-116-A01': 300*300**3/12,
        'GE-CHK-116-A02': 0.9*2550,
        'GE-CHK-116-A03': 2295/sqrt((300*300**3/12)/(300*300)),
        'GE-CHK-116-A04': 2295/(0.3*300),
    }

def oracle_ge_chk_117():
    """Sway1 effective-length factor from end stiffness ratios. Independent frozen example only."""
    return {
        'GE-CHK-117-A01': min(0.7+0.05*(1.975+1.975),0.85+0.05*1.975,1),
        'GE-CHK-117-A02': 0.8975*2550,
        'GE-CHK-117-A03': round(0.8975,2),
        'GE-CHK-117-A04': min(0.7+0.05*(0+0),0.85+0.05*0,1),
    }

def oracle_ge_chk_118():
    """Single ownership of PDelta effects and analysis generation. Independent frozen example only."""
    return {
        'GE-CHK-118-A01': 100*1.20,
        'GE-CHK-118-A02': 100*1.20*1.20,
        'GE-CHK-118-A03': ["GEN-2","GEN-2","GEN-2"]==["GEN-2"]*3,
        'GE-CHK-118-A04': ["GEN-2","GEN-1","GEN-2"]==["GEN-2"]*3,
    }

def oracle_ge_chk_119():
    """Golden 02 member beta and storey beta_s. Independent frozen example only."""
    return {
        'GE-CHK-119-A01': 1/(1-1.3*471.11/1727.29),
        'GE-CHK-119-A02': 1/(1-1.3*1975.94/15894.39),
        'GE-CHK-119-A03': (1/(1-1.3*471.11/1727.29))*(1/(1-1.3*1975.94/15894.39)),
        'GE-CHK-119-A04': round((1/(1-1.3*471.11/1727.29))*(1/(1-1.3*1975.94/15894.39)),2),
        'GE-CHK-119-A05': 1975.94<=0.45*15894.39,
    }

def oracle_ge_chk_120():
    """Independent section resultants with partial bar-hole subtraction. Independent frozen example only."""
    return {
        'GE-CHK-120-A01': (0.85*35/1.5)*(120000-1.5*pi*100)+pi*100*(-229.5+420/1.15+126),
        'GE-CHK-120-A02': -(0.85*35/1.5)*(180*pi*100)+pi*100*((-229.5)*(-200)+(420/1.15)*150+126*60),
        'GE-CHK-120-A03': -(0.85*35/1.5)*(12000000-(150*pi*100+2*10**3/3))-pi*100*((-229.5)*(-150)+(420/1.15)*150),
        'GE-CHK-120-A04': (-147518.2637337816+sqrt(147518.2637337816**2+4*9401*18849555.92153876))/(2*9401),
        'GE-CHK-120-A05': 40634295.197377674/81268590.39475535,
    }

def oracle_ge_chk_121():
    """S1 bar area centres and clear spacing. Independent frozen example only."""
    return {
        'GE-CHK-121-A01': 4*pi*18**2/4,
        'GE-CHK-121-A02': 4*pi*18**2/4/(300*300),
        'GE-CHK-121-A03': 300-2*(25+8+18/2)-18,
        'GE-CHK-121-A04': max(40,1.5*18,4*20/3),
        'GE-CHK-121-A05': 900>=2550/3 and 1500<=2*2550/3,
    }

def oracle_ge_chk_122():
    """SB201 physical confinement-region lengths. Independent frozen example only."""
    return {
        'GE-CHK-122-A01': max(3900/6,1.5*max(600,600),500),
        'GE-CHK-122-A02': 3900-2*900,
        'GE-CHK-122-A03': 900+2100+900,
    }

def oracle_ge_chk_123():
    """Detecting a missing crosstie leg in an 800 mm column. Independent frozen example only."""
    return {
        'GE-CHK-123-A01': (800-2*(40+10/2))/3,
        'GE-CHK-123-A02': 25*10,
        'GE-CHK-123-A03': min(800/3,150,6*24),
        'GE-CHK-123-A04': 118.33333333333333-(-355),
        'GE-CHK-123-A05': (118.33333333333333+355)<=25*10,
    }

def oracle_ge_chk_124():
    """Column confinement area with five 10 mm legs. Independent frozen example only."""
    return {
        'GE-CHK-124-A01': 3569.02/50986,
        'GE-CHK-124-A02': 0.3*10*72*(6400/5184-1)*0.07,
        'GE-CHK-124-A03': 0.075*10*72*0.07,
        'GE-CHK-124-A04': 5*pi*(10/10)**2/4,
        'GE-CHK-124-A05': 4*pi*(10/10)**2/4>=3.78,
    }

def oracle_ge_chk_125():
    """Strongcol1 S8 fails the basic SCWB inequality. Independent frozen example only."""
    return {
        'GE-CHK-125-A01': 10.96+11.47,
        'GE-CHK-125-A02': 12.89+7.24,
        'GE-CHK-125-A03': (10.96+11.47)/(12.89+7.24),
        'GE-CHK-125-A04': 1.2*(12.89+7.24)/(10.96+11.47),
        'GE-CHK-125-A05': 10.96+11.47>=1.2*(12.89+7.24),
    }

def oracle_ge_chk_126():
    """SB201 column capacity shear from the end mechanism. Independent frozen example only."""
    return {
        'GE-CHK-126-A01': 28.99*8.17/(8.17+3.76),
        'GE-CHK-126-A02': (19.85+34.70)/3.90,
        'GE-CHK-126-A03': round((19.85+34.70)/3.90,2),
        'GE-CHK-126-A04': 1.4*(100+120)/3,
    }

def oracle_ge_chk_127():
    """SB201 shear resistance and separate detailing acceptance. Independent frozen example only."""
    return {
        'GE-CHK-127-A01': 13.99/90.65,
        'GE-CHK-127-A02': 13.99/170.91,
        'GE-CHK-127-A03': 4*pi*10**2/4*(420/1.15)*550/100/1000,
        'GE-CHK-127-A04': (13.99/90.65<=1) and False,
    }

def oracle_ge_chk_128():
    """SB201 joint panel shear and unconfined limit. Independent frozen example only."""
    return {
        'GE-CHK-128-A01': 1.25*420*1206/9806.65-11.36,
        'GE-CHK-128-A02': 1.25*420*1206/9806.65-11.36,
        'GE-CHK-128-A03': 416*600*sqrt(30)/9806.65,
        'GE-CHK-128-A04': 53.22/139.41,
    }

def oracle_ge_chk_129():
    """Alpha iteration from an immutable base demand. Independent frozen example only."""
    return {
        'GE-CHK-129-A01': 39.21/43.21,
        'GE-CHK-129-A02': 100*43.21/39.21,
        'GE-CHK-129-A03': 100*1.05,
        'GE-CHK-129-A04': 100*43.21/39.21*1.05,
        'GE-CHK-129-A05': [2,2,2,2,2]==[2]*5,
        'GE-CHK-129-A06': [1,2,2,2,2]==[2]*5,
    }

def oracle_ge_chk_130():
    """KB241 beam applicability and physical faces. Independent frozen example only."""
    return {
        'GE-CHK-130-A01': sqrt(7600**2)-300-300,
        'GE-CHK-130-A02': 400>=250 and 400<=600+300 and 600>=max(300,3*150) and 600<=3.5*400,
        'GE-CHK-130-A03': 600>7000/4,
        'GE-CHK-130-A04': 0.1*400*600*30/1000,
    }

def oracle_ge_chk_131():
    """Independent rectangular flexural solution using KB241 demand. Independent frozen example only."""
    return {
        'GE-CHK-131-A01': 22.32*9806.65*1000,
        'GE-CHK-131-A02': 550-sqrt(550**2-2*22.32*9806.65*1000/(0.85*20*400)),
        'GE-CHK-131-A03': 0.85*20*400*(550-sqrt(550**2-2*22.32*9806.65*1000/(0.85*20*400)))/(420/1.15),
        'GE-CHK-131-A04': 6*pi*16**2/4>=1154.7963219454905,
    }

def oracle_ge_chk_132():
    """KB241 top and bottom bar layout. Independent frozen example only."""
    return {
        'GE-CHK-132-A01': 4*pi*14**2/4+2*pi*16**2/4,
        'GE-CHK-132-A02': 6*pi*16**2/4,
        'GE-CHK-132-A03': (400-2*(30+8+16/2))/5-16,
        'GE-CHK-132-A04': (400-2*(30+8)-(4*14+2*16))/5,
        'GE-CHK-132-A05': (300-2*(30+8+16/2))/5-16>=max(25,16,4*20/3),
    }

def oracle_ge_chk_133():
    """KB241 end-region ratios and continuous-bar identity. Independent frozen example only."""
    return {
        'GE-CHK-133-A01': 0.8*(0.35*sqrt(30)/1.5)/(420/1.15)*400*550,
        'GE-CHK-133-A02': (4*pi*14**2/4+2*pi*16**2/4)/(400*550),
        'GE-CHK-133-A03': 6*pi*16**2/4/(400*550),
        'GE-CHK-133-A04': 6*pi*16**2/4>=0.5*(4*pi*14**2/4+2*pi*16**2/4),
        'GE-CHK-133-A05': 6*pi*16**2/4/(400*550)<=0.85*(0.85*0.82*20/(420/1.15)*0.003/(0.003+(420/1.15)/200000)),
        'GE-CHK-133-A06': 4*pi*14**2/4>=0.25*(4*pi*14**2/4+2*pi*16**2/4),
        'GE-CHK-133-A07': 1>=2,
    }

def oracle_ge_chk_134():
    """Separate positive and negative KB241 moment capacities. Independent frozen example only."""
    return {
        'GE-CHK-134-A01': (4*pi*14**2/4+2*pi*16**2/4)*(420/1.15)*(550-(4*pi*14**2/4+2*pi*16**2/4)*(420/1.15)/(2*0.85*20*400))/1e6,
        'GE-CHK-134-A02': 6*pi*16**2/4*(420/1.15)*(550-6*pi*16**2/4*(420/1.15)/(2*0.85*20*400))/1e6,
        'GE-CHK-134-A03': 228.0499756703097>194.29890862232338,
    }

def oracle_ge_chk_135():
    """KB201 capacity shear and the raw-demand floor. Independent frozen example only."""
    return {
        'GE-CHK-135-A01': (33.19+43.65)/7.20,
        'GE-CHK-135-A02': 12.86+(33.19+43.65)/7.20,
        'GE-CHK-135-A03': 16.92+(33.19+43.65)/7.20,
        'GE-CHK-135-A04': max(24.39,min(16.92+(33.19+43.65)/7.20,23.89)),
        'GE-CHK-135-A05': max(24.39,16.92+(33.19+43.65)/7.20),
    }

def oracle_ge_chk_136():
    """Beam tie area spacing and four-leg geometry. Independent frozen example only."""
    return {
        'GE-CHK-136-A01': 1.57079632679490e-4*44335.652173913*0.67/0.10,
        'GE-CHK-136-A02': 0.3*(0.35*sqrt(35)/1.5)*600/(500/1.15),
        'GE-CHK-136-A03': 400000/((500/1.15)*670),
        'GE-CHK-136-A04': 4*pi*10**2/4/90,
        'GE-CHK-136-A05': 4*pi*10**2/4*(500/1.15)*670/90/1000,
        'GE-CHK-136-A06': min(670/4,8*20,150),
        'GE-CHK-136-A07': (600-2*(30+10/2))/3,
    }

def oracle_ge_chk_137():
    """KB239 torsion threshold and transverse-area sum. Independent frozen example only."""
    return {
        'GE-CHK-137-A01': 0.65/1.35*6.43,
        'GE-CHK-137-A02': 6.26<=0.65/1.35*6.43,
        'GE-CHK-137-A03': 4.20+5.11,
        'GE-CHK-137-A04': 6.26*9806.65*1000/(2*166400*(420/1.15)),
        'GE-CHK-137-A05': 6.26*9806.65*1000/(2*166400*(420/1.15))*1680,
    }

def oracle_ge_chk_138():
    """Service benchmark with cracked inertia long-term deflection and crack width. Independent frozen example only."""
    return {
        'GE-CHK-138-A01': (-(200000/32000)*(6*pi*16**2/4)+sqrt(((200000/32000)*(6*pi*16**2/4))**2+2*400*(200000/32000)*(6*pi*16**2/4)*550))/400,
        'GE-CHK-138-A02': 400*126.37377991720257**3/3+(200000/32000)*(6*pi*16**2/4)*(550-126.37377991720257)**2,
        'GE-CHK-138-A03': (76681158.05072325/97200000)**3*7200000000+(1-(76681158.05072325/97200000)**3)*1622187797.3592992,
        'GE-CHK-138-A04': 5*10*7200**4/(384*32000*4360803427.017007),
        'GE-CHK-138-A05': 2.507565448204587+1.2537827241022934+(2/(1+50*0))*2.507565448204587,
        'GE-CHK-138-A06': 1.3*(2*50*400/6*50)**(1/3)*(0.7*420/1.15)*1e-5,
        'GE-CHK-138-A07': 600>7200/15,
        'GE-CHK-138-A08': 0.23043711222331534<=0.2,
    }

def oracle_ge_chk_139():
    """KB241 bottom-bar development and physical extension. Independent frozen example only."""
    return {
        'GE-CHK-139-A01': max(0.12*16*(420/1.15)/(0.35*sqrt(30)/1.5),20*16),
        'GE-CHK-139-A02': 1.4*max(0.12*16*(420/1.15)/(0.35*sqrt(30)/1.5),20*16),
        'GE-CHK-139-A03': max(max(0.12*16*(420/1.15)/(0.35*sqrt(30)/1.5),20*16),50*16),
        'GE-CHK-139-A04': 850-800,
        'GE-CHK-139-A05': 780>=800,
    }

def oracle_ge_chk_140():
    """PB301 wall and analysis-component mapping. Independent frozen example only."""
    return {
        'GE-CHK-140-A01': sum([18.00,11.63]),
        'GE-CHK-140-A02': sum([18.00,11.63,29.63]),
        'GE-CHK-140-A03': 'Frame:S-A' != 'Shell:S-A',
    }

def oracle_ge_chk_141():
    """Analytical N M point using the reported wall geometry. Independent frozen example only."""
    return {
        'GE-CHK-141-A01': 12*pi*14**2/4,
        'GE-CHK-141-A02': 0.003*(1750/500-1),
        'GE-CHK-141-A03': (0.85*20*300*0.82*500-12*pi*14**2/4*0.85*20)/1000,
        'GE-CHK-141-A04': (0.85*20*300*0.82*500*(900-0.82*500/2)+(12*pi*14**2/4*(420/1.15-0.85*20)+12*pi*14**2/4*(420/1.15))*850)/1000000,
    }

def oracle_ge_chk_142():
    """PB301 critical height and boundary-zone lengths. Independent frozen example only."""
    return {
        'GE-CHK-142-A01': 7.30/1.80,
        'GE-CHK-142-A02': max(1.8,7.3/6),
        'GE-CHK-142-A03': max(0.2*1.8,2*0.3),
        'GE-CHK-142-A04': max(0.1*1.8,0.3),
    }

def oracle_ge_chk_143():
    """PB301 horizontal and vertical web reinforcement ratios. Independent frozen example only."""
    return {
        'GE-CHK-143-A01': 2*pi*10**2/4/(200*300),
        'GE-CHK-143-A02': 2*pi*12**2/4/(160*300),
        'GE-CHK-143-A03': 2*pi*10**2/4/(200*300)>=0.0025,
        'GE-CHK-143-A04': 2*pi*8**2/4/(200*300)>=0.0025,
    }

def oracle_ge_chk_144():
    """PB301 capacity shear and resistance comparison. Independent frozen example only."""
    return {
        'GE-CHK-144-A01': 1.5*213.44/110.23*29.63,
        'GE-CHK-144-A02': min(1.5*213.44/110.23*29.63,62.51),
        'GE-CHK-144-A03': 62.51/184.77,
        'GE-CHK-144-A04': 62.51<=256.36,
    }

def oracle_ge_chk_145():
    """Normal and diagonal reinforcement branches for a coupling beam. Independent frozen example only."""
    return {
        'GE-CHK-145-A01': 2.2>2*0.6,
        'GE-CHK-145-A02': (1200>2*600) or (400000<=1.5*300*550*1.2),
        'GE-CHK-145-A03': 400000/(2*(420/1.15)*sin(radians(30))),
        'GE-CHK-145-A04': 4*pi*20**2/4,
        'GE-CHK-145-A05': min(8*20,100),
    }

def oracle_ge_chk_146():
    """Same-cut storey shear share and unique contributions. Independent frozen example only."""
    return {
        'GE-CHK-146-A01': sum([40,20,30,10]),
        'GE-CHK-146-A02': sum([40,20])/sum([40,20,30,10]),
        'GE-CHK-146-A03': sum([40,20,30,10])-100,
        'GE-CHK-146-A04': sum([40,30,10])-100,
    }

def oracle_ge_chk_147():
    """Corner-joint incident roster using SB201 names. Independent frozen example only."""
    return {
        'GE-CHK-147-A01': len(['C_low:J','C_up:I','KB201:I','KB242:I']),
        'GE-CHK-147-A02': 1*0+0*1+0*0,
        'GE-CHK-147-A03': 2==4,
    }

def oracle_ge_chk_148():
    """Joint reinforcement demand at the enclosure-width boundary. Independent frozen example only."""
    return {
        'GE-CHK-148-A01': (300>=0.75*400) and (450>=0.75*600),
        'GE-CHK-148-A02': 4*pi*0.8**2/4/8,
        'GE-CHK-148-A03': 4*pi*0.8**2/4/8>=0.6*0.5,
        'GE-CHK-148-A04': 4*pi*1**2/4/10,
    }

def oracle_ge_chk_149():
    """Tracing the Golden V2 D101 slab-thickness row. Independent frozen example only."""
    return {
        'GE-CHK-149-A01': 470*(1-0.5/4)/(15+20/1),
        'GE-CHK-149-A02': max(470*(1-0.5/4)/(15+20),8),
        'GE-CHK-149-A03': 15/11.75,
    }

def oracle_ge_chk_150():
    """DB212 reinforcement and an analytical strip retaining twisting moment. Independent frozen example only."""
    return {
        'GE-CHK-150-A01': pi*1.2**2/4*100/13,
        'GE-CHK-150-A02': pi*1.2**2/4*100/20,
        'GE-CHK-150-A03': (pi*1.2**2/4*100/13)/8.17,
        'GE-CHK-150-A04': pi*1.2**2/4*100/15>=8.17,
        'GE-CHK-150-A05': (40+20)/2+sqrt(((40-20)/2)**2+10**2),
        'GE-CHK-150-A06': degrees(0.5*atan2(2*10,40-20)),
        'GE-CHK-150-A07': 0.85*20*1000*(160-sqrt(160**2-2*(30+sqrt(200))*1000000/(0.85*20*1000)))/(420/1.15),
        'GE-CHK-150-A08': (pi*12**2/4*1000/130)*(420/1.15)*(160-((pi*12**2/4*1000/130)*(420/1.15)/(0.85*20*1000))/2)/1000000,
    }

def oracle_ge_chk_151():
    """Recalculation of SB302 punching stresses with two moments. Independent frozen example only."""
    return {
        'GE-CHK-151-A01': 24289/53.5,
        'GE-CHK-151-A02': 96.2/(24289/10000)+0.4*(22.62+33.62)*0.5675/(55046211/100000000),
        'GE-CHK-151-A03': 96.2/(24289/10000)-0.4*(22.62+33.62)*0.5675/(55046211/100000000),
        'GE-CHK-151-A04': 62.80/130.32,
    }

def oracle_ge_chk_152():
    """DB315 deflection chain and a separate crack-width benchmark. Independent frozen example only."""
    return {
        'GE-CHK-152-A01': sum([0.53,0.44,0.93]),
        'GE-CHK-152-A02': 5400/360,
        'GE-CHK-152-A03': 5400/240,
        'GE-CHK-152-A04': 1.3*(6000*25)**(1/3)*210*0.00001,
    }

def oracle_ge_chk_153():
    """A 750 kN diaphragm-to-wall transfer calculation. Independent frozen example only."""
    return {
        'GE-CHK-153-A01': 3*(400-150),
        'GE-CHK-153-A02': 4*pi*16**2/4,
        'GE-CHK-153-A03': (2+1)*4*pi*16**2/4*(420/1.15)/1000,
        'GE-CHK-153-A04': 750/((2+1)*4*pi*16**2/4*(420/1.15)/1000),
    }

def oracle_ge_chk_154():
    """Unit-linked foundation and P14 loaded-footprint geometry. Independent frozen example only."""
    return {
        'GE-CHK-154-A01': 0.5*3,
        'GE-CHK-154-A02': (0.5+1.4)*(3+1.4),
        'GE-CHK-154-A03': 150-140,
    }

def oracle_ge_chk_155():
    """Source foundation pressure and a separate full-contact equilibrium example. Independent frozen example only."""
    return {
        'GE-CHK-155-A01': 40/85.03,
        'GE-CHK-155-A02': 20000/(10*10)+5000/(10*10**2/6),
        'GE-CHK-155-A03': 20000/(10*10)-5000/(10*10**2/6),
        'GE-CHK-155-A04': (230+170)/2*100,
    }

def oracle_ge_chk_156():
    """Subtracting soil reaction in P14 foundation punching. Independent frozen example only."""
    return {
        'GE-CHK-156-A01': 2*((50+140)+(300+140)),
        'GE-CHK-156-A02': 40*1.9*4.4,
        'GE-CHK-156-A03': 0.95*13.78*1260*140/1000,
        'GE-CHK-156-A04': 0.95*13.78*1260*140/1000+334.4,
        'GE-CHK-156-A05': 1516-334.4,
        'GE-CHK-156-A06': 2*(50+140)+4*(min(300/2,3*50)+140/2),
    }

def oracle_ge_chk_157():
    """From source raft reinforcement to a selected two-direction cage. Independent frozen example only."""
    return {
        'GE-CHK-157-A01': pi*2.5**2/4*100/20,
        'GE-CHK-157-A02': 2*(pi*25**2/4*1000/200)/(1000*1500)>=0.0035,
        'GE-CHK-157-A03': pi*25**2/4*1000/180,
        'GE-CHK-157-A04': 2*(pi*25**2/4*1000/180)/(1000*1500)>=0.0035,
        'GE-CHK-157-A05': (pi*25**2/4*1000/180)*(420/1.15)*(1400-((pi*25**2/4*1000/180)*(420/1.15)/(0.85*20*1000))/2)/1000000,
        'GE-CHK-157-A06': pi*16**2/4*1000/200,
        'GE-CHK-157-A07': pi*16**2/4*1000/200>=(pi*25**2/4*1000/180)/3,
        'GE-CHK-157-A08': max(0.12*(420/1.15)/1.2*25,20*25),
        'GE-CHK-157-A09': 1.3*(36000*100)**(1/3)*120*0.00001,
    }

def oracle_ge_chk_158():
    """Transferring SB301 forces and the moment reference to a foundation. Independent frozen example only."""
    return {
        'GE-CHK-158-A01': -16.537*9.80665,
        'GE-CHK-158-A02': 3.707*9.80665+2*(-16.537*9.80665),
        'GE-CHK-158-A03': -14.742*9.80665-(-16.537*9.80665),
        'GE-CHK-158-A04': (-287.99189055-2*(-162.17257105))-3.707*9.80665,
    }

def oracle_ge_adp_01():
    """Create two combinations from an empty catalogue. Independent frozen example only."""
    before_catalog = {}
    desired_catalog = {'DX': {'case_terms': {'EX': 1.0, 'EY': 0.3, 'G': 1.1016302, 'Q': 1.0}, 'operator': 'LinearAdd'},
     'DY': {'case_terms': {'EX': 0.3, 'EY': 1.0, 'G': 1.1016302, 'Q': 1.0}, 'operator': 'LinearAdd'}}
    expected_created = ['DX', 'DY']
    return {
        'GE-ADP-01-A01': sorted(expected_created),
        'GE-ADP-01-A02': len(desired_catalog['DX']['case_terms'])+len(desired_catalog['DY']['case_terms']),
    }

def oracle_ge_adp_02():
    """Complete a partial combination catalogue. Independent frozen example only."""
    before_catalog = {'DX': {'case_terms': {'EX': 1.0, 'EY': 0.3, 'G': 1.1016302, 'Q': 1.0}, 'operator': 'LinearAdd'}}
    desired_catalog = {'DX': {'case_terms': {'EX': 1.0, 'EY': 0.3, 'G': 1.1016302, 'Q': 1.0}, 'operator': 'LinearAdd'},
     'DY': {'case_terms': {'EX': 0.3, 'EY': 1.0, 'G': 1.1016302, 'Q': 1.0}, 'operator': 'LinearAdd'}}
    expected_created = ['DY']
    return {
        'GE-ADP-02-A01': len(desired_catalog)-len(before_catalog),
        'GE-ADP-02-A02': before_catalog['DX']==desired_catalog['DX'],
    }

def oracle_ge_adp_03():
    """Same combination name with different contents. Independent frozen example only."""
    return {
        'GE-ADP-03-A01': 0.4-0.3,
    }

def oracle_ge_adp_04():
    """An extra term after a setter. Independent frozen example only."""
    desired_children = ['G', 'EX']
    readback_children = ['G', 'Q', 'EX']
    native_return_code = 0
    return {
        'GE-ADP-04-A01': sorted(readback_children)==sorted(desired_children),
        'GE-ADP-04-A02': len(readback_children)-len(desired_children),
    }

def oracle_ge_adp_05():
    """Apply the same desired catalogue a second time. Independent frozen example only."""
    desired_catalog = {'DX': {'case_terms': {'EX': 1.0, 'EY': 0.3, 'G': 1.1016302, 'Q': 1.0}, 'operator': 'LinearAdd'},
     'DY': {'case_terms': {'EX': 0.3, 'EY': 1.0, 'G': 1.1016302, 'Q': 1.0}, 'operator': 'LinearAdd'}}
    readback_catalog = {'DX': {'case_terms': {'EX': 1.0, 'EY': 0.3, 'G': 1.1016302, 'Q': 1.0}, 'operator': 'LinearAdd'},
     'DY': {'case_terms': {'EX': 0.3, 'EY': 1.0, 'G': 1.1016302, 'Q': 1.0}, 'operator': 'LinearAdd'}}
    expected_mutations = []
    return {
        'GE-ADP-05-A01': readback_catalog==desired_catalog,
        'GE-ADP-05-A02': len(expected_mutations),
    }

def oracle_ge_adp_06():
    """Restore units and result selections. Independent frozen example only."""
    before = {'selected_cases': ['LC_DL'],
     'selected_combinations': ['DX'],
     'units': {'force': 'kN', 'length': 'm', 'temperature': 'C'}}
    after_success = {'selected_cases': ['LC_DL'],
     'selected_combinations': ['DX'],
     'units': {'force': 'kN', 'length': 'm', 'temperature': 'C'}}
    after_error = {'selected_cases': ['LC_DL'],
     'selected_combinations': ['DX'],
     'units': {'force': 'kN', 'length': 'm', 'temperature': 'C'}}
    after_cancel = {'selected_cases': ['LC_DL'],
     'selected_combinations': ['DX'],
     'units': {'force': 'kN', 'length': 'm', 'temperature': 'C'}}
    bad_after_error = {'selected_cases': ['LC_DL'],
     'selected_combinations': ['DX'],
     'units': {'force': 'kN', 'length': 'mm', 'temperature': 'C'}}
    return {
        'GE-ADP-06-A01': after_success==before,
        'GE-ADP-06-A02': after_error==before,
        'GE-ADP-06-A03': after_cancel==before,
        'GE-ADP-06-A04': bad_after_error==before,
    }

def oracle_ge_adp_07():
    """Direction and analysis-element-side coverage. Independent frozen example only."""
    return {
        'GE-ADP-07-A01': (4+3)/(2*4),
    }

def oracle_ge_adp_08():
    """Analysis generation after a P-Delta change. Independent frozen example only."""
    target_generation = 8
    old_force_generation = 7
    return {
        'GE-ADP-08-A01': old_force_generation==target_generation,
    }

def oracle_ge_adp_09():
    """Reinforcement revision propagates to dependent results. Independent frozen example only."""
    return {
        'GE-ADP-09-A01': 8*pi*18**2/4,
    }

def oracle_ge_adp_10():
    """Change one member using a shared section. Independent frozen example only."""
    return {
        'GE-ADP-10-A01': 10-1,
    }

def oracle_ge_adp_11():
    """An interrupted mutation sequence. Independent frozen example only."""
    return {
        'GE-ADP-11-A01': 3-2,
    }

def oracle_ge_adp_12():
    """Save and reopen the model. Independent frozen example only."""
    saved_catalog = {'DX': {'case_terms': {'EX': 1.0, 'EY': 0.3, 'G': 1.1016302, 'Q': 1.0}, 'operator': 'LinearAdd'},
     'DY': {'case_terms': {'EX': 0.3, 'EY': 1.0, 'G': 1.1016302, 'Q': 1.0}, 'operator': 'LinearAdd'}}
    readback_catalog = {'DX': {'case_terms': {'EX': 1.0, 'EY': 0.3, 'G': 1.1016302, 'Q': 1.0}, 'operator': 'LinearAdd'},
     'DY': {'case_terms': {'EX': 0.3, 'EY': 1.0, 'G': 1.1016302, 'Q': 1.0}, 'operator': 'LinearAdd'}}
    wrong_readback = {'DX': {'case_terms': {'EX': 1.0, 'EY': 0.4, 'G': 1.1016302, 'Q': 1.0}, 'operator': 'LinearAdd'},
     'DY': {'case_terms': {'EX': 0.3, 'EY': 1.0, 'G': 1.1016302, 'Q': 1.0}, 'operator': 'LinearAdd'}}
    return {
        'GE-ADP-12-A01': readback_catalog==saved_catalog,
        'GE-ADP-12-A02': wrong_readback==saved_catalog,
        'GE-ADP-12-A03': wrong_readback['DX']['case_terms']['EY']-saved_catalog['DX']['case_terms']['EY'],
    }

ORACLES = {
    'GE-SRC-001': oracle_ge_src_001,
    'GE-SRC-002': oracle_ge_src_002,
    'GE-SRC-003': oracle_ge_src_003,
    'GE-SRC-004': oracle_ge_src_004,
    'GE-SRC-005': oracle_ge_src_005,
    'GE-CHK-001': oracle_ge_chk_001,
    'GE-CHK-002': oracle_ge_chk_002,
    'GE-CHK-003': oracle_ge_chk_003,
    'GE-CHK-004': oracle_ge_chk_004,
    'GE-CHK-005': oracle_ge_chk_005,
    'GE-CHK-006': oracle_ge_chk_006,
    'GE-CHK-007': oracle_ge_chk_007,
    'GE-CHK-009': oracle_ge_chk_009,
    'GE-CHK-010': oracle_ge_chk_010,
    'GE-CHK-011': oracle_ge_chk_011,
    'GE-CHK-101': oracle_ge_chk_101,
    'GE-CHK-102': oracle_ge_chk_102,
    'GE-CHK-103': oracle_ge_chk_103,
    'GE-CHK-104': oracle_ge_chk_104,
    'GE-CHK-105': oracle_ge_chk_105,
    'GE-CHK-106': oracle_ge_chk_106,
    'GE-CHK-107': oracle_ge_chk_107,
    'GE-CHK-108': oracle_ge_chk_108,
    'GE-CHK-109': oracle_ge_chk_109,
    'GE-CHK-110': oracle_ge_chk_110,
    'GE-CHK-111': oracle_ge_chk_111,
    'GE-CHK-112': oracle_ge_chk_112,
    'GE-CHK-113': oracle_ge_chk_113,
    'GE-CHK-114': oracle_ge_chk_114,
    'GE-CHK-115': oracle_ge_chk_115,
    'GE-CHK-116': oracle_ge_chk_116,
    'GE-CHK-117': oracle_ge_chk_117,
    'GE-CHK-118': oracle_ge_chk_118,
    'GE-CHK-119': oracle_ge_chk_119,
    'GE-CHK-120': oracle_ge_chk_120,
    'GE-CHK-121': oracle_ge_chk_121,
    'GE-CHK-122': oracle_ge_chk_122,
    'GE-CHK-123': oracle_ge_chk_123,
    'GE-CHK-124': oracle_ge_chk_124,
    'GE-CHK-125': oracle_ge_chk_125,
    'GE-CHK-126': oracle_ge_chk_126,
    'GE-CHK-127': oracle_ge_chk_127,
    'GE-CHK-128': oracle_ge_chk_128,
    'GE-CHK-129': oracle_ge_chk_129,
    'GE-CHK-130': oracle_ge_chk_130,
    'GE-CHK-131': oracle_ge_chk_131,
    'GE-CHK-132': oracle_ge_chk_132,
    'GE-CHK-133': oracle_ge_chk_133,
    'GE-CHK-134': oracle_ge_chk_134,
    'GE-CHK-135': oracle_ge_chk_135,
    'GE-CHK-136': oracle_ge_chk_136,
    'GE-CHK-137': oracle_ge_chk_137,
    'GE-CHK-138': oracle_ge_chk_138,
    'GE-CHK-139': oracle_ge_chk_139,
    'GE-CHK-140': oracle_ge_chk_140,
    'GE-CHK-141': oracle_ge_chk_141,
    'GE-CHK-142': oracle_ge_chk_142,
    'GE-CHK-143': oracle_ge_chk_143,
    'GE-CHK-144': oracle_ge_chk_144,
    'GE-CHK-145': oracle_ge_chk_145,
    'GE-CHK-146': oracle_ge_chk_146,
    'GE-CHK-147': oracle_ge_chk_147,
    'GE-CHK-148': oracle_ge_chk_148,
    'GE-CHK-149': oracle_ge_chk_149,
    'GE-CHK-150': oracle_ge_chk_150,
    'GE-CHK-151': oracle_ge_chk_151,
    'GE-CHK-152': oracle_ge_chk_152,
    'GE-CHK-153': oracle_ge_chk_153,
    'GE-CHK-154': oracle_ge_chk_154,
    'GE-CHK-155': oracle_ge_chk_155,
    'GE-CHK-156': oracle_ge_chk_156,
    'GE-CHK-157': oracle_ge_chk_157,
    'GE-CHK-158': oracle_ge_chk_158,
    'GE-ADP-01': oracle_ge_adp_01,
    'GE-ADP-02': oracle_ge_adp_02,
    'GE-ADP-03': oracle_ge_adp_03,
    'GE-ADP-04': oracle_ge_adp_04,
    'GE-ADP-05': oracle_ge_adp_05,
    'GE-ADP-06': oracle_ge_adp_06,
    'GE-ADP-07': oracle_ge_adp_07,
    'GE-ADP-08': oracle_ge_adp_08,
    'GE-ADP-09': oracle_ge_adp_09,
    'GE-ADP-10': oracle_ge_adp_10,
    'GE-ADP-11': oracle_ge_adp_11,
    'GE-ADP-12': oracle_ge_adp_12,
}

FROZEN_INPUT_SHA256 = {'GE-SRC-001': 'b9762344e679875b68f6fd7e53b053d6ebbc9b8cc5ff0f315d30da6168c03f1f',
 'GE-SRC-002': '416a4d1748ba452a6c59e42da5c0574d801d034665445caf10f8474159dfa52f',
 'GE-SRC-003': '22627dbbed26967a3e2d0e73eff2f79e93afed6e28ff73946c4924d3d72e7dda',
 'GE-SRC-004': '76cd61a77cce716f5699b26e0f85f9eb4cb088ce754e7793587f6282b28e8cbd',
 'GE-SRC-005': 'a704e58f6f88bd48ca9eef78e933a8d01e892ece13ecde05c31b8b68e81b5eb0',
 'GE-CHK-001': '0f634e36a247bae1929c90fbc28b8479395d23ddd442f9b2a8bcf2a1dd9d9047',
 'GE-CHK-002': '84c23982ccd32b128ca0466ce618221794ba5b549fd80bca705ea62b49f51f74',
 'GE-CHK-003': '14573d6f408f814d06262edcb5ecb7678cf6620c487fa9f6da88c495b185d4a3',
 'GE-CHK-004': '73b3f68e861c4ada7284d38ff60128622fa021fed487bb32d96949c67b8f9618',
 'GE-CHK-005': '0f2387b24e516594ebdb0ad2a15c2e2642e6dd4df1450bf2668e7a05445b390f',
 'GE-CHK-006': '571c6e1c7a8a079f4b5f6b789e66f46cf22269b864ffe9c535708559cbd16c03',
 'GE-CHK-007': 'e295701391b34f8bcc88aaca8959397404e6395da5ebdd1097d5348cfd5c3741',
 'GE-CHK-009': 'd49476fd311f0278aee672fc204be5529ea5d1ff396fb7c7a0da1f44a22b034c',
 'GE-CHK-010': '6c386c01f39304cef49829e5be3c422e3448e73c9320a2e7d085021b7789c51b',
 'GE-CHK-011': 'f96e9f9ecb05782b14dcd422c38fe5336a20376969f2c79f3fe73f7bac8a7ee6',
 'GE-CHK-101': '6211fce09b3625ffdfcc3720829e640b504fa54f40d99bfc19dbaad245cffb48',
 'GE-CHK-102': '20adc0d34d82af7255ff5f8f6d8dc88338ad95c700bae39703b233b4f5c6d441',
 'GE-CHK-103': 'd8dcb02011700b4425fcee52d04699fc9daa86bd150e0253793c103442f8fc46',
 'GE-CHK-104': '352bebc4979cce90a9b8a5331b308ed6485a3121eee828cfe38628e046732641',
 'GE-CHK-105': 'e18222f6303318e7a59969e7415f6f834616517ae62ec39016cbe6d31142d1fd',
 'GE-CHK-106': 'ec56d027f33c7df1471ddf7d21911b84c50a5854f8d13bd5792f49cec3658c4d',
 'GE-CHK-107': 'a55a62ded0e2a878b52ce98a753c6109a2f947f2e578b1e060d8e30d031e2c43',
 'GE-CHK-108': 'd765e65d222e76f893f4590d2eff81f0be2a5626822433d6109baf4954f1bf78',
 'GE-CHK-109': '4a0eeaa44570efe02aeba23151a589a19719a08ad52b6d098d907d799c060003',
 'GE-CHK-110': '69f2951763a158e2c2196f0dc6c7edce90a15d69ed528e826dbeda60da8b3131',
 'GE-CHK-111': 'f724e282df9408a3dd6d1b53d278307f370bf612252fd1b59c8842468c23630a',
 'GE-CHK-112': 'b22c3bb42214c88b0e50728977782b75fe6066578e54a9cc50e7c9ab829bebbd',
 'GE-CHK-113': '91ff08e9064c9eb0e99a4a918578a143e7e7c9e450b794e52756f137c9c99367',
 'GE-CHK-114': '1cd840993d98c523b29be01a2c86c4f3d2e42a31b04065c9e5ac7ea044d8e966',
 'GE-CHK-115': 'baf704d61da763500380eaa5d01b201f431c3bc1ea631895dba80730e0f0abcc',
 'GE-CHK-116': 'fd6aed5d618ce58adce8d2b3a14e7c648ba4da3dd2556e7eeb41383df165a96f',
 'GE-CHK-117': '083d0ec66278d4cd0c56439c61127f559529f0fbc392ba9ac2f8c038b5993ccd',
 'GE-CHK-118': 'f323e90ea109011e0e0536c2aa6374c86b1ed783c2ec1dbdca49fe3486774ed6',
 'GE-CHK-119': 'a61da4c8b27fb9ff5975ce5444df4285f6e8c0e3baba17fe2a59a67cfd04f19b',
 'GE-CHK-120': 'b06319b243c861b27eb8940c09b35b5c3e13d873cfdcc6da6f7d1d928cde27ea',
 'GE-CHK-121': '7e73e73d4ced034820f33bd437f29cbcbc36b0277fa09de8fa10fda5b300976b',
 'GE-CHK-122': '1f035d92034d752f08a8cf2f4f7eea3f9e8a4f34db4629f158e1465168e107ce',
 'GE-CHK-123': 'b88b308b87380dfbeffb99b66d3fbf652e65aa80a5bf9b7820329c5137a3ee8a',
 'GE-CHK-124': 'a011baa548f3a08b8063ccaa2efd4521b1db27220dbc7110a87f805fe96235f3',
 'GE-CHK-125': '4a96680bba8d2264a8074815b39f5fdeb71c2ecabf9d2d44b73ea947f115304c',
 'GE-CHK-126': '32d6164b8cb3dfe8891855c3ddb135e10aaad65681ef2bccb665b2fe6347bbad',
 'GE-CHK-127': '1d528238cad0252ed097a8013639ffc1af32e0b4822bd567eeb9e09e162039bf',
 'GE-CHK-128': '1fc61c6dc97adc4153c77cfe7d4ee40df10a513314d3ab23f0c32b51ceedc596',
 'GE-CHK-129': '85fcf5103eb56b08222c61caf4299dd70d2fa0e73b5e5318f49da249e458cd25',
 'GE-CHK-130': 'b77391118669c79321a0c6d953b5990b960953c45e91c0c9340439f3a60abd37',
 'GE-CHK-131': 'efbe3fe76e12e83bc994f856c6f0f072798986abd917fde10aa5d5672528e5b2',
 'GE-CHK-132': 'ad6e7439ea8dfc8c60ac83f8d10aa645a69c153f3ec35d0f3bee0015a13a5c87',
 'GE-CHK-133': '79dddce8015735c31456fd6c12ac20d6f81aa65a857697243a485e9b138e0a2c',
 'GE-CHK-134': 'e9761a92e907805f075a3589f9548c91949e30e3941b44c650e09e90e8d4a5ea',
 'GE-CHK-135': '6dad50f93c11afd3fd45df0eb3624b2659a1aa524e4a82bfe8cfc53d6cec4cb8',
 'GE-CHK-136': '848af56be58d602ce3fded22396cc69a0588649578a2cd0f832a304bb7cafd2f',
 'GE-CHK-137': '96b1b523b45cf3b6a391793a46593f78122f9e3b17e2f183e43e54b04e799757',
 'GE-CHK-138': 'f9350cdbb69a69de99ab72ef1ccc50d8eaac6c5b05c788697d956dbe6b353960',
 'GE-CHK-139': '62afa3e18bcff20c8a863887c05f5fb9b3fad66d86317a7077b2f414d481a524',
 'GE-CHK-140': '9d4758ee22bd5111a6f1cec024821322145b28b5ed060c2d871dc1dc6f95895d',
 'GE-CHK-141': '1e4dc52607461a35937b0f59e211c780a002dc3fd6ccecb3bc4d35472766f5e1',
 'GE-CHK-142': '3524c977296781e23c7e215ce1da172316ad865c846045be54236492970455bc',
 'GE-CHK-143': 'faf6135b58df40b45184d87341e6b3b4f328feadf961380ecc9e580bad40836f',
 'GE-CHK-144': '817f7d51c2a94f8845a7e4a39579436bba2fb31a863e50bde34b5634fa0f3757',
 'GE-CHK-145': 'b566088b3942af03b4d01df7844ca6c8c7862db8fdcf743f788380617e031de9',
 'GE-CHK-146': 'c1c944d319136ea9a505eae429602089c4ac0fc7049b0a702f711c082937ffc8',
 'GE-CHK-147': '4fd1d21e480071cb0bd6752233e4953725554bbae7eda8039ee70b18327afe5a',
 'GE-CHK-148': '724b647a99f2719f5551ae66d6877610ba27e351b55d0db009a37b91b9c560f6',
 'GE-CHK-149': '5af5ebbe7afe5568418978d09a44149838681b1a3683bcc5cccbd583448a1249',
 'GE-CHK-150': '69dba5e982caae290cbdea7366882fd31c54b88db7dbfa1fe48a70aa1635223d',
 'GE-CHK-151': '377993583c412389bbd2ba98f85315c1e3ce005a883e865df71289a15a9c3f0a',
 'GE-CHK-152': '853ca1ca384b98acc81cf84148c3d057955eaacc9d2f87ddc2cd9a290a190309',
 'GE-CHK-153': 'd1dcac31b72fc7b14eb67dcfb04fa28fcd257f172fbddf3ebf89bb2516d71c6d',
 'GE-CHK-154': '41c36128ec0c5f454efc92667c7d108fb4c78513e42d9c4336b3dd0d0f818c23',
 'GE-CHK-155': 'de4a8b0e8c8c8d2c99a888c24a97f0646dbcd82150a4aec8cb62b97b67cece68',
 'GE-CHK-156': '083f3c332382660fb988b2e38a044859bb5c8de43d42dd5f57ff1955d65436f1',
 'GE-CHK-157': 'a3f3aeb68794bd55ba13fbc3419e0e174e4e223b49a6b9d979561e4d3827579c',
 'GE-CHK-158': '0c6ce09bdaeea4e44bcb80f1cccb45258555e2fc82e84c9afd6282ccd94ec4bf',
 'GE-ADP-01': '347dc8296d948fa530070940bd9236331af4c8a762d9fceea207f04bae5dc422',
 'GE-ADP-02': '12c45472ea174421d35fde74060b855a145350df7fc58eec350d4237bfa012da',
 'GE-ADP-03': '9cb18f9eacba353006605d2978aaaf67509a7e466e23f9418508604157d7a726',
 'GE-ADP-04': 'ef6e1855d66ce69891a0efc1fe8723490dc496a94569bd89b88f5637c89fb206',
 'GE-ADP-05': 'eceeaa3ec382e1c5b9fde39663fa50acc42faedad24411ccd4d9547e450b69d7',
 'GE-ADP-06': 'f734df01cf3aabecb916949b1426a19993a06d5ca0ebc31e134db8a56c0b380b',
 'GE-ADP-07': '5c418826ab9587b79698a74ec2b7c429582f973da2f68cb78309766975f41a96',
 'GE-ADP-08': '68ad26cc7defc717fa39ce31f88886c64e7c2e97f9979e3baa55a1455a02a5bc',
 'GE-ADP-09': 'ce169e875fb84cdc83d491cbb0e33c06eb2d3dda3e7cc5ab6ba96191fe40e4f7',
 'GE-ADP-10': 'bd5f991956c806e6da0e613dac492e0958652a5a0f9c81202972edb6e24962ca',
 'GE-ADP-11': '9281b21027277636407195909f3df0b0703098ae84013b5f3370630ffef944c1',
 'GE-ADP-12': 'a1d886ab7ee5700880a552392837bf4c2e38f2a04d799a607b4cde037720b1f0'}


def compare_value(observed, expected, absolute, relative):
    if isinstance(expected, bool):
        return type(observed) is bool and observed == expected, None
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        if not isinstance(observed, (int, float)) or isinstance(observed, bool):
            return False, None
        if not math.isfinite(observed) or not math.isfinite(expected):
            return False, None
        return math.isclose(observed, expected, abs_tol=absolute, rel_tol=relative), abs(observed-expected)
    if isinstance(expected, list):
        if not isinstance(observed, list) or len(observed) != len(expected):
            return False, None
        pairs = [compare_value(a,b,absolute,relative) for a,b in zip(observed,expected)]
        differences = [d for _,d in pairs if d is not None]
        return all(ok for ok,_ in pairs), max(differences) if differences else None
    return type(observed) is type(expected) and observed == expected, None


def verify(bank_path):
    bank = json.loads(bank_path.read_text(encoding="utf-8"))
    cases = bank["cases"]
    ids = [c["case_id"] for c in cases]
    if len(ids) != len(set(ids)) or set(ids) != set(ORACLES):
        raise ValueError("Frozen case population differs from the reviewed independent oracle.")
    records = []
    for case in cases:
        cid = case["case_id"]
        contract = {"case_id":cid,"inputs":case["inputs"],"fixture":case["fixture"]}
        if canonical_hash(contract) != FROZEN_INPUT_SHA256[cid]:
            raise ValueError("Frozen input contract changed for " + cid + "; review the independent calculation.")
        values = ORACLES[cid]()
        assertions = case["assertions"]
        if {a["assertion_id"] for a in assertions} != set(values) or len(assertions) != len(values):
            raise ValueError("Frozen assertion population differs for " + cid)
        for assertion in assertions:
            aid = assertion["assertion_id"]
            observed = values[aid]
            tolerance = assertion["tolerance"]
            matched, difference = compare_value(observed, assertion["expected"],
                                                tolerance["absolute"], tolerance["relative"])
            records.append({"case_id":cid,"check_id":case["check_id"],"assertion_id":aid,
                            "name":assertion["name"],"observed":observed,
                            "expected":assertion["expected"],"unit":assertion["unit"],
                            "absolute_tolerance":tolerance["absolute"],
                            "relative_tolerance":tolerance["relative"],
                            "absolute_difference":difference,"status":"MATCH" if matched else "MISMATCH"})
    matched = sum(r["status"] == "MATCH" for r in records)
    return {"schema_version":"yeni.integration.independent-arithmetic-results.v1",
            "verification_level":"INDEPENDENT_EXAMPLE_ARITHMETIC",
            "scope":"Fixed independent worked-example arithmetic and deterministic data contracts only",
            "status":"MATCH" if matched == len(records) else "MISMATCH",
            "executed_at_utc":datetime.now(timezone.utc).isoformat(),
            "command":[Path(sys.executable).name, *sys.argv],
            "environment":{"python":platform.python_version(),"implementation":platform.python_implementation(),
                           "platform":platform.platform()},
            "bank_sha256":hashlib.sha256(bank_path.read_bytes()).hexdigest(),
            "oracle_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "case_count":len(cases),"assertion_count":len(records),"matched":matched,
            "mismatched":len(records)-matched,"yeni_runtime_executed":False,
            "recorded_pipeline_replay_executed":False,"live_etabs_executed":False,
            "engineering_acceptance":"NOT_RUN",
            "limitations":["No production calculation owner is called.",
                           "No recorded-source pipeline or native ETABS session is executed.",
                           "Printed-value tolerance and frozen arithmetic agreement are not engineering acceptance.",
                           "Contract fixtures check declared values, not setter behavior or transaction rollback.",
                           "The independent oracle is valid only for its explicitly frozen input contracts."],
            "results":records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", type=Path, default=Path(__file__).resolve().parents[1]/"GOLDEN_CASES.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify(args.bank)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({k:result[k] for k in ("verification_level","status","case_count","assertion_count","matched","mismatched")}, indent=2))
    return 0 if result["status"] == "MATCH" else 1


if __name__ == "__main__":
    raise SystemExit(main())
