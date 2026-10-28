"""Independent hand-phase file consumer for sampled group-delay acceptance."""
import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--evidence', type=Path, required=True)
args = parser.parse_args()
assert not args.evidence.exists(), 'Use fresh evidence'
args.evidence.parent.mkdir(parents=True, exist_ok=True)
WORK = args.evidence.with_name(args.evidence.stem + '-cases')
WORK.mkdir(exist_ok=False)
commands, checks = [], []


def sha(data):
    return hashlib.sha256(data).hexdigest()


def check(label, condition):
    assert condition, label
    checks.append(label)


def call(label, command, source, query, code, output=None):
    argv = ['node', str(ROOT / 'tools/touchstone.mjs'), command, str(source), json.dumps(query)]
    if output is not None:
        argv.append(str(output))
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=30)
    index = len(commands) + 1
    (WORK / f'{index:02d}.stdout.log').write_bytes(result.stdout)
    (WORK / f'{index:02d}.stderr.log').write_bytes(result.stderr)
    commands.append({'label': label, 'argv': argv, 'exitCode': result.returncode,
                     'expectedExitCode': code, 'stderr': result.stderr.decode('utf-8', errors='replace')})
    check(label + ': exit', result.returncode == code)
    check(label + ': streams', (not result.stdout and bool(result.stderr))
          if code == 2 else not result.stderr)
    if code == 2:
        return None
    if output is not None:
        check(label + ': exclusive file result', not result.stdout and output.exists())
        return json.loads(output.read_bytes())
    return json.loads(result.stdout)


def source(name, frequencies, phases):
    # Phase is specified by exact quarter-turn components, never a product
    # delay result or a generated reference trace.
    lines = ['[Version] 2.1', '# Hz S RI R 50', '[Number of Ports] 2',
             '[Number of Frequencies] ' + str(len(frequencies)), '[Two-Port Data Order] 12_21',
             '[Network Data]']
    lines += [f'{f} 0 0 0 0 {re} {im} 0 0' for f, (re, im) in zip(frequencies, phases)]
    path = WORK / name
    path.write_bytes(('\r\n'.join(lines + ['[End]', ''])).encode('ascii'))
    return path


def report(label, value, frequencies, values, points, status, covered, minimum=None, maximum=None):
    check(label + ': report identity', value['kind'] == 'group_delay_band_report'
          and value['scope'] == 'sampled_points_only' and value['estimator'] == 'endpoint_or_centered_secant'
          and value['input'] == 0 and value['output'] == 1 and value['reference_ohms'] == [50, 50])
    check(label + ': outcome and units', value['status'] == status and value['range_covered'] == covered
          and value['minimum_seconds'] == minimum and value['maximum_seconds'] == maximum
          and value['sample_count'] == len(points))
    below, above = 0, 0
    for sample, point in zip(value['samples'], points):
        wanted = float(values[point])
        low = minimum is not None and wanted < minimum
        high = maximum is not None and wanted > maximum
        below += low
        above += high
        check(label + f': original point {point}', sample['point'] == point
              and sample['frequency_hz'] == frequencies[point]
              and math.isclose(sample['delay_seconds'], wanted, rel_tol=2e-13, abs_tol=1e-20))
        check(label + f': actual aperture {point}',
              sample['aperture_start_hz'] == frequencies[max(0, point - 1)]
              and sample['aperture_end_hz'] == frequencies[min(len(frequencies) - 1, point + 1)])
        check(label + f': strict disposition {point}', sample['below_minimum'] == low
              and sample['above_maximum'] == high and sample['status'] == ('fail' if low or high else 'pass'))
    check(label + ': all rows and counts', len(value['samples']) == len(points)
          and value['below_minimum_count'] == below and value['above_maximum_count'] == above
          and value['failed_count'] == below + above)
    if not points:
        check(label + ': no invented extrema', value['lowest'] is None and value['highest'] is None)
    else:
        # Locate extrema in the actual finite estimates; analytic ties may
        # differ by rounding. Each estimate was independently checked above.
        low_point = min(value['samples'], key=lambda s: s['delay_seconds'])['point']
        high_point = max(value['samples'], key=lambda s: s['delay_seconds'])['point']
        check(label + ': located extrema', value['lowest']['point'] == low_point
              and value['highest']['point'] == high_point)


