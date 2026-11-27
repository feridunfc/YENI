"""Typed receipt dependencies for the full, frozen building scope."""
from graphlib import TopologicalSorter
from .pipeline_snapshot import _digest

# The evaluation order and owners come from stage_registry. The contract names
# the persisted input edges and the discriminator of each registered output.
CONTRACTS = {
    "schema-discovery": ((), "stage", "MODAL_SCHEMA_DISCOVERY"),
    "schema": (("schema-discovery",), "stage", "MODAL_ROW_VALIDATION"),
    "modal": (("schema",), "stage", "MODAL_NUMERICAL_CHECK"),
    "quick-geometry": ((), "stage", "QUICK_GEOMETRY_SCREENING"),
    "quick-extra": (("quick-geometry",), "stage", "VS03_MATERIAL_A1"),
    "vs04-schema": ((), "stage", "VS04_ANALYSIS_SOURCE_SCHEMA"),
    "vs04-numerics": (("vs04-schema",), "stage", "VS04_ANALYSIS_NUMERIC_SOURCE"),
    "vs04-readiness": (("vs04-schema","vs04-numerics"), "stage", "VS04_E_NORMATIVE_READINESS"),
    "vs04-pipeline": (("modal","vs04-readiness"), "stage", "VS04_E_TO_J_SAME_RUN_SOURCE_PIPELINE"),
    "vs05-story-drift": (("vs04-pipeline",), "schema", "tbdy.next.vs05.story-drift-check-record.v1"),
    "r03-analysis-setup": (("vs04-schema",), "schema", "tbdy.next.r03.model-analysis-setup-audit.v2"),
    "column-axial": (("quick-geometry","quick-extra","r03-analysis-setup"), "schema", "tbdy.next.column-axial-check.v1"),
    "column-pmm": (("column-axial",), "schema", "tbdy.next.column-pmm-check.v1"),
    "r08-second-order": (("vs05-story-drift",), "schema", "tbdy.next.r08.story-pdelta-source-numerical.v2"),
    "building-design": (("column-pmm","r08-second-order","vs04-pipeline"), "schema", "tbdy.next.building-results.v1"),
    "engine-results": (("building-design",), "schema", "tbdy.next.pipeline-stage-snapshot.v3"),
}

# These are transport contracts. A reported design failure or normative hold
# remains valid evidence. A missing or ill-typed numerical population cannot
# be substituted for an upstream stage.
FIELDS = {
    "schema-discovery": ("observed_fields", list), "schema": ("case_row_count", int),
    "modal": ("case", str), "quick-geometry": ("checks", list), "quick-extra": ("checks", list),
    "vs04-schema": ("tables", list), "vs04-numerics": ("results", list),
    "vs04-readiness": ("checks", list), "vs04-pipeline": ("stages", dict),
    "vs05-story-drift": ("evaluated_story_case_direction_count", int),
    "r03-analysis-setup": ("defined_combination_names", list), "column-axial": ("columns", list),
    "column-pmm": ("members", list), "r08-second-order": ("direction_results", dict),
    "building-design": ("column_count", int), "engine-results": ("stage_inventory", list),
}


class BuildingStageGraph:
    def __init__(self, registry, input_sha):
        self.input_sha = input_sha
        owners = [(name, row["owner"]) for row in registry for name in row["receipts"] if name in CONTRACTS]
        self.order = [name for name,_ in owners]
        visited = set()
        for name in self.order:
            if name in visited or not set(CONTRACTS[name][0])<=visited:
                raise ValueError("BUILDING_DAG_INVALID_REGISTRY:"+name)
            visited.add(name)
        if visited != CONTRACTS.keys():
            raise ValueError("BUILDING_DAG_UNREGISTERED_STAGE")
        tuple(TopologicalSorter({name:v[0] for name,v in CONTRACTS.items()}).static_order())
        self.topology_sha256 = _digest([[n,owner,*CONTRACTS[n],FIELDS[n][0],FIELDS[n][1].__name__] for n,owner in owners])
        self.outputs = {}

    def before(self, name):
        if name=="live-capture":
            needs = ("engine-results",)
        else:
            needs = CONTRACTS[name][0]
        missing = [p for p in needs if p not in self.outputs]
        if missing or name in self.outputs:
            raise ValueError("BUILDING_DAG_BLOCKED:"+name+":"+",".join(missing or ["DUPLICATE"]))

    def validate(self, name, payload, input_sha):
        self.before(name)
        if input_sha != self.input_sha:
            raise ValueError("BUILDING_DAG_SOURCE_CHANGED:"+name)
        if name=="live-capture":
            if payload.get("engine_snapshot",{}).get("snapshot_sha256")!=self.outputs["engine-results"]:
                raise ValueError("BUILDING_DAG_INVALID_TERMINAL")
            return
        _,field,value = CONTRACTS[name]
        if payload.get(field)!=value or len(payload)<3:
            raise ValueError("BUILDING_DAG_WRONG_OUTPUT:"+name)
        key,kind=FIELDS[name]
        datum=payload.get(key)
        if type(datum) is not kind or (datum<0 if kind is int else not datum):
            raise ValueError("BUILDING_DAG_INVALID_CONTENT:"+name)
        if name=="engine-results":
            inventory = {e["stage"]:e["payload_sha256"] for e in payload["stage_inventory"]}
            if (inventory!=self.outputs or len(inventory)!=len(payload["stage_inventory"])
                    or payload.get("input_sha256")!=input_sha):
                raise ValueError("BUILDING_DAG_SNAPSHOT_DEPENDENCIES_CHANGED")

    def accepted(self, name, payload):
        if name!="live-capture":
            self.outputs[name] = _digest(payload)

    def projection(self, building):
        if set(self.outputs)!=set(self.order):
            raise ValueError("BUILDING_DAG_INCOMPLETE_PROJECTION")
        return {"schema":"tbdy.next.building-stage-projection.v1","input_sha256":self.input_sha,
                "topology_sha256":self.topology_sha256,"stages":{n:self.outputs[n] for n in self.order},
                "building_sha256":_digest(building)}


def verified_projection(directory, input_sha, case):
    """Replay stage identities from the exact archive requested by the HTTP adapter."""
    from .pipeline import stage_registry
    from .pipeline_snapshot import method_fingerprint, read_receipts, read_snapshot
    records = read_receipts(directory, input_sha=input_sha)
    snapshot = read_snapshot(directory, input_sha=input_sha, receipts=records)
    registry = stage_registry()
    if (not snapshot or snapshot["method"]!=method_fingerprint() or snapshot["stage_plan_sha256"]!=_digest(registry)
            or records["modal"]["payload"]["case"]!=case or "building-design" not in records):
        raise ValueError("REQUESTED_BUILDING_SOURCE_CASE_OR_METHOD_DIFFERS")
    graph=BuildingStageGraph(registry,input_sha)
    for name, record in records.items():
        graph.validate(name,record["payload"],record["input_sha256"])
        graph.accepted(name,record["payload"])
    return graph.projection(snapshot["results"]["building_design"])
