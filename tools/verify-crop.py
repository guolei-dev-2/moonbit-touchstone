#!/usr/bin/env python3
"""Independent original-point document/file export and downstream receivers."""
import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import subprocess

P = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--evidence', required=True)
options = parser.parse_args()
evidence = Path(options.evidence).resolve()
assert not evidence.exists(), 'Use a fresh evidence path and preserve failures'
evidence.parent.mkdir(parents=True, exist_ok=True)
files = evidence.with_name(evidence.stem + '-cases')
files.mkdir(exist_ok=False)
calls, checks, inputs = [], [], {}


def check(label, condition):
    checks.append(label)
    if not condition:
        raise AssertionError(label)


def close(label, value, wanted):
    check(label + ': finite', isinstance(value, (int, float)) and math.isfinite(value))
    check(label + ': independent value', abs(value - wanted) <= 2e-13 * max(1, abs(wanted)))


def fresh(name, data):
    path = files / name
    if isinstance(data, str):
        data = data.encode('ascii')
    with path.open('xb') as stream:
        stream.write(data)
    inputs[str(path)] = hashlib.sha256(data).hexdigest()
    return path


def call(label, command, source, query=None, code=0, output=None, error=None):
    argv = ['node', 'tools/touchstone.mjs', command, str(source), json.dumps(query or {})]
    if output is not None:
        argv.append(str(output))
    existed = output is not None and output.exists()
    result = subprocess.run(argv, cwd=P, capture_output=True)
    stem = f'{len(calls) + 1:02d}-{label}'
    for stream in ['stdout', 'stderr']:
        (files / (stem + '.' + stream + '.txt')).write_bytes(getattr(result, stream))
    calls.append({'label': label, 'argv': argv, 'exitCode': result.returncode, 'expectedExitCode': code,
                  **{s: str((files / (stem + '.' + s + '.txt')).relative_to(evidence.parent)) for s in ['stdout', 'stderr']},
                  **{s + 'SHA256': hashlib.sha256(getattr(result, s)).hexdigest() for s in ['stdout', 'stderr']}})
    check(label + ': exit', result.returncode == code)
    if code == 2:
        check(label + ': error/no stdout', bool(result.stderr) and not result.stdout)
        if error:
            check(label + ': reason', error in result.stderr.decode('utf-8'))
        if output is not None and not existed:
            check(label + ': no partial output', not output.exists())
        return None
    check(label + ': no stderr', not result.stderr)
    if output is not None:
        check(label + ': exclusive saved output', not result.stdout and output.exists())
        return output.read_text(encoding='ascii')
    return result.stdout.decode('ascii')


INFO = ['original sweep for frequency-window export', '', 'keep source units and port labels']
FREQUENCIES = [0, 1000000, 2000000, 4000000]
MATRICES = []
for p in range(4):
    matrix = []
    for k in range(9):
        row, col = divmod(k, 3)
        matrix.append({'re': [25, 50, 75][row] * (p + 1 + row) if row == col else 0, 'im': 0})
    MATRICES.append(matrix)
QUERY = {'start_hz': 1000000, 'end_hz': 2000000}
SELECTED = [MATRICES[1], MATRICES[2]]


def original_fields(value, points, description=False, n=3, kind='Z', refs=None, matrices=None,
                    info=None, modes=None, noise_ref=37.5):
    refs = refs if refs is not None else [25, 50, 75]
    matrices = matrices if matrices is not None else [MATRICES[i] for i in points]
    frequencies = [FREQUENCIES[i] for i in points]
    if description:
        check('complete public description', set(value) == {'ports', 'parameter', 'points', 'frequency_hz',
              'reference_ohms', 'noise_reference_ohms', 'noise', 'mixed_mode_order', 'information', 'values'})
        check('all document conditions', value['points'] == len(points) and value['noise'] == []
              and value['noise_reference_ohms'] == noise_ref
              and value['information'] == (INFO if info is None else info))
    else:
        check('complete dump schema', set(value) == {'ports', 'parameter', 'frequency_hz',
              'reference_ohms', 'values', 'mixed_mode_order'})
    check('ports/quantity/references', value['ports'] == n and value['parameter'] == kind and value['reference_ohms'] == refs)
    check('all ordered Hz original points', value['frequency_hz'] == frequencies)
    check('unchanged raw mode descriptors', value['mixed_mode_order'] == (modes or []))
    check('every original Cartesian coordinate', value['values'] == matrices)


