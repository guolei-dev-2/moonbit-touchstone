"""Fresh five-port export transaction, independently solved with Fractions.

The oracle solves all original incident-wave equations; it never derives GT
from a product-reduced network. The small wire decoder checks only the current
writer's two-port Touchstone 2.1/RI output, not a new general file format.
"""
import argparse
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REFS = [50, 60, 75, 90, 100]
KEEP = [1, 3]
FREQ = [1000000000, 2000000000]
INFO = ['Fresh coupled five-port transaction; synthetic data.',
        'Original survivors 1 and 3 become output ports 0 and 1.']
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--evidence', type=Path, required=True)
args = parser.parse_args()
assert not args.evidence.exists(), 'Choose fresh evidence'
args.evidence.parent.mkdir(parents=True, exist_ok=True)
WORK = args.evidence.with_name(args.evidence.stem + '-cases')
WORK.mkdir(exist_ok=False)
commands, checks, references = [], [], {}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def check(label, condition):
    assert condition, label
    checks.append(label)


def close(actual, expected):
    return math.isfinite(actual) and math.isclose(actual, float(expected), rel_tol=2e-12, abs_tol=2e-12)


def call(label, command, source, options, code, output=None):
    argv = ['node', str(ROOT / 'tools/touchstone.mjs'), command, str(source), json.dumps(options)]
    if output is not None:
        argv.append(str(output))
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=30)
    number = len(commands) + 1
    (WORK / f'{number:02d}.stdout.log').write_bytes(result.stdout)
    (WORK / f'{number:02d}.stderr.log').write_bytes(result.stderr)
    commands.append({'label': label, 'argv': argv, 'exitCode': result.returncode,
                     'expectedExitCode': code, 'stderr': result.stderr.decode('utf-8', errors='replace')})
    check(label + ': exit', result.returncode == code)
    check(label + ': streams', (not result.stdout and bool(result.stderr))
          if code == 2 else not result.stderr)
    if output is not None and code != 2:
        check(label + ': actual file only', not result.stdout and output.is_file())
        return output.read_bytes()
    return result.stdout


def solve_all(a, rhs):
    rows = [list(row) + [value] for row, value in zip(a, rhs)]
    for col in range(5):
        pivot = next((i for i in range(col, 5) if rows[i][col]), None)
        if pivot is None:
            raise ValueError('singular original five-port wave system')
        rows[col], rows[pivot] = rows[pivot], rows[col]
        divisor = rows[col][col]
        rows[col] = [v / divisor for v in rows[col]]
        for i in range(5):
            if i != col:
                multiplier = rows[i][col]
                rows[i] = [x - multiplier * y for x, y in zip(rows[i], rows[col])]
    return [row[-1] for row in rows]


def outgoing(s, gamma, forcing):
    # a_i = forcing_i + Gamma_i*b_i, b_i = sum(S_ij*a_j), at ALL five ports.
    incident = solve_all([[F(i == j) - gamma[i] * s[i][j] for j in range(5)]
                          for i in range(5)], forcing)
    return [sum(s[i][j] * incident[j] for j in range(5)) for i in range(5)]


def expected(s, g4):
    gamma = [F(1, 2), F(0), F(-1, 2), F(0), g4]
    columns = [outgoing(s, gamma, [F(i == driven) for i in range(5)]) for driven in KEEP]
    reduced = [columns[j][i] for i in KEEP for j in range(2)]
    # Source/load are physical 100/54 ohms at original retained ports 1/3.
    gamma[1] = (F(100) - REFS[1]) / (100 + REFS[1])
    gamma[3] = (F(54) - REFS[3]) / (54 + REFS[3])
    wave = outgoing(s, gamma, [F(i == 1) for i in range(5)])
    gain = (1 - gamma[1] ** 2) * (1 - gamma[3] ** 2) * wave[3] ** 2
    return reduced, gain


def decode_writer_bytes(raw):
    headers, values, information = {}, [], []
    current, in_info = None, False
    refs = []
    for original in raw.decode('ascii').splitlines():
        text = original.strip()
        if in_info:
            if text.lower() == '[end information]':
                in_info = False
            else:
                information.append(original)
            continue
        text = text.split('!', 1)[0].strip()
        if not text:
            continue
        if text.startswith('#'):
            option = text.upper().split()
            assert option[1:4] == ['HZ', 'S', 'RI']
            continue
        tag = re.match(r'^\[([^]]+)\]\s*(.*)$', text)
        if tag:
            current, tail = tag.group(1).lower(), tag.group(2)
            if current == 'begin information':
                in_info = True
            elif current == 'reference':
                refs.extend(tail.split())
            else:
                headers[current] = tail
            continue
        if current == 'network data':
            values.extend(float(v) for v in text.split())
        elif current == 'reference':
            refs.extend(text.split())
        else:
            raise AssertionError('Unexpected continuation in writer output')
    assert headers['version'] == '2.1' and int(headers['number of ports']) == 2
    assert int(headers['number of frequencies']) == 2 and len(values) == 18
    order = headers['two-port data order']
    assert order in ('12_21', '21_12')
    matrices, frequencies = [], []
    for offset in [0, 9]:
        frequencies.append(values[offset])
        matrix = [complex(values[offset + 1 + 2 * i], values[offset + 2 + 2 * i]) for i in range(4)]
        matrices.append(matrix if order == '12_21' else [matrix[i] for i in [0, 2, 1, 3]])
    return {'refs': list(map(float, refs)), 'frequency': frequencies,
            'matrices': matrices, 'information': information, 'wireOrder': order}