failure = None
try:
    frequencies = [1000000, 2000000, 4000000]
    expected = [Fraction(1, 4000000), Fraction(1, 6000000), Fraction(1, 8000000)]
    normal = source('nonuniform input.ts', frequencies, [(1, 0), (0, -1), (-1, 0)])
    original = normal.read_bytes()
    band = {'start_hz': frequencies[0], 'end_hz': frequencies[-1], 'input': 0, 'output': 1}
    fail_query = {**band, 'minimum_seconds': 0, 'maximum_seconds': 2e-7}
    saved = WORK / 'saved sampled fail.json'
    failed = call('nonuniform fail saved', 'delay-check', normal, fail_query, 3, saved)
    report('nonuniform fail', failed, frequencies, expected, [0, 1, 2], 'fail', True, 0, 2e-7)
    check('sampled endpoints disclosed', failed['start_sampled'] and failed['end_sampled'])
    passed = call('nonuniform pass', 'delay-check', normal, {**band, 'maximum_seconds': 3e-7}, 0)
    report('nonuniform pass', passed, frequencies, expected, [0, 1, 2], 'pass', True, maximum=3e-7)
    below = call('minimum-only violation', 'delay-check', normal,
                 {**band, 'minimum_seconds': 2e-7}, 3)
    report('minimum-only violation', below, frequencies, expected, [0, 1, 2],
           'fail', True, minimum=2e-7)
    one = call('single original point', 'delay-check', normal,
               {**band, 'start_hz': 2e6, 'end_hz': 2e6, 'minimum_seconds': 0}, 0)
    report('single original point', one, frequencies, expected, [1], 'pass', True, minimum=0)
    empty = call('covered no selected samples', 'delay-check', normal,
                 {**band, 'start_hz': 2.1e6, 'end_hz': 3.9e6, 'minimum_seconds': 0}, 4)
    report('empty', empty, frequencies, expected, [], 'inconclusive', True, minimum=0)
    check('no sampled query edges', not empty['start_sampled'] and not empty['end_sampled'])
    gap = call('uncovered range', 'delay-check', normal,
               {**band, 'start_hz': 0, 'end_hz': 5e6, 'maximum_seconds': 3e-7}, 4)
    report('uncovered', gap, frequencies, expected, [0, 1, 2], 'inconclusive', False, maximum=3e-7)
    gap_fail = call('fail wins over uncovered', 'delay-check', normal,
                    {**band, 'start_hz': 0, 'end_hz': 5e6, 'maximum_seconds': 2e-7}, 3)
    report('uncovered fail', gap_fail, frequencies, expected, [0, 1, 2], 'fail', False, maximum=2e-7)

    uniform_f = [1000000, 2000000, 3000000, 4000000]
    uniform = source('uniform quarter turns.ts', uniform_f, [(1, 0), (0, -1), (-1, 0), (0, 1)])
    uniform_result = call('analytic constant delay', 'delay-check', uniform,
                          {**band, 'maximum_seconds': 3e-7}, 0)
    report('uniform hand delay', uniform_result, uniform_f, [Fraction(1, 4000000)] * 4,
           [0, 1, 2, 3], 'pass', True, maximum=3e-7)
    negative = source('negative delay.ts', [1000000, 2000000], [(1, 0), (0, 1)])
    advance = call('negative delay legal', 'delay-check', negative,
                   {**band, 'end_hz': 2e6, 'minimum_seconds': -3e-7, 'maximum_seconds': 0}, 0)
    report('negative', advance, [1000000, 2000000], [Fraction(-1, 4000000)] * 2,
           [0, 1], 'pass', True, -3e-7, 0)
    zero = source('zero phase slope.ts', frequencies, [(1, 0)] * 3)
    zeros = call('inclusive exact zero limits', 'delay-check', zero,
                 {**band, 'minimum_seconds': 0, 'maximum_seconds': 0}, 0)
    report('exact zero', zeros, frequencies, [Fraction(0)] * 3, [0, 1, 2], 'pass', True, 0, 0)

    old = call('legacy delay control', 'delay', normal, {'input': 0, 'output': 1}, 0)
    check('legacy numerical definition unchanged', old == [x['delay_seconds'] for x in failed['samples']])
    for label, query in [
        ('missing seconds bound', band),
        ('inverted seconds bounds', {**band, 'minimum_seconds': 1, 'maximum_seconds': 0}),
        ('inverted frequency band', {**band, 'end_hz': 0, 'minimum_seconds': 0}),
        ('invalid output port', {**band, 'output': 2, 'minimum_seconds': 0}),
        ('fractional port', {**band, 'input': 0.5, 'minimum_seconds': 0}),
        ('unit typo', {**band, 'maximum_ns': 300}),
        ('fixture key not read', {**band, 'maximum_seconds': 3e-7, 'left_file': str(WORK / 'not-opened.ts')}),
    ]:
        target = WORK / (label + '.json')
        call(label, 'delay-check', normal, query, 2, target)
        check(label + ': no output', not target.exists())
        if label == 'fixture key not read':
            check('unknown fixture rejected before host IO', 'left_file' in commands[-1]['stderr']
                  and 'ENOENT' not in commands[-1]['stderr'])
    one_frequency = source('one frequency.ts', [1000000], [(1, 0)])
    call('single frequency domain error', 'delay-check', one_frequency, {**band, 'maximum_seconds': 1}, 2)
    zero_outside = source('zero outside chosen band.ts', frequencies, [(0, 0), (1, 0), (1, 0)])
    call('zero outside band retains old domain', 'delay-check', zero_outside,
         {**band, 'start_hz': 2e6, 'minimum_seconds': 0}, 2)
    saved_bytes = saved.read_bytes()
    call('occupied output', 'delay-check', normal, fail_query, 2, saved)
    check('occupied output and original input preserved', saved.read_bytes() == saved_bytes
          and normal.read_bytes() == original)

    # Actual pure MoonBit consumers were run on both backends by the caller.
    for target in ['js', 'wasm-gc']:
        example_path = args.evidence.parent / ('delay-example-' + target + '.json')
        example = json.loads(example_path.read_bytes())
        report('MoonBit example ' + target, example, frequencies, expected,
               [0, 1, 2], 'fail', True, 0, 2e-7)
        def metadata(value):
            if isinstance(value, dict):
                return {k: metadata(v) for k, v in value.items() if k != 'delay_seconds'}
            if isinstance(value, list):
                return [metadata(v) for v in value]
            return value
        check('MoonBit/file metadata agrees ' + target, metadata(example) == metadata(failed))
except Exception as exc:
    failure = exc
finally:
    receipt = {'status': 'passed' if failure is None else 'failed',
               'failure': repr(failure) if failure is not None else None,
               'oracle': 'Exact hand quarter-turn phase ratios on uniform/nonuniform original grids; Fraction seconds, aperture/index and status truth. Legacy delay is compatibility control, not numerical oracle.',
               'CLIProcesses': len(commands), 'checks': checks, 'commands': commands,
               'compiledBridgeSha256': sha((ROOT / '_build/js/release/build/cmd/bridge/bridge.js').read_bytes()),
               'sourceSha256': {name: sha((ROOT / name).read_bytes()) for name in
                                ['delay_band.mbt', 'analysis.mbt', 'cmd/bridge/main.mbt',
                                 'tools/touchstone.mjs', 'tools/verify-delay-check.py']},
               'artifacts': [{'path': str(path), 'sha256': sha(path.read_bytes())}
                             for path in sorted(WORK.iterdir()) if path.is_file()]}
    args.evidence.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: receipt[key] for key in ['status', 'failure', 'CLIProcesses']}
                     | {'checkCount': len(checks)}, indent=2))
if failure is not None:
    raise failure
