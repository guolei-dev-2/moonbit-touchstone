# Round12: opt-in gain receipt and replay review

## Three bounded gaps and choice

1. A saved gain-check summary has matching/limits but no identity binding to the exact input bytes. A comment/line-ending change or wrong file cannot be distinguished from the saved summary alone.
2. There is no one-command replay comparison of that saved decision against the current local implementation.
3. Review success must remain distinct from the device/limit status: a correctly reproduced fail is still an analysis fail.

No old-code defect is asserted. Select one finite workflow extension: opt-in gain-record plus gain-review. Preserve old gain-check/GT output and all math. Generic evidence ledgers, signatures, timelines, binary attestation, CSV and broader analysis are out of scope.

## Ecosystem/source review (2026-10-28)

Queries covered Mooncakes provenance/SHA256/report and related tools. Primary published surfaces:
- hcjbat/moonbit-notary0.1.0 https://mooncakes.io/docs/hcjbat/moonbit-notary : reusable evidence manifests, fingerprints, audit/report workflows. We do not recreate that generic library or claim its security properties.
- WeiR-h/moonldif0.7.0 https://mooncakes.io/docs/WeiR-h/moonldif@0.7.0 : LDIF byte-preserving/review reports and input identity, a different domain. Similar provenance patterns already exist.
- gmlewis/sha2560.18.0 is listed by Mooncakes search as a hash implementation; its versioned page fetch was unavailable. It is not imported, copied or used as an absence/quality claim.
- Node24 crypto official API https://nodejs.org/docs/latest-v24.x/api/crypto.html : standard SHA256 host IO. Runtime observed v24.11.0. No new MoonBit/runtime dependency or own hash implementation.
- Fixed local MoonBit Json Eq compares numbers by value, arrays positionally and objects via Map equality; replay tests will check reformatted/reordered JSON, not textual equality.

Difference: a thin Touchstone loaded-GT workflow that binds actual read bytes, captures effective units/defaults/limits/port hints, then reruns existing MoonBit gain-check and compares the whole parsed result. Not novel cryptography, an authenticity/notary service or ecosystem exclusivity.

## Frozen protocol before implementation

New gain-record INPUT OPTIONS [OUTPUT] has the same valid query options and0/3/4 analysis exits as gain-check. It outputs an envelope with exactly schema,input,request,result. Schema is touchstone.gain-receipt.v1; input has sha256 and bytes. Node hashes the SAME ASCII string read once and passed to MoonBit, including comments/CRLF; no input path, timestamp, user identity or claimed executable attestation. MoonBit runs the unchanged gain-check, expands default matching/mode and bounds into request, preserves an effective ports hint when present, and retains the unchanged result. Zero-valued bounds must be retained.

New gain-review INPUT @RECEIPT [OUTPUT] reads the current input once and supplies its hash/byte count plus saved JSON to MoonBit. Validate envelope/schema/basic types, restrict replay request.command to gain-check, and validate a canonical recorded pass/fail/inconclusive status. Upper/lower hex cases identify the same SHA256 value. Plain old gain-check output lacks identity and gets an actionable error; it is never silently upgraded.

If input hash OR byte count differs, return input_mismatch without parsing/recomputing the network. Otherwise replay the saved normalized request with the current bridge, and compare the complete parsed JSON result structurally. Object order/whitespace/numeric spelling do not matter; arrays/values/extra or missing result sections do. Return reproduced or result_mismatch, recorded_status/current_status, input/result match flags, recorded/actual input identities, changed top-level result sections and current_result (null when not run). Schema/IO/invalid replay request errors remain exit2. Review exits0 for reproduced,5 for input/result mismatch. A reproduced fail/inconclusive remains fail/inconclusive, never device acceptance.

Identity check follows basic protocol validation and precedes analysis. Existing ASCII64MB input and1MB options/receipt budgets apply. Hash+replay proves current reproducibility, not signer/authenticity/time/history or cross-version numerical equivalence. Changed source bytes require a new receipt even if matrices are numerically equivalent. Renamed identical bytes may replay because the recorded port hint is used.

All report/replay normalization and JSON comparison stay in MoonBit; Node only handles file/argv/fingerprint IO and exit mapping. Public library API and old numerical/report algorithms stay unchanged. No auto-read of paths nested in receipts, fixture IO, arbitrary replay command or external action. User annotations belong outside the strict envelope.

## Acceptance and bounded verification

Actual file record/review for pass/fail/inconclusive, zero-valued lower/upper bounds, CRLF raw bytes, renamed identical bytes and versioned input. Python hashlib and protocol assertions independently check identity/defaults/requests; compare old plain payloads with frozen11 references rather than rerunning39/27. Review formatting/key order/hex-case portability; source hash/size mismatch (including invalid-ASCII-content-as-Touchstone but ASCII bytes) must stop before analysis; altered status/summary/matching/request bounds must be distinguished from source mismatch. Malformed schema/metadata/legacy report/arbitrary command and exclusive output safety are checked. Demo runs record fail then reproduced review; optional pinned NXP record/replay tests only receipt identity/reproducibility, not a new GT numerical collection. Old tests/collections are not rerun.

Bridge is JS-only; actual CLI workflow tests plus strict all-target compilation are relevant. No unchanged Wasm/native suite rerun or claimed new backend coverage. Once passed, accurate README/PROPOSAL, source/compiled identity, fresh source/module ZIP per-file readback and RESULT closure. Preserve frozen05-11. No Git metadata: no invented commit. No push/publish/contest/account/globalSDK/globalSTATE or other-chat messaging.
