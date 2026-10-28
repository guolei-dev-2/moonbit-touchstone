# Round16: explicit termination to a reusable Touchstone file

## Outcome and selected boundary

The history pass established that explicit fixture grid alignment already has Network/Document/CLI interpolation, cascade and deembedding paths, with the2026-10-23 RF/noise reference coverage retained. No new fixture probe or automatic alignment policy was added.

One concrete file workflow gap was selected: existing terminate correctly returns analysis JSON, while GT/report/receipt file commands read Touchstone. BASELINE.json records the new four-port model's old JSON output and the expected rejection when treating that JSON as Touchstone. This is not an old termination-math defect. New opt-in terminate-file closes the file handoff without changing the old command.

## Final implementation

- One new private bridge case reuses network_only(), terminate_ports and the Document writer. It emits reduced single-ended S data with surviving ports in ascending original order, original frequencies/references and input information lines. No new RF, parser or writer algorithm/public library API.
- Same complex Gamma/default or physical-ohm input triples and existing finite/feedback domain, including allowed active internal loads. Exact integer/type/duplicate/range/all-ports checks remain meaningful. Empty terminations is an S-view identity. The new case strictly checks its option names and does not read unrelated fixture paths.
- The new file path rejects any noise records rather than assigning a stale two-port noise model after port reduction. This restriction belongs to the new file contract; old terminate JSON behavior/input domain is untouched. Mixed-mode input is normalized through the existing single-ended view, then emitted without stale modal order.
- Node only adds usage/new-command no-fixture routing. Existing stdout/exclusive output writes remain. A project-owned four-port file, load/query options and executable Node orchestration example demonstrate reduction -> GT sampled receipt. The receipt binds the reduced file only, not an invented chain-of-custody for original loads/input.

## Actual verification and transparent development corrections

The accepted consumer record independent-complete.json contains27 actual tool CLI cases and19 checks. Six GT points across physicalohm, Gamma active internal loads and mixed-mode file input match independent full-original-four-port incident-wave equations. The oracle solves all source/internal-load/output-load boundary equations together; it does not consume the reduced S matrix or mirror the production Schur complement as its sole truth. The generated file also reads back to the pre-implementation old terminate JSON, preserving original0/3 -> reduced0/1 references50/75ohm and information.

Coverage includes file/stdout, empty identity, metadata/port order, subsequent gain-record and reproduced-fail gain-review, active internal loads, mixed single-ended export, invalid/malformed/fractional/duplicate/out-of-range/all-port requests, unknown option/fixture path, valid-noise rejection, singular feedback, refused overwrite and unchanged source input. Old terminate JSON on the new input is unchanged.

Two development fixture mistakes are retained, not relabeled as product defects:

1. independent-first.json stopped after13 tool processes because its mixed fixture assumed the existing mixed command propagated the original information lines. The exporter correctly preserved its actual input. The fixture was changed to explicitly include information before testing the new exporter.
2. independent-final.json stopped after25 tool processes because its noisy2.1 two-port fixture omitted mandatory Two-Port Data Order; the parser rejected it before the new noise guard. The final tool corrects that one literal. complete-consumer.py proves this exact single-literal source difference, reuses the24 accepted prefix cases without executing them again and runs only the3 remaining cases. The executed prefix validator is frozen separately. independent-complete.json records that assembly and both failure records stay intact.

Thus27 is the number of accepted complete-consumer cases, not a claim that the corrected standalone script was freshly rerun end-to-end. Accepted case code/production source identities are bound. The baseline has2 additional processes, the runnable demo has2 tool children; all development attempts total45 tool CLI processes (2 baseline+13 first+25 second+3 tail+2 demo), with failures/fixture corrections disclosed. Failed attempts are not added to accepted numerical comparison counts.

The example ran successfully and saved a deliberately failing3–10dB receipt. Its reduced-file identity and receipt match the accepted file case. Initial release JS build, moon info, strict moon check --target all --deny-warn and moon fmt --check pass. The bridge is JS-only; no new Wasm/native runtime coverage is claimed. Existing numerical/format/report/receipt sources, all generated public interface files and old bridge branches are retained. No old RF/GT/CSV/receipt/backend/manufacturer collection is rerun.

## Adjacent finding, report only

The existing mixed CLI builds a new Document from a Network without passing the original information lines. That preparation step therefore omits them. It is outside the selected terminate-file handoff and is not changed here. The new command preserves information actually present in its input; it cannot recover metadata omitted upstream. This finding remains report-only rather than expanding the round into unrelated mixed-mode metadata work.

## Sources and delivery

DESIGN.md records the bounded Mooncakes/multiport searches and previously checked MoonElec/circuit-solver versioned surfaces, plus primary scikit-rf Circuit and write_touchstone documentation. Connected/reduced network export is established functionality. No copied upstream code/dependency, novelty/exclusivity or instrument certification claim.

README, <=30-line PROPOSAL/identical attachment and TERMINATE-FILE.md describe the actual feature, limits and accepted evidence. Final closure records source/compiled identity and byte-identical old APIs/algorithms/evidence, runs local package once and reads every new source/module ZIP file. RESULT and DELIVERY-CHECK give the final counts and remainingRequiredWork. No source Git metadata exists, so no commit is invented. No push, publication, contest submission, globalSDK/account/author/STATE modification or other-chat message.
