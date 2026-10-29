"""Independent handwritten physical-source NF package/file receiver acceptance."""
import argparse
from decimal import Decimal, localcontext
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--evidence', type=Path, required=True)
args = parser.parse_args()
args.evidence = args.evidence.resolve()
assert not args.evidence.exists(), 'Use fresh evidence'
args.evidence.parent.mkdir(parents=True, exist_ok=True)
WORK = args.evidence.with_name(args.evidence.stem + '-cases')
WORK.mkdir(exist_ok=False)
commands, checks, originals = [], [], {}
KEYS = {'source_mode', 'source_ohms', 'noise_reference_ohms', 'network_reference_ohms',
        'frequency_hz', 'figure_db', 'quantity', 'source_units', 'figure_units'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def check(label, condition):
    assert condition, label
    checks.append(label)


def load(data):
    def nonfinite(value):
        raise ValueError('Nonfinite JSON: ' + value)
    result = json.loads(data, parse_constant=nonfinite)
    def walk(value):
        if isinstance(value, float):
            assert math.isfinite(value), 'Nonfinite JSON number'
        elif isinstance(value, dict):
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
    walk(result)
    return result


def raw(name, data):
    path = WORK / name
    path.write_bytes(data)
    originals[path] = sha(data)
    return path


def source(name, frequencies=(1000000, 2000000), references=(75, 100), noise_reference=50,
           noise=((1000000, 0, 0, 0, 25),), zero_forward=False, unit='Hz'):
    scale = 1000000 if unit == 'MHz' else 1
    lines = ['[Version] 2.1', f'# {unit} S RI R {noise_reference}', '[Number of Ports] 2',
             f'[Number of Frequencies] {len(frequencies)}', '[Two-Port Data Order] 12_21',
             '[Reference] ' + ' '.join(map(str, references))]
    if noise:
        lines.append('[Number of Noise Frequencies] ' + str(len(noise)))
    lines.append('[Network Data]')
    for i, frequency in enumerate(frequencies):
        gain = 0 if zero_forward else (0.5 if i == 0 else 0.25)
        lines.append(f'{frequency / scale} 0 0 0 0 {gain} 0 0 0')
    if noise:
        lines.append('[Noise Data]')
        lines += [' '.join([str(row[0] / scale), *map(str, row[1:])]) for row in noise]
    lines.append('[End]')
    return raw(name, ('\r\n'.join(lines) + '\r\n').encode('ascii'))


def call(label, input_path, query, code=0, output=None, command='noise'):
    options = query if isinstance(query, str) else json.dumps(query)
    argv = ['node', str(ROOT / 'tools/touchstone.mjs'), command, str(input_path), options]
    if output is not None:
        argv.append(str(output))
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=30)
    index = len(commands) + 1
    (WORK / f'{index:02d}.stdout.log').write_bytes(result.stdout)
    (WORK / f'{index:02d}.stderr.log').write_bytes(result.stderr)
    commands.append({'label': label, 'argv': argv, 'exitCode': result.returncode,
                     'expectedExitCode': code, 'stderr': result.stderr.decode('utf-8', errors='replace')})
    check(label + ': exit', result.returncode == code)
    if code == 2:
        check(label + ': no partial numerical stdout', not result.stdout and bool(result.stderr))
        return None
    check(label + ': stderr empty', not result.stderr)
    if output is not None:
        check(label + ': saved exclusively', not result.stdout and output.is_file())
        return load(output.read_bytes()) if command == 'noise' else output.read_bytes()
    check(label + ': stdout response', bool(result.stdout))
    return load(result.stdout)