def canonical(label, text, n, kind, refs, noise_ref, frequencies, matrices, info, modes):
    # A deliberately bounded independent decoder of this writer's fixed
    # canonical2.1/Hz/RI/full output. It is not another product parser.
    check(label + ': canonical version/units/quantity', text.startswith(f'[Version] 2.1\n# Hz {kind} RI R {noise_ref:g}\n'))
    check(label + ': full original references', '[Reference] ' + ' '.join(f'{x:g}' for x in refs) + '\n' in text)
    check(label + ': dimensions/count', f'[Number of Ports] {n}\n' in text and f'[Number of Frequencies] {len(frequencies)}\n' in text)
    check(label + ': full representation', '[Matrix Format] Full\n' in text)
    check(label + ': no invented noise', '[Noise Data]' not in text and '[Number of Noise Frequencies]' not in text)
    if info:
        check(label + ': exact information lines', '[Begin Information]\n' + '\n'.join(info) + '\n[End Information]\n' in text)
    else:
        check(label + ': no invented information', '[Begin Information]' not in text)
    if modes:
        check(label + ': raw basis retained', '[Mixed-Mode Order] ' + ' '.join(modes) + '\n' in text)
    else:
        check(label + ': no invented mode', '[Mixed-Mode Order]' not in text)
    if n == 2:
        check(label + ': canonical two-port order', '[Two-Port Data Order] 12_21\n' in text)
    values = list(map(float, text.split('[Network Data]\n')[1].split('[End]')[0].split()))
    width = 1 + 2*n*n
    check(label + ': all original records/fields', len(values) == len(frequencies)*width)
    for p, (f, matrix) in enumerate(zip(frequencies, matrices)):
        record = values[p*width:(p+1)*width]
        check(label + f':{p}: original frequency', record[0] == f)
        check(label + f':{p}: full original matrix', record[1:] == [v for z in matrix for v in [z['re'], z['im']]])


def metrics(label, value):
    check(label + ': full two-point metric output', len(value) == 2)
    for p, r in enumerate([Fraction(1, 3), Fraction(1, 2)]):
        row = value[p]
        check(label + ': complete metric schema', set(row) == {'frequency_hz', 'reflection_magnitude',
              'transmission_magnitude', 'return_loss_db', 'return_loss_infinite', 'insertion_loss_db',
              'insertion_loss_infinite', 'vswr', 'vswr_state'})
        check(label + ': original metric point', row['frequency_hz'] == [1000000, 2000000][p])
        for field in ['reflection_magnitude', 'transmission_magnitude']:
            close(label + ':' + field, row[field], float(r))
        for field in ['return_loss_db', 'insertion_loss_db']:
            close(label + ':' + field, row[field], -20*math.log10(float(r)))
        close(label + ': VSWR', row['vswr'], float((1+r)/(1-r)))
        check(label + ': metric states', not row['return_loss_infinite'] and not row['insertion_loss_infinite'] and row['vswr_state'] == 'finite')


source_path = P / 'examples/crop-wideband.ts'
source_bytes = source_path.read_bytes()
source = fresh('actual-source-copy.ts', source_bytes)
check('test input is original working byte copy', source.read_bytes() == source_bytes)
original_fields(json.loads(call('original-dump', 'dump', source)), [0, 1, 2, 3])
meta = json.loads(call('original-conditions', 'inspect', source))
check('complete original metadata', meta == {'ports': 3, 'parameter': 'Z', 'points': 4,
      'frequency_hz': FREQUENCIES, 'reference_ohms': [25, 50, 75], 'noise_reference_ohms': 37.5,
      'noise': [], 'mixed_mode_order': [], 'information': INFO})
output = files / 'cropped.ts'
text = call('file-crop', 'crop', source, QUERY, output=output)
canonical('file-crop', text, 3, 'Z', [25, 50, 75], 37.5, [1000000, 2000000], SELECTED, INFO, [])
original_fields(json.loads(call('file-readback', 'dump', output)), [1, 2])
metrics('file-downstream', json.loads(call('file-downstream', 'metrics', output, {'input': 0, 'output': 0})))

