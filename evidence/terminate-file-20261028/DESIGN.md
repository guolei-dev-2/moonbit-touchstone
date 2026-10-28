# Round16 selected extension: explicit termination to a reusable Touchstone file

## Historical coverage and two bounded needs

First read docs/API.md and docs/RF-0.3.md plus the sealed2026-10-23 reference summary. The old368-request/1103-assertion record covers termination via scikit-rf connect,20 random noisy chains, covariance interpolation/cascade and two-sided independent noise subtraction. Network/Document interpolate, cascade and deembed plus file bridge paths already exist. Explicit grid alignment is intended; cascade requires equal frequencies and connected references. No new fixture-grid probe or automatic alignment feature is justified, and none is run.

Second need: users close unused ports with nonmatched complex loads, then want to use the resulting two-port file in existing GT/band/receipt commands or other Touchstone consumers. Network::terminate_ports plus document(...).write() already supports this in MoonBit. Existing file terminate deliberately emits analysis JSON only. select writes a file but gives omitted ports matched loads and cannot substitute for explicit nonmatched termination.

BASELINE.json records two actual pre-implementation CLI processes on one new4-port/two-frequency synthetic model: old terminate returns the correct2-port JSON at50/75ohm, with no text payload; attempting to consume that JSON as a Touchstone input fails2. This is an actual missing file entry point, not an old mathematical defect. The old JSON remains a supported analysis output.

## Ecosystem/similar work and difference

Bounded searches covered Mooncakes Touchstone/multiport termination and RF connect. No absence or exclusivity is inferred. Previously checked versioned MoonElec0.1.0 https://mooncakes.io/docs/SupremeHuaji/MoonElec@0.1.0 and circuit-solver0.1.1 https://mooncakes.io/docs/hsy-bit/moonbit-circuit-solver@0.1.1 provide adjacent electrical/circuit analysis; they are not imported or copied.

Primary scikit-rf2.1.0 https://scikit-rf.readthedocs.io/en/v2.1.0/tutorials/Circuit.html describes networks with attached loads and external ports; https://scikit-rf.readthedocs.io/en/v2.1.0/api/generated/skrf.network.Network.write_touchstone.html documents writing the resulting network. This is established functionality, not a novel RF algorithm. Frequency interpolation is likewise established https://scikit-rf.readthedocs.io/en/latest/api/generated/skrf.network.Network.interpolate.html .

Difference: one explicit MoonBit file CLI entry using the already implemented termination and document writer, so a loaded multiport -> reduced file -> physical-ohm GT -> saved band receipt chain works without a custom converter or Python runtime. Do not build a circuit solver, fixture extractor, automatic grid policy, generic provenance ledger or new power-wave model.

## Frozen contract before code

Add terminate-file INPUT OPTIONS [OUTPUT]. Required terminations is the same array of [zero-based original port,real,imag] triples as old terminate. impedance defaults false for complex Gamma; true means physicalohm. Exact integer ports and the old finite complex/feedback rules apply, including active loads and finite Gamma poles when the existing homogeneous solver permits. Empty termination array remains a valid S-view identity. At least one port remains; remaining ports keep ascending original order, their references and all original frequency indices. No new port reordering option or RF math.

The new command returns writer Touchstone text through the existing file/stdout host path and exits0; errors2. It accepts only command,ports,terminations,impedance. It does not accept/read fixture paths or unrelated options. Existing output is never overwritten. Node only adds command routing/help; parsing, integer/type validation, termination, single-ended view and text writing stay in MoonBit.

Use Document::network_only() and emit a single-ended S Document with original information lines. Mixed-mode inputs therefore become an explicitly single-ended reduced network, with no stale Mixed-Mode Order. Do not silently carry noise records through a port-count/direction change: the new file command rejects any document with noise data, with an explanatory error. Old terminate/noisy analysis behavior and every old valid input remain unchanged. No multiport noise model is added. Output is a normalized writer document, not a byte-preserving edit.

The file does not automatically attest original input identity, load options or original-port mapping. Keep original/options alongside it. Existing gain-record binds its actual reduced-file bytes and effective gain query only; do not claim a new chain-of-custody or change the v1 protocol. Example explicitly documents surviving original ports0/3 becoming reduced0/1.

## Acceptance and compatibility gate

Add a project-owned synthetic four-port file, option files and a runnable Node orchestration example using fresh output directory: terminate-file -> reduced Touchstone -> gain-record with physical source/load. No new runtime dependency/public library API. Exact old .mbti files and all old RF/format/report/receipt source stay unchanged; only a new bridge case and host command name are added.

Independent Python full-original-network incident-wave equations with all attached loads and the physical source/load provide the GT reference. Solve four unknown incident waves with partial-pivot complex elimination, then compute load/source power; do not use the reduced S matrix or copy Schur complement as the sole oracle. Check the actual exported file's GT at both frequencies for physicalohm and Gamma loads, metadata/port order/info, subsequent sampled receipt and optional demo artifacts. Compare exported parsed network with the pre-implementation old JSON as a compatibility/readback check, not a numerical oracle.

Actual new CLI checks cover stdout/file output, empty termination identity, unmodified old JSON payload on the new input, single-ended normalization of a mixed-mode input, no noise loss, illegal/duplicate/fractional/all/out-of-range ports, malformed triples/unknown keys/fixture path, singular feedback, rejected overwrite and untouched input. Use one clean relevant JS release build, strict all-target compile, formatter and generated API review. Bridge is JS-only; no unchanged Wasm/native runtime suite or old368/1103/GT/CSV/receipt collection rerun. Package only after docs/evidence align, then per-file ZIP readback and RESULT completed/notSupported/remainingRequiredWork. No push/publication/contest, globalSDK/account/author/STATE edit or other-chat message.
