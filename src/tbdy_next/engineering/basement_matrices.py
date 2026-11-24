"""Replay CSI's case stiffness with full and upper-only joint masses (TBDY Eq. 3.1)."""
from base64 import b64decode, b64encode
from collections import Counter, defaultdict
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import re
import zlib

from .basement_pier_geometry import required
from .pier_force_source import _table


SCHEMA = "tbdy.next.basement-modal-matrices.v1"
LIMITS = {"TXA": 16_384, "TXE": 4_000_000, "TXC": 4_000_000, "TXM": 12_000_000,
          "TXK": 120_000_000, "LOG": 1_000_000, "$et": 2_000_000}


def pack_matrices(header, source, ground_story):
    """Import one solver output family, keeping the native bytes in the scenario."""
    header = Path(header)
    required(header.suffix.upper() == ".TXA", "CSI_TXA_FILE_REQUIRED")
    files = {}
    for ext, limit in LIMITS.items():
        path = header.with_suffix("." + ext)
        if ext == "TXC" and not path.exists():
            continue
        required(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size <= limit,
                 "CSI_ARTIFACT_MISSING_OR_TOO_LARGE:" + ext)
        data = path.read_bytes()
        files[ext] = {"size": len(data), "sha256": sha256(data).hexdigest(),
                      "zlib_base64": b64encode(zlib.compress(data, 6)).decode("ascii")}
    required(isinstance(ground_story, str) and ground_story.strip() == ground_story and ground_story,
             "CSI_CANDIDATE_GROUND_STOREY_REQUIRED")
    return {"schema": SCHEMA, "source_data_sha256": source["source_data_sha256"],
            "ground_story": ground_story, "files": files}