def exported_case(name, source, options, g4, stdout=False):
    file = WORK / (name + '.ts')
    raw = call(name + ' export', 'terminate-file', source, options, 0, None if stdout else file)
    if stdout:
        file.write_bytes(raw)
    wire = decode_writer_bytes(raw)
    check(name + ': independent wire metadata', wire['refs'] == [60, 90]
          and wire['frequency'] == FREQ and wire['information'] == INFO)
    reference = [expected(s, g4) for s in matrices]
    for i, (wanted, _) in enumerate(reference):
        check(name + f': all four wire S at sample {i}', all(close(z.real, q) and close(z.imag, 0)
              for z, q in zip(wire['matrices'][i], wanted)))
    dump = json.loads(call(name + ' matrix readback', 'dump', file, {}, 0))
    check(name + ': survivor order 1/3 to 0/1', dump['ports'] == 2
          and dump['reference_ohms'] == [60, 90] and dump['frequency_hz'] == FREQ)
    for i, (wanted, _) in enumerate(reference):
        check(name + f': current parser S at sample {i}', all(close(z['re'], q) and close(z['im'], 0)
              for z, q in zip(dump['values'][i], wanted)))
    info = json.loads(call(name + ' metadata readback', 'inspect', file, {}, 0))
    check(name + ': information and single-ended identity', info['information'] == INFO
          and info['noise'] == [] and info['mixed_mode_order'] == [])
    gains = json.loads(call(name + ' existing physical gain consumer', 'transducer-gain-impedance',
                           file, {'source_ohms': [100, 0], 'load_ohms': [54, 0]}, 0))
    check(name + ': complete gain samples', len(gains) == 2)
    for i, (_, gain) in enumerate(reference):
        check(name + f': full original-wave GT at sample {i}', gains[i]['state'] == 'finite'
              and gains[i]['frequency_hz'] == FREQ[i] and close(gains[i]['gain'], gain)
              and close(gains[i]['gain_db'], 10 * math.log10(float(gain))))
    references[name] = [{'sRowMajor': [str(q) for q in matrix], 'gain': str(gain),
                         'gain_db': 10 * math.log10(float(gain))} for matrix, gain in reference]
    return file, raw


