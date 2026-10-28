import hashlib
import json
import math
import subprocess
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2] / 'projects/moonbit-touchstone'
BRIDGE = ROOT / '_build/js/release/build/cmd/bridge/bridge.js'
INPUT = '''[Version] 2.1
# Hz S RI R 50
[Number of Ports] 2
[Two-Port Data Order] 21_12
[Number of Frequencies] 1
[Number of Noise Frequencies] 1
[Network Data]
1000000000 0 0 .5 0 0 0 0 0
[Noise Data]
1000000000 1 0 0 50
[End]
'''
CASES = [
    ('matched', [0.0, 0.0]),
    ('rounded-unit-legal', [1.0 - 2.0**-53, math.nextafter(2.0**-26, 0.0)]),
    ('accepted-near-unit', [0.6, math.nextafter(0.8, 0.0)]),
]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')

def reference(source):
    x, y = map(Fraction, source)
    margin = 1 - x*x - y*y
    with localcontext() as ctx:
        ctx.prec = 160
        def dec(v):
            return Decimal(v.numerator) / Decimal(v.denominator)
        factor = Decimal(10)**(Decimal(1)/10) + 4*dec(1-margin)/dec(margin)
        # Positive real source impedance is an independent passive-domain check.
        resistance = 50 * margin / ((1-x)**2 + y*y)
        return {
            'exact_margin_fraction': str(margin),
            'margin_decimal': str(dec(margin)),
            'source_resistance_ohms': str(dec(resistance)),
            'expected_figure_db': str(10*factor.log10()),
        }

if __name__ == '__main__':
    assert not (OUT / 'BASELINE.json').exists(), 'baseline is immutable'
    pinned = json.loads((OUT/'COMPILED-BEFORE.json').read_text())
    assert sha(BRIDGE) == pinned['sha256']
    (OUT/'source-noise.s2p').write_text(INPUT, encoding='ascii')
    records = []
    for name, source in CASES:
        options = {'source': source, 'figure_db': 3.0}
        save(OUT/(name+'.options.json'), options)
        args = ['node', str(ROOT/'tools/touchstone.mjs'), 'noise', str(OUT/'source-noise.s2p'), '@'+str(OUT/(name+'.options.json'))]
        run = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
        (OUT/(name+'.before.stdout.log')).write_text(run.stdout, encoding='utf-8')
        (OUT/(name+'.before.stderr.log')).write_text(run.stderr, encoding='utf-8')
        record = {'name': name, 'source': source, 'exit': run.returncode, 'stdout': run.stdout, 'stderr': run.stderr, **reference(source)}
        if run.returncode == 0:
            record['actual_figure_db'] = json.loads(run.stdout)['figure_db'][0]
        records.append(record)
    assert records[0]['exit'] == 0 and abs(records[0]['actual_figure_db'] - 1.0) < 1e-12, 'legal physical control must work'
    save(OUT/'BASELINE.json', {'status': 'reproduced', 'bridge_sha256': sha(BRIDGE), 'input_sha256': sha(OUT/'source-noise.s2p'), 'oracle': 'Fraction binary64 inputs, Decimal 160 digits, direct noise-parameter formula; no production magnitude or covariance implementation', 'records': records})
    for row in records:
        print(row['name'], 'exit='+str(row['exit']), 'expected='+row['expected_figure_db'], 'actual='+str(row.get('actual_figure_db')), row['stderr'].strip())
