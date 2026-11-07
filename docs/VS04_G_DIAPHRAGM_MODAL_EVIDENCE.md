# VS04-G — Diaphragm assignment and response-spectrum modal diagnostic

### Trigger and accepted status

The Windows VS04-F real-source replay at branch `82ff23f` returned:
`SEISMIC_MASS_RECONCILIATION`, `RESPONSE_SPECTRUM_CASE_BINDINGS` and
`PHYSICAL_STORY_GEOMETRY` as `SOURCE_CONTRACT_OBSERVED_UNAPPROVED`,
with the fourth `SPECTRUM_MODAL_OUTPUT = NOT_PROVEN`.

- Group/Story X/Y = 4380.4916 ton
- Assembled joints (6151 point elements) X/Y = 4380.5183 ton
- Difference = 0.0267 ton (26.7 kg; ~0.00061% of group total)
- All three reported diaphragm X/Y masses = 0 ton
- RSX/RSY `EccenRatio=0.05`, not proof of applied eccentricity
- `Response Spectrum Modal Info` returned `ret_code=1` for both
  previously tested signatures while original selected cases were empty
- `I` value in spectrum header = 1.5, but source units metadata labels
  the `I` field `sec`; preserve anomaly without guessing.

## Narrow new source collection

`tools/probe_vs04g_diaphragm_windows.py` uses the already-open and
analysis-locked ETABS model and the established same-thread `comtypes`
session. It gets the exact available table keys and captures:

1. `Diaphragm Definitions`
2. `Area Assignments - Diaphragms`
3. `Joint Assignments - Diaphragms`
4. `Response Spectrum Modal Info` under original display selection
5. `Response Spectrum Modal Info` with exactly `RSX` and `RSY` selected

The RSX/RSY display selection is temporary and restored in `finally`.
The previous selection, current units, and exact restoration are checked;
failed restoration stops capture and prohibits a successful output.

**No analysis execution, no model save, no structural property or mass
modification, no present-units mutation.** The only setter used is the
reversible display-case selector, already accepted in VS01/VS04.

The code returns the complete raw source row and field metadata for exact
observed keys, `CAPTURE_ERROR` for unavailable output, and shape-only
`OBSERVED_UNAPPROVED` for internally coherent nonempty tables. It does
not infer diaphragm assignment, constraint effectiveness or code compliance.
The original VS04-E and VS04-F evidence remains immutable.

### Why these tables matter

A diaphragm definition is not proof it is assigned. A shell/area diaphragm
assignment can constrain its corners and additional internal analysis joints,
including automeshing points; a point assignment has different scope.
CSI guidance:
https://docs.csiamerica.com/help-files/etabs/Menus/Assign/Shell/Diaphragms_Shells.htm

Furthermore, story lumped-mass accounting may differ from assembled joint
masses for meshed elements between stories. CSI mass FAQ:
https://web.wiki.csiamerica.com/wiki/spaces/etabs/pages/1474672/Mass%2BFAQ

Selection-dependent table output is an investigated hypothesis only. If
`Response Spectrum Modal Info` still returns `ret_code=1` after confirmed
RSX/RSY selection, it remains `NOT_PROVEN`: do not report false empty rows.

### Windows PowerShell

```powershell
Set-Location "C:\Users\efeya\PycharmProjects\YENI_VS04"
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
.\.venv\Scripts\python.exe tools\probe_vs04g_diaphragm_windows.py `
  --out ".receipts\VS04\VS04G_DIAPHRAGM_MODAL_$stamp.json"
```

Send the resulting JSON only after inspecting for sensitive structural
model data; do not push it to GitHub.

### Supervisor acceptance

This is a bounded source-capture implementation only. Offline CI passing
cannot prove the Windows ETABS 23.2 behavior. After actual capture,
reconcile defined diaphragms vs assigned shells/joints vs
`Mass Summary by Diaphragm` zeros, and only then decide whether
`EccenRatio=0.05` is effective in the analyzed load cases.

`ENGINEERING_RELEASE=NOT_READY`, `main` unchanged, `MERGE=HOLD`.
