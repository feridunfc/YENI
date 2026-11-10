"""Offline reproducible B1 pilot. Data are artificial numerical fixtures, NOT projects."""
from __future__ import annotations
from dataclasses import replace
from tbdy_column_core.domain.quantities import Length,Force,Moment,Stress,ElasticModulus,Angle
from tbdy_column_core.domain.identity import RevisionRef,RuleRef,SourceRef,EvidenceRef
from tbdy_column_core.domain.coordinates import Point3D,LocalFrame,AxialSignConvention
from tbdy_column_core.domain.tolerances import NumericalPolicy
from tbdy_column_core.domain.section_models import (
    RectangularSection,ConcreteMaterial,DesignSteelLaw,
    DesignMaterial,BarPoint,LongitudinalLayout,RCSection,
)
from tbdy_column_core.domain.section_requests import (
    AtStrainState,EnvelopeAtAxialForce,RadialCapacityAtAxialForce,
    SectionCapacityProblem,FrameModelContract,
)
from tbdy_column_core.application.services import calculate_section
from tbdy_column_core.reporting.section_report import section_report_html,section_report_json


def fixture_problem(*, layout="A", b_mm=400, h_mm=600, units="mm",
                    request=None, angle_count=72, max_iterations=100):
    if layout not in ("A","B") or units not in ("mm","cm"):
        raise ValueError("fixture only supports A/B and mm/cm")
    f=Length.mm if units=="mm" else Length.cm
    factor=1. if units=="mm" else .1
    concrete=ConcreteMaterial(RevisionRef("material","C35","rev1"),Stress.mpa(35))
    rule=RuleRef("TS500","2000","7.1")
    steel=DesignSteelLaw("B420C",Stress.mpa(420/1.15),
                         ElasticModulus.mpa(200000),
                         RevisionRef("steel-law","B420C","rev1"))
    material=DesignMaterial(concrete,Stress.mpa(35/1.5),.79,.003,
                            (steel,),rule,
                            RevisionRef("design-law","C35+B420C","rev1"))
    x=b_mm/2-50
    y=h_mm/2-50
    coords=[(-x,-y),(x,-y),(-x,y),(x,y)]
    if layout=="B":
        coords.extend([(-x,0),(x,0)])
    bars=tuple(BarPoint(f"b{i+1}",f(px*factor),f(py*factor),
                        f(20*factor),"B420C") for i,(px,py) in enumerate(coords))
    geom=RectangularSection(f(b_mm*factor),f(h_mm*factor))
    long=LongitudinalLayout(f(30*factor),f(10*factor),bars,
                             RevisionRef("longitudinal",layout,"rev1"))
    section=RCSection(RevisionRef("section",f"R{b_mm}x{h_mm}{layout}","rev1"),
                      geom,material,long)
    origin=Point3D(Length.mm(0),Length.mm(0),Length.mm(0))
    frame=LocalFrame(origin,(1.,0.,0.),(0.,1.,0.),(0.,0.,1.))
    frame_contract=FrameModelContract(frame,AxialSignConvention.F1_COMPRESSION_POSITIVE,
                                      "SECTION_GEOMETRIC_CENTROID")
    policy=NumericalPolicy(Length.mm(.001),1e-10,Force.n(1),Moment.nmm(1000),
                           0.,angle_count,max_iterations)
    if request is None:
        request=AtStrainState(Angle.deg(33),Length.cm(24))
    source=EvidenceRef("NUMERICAL_EXAMPLE",
        SourceRef("MANUAL","synthetic_fixture","layout:"+layout,"mm","offline"),
        RevisionRef("source","synthetic","rev1"))
    return SectionCapacityProblem(section,request,policy,frame_contract,(source,))


def main():
    for layout in ("A","B"):
        problem=fixture_problem(layout=layout)
        result=calculate_section(problem)
        json_text=section_report_json(result)
        html=section_report_html(result)
        print(f"LAYOUT_{layout}: {result.status.value}, {len(result.states)} state, "+
              f"N={result.states[0].n.as_n:.3f} N "+
              f"JSON={len(json_text)} chars HTML={len(html)} chars")
    second=fixture_problem(layout="B",b_mm=450,h_mm=650,
        request=EnvelopeAtAxialForce(Force.kn(500)),angle_count=8)
    result=calculate_section(second)
    print(f"SECOND_SECTION: {result.status.value}, {len(result.states)}/8 angles, "+
          f"issues={len(result.issues)}")
    assert all(not x for x in (result.full_column_design_pass,))
    print("B1_OFFLINE_EXAMPLE_OK; NOT A COLUMN-CODE DESIGN APPROVAL")
    from tbdy_column_core.engineering.convergence import assess_radial_angular_refinement
    radial_problem=fixture_problem(layout="B",angle_count=8,
        request=RadialCapacityAtAxialForce(
            Force.kn(500),Moment.kn_m(40),Moment.kn_m(20)))
    refinement=assess_radial_angular_refinement(radial_problem)
    print(f"B2_ANGULAR_REFINEMENT: {refinement.status.value}, "+
          f"8/16 sampled angles, "+
          f"delta_nmm={refinement.observed_delta.as_nmm if refinement.observed_delta else 'UNRESOLVED'}, "+
          f"budget_nmm={refinement.numeric_budget.as_nmm}")
    print("B2_OBSERVED_NUMERIC_EVIDENCE_ONLY; NOT A CODE PASS")


if __name__=="__main__":
    main()