def normalize_matrices(value, *, source_data_sha256):
    required(isinstance(value, dict) and set(value) == {"schema", "source_data_sha256", "ground_story", "files"}
             and value["schema"] == SCHEMA and value["source_data_sha256"] == source_data_sha256
             and isinstance(value["ground_story"], str) and value["ground_story"].strip() == value["ground_story"]
             and value["ground_story"],
             "CSI_MATRIX_SOURCE_BINDING_INVALID")
    files = value["files"]
    required(isinstance(files, dict) and set(files) in (set(LIMITS), set(LIMITS) - {"TXC"}),
             "CSI_MATRIX_FAMILY_INCOMPLETE")
    for ext, part in files.items():
        required(isinstance(part, dict) and set(part) == {"size", "sha256", "zlib_base64"}
                 and type(part["size"]) is int and 0 < part["size"] <= LIMITS[ext]
                 and isinstance(part["sha256"], str) and re.fullmatch("[0-9a-f]{64}", part["sha256"])
                 and isinstance(part["zlib_base64"], str)
                 and 0 < len(part["zlib_base64"]) <= 4 * (part["size"] // 3 + 128), "CSI_ARTIFACT_INVALID:" + ext)
    return value


def _unpack(files):
    native = {}
    for ext, part in files.items():
        decoder = zlib.decompressobj()
        try:
            data = decoder.decompress(b64decode(part["zlib_base64"], validate=True), part["size"] + 1)
        except (ValueError, zlib.error) as exc:
            raise ValueError("CSI_ARTIFACT_ENCODING_INVALID:" + ext) from exc
        required(decoder.eof and not decoder.unused_data and len(data) == part["size"]
                 and sha256(data).hexdigest() == part["sha256"], "CSI_ARTIFACT_DIGEST_DIFFERS:" + ext)
        native[ext] = data
    return native


def _model_lines(data):
    lines = data.splitlines()
    # ETABS annotates Save As in the file header and in the final log only.
    required(lines and lines[0].startswith(b"$ File ") and b"$ LOG" in lines, "CSI_MODEL_EXPORT_REQUIRED")
    start = lines.index(b"$ LOG")
    after = [line for line in lines[start:] if not re.fullmatch(rb"ETABS .+ File (?:saved as|imported from) .+", line, re.I)]
    return lines[1:start] + after


def _global_joint_axes(deck):
    # TXE uses local joint components. Only the default global joint axes are
    # supported. Other point assignment types require an explicit basis.
    first, last = deck.index(b"$ POINT ASSIGNS"), deck.index(b"$ LINE ASSIGNS")
    pattern = rb'\s*POINTASSIGN\s+"[^"]+"\s+"[^"]+"(?:\s+(?:DIAPH|RESTRAINT|USERJOINT)\s+"[^"]*")+\s*'
    required(first < last and all(not row.strip() or re.fullmatch(pattern, row, re.I)
                                  for row in deck[first+1:last]), "CSI_GLOBAL_JOINT_AXES_UNVERIFIED")


def _count(text, name):
    match = re.findall(re.escape(name) + r"\s*=\s*(\d+)", text, re.I)
    required(len(match) == 1, "CSI_MATRIX_COUNT_REQUIRED:" + name)
    return int(match[0])


def _equations(native, np, n, joints, n_constraints, rows):
    tokens = native["TXE"].split(b"\n", 1)[1].split()
    required(len(tokens) == 7 * joints, "CSI_EQUATION_JOINT_COUNT_DIFFERS")
    elevation = {row["PointElm"]: float(row["Z"]) for row in rows}
    required(len(elevation) == len(rows), "DUPLICATE_JOINT_MASS")
    constraints = defaultdict(list)
    if n_constraints:
        required("TXC" in native, "CSI_CONSTRAINT_EQUATIONS_REQUIRED")
        for c, q, factor in np.loadtxt(BytesIO(native["TXC"]), skiprows=1, ndmin=2):
            required(c == int(c) and q == int(q) and 0 < q <= n and np.isfinite(factor) and factor != 0,
                     "CSI_INVALID_CONSTRAINT_EQUATION")
            constraints[int(c)].append((int(q), factor))
    required(set(constraints) == set(range(-n_constraints, 0)), "CSI_CONSTRAINT_POPULATION_DIFFERS")
    axes = defaultdict(set)
    levels = defaultdict(set)
    physical = []
    seen = Counter()
    for offset in range(0, len(tokens), 7):
        point = tokens[offset].decode("ascii")
        eqs = [int(item) for item in tokens[offset+1:offset+7]]
        if point in elevation:
            seen[point] += 1
            physical.append((point, eqs))
        for dof, eq in enumerate(eqs):
            required(-n_constraints <= eq <= n, "CSI_EQUATION_OUT_OF_RANGE")
            if eq > 0:
                axes[eq].add(dof)
            if point in elevation:
                for active, _ in constraints[eq] if eq < 0 else [(eq, 1)] if eq else ():
                    levels[active].add(elevation[point])
    required(set(axes) == set(range(1, n+1)) and seen == Counter(elevation.keys()),
             "CSI_JOINT_OR_EQUATION_POPULATION_DIFFERS")
    # Verify a rigid translation in each global direction through every active
    # constraint on the physical mass joints. A shared rotational equation can
    # have two local rotation indices. Its translational influence remains zero.
    influence = np.zeros((n, 3))
    for q, dofs in axes.items():
        translations = dofs & {0, 1, 2}
        required(not translations or len(dofs) == 1, "CSI_TRANSLATION_AXES_MIXED")
        if translations:
            influence[q-1, next(iter(translations))] = 1
    for _, eqs in physical:
        for d, eq in enumerate(eqs):
            if eq < 0:
                moved = sum(f * influence[q-1] for q, f in constraints[eq])
                required(np.allclose(moved, np.eye(3)[d] if d < 3 else 0., rtol=0, atol=1e-10),
                         "CSI_CONSTRAINT_GLOBAL_TRANSLATION_UNRESOLVED")
    return levels, influence, physical


def _spectrum(np, solve, stiffness, mass, influence):
    from scipy.sparse.linalg import eigsh, LinearOperator
    indices = np.flatnonzero(mass > 0)
    roots = np.sqrt(mass[indices])
    def apply(v):
        rhs = np.zeros(mass.size)
        rhs[indices] = roots * v
        return roots * solve(rhs)[indices]
    operator = LinearOperator((len(indices), len(indices)), matvec=apply, dtype=float)
    k = min(8, len(indices) - 1)
    required(k >= 2, "INSUFFICIENT_MODAL_EQUATIONS")
    values, vectors = eigsh(operator, k=k, which="LA", tol=1e-10,
                            v0=np.random.default_rng(3311).normal(size=len(indices)))
    excitation = roots[:, None] * influence[indices, :2]
    total = (excitation ** 2).sum(axis=0)
    required(np.all(total > 0), "HORIZONTAL_ACTIVE_MASS_REQUIRED")
    modes = []
    for i in np.argsort(-values):
        mu, q = values[i], vectors[:, i]
        required(mu > 0, "NONPOSITIVE_MODAL_COMPLIANCE")
        residual = np.linalg.norm(apply(q) - mu*q) / mu
        required(residual < 1e-7, "MODAL_EIGENPAIR_RESIDUAL_TOO_LARGE")
        rhs = np.zeros(mass.size)
        rhs[indices] = roots*q
        displacement = solve(rhs)
        restoring = stiffness @ displacement
        inertia = mass*displacement/mu
        equilibrium = np.linalg.norm(restoring-inertia) / np.linalg.norm(inertia)
        required(equilibrium < 1e-5, "MODAL_FORCE_EQUILIBRIUM_DIFFERS")
        rx, ry = (excitation.T @ q) ** 2 / total
        modes.append({"mode": len(modes)+1, "period_s": round(float(2*np.pi*np.sqrt(mu)), 10),
                      "X": round(float(rx), 9), "Y": round(float(ry), 9),
                      "relative_residual": float(f"{residual:.1e}"), "force_residual": float(f"{equilibrium:.1e}")})
    return modes


def solve_period_pair(source, modal, top):
    try:
        import numpy as np
        from scipy.sparse import coo_matrix, diags
        from scipy.sparse.linalg import splu
    except ImportError as exc:
        raise ValueError("BASEMENT_MODAL_MATRICES_REQUIRE_NUMPY_SCIPY") from exc
    files = source["basement_modal_matrices"]["files"]
    native = _unpack(files)
    archive = source["analysis_archive"]
    original = _model_lines(b64decode(archive["model_export_base64"], validate=True))
    required(original == _model_lines(native["$et"]), "CSI_PRIVATE_MODEL_INPUTS_DIFFER")
    _global_joint_axes(original)
    header, log = native["TXA"].decode("ascii"), native["LOG"].decode("latin1")
    required(header.splitlines()[1].strip().strip('"').casefold() == modal.casefold()
             and re.search(r"UNITS \(FORCE, LENGTH, TEMPERATURE, TIME\)\s*= kN, m, .C, sec", log)
             and _count(log, "NUMBER OF NEGATIVE EIGENVALUES") == 0
             and log.count("A N A L Y S I S   C O M P L E T E") == 1, "CSI_CASE_UNITS_OR_STABILITY_UNVERIFIED")
    block = re.split(r"(?:R I T Z|E I G E N)   M O D A L   A N A L Y S I S", log)
    required(len(block) == 2 and re.search(r"CASE:\s*" + re.escape(modal) + r"\s*\n", block[1], re.I)
             and "USING STIFFNESS AT ZERO (UNSTRESSED) INITIAL CONDITIONS" in block[1], "CSI_MODAL_STIFFNESS_UNVERIFIED")
    n = _count(header, "number of active equations")
    n_constraints = _count(header, "number of constraint equations")
    joints = _count(header, "number of regular joints") + _count(header, "number of internal master joints")
    required(2 < n <= 250000 and n == _count(block[1], "NUMBER OF STIFFNESS DEGREES OF FREEDOM"), "CSI_STIFFNESS_SIZE_DIFFERS")
    rows = _table(source["vs04_basis_probe"]["table_reads"], "Assembled Joint Masses")
    levels, influence, physical = _equations(native, np, n, joints, n_constraints, rows)
    idx, col, mass = np.loadtxt(BytesIO(native["TXM"]), skiprows=1, unpack=True)
    required(len(idx) == n and np.array_equal(idx, np.arange(1, n+1)) and np.array_equal(idx, col)
             and np.all(np.isfinite(mass)) and np.all(mass >= 0), "CSI_DIAGONAL_ASSEMBLED_MASS_REQUIRED")
    positive = np.flatnonzero(mass > 0)
    required(len(positive) == _count(block[1], "NUMBER OF MASS DEGREES OF FREEDOM")
             and all(len(levels[q+1]) == 1 for q in positive), "CSI_MASS_ELEVATION_UNRESOLVED")
    upper = mass.copy()
    for q in positive:
        if next(iter(levels[q+1])) <= top:
            upper[q] = 0
    required(0 < np.count_nonzero(upper) < len(positive), "CSI_UPPER_MASS_SCOPE_EMPTY")
    # Independent physical masses are printed to 0.0001 t. Fixed translations
    # produce support reactions and are excluded from the active matrix sum.
    point_equations = dict(physical)
    for side, values in ((True, upper), (False, mass-upper)):
        pop = [r for r in rows if (float(r["Z"]) > top) == side]
        for d, key in enumerate(("UX", "UY", "UZ")):
            vals = [float(r[key]) for r in pop if point_equations[r["PointElm"]][d] != 0]
            required(abs(sum(vals) - values @ influence[:, d]) <= len(vals)*.0000501,
                     "CSI_ACTIVE_MASS_CONTROL_DIFFERS:" + key)
    rr, cc, val = np.loadtxt(BytesIO(native["TXK"]), skiprows=1, unpack=True)
    required(len(rr) == _count(log, "NUMBER OF NON-ZERO STIFFNESS TERMS") and np.all(np.isfinite(val))
             and np.all((cc >= 1) & (rr <= n) & (cc <= rr)) and np.all(rr == rr.astype(int))
             and np.all(cc == cc.astype(int)), "CSI_LOWER_STIFFNESS_DATA_INVALID")
    lower = coo_matrix((val, (rr.astype(int)-1, cc.astype(int)-1)), shape=(n,n)).tocsc()
    required(lower.nnz == len(rr), "CSI_DUPLICATE_STIFFNESS_TERM")
    stiffness = (lower + lower.T - diags(lower.diagonal())).tocsc()
    stiffness.eliminate_zeros()
    diagonal = stiffness.diagonal()
    required(np.all(diagonal > 0), "CSI_NONPOSITIVE_STIFFNESS_DIAGONAL")
    scale = 1/np.sqrt(diagonal)
    scaling = diags(scale)
    scaled = (scaling @ stiffness @ scaling).tocsc()
    factor = splu(scaled, permc_spec="MMD_AT_PLUS_A", diag_pivot_thresh=0., options={"SymmetricMode": True})
    def solve(rhs):
        return scale * factor.solve(scale*rhs)
    return {"active_equations": n, "mass_equations": len(positive), "upper_mass_equations": int(np.count_nonzero(upper)),
            "constraint_equations": n_constraints, "full": _spectrum(np, solve, stiffness, mass, influence),
            "upper": _spectrum(np, solve, stiffness, upper, influence), "stiffness_sha256": files["TXK"]["sha256"],
            "active_mass_t": {k: round(float(mass @ influence[:,d]), 6) for d,k in enumerate(("X","Y","Z"))},
            "upper_active_mass_t": {k: round(float(upper @ influence[:,d]), 6) for d,k in enumerate(("X","Y","Z"))}}
