# Round17: repair mixed file Information preservation within the current contract

## Scope decision and legal counterexample

This round revisits the explicitly authorized adjacent16 finding before choosing any new feature. README says file metadata is not silently discarded; docs/SCOPE.md's file model requires information and noise/modal metadata preservation. RF-0.3 explicitly rejects noisy mixed conversion but provides no Information-discard exception. Preserving legal parsed Information through the mixed file path is therefore inside the current promise.

BASELINE.json records four actual Node processes before implementation on a new legal3-port/two-frequency2.1 file with three ASCII information lines. inspect reads all3; mixed produces the expected D1,2/C1,2/S3 network, but inspect of that file reads0. A no-information control response is frozen too. This is a reproduced metadata-loss defect, not a new format or RF task.

IBIS2.1 page28 https://www.ibis.org/touchstone_ver2.1/touchstone_ver2_1.pdf describes the optional Information block and permits consumers to ignore it. The fix is required by this project's stronger preservation contract, not falsely claimed as a standard-mandated preservation rule. Existing MoonBit Document information_lines(), document(...information=...), and writer already support it; there is no missing parser/API/dependency or ecosystem algorithm to build. The related electrical/circuit libraries reviewed in prior rounds are not replaced or imported for a metadata handoff.

## Cause and minimal repair before code

The CLI parses a Document, then calls doc.network_only().to_mixed_mode(...). Network::to_mixed_mode correctly returns a fresh mixed Document from network data, since Network has no file Information. The bridge currently writes that fresh Document without attaching the original Document's information_lines(). Repair only its text expression: construct the output Document from mixed.raw_network(), its existing noise reference and mixed order, plus doc.information_lines(), then call the same writer. Leave returned network/order fields and all mixed-mode math untouched. No new output fields or public API.

The old noisy-input guard stays unchanged and no legal input domain is narrowed. Existing no-information output must remain byte-identical. Existing mixed inputs with information must preserve it once, not duplicate it. This is normalized document preservation, not byte/layout/comment preservation or interpretation of new information keywords.

One current verification fixture from16 unconditionally adds an Information block because the old mixed CLI omitted one. Make that setup conditional on absence so it accepts both old producer output and the corrected output. This is an in-scope compatibility consequence, not a16-suite rerun or edit of its frozen reports/scripts/evidence. No16 terminate-file or RF source change.

## Acceptance and stopping point

Use the frozen before responses and an independent Python text-section extractor, not only the library parser, to verify the exact three expected lines. Actual fixed bridge responses retain network/order exactly; removing only the Information block yields the old text. No-information full response remains identical. Actual CLI file output and inspect preserve the same lines, frequencies, references and mode order. Test an already-mixed input with an explicit Information block for single-copy preservation, then one new mixed->terminate-file metadata handoff on this new3-port input. Preserve the existing noisy mixed rejection on a valid2-port noisy fixture.

Add one project-owned counterexample file/options as a runnable existing-CLI example and a focused independent regression tool. No generic metadata framework, new format, new RF math, new model data or another operation gap is pursued. The new bridge is JS-only; one release build, strict all-target check, formatter and regenerated API identity are relevant. Do not rerun16's27/6, old numerical/mixed-mode/receipt suites or unchanged Wasm/native runtime tests. After one clean relevant regression pass, align README/<=30-line proposal/attachment, bind source/compiled identities, package once, per-file readback both ZIPs and close RESULT. No push/publication/contest/globalSDK/account/author/STATE edit or other-chat message.