package_receipts = []
for backend in ['js', 'wasm-gc']:
    path = P / f'_build/ci/crop-example-{backend}.json'
    value = json.loads(path.read_bytes())
    check(backend + ': complete public result', set(value) == {'input_text', 'query', 'original', 'cropped', 'cropped_text', 'metrics'})
    check(backend + ': frozen original input/query', value['input_text'].replace('\r\n', '\n') == source_bytes.decode('ascii').replace('\r\n', '\n') and value['query'] == QUERY)
    original_fields(value['original'], [0, 1, 2, 3], description=True)
    original_fields(value['cropped'], [1, 2], description=True)
    metrics(backend + ': public downstream', value['metrics'])
    canonical(backend, value['cropped_text'], 3, 'Z', [25, 50, 75], 37.5, [1000000, 2000000], SELECTED, INFO, [])
    produced = fresh('actual-package-' + backend + '.ts', value['cropped_text'])
    original_fields(json.loads(call(backend + '-readback', 'dump', produced)), [1, 2])
    metrics(backend + ': file downstream', json.loads(call(backend + '-downstream', 'metrics', produced, {'input': 0, 'output': 0})))
    package_receipts.append({'backend': backend, 'actualOutput': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                             'actualWrittenCopy': str(produced), 'actualWrittenCopySHA256': hashlib.sha256(produced.read_bytes()).hexdigest()})

for label, bounds, points in [
    ('nonaligned-single', {'start_hz': 1100000, 'end_hz': 3900000}, [2]),
    ('equal-first', {'start_hz': 0, 'end_hz': 0}, [0]),
    ('equal-last', {'start_hz': 4000000, 'end_hz': 4000000}, [3]),
    ('outside-intersection', {'start_hz': 0, 'end_hz': 5000000}, [0, 1, 2, 3]),
]:
    selected = [MATRICES[i] for i in points]
    content = call(label, 'crop', source, bounds)
    canonical(label, content, 3, 'Z', [25, 50, 75], 37.5, [FREQUENCIES[i] for i in points], selected, INFO, [])
    if label == 'equal-first':
        one = fresh('one-retained.ts', content)
        call('one-point-old-delay-error', 'delay', one, {'input': 0, 'output': 0}, 2, files / 'no-delay.json', 'at least two frequencies')

# Nonsequential raw modal coordinates must never become a single-ended matrix
# while retaining a now-wrong mode descriptor header.
modes = ['C3,4', 'D1,2', 'D3,4', 'C1,2']
modal_matrices = [[{'re': (p*16+k+1)/256, 'im': -k/512} for k in range(16)] for p in range(3)]
mixed_text = '[Version] 2.1\n# MHz S RI R 40\n[Number of Ports] 4\n[Number of Frequencies] 3\n[Reference] 50 50 75 75\n[Mixed-Mode Order] ' + ' '.join(modes) + '\n[Begin Information]\nraw modal samples\n[End Information]\n[Network Data]\n'
mixed_text += ''.join(str(f) + ' ' + ' '.join(str(v) for z in matrix for v in [z['re'], z['im']]) + '\n' for f, matrix in zip([1, 3, 5], modal_matrices)) + '[End]\n'
mixed = fresh('mixed.ts', mixed_text)
mixed_out = files / 'mixed-cropped.ts'
content = call('mixed-crop', 'crop', mixed, {'start_hz': 3000000, 'end_hz': 3000000}, output=mixed_out)
canonical('mixed-crop', content, 4, 'S', [50, 50, 75, 75], 40, [3000000], [modal_matrices[1]], ['raw modal samples'], modes)
value = json.loads(call('mixed-readback', 'dump', mixed_out))
check('complete mixed raw result', value == {'ports': 4, 'parameter': 'S', 'frequency_hz': [3000000],
      'reference_ohms': [50, 50, 75, 75], 'values': [modal_matrices[1]], 'mixed_mode_order': modes})

legacy_matrices = [[{'re': (p*4+k+1)/32, 'im': -k/64} for k in range(4)] for p in range(3)]
legacy_text = '# GHz S RI R 50 75\n' + ''.join(str(f) + ' ' + ' '.join(str(v) for k in [0, 2, 1, 3] for v in [matrix[k]['re'], matrix[k]['im']]) + '\n' for f, matrix in zip([1, 2, 4], legacy_matrices))
legacy = fresh('legacy.s2p', legacy_text)
legacy_out = files / 'legacy-cropped.ts'
content = call('legacy-crop', 'crop', legacy, {'start_hz': 1e9, 'end_hz': 2e9}, output=legacy_out)
canonical('legacy-crop', content, 2, 'S', [50, 75], 50, [1e9, 2e9], legacy_matrices[:2], [], [])
value = json.loads(call('legacy-readback', 'dump', legacy_out))
check('all legacy order/units/coordinates', value == {'ports': 2, 'parameter': 'S', 'frequency_hz': [1e9, 2e9], 'reference_ohms': [50, 75], 'values': legacy_matrices[:2], 'mixed_mode_order': []})