def report(label, value, source_ohms, factors, frequencies=(1000000, 2000000),
           references=(75, 100), noise_reference=50):
    check(label + ': exact physical mode schema', set(value) == KEYS
          and value['source_mode'] == 'impedance' and value['quantity'] == 'source_noise_figure'
          and value['source_units'] == 'ohm' and value['figure_units'] == 'dB')
    check(label + ': explicit source and distinct reference conditions',
          value['source_ohms'] == source_ohms and value['noise_reference_ohms'] == noise_reference
          and value['network_reference_ohms'] == list(references))
    check(label + ': original ordered curve', value['frequency_hz'] == list(frequencies)
          and len(value['figure_db']) == len(factors) == len(frequencies))
    for i, factor in enumerate(factors):
        expected = 10 * math.log10(float(factor))
        actual = value['figure_db'][i]
        check(label + f': independent factor/dB at original {i}',
              isinstance(actual, (int, float)) and not isinstance(actual, bool)
              and math.isfinite(actual) and math.isclose(actual, expected, rel_tol=2e-12, abs_tol=2e-10))


failure = None
try:
    hand = source('arbitrary receiver input.ts')
    query = {'source_mode': 'impedance', 'source_ohms': [150, 0]}
    saved = WORK / 'physical NF.json'
    result = call('handwritten150 saved', hand, query, output=saved)
    report('handwritten150', result, [150, 0], [F(5, 3)] * 2)
    for label, ohms, factor in [('matched noise reference', [50, 0], F(1)),
                                ('complex physical source', [50, 50], F(3, 2))]:
        value = call(label, hand, {**query, 'source_ohms': ohms})
        report(label, value, ohms, [factor] * 2)

    # Actual public-package outputs, executed by the caller on both backends.
    for target in ['js', 'wasm-gc']:
        path = args.evidence.parent / f'noise-impedance-{target}.json'
        api = load(path.read_bytes())
        check('package cases ' + target, len(api['cases']) == 3)
        receiver_file = raw('public package exact input ' + target + '.ts', api['input_text'].encode('ascii'))
        for i, (ohms, factor) in enumerate([([50, 0], F(1)), ([150, 0], F(5, 3)), ([50, 50], F(3, 2))]):
            report('package ' + target + str(i), api['cases'][i], ohms, [factor] * 2)
            value = call('package to arbitrary file ' + target + str(i), receiver_file,
                         {**query, 'source_ohms': ohms})
            report('package file ' + target + str(i), value, ohms, [factor] * 2)
            check('package/file conditions agree ' + target + str(i),
                  {k: v for k, v in value.items() if k != 'figure_db'} ==
                  {k: v for k, v in api['cases'][i].items() if k != 'figure_db'})

    changed_path = WORK / 'actual compatible S renormalization.ts'
    call('actual S reference change', hand, {'reference_ohms': [50, 50]},
         output=changed_path, command='renormalize')
    originals[changed_path] = sha(changed_path.read_bytes())
    changed = call('NF after S reference change', changed_path, query)
    report('NF after S reference change', changed, [150, 0], [F(5, 3)] * 2, references=[50, 50])
    check('physical NF invariant to compatible S reference change', changed['figure_db'] == result['figure_db'])
    different_noise = source('noise reference100.ts', noise_reference=100)
    value = call('separate noise reference100', different_noise, {**query, 'source_ohms': [50, 0]})
    report('separate noise reference100', value, [50, 0], [F(9, 8)] * 2, noise_reference=100)
    mhz = source('same Hz from MHz.ts', unit='MHz')
    value = call('parsed Hz conditions', mhz, query)
    report('parsed Hz', value, [150, 0], [F(5, 3)] * 2)

    sparse = source('sparse covariance.ts', frequencies=[1000000, 2000000, 3000000],
                    noise=[(1000000, 0, 0, 0, 25), (3000000, 0, 0, 0, 50)])
    value = call('original sparse covariance curve', sparse, query)
    report('sparse covariance', value, [150, 0], [F(5, 3), F(2), F(7, 3)],
           frequencies=[1000000, 2000000, 3000000])
    interpolated_path = WORK / 'actual resampled covariance.ts'
    call('actual Document interpolation', sparse, {'frequency_hz': [1500000, 2500000]},
         output=interpolated_path, command='interpolate')
    originals[interpolated_path] = sha(interpolated_path.read_bytes())
    value = call('NF after Document interpolation', interpolated_path, query)
    report('resampled covariance', value, [150, 0], [F(11, 6), F(13, 6)], frequencies=[1500000, 2500000])
    optimum = source('complex optimum.ts', noise=[(1000000, 0, 0.5, 90, 25)])
    for ohms, factor in [([30, 40], F(1)), ([30, -40], F(47, 15))]:
        value = call('complex optimum ' + str(ohms), optimum, {**query, 'source_ohms': ohms})
        report('complex optimum ' + str(ohms), value, ohms, [factor] * 2)
    zero_forward = source('zero deterministic forward.ts', zero_forward=True)
    value = call('NF does not request unrelated S covariance', zero_forward, query)
    report('zero deterministic forward', value, [150, 0], [F(5, 3)] * 2)

    # Independent physical resistance formula, NOT rounded-Gamma output.
    for resistance in [1e308, 1e-300]:
        with localcontext() as ctx:
            ctx.prec = 110
            r = Decimal(str(resistance))
            factor = r / 100 + 25 / r
        value = call('scaled positive real source ' + str(resistance), hand,
                     {**query, 'source_ohms': [resistance, 0]})
        report('scaled positive real source ' + str(resistance), value, [resistance, 0], [factor] * 2)
    ideal = source('explicit zero covariance.ts', noise=[(1000000, 0, 0, 0, 0)])
    extreme = [5e-324, 1e308]
    value = call('ideal covariance extreme positive source', ideal, {**query, 'source_ohms': extreme})
    report('ideal covariance', value, extreme, [F(1)] * 2)

    golden = load((ROOT / 'tools/fixtures/noise-source-impedance/gamma-before.json').read_bytes())
    gamma_file = raw('exact pre-edit Gamma input.ts', golden['input_text'].encode('ascii'))
    for i, case in enumerate(golden['cases']):
        value = call('original Gamma full golden ' + str(i), gamma_file, case['query'])
        check('full original Gamma output preserved ' + str(i), value == case['result'])
    value = call('explicit Gamma mode same schema', gamma_file, {**golden['cases'][0]['query'], 'source_mode': 'gamma'})
    check('explicit Gamma full output unchanged', value == golden['cases'][0]['result'])
    call('old Gamma unit circle still rejected', hand, {'source': [1, 0]}, 2)

    no_noise = source('missing noise.ts', noise=())
    outside = source('last noise point outside range.ts', frequencies=[1000000, 1500000, 3000000],
                     noise=[(1000000, 0, 0, 0, 25), (2000000, 0, 0, 0, 50)])
    nonphysical = source('non PSD model.ts', noise=[(1000000, 20, 0, 0, 25)])
    bad = raw('malformed.ts', b'not a Touchstone file\n')
    nonascii = raw('non ASCII.ts', b'# Hz S RI R 50\n\x80\n')
    errors = [
        ('zero real source', hand, {**query, 'source_ohms': [0, 0]}),
        ('pure reactive source', hand, {**query, 'source_ohms': [0, 50]}),
        ('negative resistance', hand, {**query, 'source_ohms': [-1, 0]}),
        ('missing source', hand, {'source_mode': 'impedance'}),
        ('short source array', hand, {**query, 'source_ohms': [50]}),
        ('long source array', hand, {**query, 'source_ohms': [50, 0, 0]}),
        ('string source', hand, {**query, 'source_ohms': '50'}),
        ('null source', hand, {**query, 'source_ohms': None}),
        ('nonfinite source', hand, json.dumps(query).replace('150', '1e400')),
        ('NaN source JSON', hand, json.dumps(query).replace('150', 'NaN')),
        ('unknown source mode', hand, {**query, 'source_mode': 'impednace'}),
        ('wrong mode type', hand, {**query, 'source_mode': False}),
        ('mixed units rejected', hand, {**query, 'source': [0, 0]}),
        ('circle request not NF input', hand, {**query, 'figure_db': 3}),
        ('unknown fixture not opened', hand, {**query, 'left_file': str(WORK / 'must not open.ts')}),
        ('fractional port hint', hand, {**query, 'ports': 1.5}),
        ('missing mode does not infer Ohm', hand, {'source_ohms': [50, 0]}),
        ('missing noise model', no_noise, query),
        ('noise extrapolation no partial curve', outside, query),
        ('nonphysical covariance', nonphysical, query),
        ('unrepresentable tiny resistance factor', hand, {**query, 'source_ohms': [5e-324, 0]}),
        ('unrepresentable reactive factor', hand, {**query, 'source_ohms': [1, 1e308]}),
        ('malformed file', bad, query), ('non ASCII file', nonascii, query),
        ('missing file', WORK / 'missing.ts', query), ('directory input', WORK, query),
        ('malformed options', hand, '{'), ('array options', hand, '[]'),
    ]
    for label, input_path, options in errors:
        target = WORK / (label + ' forbidden.json')
        call(label, input_path, options, 2, target)
        check(label + ': no partial saved report', not target.exists())
        if label == 'unknown fixture not opened':
            check('unknown fixture key reaches validation', 'left_file' in commands[-1]['stderr']
                  and 'ENOENT' not in commands[-1]['stderr'])
        if label.startswith('unrepresentable'):
            check(label + ': numerical error explicit', 'noise factor is not finite positive' in commands[-1]['stderr'])
    occupied = saved.read_bytes()
    call('existing output preserved', hand, query, 2, saved)
    check('existing report bytes preserved', saved.read_bytes() == occupied)
    before = hand.read_bytes()
    call('input output alias', hand, query, 2, hand)
    check('input alias original preserved', hand.read_bytes() == before)
    parent = WORK / 'missing parent' / 'out.json'
    call('missing output parent', hand, query, 2, parent)
    check('parent not created', not parent.parent.exists())
    for path, wanted in originals.items():
        check('original input preserved ' + path.name, sha(path.read_bytes()) == wanted)
