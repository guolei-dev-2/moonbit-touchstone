# Round10: physical terminal impedance input for GT

## Bounded investigation and candidate choice

The existing Gamma command correctly rejects Gamma_s=1, and the proposed physical-ohm command is currently unknown. Neither is an existing-code bug. The verified user gap is that a Touchstone consumer often has source/load impedances in ohm; requiring manual Gamma conversion can also lose a positive resistance when the converted double rounds to +/-1.

Candidates: (1) direct finite complex terminal-impedance GT input; (2) frequency-dependent matching arrays, which need grid/interpolation contracts; (3) additional report/CSV formatting. Select only(1): it removes a real input/unit conversion step and preserves physical available-power information. No numerical/format defect is fabricated to justify a round, and no unrelated feature is added.

## Live ecosystem review (2026-10-28)

Searches covered Mooncakes transducer+impedance and Touchstone+RF+impedance, then directly inspected these primary published surfaces:

- MoonElec0.1.0 https://mooncakes.io/docs/SupremeHuaji/MoonElec : public general electrical/complex/impedance calculations. No direct Touchstone-terminal-GT consumer surfaced in the reviewed symbols.
- circuit-solver0.1.1 https://mooncakes.io/docs/hsy-bit/moonbit-circuit-solver@0.1.1 : public README centers on MNA/SPICE/AC/linear algebra. No Touchstone consumer is listed there; this is not a source-wide absence claim.
- scikit-rf2.1.0 https://scikit-rf.readthedocs.io/en/v2.1.0/tutorials/Circuit.html : general network interconnections and physical loads already exist. The difference is a portable MoonBit single-call/CLI physical-terminal gain consumer without Python runtime, not new RF theory or exclusive functionality.
- RF definition https://qucs.sourceforge.net/tech/node6.html : standard bilateral gain/source/load factors. Physical boundary equations follow V=sqrt(R0)(a+b), I=(a-b)/sqrt(R0). No upstream implementation is copied.

## Frozen contract before implementation

Add `Network::transducer_gain_impedance(source:Complex, load:Complex)` returning the existing `TransducerGainPoint` array. Both arguments are physical ohm and required. Two-port only; source finite with real part>0; load finite with real part>=0 (zero/pure-reactive load delivers zero unless feedback singular). Negative-real and nonfinite terminal impedances raise. Both network port references retain the current fixed positive-real model; references need not equal each other or the terminal impedances.

Add separate CLI `transducer-gain-impedance INPUT OPTIONS` with required `source_ohms:[re,im]`, `load_ohms:[re,im]`. Reject Gamma keys, unknown/fixture options and incomplete inputs. Existing Gamma command, signatures,09 exact matching classification and all05-09 core implementations remain byte-identical. New branch/IO routing and additive mbti entry only. No overload that guesses units, no active-terminal gain, infinite impedance, frequency-varying arrays, optimizer, complex-reference-power-wave expansion or metadata transformation.

Use the same finite/zero/singular/overflow/underflow semantics and optional dB fields. Exact feedback singularity precedes zero. A finite result does not establish stability or nonlinear device power performance.

For Rs,Rl network references and Zs,Zl physical terminals, Ns=Zs-Rs, Ds=Zs+Rs and similarly at the load. The homogeneous determinant is
H=DsDl-S11*NsDl-S22*NlDs+det(S)*NsNl.
The power numerator is |S21|^2 *16*Rs*Rl*Re(Zs)*Re(Zl).
Do not form Gamma or differences of squared rounded Ns/Ds. Expand H by the physical terminal components before summation, so real terms survive cancellation of huge reactances or nearly equal Ns/Ds:
A=1-S11-S22+det(S), B=1-S11+S22-det(S), C=1+S11-S22-det(S), E=1+S11+S22+det(S);
H=A*ZsZl+B*ZsRl+C*RsZl+E*RsRl.
Split Z real/imaginary components into nine scaled terms to retain a very small real resistance alongside a huge reactance. Reuse the immutable08 bounded gain arithmetic. Ordinary binary64 coefficient cancellation still limits near-singular accuracy.

## Acceptance

Ordinary matched physical impedances give |S21|^2; unequal references, independent rational bilateral example, moderate complex impedances; huge/tiny identical real terminals on an ideal wire give1; conjugate reactances with a minimum-subnormal positive resistance also give1; positive power below/above double range retains dB. Zero/pure-imaginary load, true physical feedback singularity, invalid source/load/port count and strict CLI errors are checked. Four-wave Fraction equations with Thevenin physical boundary conditions are the primary oracle, not the polynomial or a Gamma roundtrip. New API example runs JS/Wasm-GC, new tests run JS/Wasm-GC/native. Existing Gamma CLI gets a few routing/09 boundary controls, not a rerun of old collections. A pinned existing NXP file may support a new ordinary physical-terminal query on three selected samples without exporting original/full data.

After the relevant checks pass: accurate README/PROPOSAL and unit contract, preserved old API/production identities, final source/compiled hashes, fresh source/module ZIPs with every file read back, RESULT remainingRequiredWork empty. No push, publication, contest submission, account/globalSDK/globalSTATE change or other-chat message. Source snapshot has no Git metadata; do not invent commits.

## Numerical refinement during acceptance

The first physical implementation and53-request oracle passed their initial set. A further direct acceptance counterexample, source=load=R0 and rank-one S with all entries1e100, must give GT=1e200 but failed: pre-rounding A/E coefficients lost their constants. rank-one-physical-before.log retains the failed eighth test. Keep the algebra above, but evaluate its nine physical products times four separate network contributions (36 scaled terms), summing only after the large terms can cancel. Add finite/overflow rank-one points to the physical oracle. The final physical checks are repeated because this failed criterion changed the physical denominator; unchanged Gamma file controls are retained from the first receipt, not rerun after the physical-only correction.

The ordinary36-term sum still left a large rounding residual (rank-one-physical-after.log). Retain real/imaginary TwoSum residuals as separate binary-scaled expansion components, including exponent gaps too wide for a normal alignment, until cancellation is complete. This is local to the new physical denominator; immutable08/09 helpers are reused, not changed. Final magnitude rounding occurs only after the expansion has absorbed all terms.