failure = None
try:
    s = [[F(1, 4), F(1, 8), F(1, 8), F(0), F(1, 16)],
         [F(1, 8), F(1, 8), F(1, 4), F(1, 16), F(0)],
         [F(1, 8), F(1, 4), F(0), F(1, 8), F(1, 8)],
         [F(0), F(1, 2), F(1, 8), F(1, 4), F(1, 4)],
         [F(1, 16), F(0), F(1, 8), F(1, 4), F(1, 8)]]
    matrices = []
    for direct in [F(1, 2), F(1, 4)]:
        point = [row[:] for row in s]
        point[3][1] = direct
        matrices.append(point)
    check('frozen rational cross-check', expected(matrices[0], F(1, 2))[0][2] == F(13065, 27088)
          and expected(matrices[1], F(1, 2))[1] == F(9124266009600, 208890741020809))
    lines = ['[Version] 2.1', '# Hz S RI R 50', '[Number of Ports] 5', '[Number of Frequencies] 2',
             '[Reference] ' + ' '.join(map(str, REFS)), '[Begin Information]', *INFO,
             '[End Information]', '[Network Data]']
    lines += [' '.join([str(f)] + [str(x) for row in point for v in row for x in [float(v), 0]])
              for f, point in zip(FREQ, matrices)]
    source = WORK / 'coupled five port.ts'
    original = ('\r\n'.join(lines + ['[End]', ''])).encode('ascii')
    source.write_bytes(original)
    physical = {'terminations': [[4, 300, 0], [0, 150, 0], [2, 25, 0]], 'impedance': True}
    reduced, reduced_bytes = exported_case('physical unordered loads', source, physical, F(1, 2))
    exported_case('equivalent Gamma reordered stdout', source,
                  {'terminations': [[2, -0.5, 0], [4, 0.5, 0], [0, 0.5, 0]]}, F(1, 2), stdout=True)
    exported_case('legal active Gamma', source,
                  {'terminations': [[4, 1.25, 0], [2, -0.5, 0], [0, 0.5, 0]]}, F(5, 4))

    query = {'terminal_mode': 'impedance', 'source_ohms': [100, 0], 'load_ohms': [54, 0],
             'start_hz': FREQ[0], 'end_hz': FREQ[1], 'minimum_db': -10, 'maximum_db': 0}
    receipt_file = WORK / 'exported gain receipt.json'
    receipt = json.loads(call('exported bytes to gain record', 'gain-record', reduced, query, 3, receipt_file))
    check('receipt binds exported bytes rather than original five-port',
          receipt['input'] == {'sha256': sha(reduced_bytes), 'bytes': len(reduced_bytes)}
          and receipt['input']['sha256'] != sha(original))
    check('independent two-point band result', receipt['result']['reference_ohms'] == [60, 90]
          and receipt['result']['status'] == 'fail'
          and receipt['result']['report']['below_minimum_count'] == 1
          and receipt['result']['report']['sample_count'] == 2
          and receipt['result']['report']['lowest']['point'] == 1)
    replay = json.loads(call('exported receipt is reproducible', 'gain-review', reduced, receipt, 0))
    check('failed analysis stays fail after successful replay', replay['status'] == 'reproduced'
          and replay['current_status'] == replay['recorded_status'] == 'fail'
          and replay['current_result'] == receipt['result'])

    noise_raw = (b'[Version] 2.1\n# Hz S RI R 50\n[Number of Ports] 2\n[Number of Frequencies] 1\n'
                 b'[Two-Port Data Order] 12_21\n[Number of Noise Frequencies] 1\n[Network Data]\n'
                 b'1000000000 .125 0 0 0 .5 0 .125 0\n[Noise Data]\n1000000000 1 0 0 100\n[End]\n')
    noisy = WORK / 'accepted noisy input.ts'
    noisy.write_bytes(noise_raw)
    inspect = json.loads(call('noisy input is valid syntax', 'inspect', noisy, {}, 0))
    check('noise refusal has a parsed legal input', len(inspect['noise']) == 1 and inspect['ports'] == 2)
    old = json.loads(call('legacy network-only termination remains legal', 'terminate', noisy,
                          {'terminations': [[1, 0, 0]]}, 0))
    check('legacy noise behavior not narrowed', old['ports'] == 1)
    forbidden = WORK / 'must not lose noise.ts'
    call('file export refuses unsupported noise', 'terminate-file', noisy, {'terminations': [[1, 0, 0]]}, 2, forbidden)
    check('noise refusal before output creation', 'noise' in commands[-1]['stderr'].lower() and not forbidden.exists())
    occupied = WORK / 'occupied sentinel.ts'
    sentinel = b'Existing bytes must survive even unsupported input.\r\n'
    occupied.write_bytes(sentinel)
    call('noise refusal preserves occupied output', 'terminate-file', noisy, {'terminations': [[1, 0, 0]]}, 2, occupied)
    check('unsupported noise does not become an IO/parse error', 'noise' in commands[-1]['stderr'].lower()
          and occupied.read_bytes() == sentinel)

    call('valid export refuses occupied output', 'terminate-file', source, physical, 2, reduced)
    check('valid occupied output protected', 'EEXIST' in commands[-1]['stderr'] and reduced.read_bytes() == reduced_bytes)
    call('input path used as output', 'terminate-file', source, physical, 2, source)
    check('input output alias protected', 'EEXIST' in commands[-1]['stderr'] and source.read_bytes() == original)
    missing = WORK / 'missing parent' / 'output.ts'
    call('missing output parent', 'terminate-file', source, physical, 2, missing)
    check('missing parent is real IO failure', 'ENOENT' in commands[-1]['stderr'] and not missing.exists())

    singular_gamma = [F(4), F(0), F(0), F(0), F(0)]
    singular = False
    try:
        outgoing(matrices[0], singular_gamma, [F(i == 1) for i in range(5)])
    except ValueError:
        singular = True
    check('singular loop established independently', singular)
    pole_output = WORK / 'must not write a pole.ts'
    call('actual singular feedback rejected', 'terminate-file', source,
         {'terminations': [[0, 4, 0], [2, 0, 0], [4, 0, 0]]}, 2, pole_output)
    check('singular loop does not produce finite file', 'singular' in commands[-1]['stderr'].lower()
          and not pole_output.exists())
    check('all original input bytes preserved', source.read_bytes() == original and noisy.read_bytes() == noise_raw)
except Exception as exc:
    failure = exc
finally:
    report = {'status': 'passed' if failure is None else 'failed',
              'failure': repr(failure) if failure is not None else None,
              'oracle': 'Fresh five-port rational S; exact full five-port incident-wave solve, independent limited writer-byte decoder, and raw byte comparisons. No historical fixture or product-reduced matrix is the GT oracle.',
              'actualCLIProcesses': len(commands), 'checks': checks, 'commands': commands,
              'independentReferences': references,
              'compiledBridgeSha256': sha((ROOT / '_build/js/release/build/cmd/bridge/bridge.js').read_bytes()),
              'sourceSha256': {name: sha((ROOT / name).read_bytes()) for name in
                               ['tools/verify-termination-chain.py', 'tools/touchstone.mjs',
                                'cmd/bridge/main.mbt', 'amplifier.mbt', 'gain_impedance.mbt']},
              'artifacts': [{'path': str(path), 'sha256': sha(path.read_bytes())}
                            for path in sorted(WORK.iterdir()) if path.is_file()]}
    args.evidence.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: report[key] for key in ['status', 'failure', 'actualCLIProcesses']}
                     | {'checkCount': len(checks)}, indent=2))
if failure is not None:
    raise failure
