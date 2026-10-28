# Round13 outcome: loaded-GT selected-sample CSV review

One bounded feature need was selected from the real-file -> Gamma/ohm GT -> sampled limit summary -> recipient review chain. No existing-product defect was established. A summary intentionally gives counts and extrema, while raw GT gives all points without the query's selected-band classification; reviewers needed to join them. The new opt-in gain-csv command and one public pure-MoonBit transducer_gain_samples_csv renderer provide that table directly.

## Final implementation

- New gain_csv.mbt reuses check_transducer_gain for canonical whole-trace and bounds validation, including malformed points outside the band. It renders all selected original indices, Hz, linear/dB/state, finite optional bounds, known/unknown per-point flags and sample status, together with repeated global report status/coverage. No interpolation, truncation, renamed fields or RF algorithm change.
- Zero has gain0/blank dB but remains known negative-infinite power; singular has blank gain/dB/limit flags and unknown sample status. Positive overflow/underflow retain finite dB and known limit disposition. Empty selection produces only a header with CLI exit4, never an invented passing row.
- The bridge shares the old gain-check parsing/GT/report path with gain-csv. Only gain-csv attaches the CSV text. Ordinary gain-check retains its exact parsed payload; new and old callers use the same network/trace. The public library API addition is one standalone renderer; all existing declarations remain.
- Node adds only the command name to usage, the no-fixture-IO path and status-exit mapping. It emits the already rendered MoonBit text through existing stdout/exclusive-output IO. No new runtime dependency or RF/CSV logic is moved to Node.
- CSV intentionally omits terminal conditions, reference impedance and byte identity; a companion unchanged gain-record provides them. Existing v1 receipts remain gain-check-only. This is a finite13-round extension of the historically dated11-round CSV non-goal, not a claim that old releases already supported it.

## Relevant verification completed once

- moon info regenerated interfaces. Final closure checks retain all old public declaration blocks and permit only transducer_gain_samples_csv at the root; non-root existing interface files stay byte-identical.
- New gain_csv_test.mbt:7/7 on JS,7/7 on Wasm-GC,7/7 native. Hand-specified five-state truth table, closed selection/original indices, inclusive zero bounds, single-bound zero/singular cases, local-vs-global disposition, header-only empty selections, canonical validation including out-of-band input, invalid bounds/order, full100000 rows and rejected100001.
- New pure-MoonBit examples/gain_csv ran on JS and Wasm-GC. Their parsed CSV matches the actual ohm file CLI output, without executing the examples again.
- Strict all-target check, release JS build, format and format-check pass. Initial new example used an unbound print identifier; corrected to existing println before the successful final pass. Diagnostic retained in DEVELOPMENT-CORRECTIONS.json and not counted as an old defect.
- independent-first.json records27 actual CLI processes and29 consumer checks. Python stdlib csv.DictReader validates columns, empty values, row indices, state/flags, sampled/global dispositions, actual Gamma/ohm files,0/3/4/2 exits, saving a failing CSV and refusing overwrite. A100000-point synthetic file exports without truncation and every row is consumed. Two pure-example artifact comparisons are part of29, not additional CLI processes.
- Because the shared branch changed, two ordinary gain-check payloads and one full old receipt review are compared with sealed12 evidence. The v1 receipt also rejects the new gain-csv replay command. No old43/32 receipt suite,39/27 gain-report collection, RF reference environment, manufacturer model collection or unchanged numerical suite is rerun. New GT numerical comparisons:0; new manufacturer inputs:0.

## Scope, sources and closure

DESIGN.md records primary ecosystem/similar-tool review before implementation: MoonFrame0.5.5 tabular CSV rendering, moonlake0.5.0 downstream SQL/CSV, scikit-rf spreadsheet export, Keysight trace export. No copied code, dependency, novelty/exclusivity claim or verified third-party integration. This remains a typed RF-semantic review table, not a general CSV engine, workbook editor, new measurement or instrument certification.

README, GAIN-CSV.md and <=30-line PROPOSAL/identical attachment describe the final behavior and its limits. Closure binds production source/compiled identities, retains sealed05–12 and old numerical/report/receipt code, packages locally, and reads back every source/module ZIP file. Final results and readback counts are in RESULT.json and DELIVERY-CHECK.json. No Git metadata is present, so no commit is invented. No push, publication, contest submission, global SDK/account/author/STATE change or other-chat message.
