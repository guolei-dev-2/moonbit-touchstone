# Round12 result and acceptance evidence

Selected one finite file-to-review workflow, not a defect repair: opt-in `gain-record` and `gain-review`. Ordinary `gain-check` outputs contain no raw-input identity, so an old summary alone cannot identify which bytes produced it. The new envelope binds the bytes actually read, the normalized Gamma/physical-ohm request, and the complete unchanged sampled report. Current replay success is separate from pass/fail/inconclusive analysis status.

## Implementation and boundaries

- Only the private JS bridge gains receipt normalization, validation, input identity comparison, and structural JSON replay comparison. All old branches and the public bridge signature are preserved. Existing numerical/report MoonBit sources and all generated public interface files remain byte-identical to sealed11.
- Node uses built-in `crypto.createHash` on the same bounded ASCII input string sent to MoonBit; it handles file/argv/exit IO only. No new package/runtime dependency or RF math in Node. The new demo demonstrates a deliberately failed ohm-limit check reproduced successfully.
- Strict schema/envelope/input metadata, gain-check-only replay and recorded analysis status validation precede identity comparison. If hash or length differs, return `input_mismatch` before parsing the network. If equal, validate/recompute the saved query and compare full parsed JSON with no tolerance. Object key order/whitespace do not matter; arrays/values/extra or missing result sections do.
- SHA256 and byte count cover comments and line endings, not a canonicalized network. Stored port hints allow identical bytes under a renamed legacy extension. Explicit zero bounds and effective defaults survive. No paths, timestamps or user/executable attestations are added.
- Review exit0 means reproduced, exit5 input/result mismatch, exit2 input/protocol/IO/replay error. Record keeps analysis exits0/3/4. Reproduced fail is still fail. Old plain reports cannot be retroactively assigned an authentic original input identity.
- This unsigned local reproducibility record is editable by its holder. It proves neither origin, historic immutability, a signature nor cross-version numerical equivalence. It is not generic notary infrastructure; source comparisons are in DESIGN.md.

## Actual checks, without repeating settled collections

`workflow-first.json` records 41 actual CLI processes and30 protocol/workflow checks using independent Python hashlib and mutation truth cases. It covers Gamma/ohm pass/fail/inconclusive, zero lower/upper bounds, CRLF byte identity, versioned input, renamed identical bytes, malformed different same-length network returning mismatch before parse, changed comments/digest/length, reordered nested JSON/hex-case, changed result status/summary/matching and request bound, malformed schema/identity/arbitrary replay command, ignored-as-path nested fixture rejection, legacy report rejection, invalid new query, and exclusive receipt output. Invalid cases have recorded expected exit2; they are not all counted as independent successful report checks.

`review-output-check.json` adds2 actual CLI processes and2 checks solely for the separate new gain-review OUTPUT path: saved reproduced-fail JSON and refused overwrite with unchanged hash. Thus the workflow total is43 CLI processes/32 checks. `examples/gain_receipt_demo.mjs` ran successfully with2 child processes recorded separately; they are not included again in43.

Two ordinary gain-check controls are compared with sealed11 outputs, not a rerun of the39-request/27-report collection. Optional pinned NXP input uses its fixed SHA256 and sealed11 aggregate expected status/counts only; record+replay verifies identity and reproducibility, with0 new GT numerical comparisons. No model/S-matrix/full GT export is copied to the product evidence.

`CHECKS.json` records the successful initial release JS build, actual demo, independent workflow, `moon fmt --check`, strict `moon check --target all --deny-warn`, and targeted OUTPUT checks. The bridge supports JS; no unchanged Wasm/native runtime suite was rerun or counted as new coverage. Documentation, proposal alignment, old-source/API closure, local module package and source/package per-file ZIP readback are the remaining closure operations; final status and their results belong to RESULT.json and DELIVERY-CHECK.json.

## Delivery boundary

No Git metadata exists in the supplied snapshot; no commit is invented. No push, publish, contest submission, account/SDK/global STATE modification or other-chat message. Sealed05–11 reports and artifacts are retained. README/proposal and GAIN-RECEIPTS.md describe current behavior and distinguish the12-round workflow from the historical numerical evidence. Completion is local artifact/readback completion only.
