"""CLI and compatibility re-export wrapper for tbdy_next.etabs_source_gateway_windows."""
from __future__ import annotations

import sys

from tbdy_next.etabs_source_gateway_windows import (
    BIND_SCHEMA,
    OUTPUT_SCHEMA,
    PROFILES,
    SCHEMA,
    SourceError,
    attach_live,
    available_tables,
    bind,
    canonical,
    capture,
    capture_distributed_frame_loads_by_object,
    capture_physical_object_inventory,
    capture_receipt_sha,
    dual_hashes,
    field_schema,
    get_results_setup_state,
    main,
    make_template,
    model_file,
    read_json,
    read_table,
    resolve_keys,
    restore_results_setup_state,
    return_code,
    save_new,
    seal,
    selected_cases,
    selected_combinations,
    semantic_source_sha,
    set_cases,
    set_combinations,
    verify,
)

__all__ = [
    "BIND_SCHEMA",
    "OUTPUT_SCHEMA",
    "PROFILES",
    "SCHEMA",
    "SourceError",
    "attach_live",
    "available_tables",
    "bind",
    "canonical",
    "capture",
    "capture_distributed_frame_loads_by_object",
    "capture_physical_object_inventory",
    "capture_receipt_sha",
    "dual_hashes",
    "field_schema",
    "get_results_setup_state",
    "main",
    "make_template",
    "model_file",
    "read_json",
    "read_table",
    "resolve_keys",
    "restore_results_setup_state",
    "return_code",
    "save_new",
    "seal",
    "selected_cases",
    "selected_combinations",
    "semantic_source_sha",
    "set_cases",
    "set_combinations",
    "verify",
]

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (SourceError, OSError) as exc:
        print("SOURCE_CAPTURE_ERROR:", exc, file=sys.stderr)
        raise SystemExit(3)
