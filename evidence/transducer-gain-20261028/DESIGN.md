# Authorized extension: source/load transducer gain

Authorization: after closing proven defects, research a few useful extensions, check the MoonBit ecosystem and adjacent projects, then implement one within the established RF/Touchstone proposal. No publication, account changes, new chat, or changes to other projects. Round07 is sealed separately.

## Candidates and selection

1. Actual delivered transducer power gain for complex source/load reflection coefficients. A designer can compare an amplifier's matched S21 against a proposed source and load, including bilateral feedback. Existing MAG/stability/gain circles describe limits/loci, but do not directly return the gain for a concrete pair. Select this: useful, small additive API, no new runtime dependency, complete analytic and independent wave-equation verification possible.
2. Cross-file frequency-grid comparison. Useful for measurement revisions, but would need an explicit extrapolation/interpolation policy and a larger comparison contract; retain as a future idea.
3. Time-domain reflectometry/gating. Useful for locating discontinuities, but requires a DC completion/window/grid/FFT contract and would exceed this extension. Do not implement it here.

## Ecosystem/related-project check (2026-10-28)

Queries covered Mooncakes touchstone/RF/transducer and GitHub MoonBit Touchstone/S-parameter. No indexed dedicated transducer consumer surfaced, which is a bounded search result rather than proof of absence.

- MoonElec 0.1.0: https://mooncakes.io/docs/SupremeHuaji/MoonElec. Reviewed published README/public symbols: broad electrical calculations, complex numbers, impedance and op-amp helpers. No transducer/S-parameter consumer was found in that surface.
- hsy-bit/moonbit-circuit-solver 0.1.1: https://mooncakes.io/docs/hsy-bit/moonbit-circuit-solver@0.1.1. Reviewed published README: MNA/SPICE/AC/linear algebra pipeline. No Touchstone or S-parameter entry found in that README; this is not a source-wide absence claim.
- scikit-rf: https://github.com/scikit-rf/scikit-rf. It already supplies extensive RF analysis including max_gain/gain_circle; installed 2.1.0 Network symbol inspection confirms those related APIs. MoonTouchstone differentiates through a portable MoonBit Touchstone-to-report API/CLI without Python runtime, not novel gain mathematics or exclusive RF capability.
- Qucs primary technical description: https://qucs.sourceforge.net/tech/node6.html, equations 1.49-1.57. The source/load factors and bilateral input reflection combine to the standard transducer gain used below. Link/reference only; no upstream code copied.

## Contract frozen before implementation

Add `Network::transducer_gain(source?:Complex, load?:Complex)` and a JSON-serializable point type. Default source/load Gamma are zero (matched). Two-port only, converted to S through existing rules. Row-major S[out,in], port0 source/input, port1 load/output; Gamma values reference each port's own fixed positive real Z0. Frequencies and original data are not mutated. A Document consumer takes its network analysis view; noise metadata is not transformed or discarded into another file.

Source must be finite with |Gamma_s|<1 (positive available source power). Load must be finite with |Gamma_l|<=1; a lossless unit-circle load delivers zero power unless the feedback system is singular. Active source/load reflection coefficients are outside this gain definition and raise. No impedance-option overload, matching-network synthesis, optimization, nonlinear compression, or broadband-stability certification.

D=(1-S11*Gamma_s)(1-S22*Gamma_l)-S12*S21*Gamma_s*Gamma_l.
GT=|S21|^2*(1-|Gamma_s|^2)*(1-|Gamma_l|^2)/|D|^2.

Return frequency_hz, gain (linear power ratio), gain_db, state. Finite positive GT: `finite`; exact zero transmission or lossless load: `zero`, gain=0 and no finite dB. Exact D=0 takes priority: `singular`, both absent. A positive result beyond double range: `overflow`, gain absent but dB finite. Positive result rounded to zero: `underflow`, gain=0 but dB finite. Use bounded complex mantissas with explicit binary exponents for denominator products and power scaling, so large/tiny S21 does not disappear through squaring. Ordinary binary64 cancellation still limits near-singular accuracy; finite per-frequency feedback does not certify stable operation.

CLI `transducer-gain INPUT [OPTIONS]` accepts `source:[re,im]`, `load:[re,im]` (defaults matched). Reject unknown options in this new command. Node remains IO-only. Add a pure MoonBit example and synthetic S2P/JSON options for an actual file CLI consumer.

Acceptance: matched GT=|S21|^2; independent bilateral rational example; complex source/load wave solve; unequal port references and other input parameter representations; zero transmission, lossless load, singular feedback; source/load domain rejection; positive overflow/underflow distinguished from true zero; JS/Wasm-GC/native tests and JS/Wasm-GC example; real CLI file consumption; exact Fraction and NumPy wave-equation oracle. Preserve existing exported signatures/05-07 production files except additive bridge branch and CLI command list. Run relevant previous regression files once after the new implementation passes, without rerunning archived vendor suites.