manual = call('old-interpolate-control', 'interpolate', source, {'frequency_hz': [1000000, 2000000]})
baseline = (P / 'tools/fixtures/crop/interpolate-before.ts').read_bytes()
check('old manual composition and output unchanged', manual.encode('ascii') == baseline and manual == text)
for i, query in enumerate([
    {'start_hz': -1, 'end_hz': 2000000}, {'start_hz': 2000000, 'end_hz': 1000000},
    {'start_hz': 1100000, 'end_hz': 1900000}, {'start_hz': 6000000, 'end_hz': 7000000},
    {'start_hz': 0}, {'end_hz': 2000000}, {'start_hz': '1MHz', 'end_hz': 2000000},
    {**QUERY, 'frequency_hz': [1000000]}, {**QUERY, 'left_file': 'not-a-fixture-input.ts'},
]):
    reason = 'unknown crop option' if i >= 7 else None
    call('reject-query-' + str(i), 'crop', source, query, 2, files / f'no-query-{i}.ts', reason)
noisy_text = '[Version] 2.1\n# Hz S RI R 50\n[Number of Ports] 2\n[Two-Port Data Order] 12_21\n[Number of Frequencies] 2\n[Reference] 75 100\n[Number of Noise Frequencies] 1\n[Network Data]\n1000000 0 0 0 0 0.5 0 0 0\n2000000 0 0 0 0 0.25 0 0 0\n[Noise Data]\n0 0 0 0 25\n[End]\n'
noisy = fresh('old-legal-noisy.ts', noisy_text)
value = json.loads(call('old-noise-input-control', 'inspect', noisy))
check('original legal noisy input remains accepted', value['noise_reference_ohms'] == 50 and value['reference_ohms'] == [75, 100] and len(value['noise']) == 1)
call('crop-noise-rejected', 'crop', noisy, QUERY, 2, files / 'no-noise.ts', 'does not support noise data')
occupied = fresh('occupied.ts', 'preserve output\n')
call('occupied-output', 'crop', source, QUERY, 2, occupied, 'EEXIST')
call('same-path-output', 'crop', source, QUERY, 2, source, 'EEXIST')
call('missing-output-parent', 'crop', source, QUERY, 2, files / 'absent-parent/out.ts', 'ENOENT')
for path, digest in inputs.items():
    check('original/test/occupied bytes preserved:' + Path(path).name, hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest)

receipt = {'status': 'passed', 'actualCLIProcesses': len(calls), 'checks': len(checks), 'checkNames': checks,
           'oracle': 'Fixed original integer/fraction matrices and exact original point indices; independent fixed-canonical decoder; Gamma=(Z-R)/(Z+R), rational VSWR and independent log10 for actual downstream receiver',
           'productionBugClaimed': False, 'existingCompositionAcknowledged': True,
           'packageExecutionsConsumed': package_receipts,
           'actualTestInputCopies': [{'originalWorkingPath': str(source_path), 'originalWorkingSHA256': hashlib.sha256(source_bytes).hexdigest(), 'actualTestCopy': str(source), 'actualTestCopySHA256': hashlib.sha256(source.read_bytes()).hexdigest(), 'byteIdentical': source.read_bytes() == source_bytes}],
           'sourceWorkingBytesSHA256': {name: hashlib.sha256((P / name).read_bytes()).hexdigest() for name in ['crop.mbt', 'crop_test.mbt', 'cmd/bridge/main.mbt', 'tools/touchstone.mjs', 'examples/crop_document/main.mbt', 'tools/verify-crop.py']},
           'actualBridge': {'path': str(P / '_build/js/release/build/cmd/bridge/bridge.js'), 'sha256': hashlib.sha256((P / '_build/js/release/build/cmd/bridge/bridge.js').read_bytes()).hexdigest()},
           'calls': calls, 'inputSHA256': inputs, 'externalAdoptionClaimed': False, 'nativeRuntimeClaimed': False}
evidence.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'status': 'passed', 'actualCLIProcesses': len(calls), 'checks': len(checks), 'evidence': str(evidence)}))
