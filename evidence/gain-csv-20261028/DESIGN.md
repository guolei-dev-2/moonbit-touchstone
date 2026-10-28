# Round13: selected GT samples to a CSV review table

## Bounded finding and selected need

No old defect established. Reviewed the real-file -> Gamma/ohm GT -> sampled limit report -> recipient review chain. The old gain-check correctly emits counts and first tied extrema; it intentionally does not list every selected sample or its individual limit disposition. The separate raw GT JSON contains all frequencies but no selected-band classification. A reviewer wanting a CSV table must join these manually while preserving zero/overflow/underflow/singular meaning.

Select one finite extension: a public pure-MoonBit GT sample CSV renderer plus opt-in gain-csv file command, consuming the existing canonical trace and unchanged limit contract. Do not change ordinary gain-check, gain-record/review protocol, old numerical algorithms, accepted inputs, historical evidence or existing public declarations. No new measurements, optimizer, CSV importer, generic table engine, workbook generator or additional RF feature.

## Ecosystem and primary-source review, 2026-10-28

- https://mooncakes.io/docs/ihb2032/MoonFrame@0.5.5 : existing DataFrame and CSV read/write/format exports. The versioned published page was reviewed; it displays newer versions too. This is general tabular work, not loaded-GT state/limit selection. Do not recreate a DataFrame or claim CSV novelty/absence.
- https://mooncakes.io/docs/superbigcup325/moonlake@0.5.0 : existing SQL over CSV/Parquet and columnar results. A downstream consumer category, not an RF semantic renderer. No dependency/copy or unverified interoperability claim.
- https://scikit-rf.readthedocs.io/en/latest/_modules/skrf/io/general.html : network_2_spreadsheet documents S-parameter export to CSV/Excel/HTML. The separate generated function page could not be fetched; do not claim it was reviewed. The existing export use case is established.
- https://helpfiles.keysight.com/csg/e5072a/measurement/data_output/saving_trace_data_to_a_file.htm : trace CSV export for PC processing, frequency/data column example. Link only; no instrument compatibility claim.
- Local API discovery with fixed toolchain moon ide doc StringBuilder and Double::to_string; use existing core builtins and bounded numeric/fixed-enum fields. No arbitrary strings require CSV quoting. No new runtime dependency.

The difference is a narrow loaded-GT review table in MoonBit: original full-trace index, Hz, linear/dB gain, canonical state, per-point bound flags and sample disposition together with global sampled report status/coverage. No RF math moves to Node and no external algorithm/code is copied.

## Frozen contract before implementation

Public transducer_gain_samples_csv(points,start_hz,end_hz,minimum_db?,maximum_db?) -> String raise reuses check_transducer_gain for whole-trace and bounds validation. It accepts the same canonical trace<=100000 and finite ordered frequencies, including empty traces. It emits one header plus every original sample inside the closed band in original order; no interpolation, filtering to failures, renumbering or row truncation. LF comma-delimited, ASCII, no BOM. Fixed header:

point,frequency_hz,gain,gain_db,state,start_hz,end_hz,minimum_db,maximum_db,below_minimum,above_maximum,sample_status,report_status,range_covered

Numbers use core Double::to_string; booleans true/false. Empty optional numeric cells are not invented zero. Zero power has gain0, blank dB and statezero, denotes negative-infinite dB, fails any finite lower bound and satisfies any finite upper bound. Singular has blank gain/dB and blank below/above flags; sample_statusunknown. Positive overflow/underflow retain finite dB and are classified normally. Other known points have true/false bound flags and sample_statuspass/fail; missing bound means false, strict violations preserve inclusive equality. Global report_status/range_covered repeat in rows, so a locally passing sample is not confused with whole-band acceptance. Empty selection yields header only; CLI still exits4.

New gain-csv INPUT OPTIONS [OUTPUT] has the exact gain-check query options, units, Gamma defaults and required ohm fields. It uses the same parsed network and GT trace and returns text plus internal summary/context through the bridge; Node emits the CSV text and maps global analysis status to0/3/4, with errors2 and exclusive OUTPUT. The CSV intentionally does not carry terminal conditions, reference ohms, byte identity or a receipt; retain a companion gain-record when those are needed. Do not infer authenticity or approval from this table.

The gain-check and new gain-csv bridge branches share the existing query/GT/report path; the old payload stays structurally identical. Existing receipt transport remains gain-check-only, and no existing flag changes meaning. This is an authorized13-round addition to the earlier CSV non-goal; the11/12 historical scope/evidence statements stay dated.

## Acceptance and stopping boundary

New public renderer tests use hand-specified canonical mixed-state truth cases, not duplicated RF formulas: all five states, both bounds/one bound/zero bounds/inclusive equality, original indices/closed selection/global fail or inconclusive, empty/header-only, invalid canonical state outside band, invalid options/order, and100000/100001 capacity. Run only new test file on JS/Wasm-GC/native; new pure-MoonBit consumer on JS/Wasm-GC; strict all-target check, format and regenerated API review. No old numerical/receipt suite rerun.

Independent Python csv.DictReader consumer checks parsed cells, header, row counts and fixed expected classifications. Actual file CLI covers Gamma/ohm,0/3/4/2, saved failing CSV/refused overwrite, no selected samples, zero/singular/extreme states, invalid new query/fixture key, and changed shared-path ordinary gain-check payloads versus sealed references. Frozen numeric references may be consumed without rerunning RF oracles. No new manufacturer input is needed. After one successful relevant verification pass, align README/<=30-line proposal and attachment, prove old sources/API retained, bind source/compiled identities, package locally, per-file read back both ZIPs and close RESULT. No push/publish/contest/account/global SDK or STATE edit, no other-chat message; sealed05–12 are read-only.
