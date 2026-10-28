# Round11: sampled loaded-GT limit report

## Bounded questions and choice

1. Can a file consumer apply finite dB limits to an actual Gamma/ohm-loaded GT trace and locate the worst sample? The existing GT commands return arrays only; gain-check is currently unknown. This is a capability gap, not an old-code defect.
2. Can a report distinguish exact zero, positive underflow/overflow and singular feedback? Existing GT points encode these correctly; a downstream limit decision must preserve that meaning rather than treating every absent number as zero.
3. How should partial/empty bands and matching units be explained? Existing BANDS.md already defines sampled-only, fail-before-inconclusive, range/edge flags and single-point checks. Preserve that policy; do not expand to interpolation or continuous certification.

Select one finite extension: a sampled GT dB-band report consuming existing Gamma or physical-ohm point arrays. Frequency-varying matching, optimizer/Smith plots and CSV exports remain outside this round. No new numerical failure is claimed or manufactured.

## Ecosystem/related review (2026-10-28)

Queries covered Mooncakes gain+band+RF+Touchstone and scikit-rf/Keysight band/limit use. Primary surfaces reviewed:
- https://mooncakes.io/docs/SupremeHuaji/MoonElec : published gain entries describe general/op-amp calculations, no loaded-Touchstone band consumer surfaced in the reviewed interface.
- https://mooncakes.io/docs/hsy-bit/moonbit-circuit-solver@0.1.1 : public MNA/SPICE/AC README has no Touchstone entry; not a source-wide absence claim.
- https://scikit-rf.readthedocs.io/en/latest/api/generated/skrf.network.Network.crop.html : frequency selection without interpolation is established functionality.
- https://helpfiles.keysight.com/csg/89600B/Webhelp/Subsystems/gui/content/mnu_utilities_limittests.htm : trace limit tests and pass/fail information are established workflows. We do not copy its implementation or claim instrument compatibility/certification.

Difference: MoonBit-native report on both existing loaded-GT input paths, with the project's canonical zero/underflow/overflow/singular states, matching units, original-point localization and explicit inconclusive coverage. Not novel RF theory or ecosystem exclusivity. Internal reference policy is existing docs/BANDS.md, not an inferred vendor standard.

## Contract frozen before code

Add check_transducer_gain(points,start_hz,end_hz,minimum_db?,maximum_db?) and report/observation types. At least one finite inclusive bound, minimum<=maximum, finite0<=start<=end. Closed interval selects original points only. Frequencies in supplied trace must be finite, nonnegative, strictly increasing; at most100000 points. Empty input is allowed and yields inconclusive. Validate canonical GT state/optional-field shape; consume the supplied gain_db, without recalculating or enforcing a new gain-vs-dB numerical identity.

Known states: finite uses finite dB; positive overflow/underflow also use their finite dB; exact zero ranks as negative-infinite dB (fails any finite lower bound, satisfies any finite upper bound). Singular is unknown, excluded from extrema and numerical violation counts. Extrema ties retain the first supplied index. CLI uses the full network trace, so that index is the original file sample; API callers who prefilter have indices relative to their supplied trace.

pass: at least one selected sample, dataset endpoints span the requested band, no selected singular points, no violations. Single selected points are permitted, matching existing band semantics; edge_sampled flags expose unsampled endpoints. fail: any known violation, even with singular/coverage gaps. Otherwise inconclusive. Report reasons, exact complete counts, canonical state counts, range/edge flags, lowest/highest with index/frequency/gain/dB/state. No issue-list/CSV budget or continuous-frequency guarantee.

New CLI gain-check INPUT OPTIONS: terminal_mode defaults gamma (optional source/load, matched defaults) or explicit impedance (required source_ohms/load_ohms). Both require start_hz/end_hz and finite minimum_db and/or maximum_db. Reject unknown/mixed unit keys and fixture-file options. Output root status, terminal_mode, reference_ohms, matching values and report. Node maps pass/fail/inconclusive to0/3/4; invalid input remains2. Node remains IO/routing only; core algorithms are unchanged.

Acceptance: analytic matched gain/zero, bound equality, ties, overflow/underflow finite dB, singular unknown/fail precedence, incomplete/no-sample/single-point selection, canonical trace validation and100000-point boundary. New Gamma and ohm file examples plus pure MoonBit JS/Wasm-GC report. Independent Decimal/Fraction GT references and declarative sample masks/counts/extrema; real CLI0/3/4/2 and saved-fail report. One new aggregate NXP-file use may independently compare summary/extrema against98 reference samples without claiming98 individual GT numeric comparisons or distributing original/full data. Old numerical collections are not rerun.

Only add report/API/command/examples and necessary docs. Preserve all05-10 numerical code and old API signatures, existing command behavior, frozen reports/ZIPs. Source/compiled before captured directly, fresh source/module archive readback and RESULT closure. No Git metadata: no fabricated commit. No push/publish/contest/account/globalSDK/globalSTATE/other-chat changes.
