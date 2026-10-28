# Round 07: format numerical limits

Two causes were established with three failing black-box tests in `before-format.log`: legacy Y normalization materialized an overflowing factor, legacy Z output materialized an overflowing reciprocal, and huge degree values lost their period after premature radian conversion. `after-format.log` preserves their first passing run. The final related pass covers 10 tests per backend and 70 independent bridge requests.

Only `text.mbt` and its legacy parser/writer call sites in `legacy.mbt` change production semantics. H/G normalization uses the same row/column units as before. Each real/imaginary component receives a bounded mantissa and exponent; genuinely unrepresentable final values still raise. MA/DB and noise angles reduce degrees modulo 360 before radian conversion.

Fraction references independently encode the old normalized units and decode the actual emitted legacy layout. They are not generated from the new scaling routine. Exact rational degree remainders precede small-angle trigonometry. Metadata checks include the separate noise option-line reference and information content through canonical writing. Analytic nonuniform phase secants cover the documented group-delay definition without changing it.

Primary standard reviewed: https://www.ibis.org/touchstone_ver2.1/touchstone_ver2_1.pdf (2.1, ratified 2024-01-26). Angles are degrees (p4); legacy voltage/current normalization (p8); noise count must be greater than zero (p10); information follows Number of Ports and precedes network data (p28). The latter two existing rejection rules are correct and were not changed. No standard PDF or vendor originals are redistributed.

05/06 numerical/RF implementation files and public mbti are checked against SOURCE-BEFORE. Previous passing suites and vendor inputs were not rerun. The before JS release hash was captured at the start of round07; this is an observed artifact, unlike round06's explicitly reconstructed baseline.

The source snapshot has no Git metadata; no commit/push/publication/submission is claimed. Round07 is closed before the separately authorized feature research/implementation round08. Historical archives and reports remain intact.