except Exception as exc:
    failure = exc
finally:
    receipt = {'status': 'passed' if failure is None else 'failed', 'failure': repr(failure) if failure else None,
        'oracle': 'Pre-edit handwritten rational NF factors1/5over3/3over2, interpolated covariance factors, signed complex-optimum witnesses, and independent Decimal R/100+25/R. Gamma goldens are compatibility only.',
        'CLIProcesses': len(commands), 'checks': checks, 'commands': commands,
        'newPackageBackendsConsumed': ['js', 'wasm-gc'], 'wholeDoubleAccuracyClaimed': False,
        'compiledBridgeSHA256': sha((ROOT / '_build/js/release/build/cmd/bridge/bridge.js').read_bytes()),
        'sourceSHA256': {name: sha((ROOT / name).read_bytes()) for name in
                        ['noise_impedance.mbt', 'noise.mbt', 'gain.mbt', 'gain_impedance.mbt',
                         'cmd/bridge/main.mbt', 'tools/touchstone.mjs', 'pkg.generated.mbti',
                         'examples/noise_source_impedance/main.mbt', 'tools/verify-noise-source-impedance.py',
                         'tools/fixtures/noise-source-impedance/gamma-before.json']},
        'originalInputSHA256': {str(path): value for path, value in originals.items()},
        'artifacts': [{'path': str(path), 'sha256': sha(path.read_bytes()), 'bytes': path.stat().st_size}
                      for path in sorted(WORK.iterdir()) if path.is_file()]}
    args.evidence.write_text(json.dumps(receipt, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({'status': receipt['status'], 'failure': receipt['failure'],
                      'CLIProcesses': len(commands), 'checkCount': len(checks)}, indent=2))
if failure is not None:
    raise failure
