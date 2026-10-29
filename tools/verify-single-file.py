#!/usr/bin/env python3
"""Exact original-wave oracle and complete single-ended file receivers."""
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
assert not evidence.exists(), 'Use fresh evidence and preserve previous failures'
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
    check(label + ': independent value', abs(value - wanted) <= 5e-13 * max(1, abs(wanted)))


def fresh(name, data):
    if isinstance(data, str):
        data = data.encode('ascii')
    path = files / name
    with path.open('xb') as stream:
        stream.write(data)
    inputs[str(path)] = hashlib.sha256(data).hexdigest()
    return path


def call(label, command, source, query=None, output=None, code=0, error=None):
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
        check(label + ': no partial stdout', bool(result.stderr) and not result.stdout)
        if error:
            check(label + ': explicit error', error in result.stderr.decode('utf-8'))
        if output is not None and not existed:
            check(label + ': no new partial file', not output.exists())
        return None
    check(label + ': no stderr', not result.stderr)
    if output is not None:
        check(label + ': real saved output only', output.exists() and not result.stdout)
        return output.read_text(encoding='ascii')
    return result.stdout.decode('ascii')


REAL = [[1, 2, 3, 4], [5, 7, 11, 13], [17, 19, 23, 29], [31, 37, 41, 43]]
IMAG = [[0, 1, -1, 2], [3, -2, 4, -3], [5, -4, 6, -5], [7, -6, 8, -7]]
B = [[0, 0, 1, 1], [1, -1, 0, 0], [0, 0, 1, -1], [1, 1, 0, 0]]
MODES = ['C3,4', 'D1,2', 'D3,4', 'C1,2']
INFO = ['source sweep run A', '', 'fixture labels are source annotations']
FREQUENCIES, REFS = [1000000, 2000000], [50, 50, 75, 75]
RAW, SINGLE = [], []
for p in range(2):
    re = [[Fraction(REAL[i][j], 128 if p == 0 else 256) for j in range(4)] for i in range(4)]
    im = [[Fraction(IMAG[i][j], 256) if p == 0 else -Fraction(IMAG[i][j], 128) for j in range(4)] for i in range(4)]
    RAW.append([{'re': float(re[i][j]), 'im': float(im[i][j])} for i in range(4) for j in range(4)])
    result = []
    for i in range(4):
        for j in range(4):
            # Independent IBIS normalized-wave conjugation, no inverse solver.
            parts = [sum((Fraction(B[m][i]*B[n][j], 2)*a[m][n] for m in range(4) for n in range(4)), Fraction()) for a in [re, im]]
            result.append({'re': float(parts[0]), 'im': float(parts[1])})
    SINGLE.append(result)


def all_matrices(label, actual, expected):
    check(label + ': all frequency records', len(actual) == len(expected))
    for p, (matrix, wanted) in enumerate(zip(actual, expected)):
        check(label + f':{p}: every coordinate', len(matrix) == len(wanted))
        for k, (z, target) in enumerate(zip(matrix, wanted)):
            check(label + f':{p}:{k}: complex schema', set(z) == {'re', 'im'})
            for part in ['re', 'im']:
                close(label + f':{p}:{k}:{part}', z[part], target[part])


def network(label, value, n, kind, frequencies, refs, matrices, modes, description=False,
            info=None, noise_ref=40):
    keys = {'ports', 'parameter', 'frequency_hz', 'reference_ohms', 'values'}
    if description:
        keys |= {'points', 'mixed_mode_order', 'noise_reference_ohms', 'noise', 'information'}
        check(label + ': complete conditions', value['points'] == len(frequencies)
              and value['noise_reference_ohms'] == noise_ref and value['noise'] == []
              and value['information'] == (INFO if info is None else info))
    else:
        keys.add('mixed_mode_order')
    check(label + ': full schema', set(value) == keys)
    check(label + ': original coordinates/units/references', value['ports'] == n and value['parameter'] == kind
          and value['frequency_hz'] == frequencies and value['reference_ohms'] == refs
          and value['mixed_mode_order'] == modes)
    all_matrices(label, value['values'], matrices)


def canonical(label, text, n, kind, frequencies, refs, matrices, info, noise_ref):
    # Finite independent decoder of the existing canonical writer grammar.
    check(label + ': canonical physical representation', text.startswith(f'[Version] 2.1\n# Hz {kind} RI R {noise_ref:g}\n'))
    check(label + ': dimensions', f'[Number of Ports] {n}\n' in text and f'[Number of Frequencies] {len(frequencies)}\n' in text)
    check(label + ': original references', '[Reference] ' + ' '.join(f'{x:g}' for x in refs) + '\n' in text)
    check(label + ': actual single-ended header', '[Mixed-Mode Order]' not in text and '[Matrix Format] Full\n' in text)
    check(label + ': no invented noise', '[Noise Data]' not in text)
    if info:
        check(label + ': preserved Information', '[Begin Information]\n' + '\n'.join(info) + '\n[End Information]\n' in text)
    else:
        check(label + ': no invented information', '[Begin Information]' not in text)
    if n == 2:
        check(label + ': original numbered two-port frame', '[Two-Port Data Order] 12_21\n' in text)
    fields = list(map(float, text.split('[Network Data]\n')[1].split('[End]')[0].split()))
    width = 1 + 2*n*n
    check(label + ': every serialized field', len(fields) == len(frequencies)*width)
    decoded = []
    for p, f in enumerate(frequencies):
        record = fields[p*width:(p+1)*width]
        check(label + f':{p}: original frequency', record[0] == f)
        decoded.append([{'re': record[1+2*k], 'im': record[2+2*k]} for k in range(n*n)])
    all_matrices(label + ': independent bytes', decoded, matrices)


def metrics(label, rows):
    check(label + ': complete metric array', len(rows) == 2)
    for p, row in enumerate(rows):
        z, t = SINGLE[p][0], SINGLE[p][8]
        r = math.hypot(z['re'], z['im'])
        gain = math.hypot(t['re'], t['im'])
        check(label + ': full metric schema', set(row) == {'frequency_hz', 'reflection_magnitude', 'transmission_magnitude',
              'return_loss_db', 'return_loss_infinite', 'insertion_loss_db', 'insertion_loss_infinite', 'vswr', 'vswr_state'})
        check(label + ': original Hz/state', row['frequency_hz'] == FREQUENCIES[p] and not row['return_loss_infinite'] and not row['insertion_loss_infinite'] and row['vswr_state'] == 'finite')
        for field, wanted in [('reflection_magnitude', r), ('transmission_magnitude', gain),
                              ('return_loss_db', -20*math.log10(r)), ('insertion_loss_db', -20*math.log10(gain)),
                              ('vswr', (1+r)/(1-r))]:
            close(label + ':' + field, row[field], wanted)


source_path = P / 'examples/single-file-source.ts'
source_bytes = source_path.read_bytes()
source = fresh('actual-mixed-input-copy.ts', source_bytes)
check('actual tested input copy equals original working bytes', source.read_bytes() == source_bytes)
network('original raw input', json.loads(call('original-raw', 'dump', source)), 4, 'S', FREQUENCIES, REFS, RAW, MODES)
original_info = json.loads(call('original-conditions', 'inspect', source))
check('complete original conditions', original_info == {'ports': 4, 'parameter': 'S', 'points': 2, 'frequency_hz': FREQUENCIES,
      'reference_ohms': REFS, 'noise': [], 'noise_reference_ohms': 40, 'mixed_mode_order': MODES, 'information': INFO})
output = files / 'single-ended.ts'
text = call('single-file-export', 'single-file', source, output=output)
canonical('single-file-export', text, 4, 'S', FREQUENCIES, REFS, SINGLE, INFO, 40)
network('actual file readback', json.loads(call('single-file-readback', 'dump', output)), 4, 'S', FREQUENCIES, REFS, SINGLE, [])
metrics('actual downstream file', json.loads(call('single-file-metrics', 'metrics', output, {'input': 0, 'output': 2})))
again = call('idempotent-single-file', 'single-file', output)
check('already single-ended output is not transformed twice', again == text)

packages = []
for backend in ['js', 'wasm-gc']:
    path = P / f'_build/ci/single-file-example-{backend}.json'
    value = json.loads(path.read_bytes())
    check(backend + ': complete package output', set(value) == {'input_text', 'original', 'single_ended', 'output_text', 'metrics'})
    check(backend + ': complete original input', value['input_text'].replace('\r\n', '\n') == source_bytes.decode('ascii').replace('\r\n', '\n'))
    network(backend + ': source', value['original'], 4, 'S', FREQUENCIES, REFS, RAW, MODES, description=True)
    network(backend + ': restored', value['single_ended'], 4, 'S', FREQUENCIES, REFS, SINGLE, [], description=True)
    canonical(backend + ': output', value['output_text'], 4, 'S', FREQUENCIES, REFS, SINGLE, INFO, 40)
    metrics(backend + ': public downstream', value['metrics'])
    produced = fresh('actual-public-' + backend + '.ts', value['output_text'])
    network(backend + ': file', json.loads(call(backend + '-readback', 'dump', produced)), 4, 'S', FREQUENCIES, REFS, SINGLE, [])
    metrics(backend + ': file metrics', json.loads(call(backend + '-metrics', 'metrics', produced, {'input': 0, 'output': 2})))
    packages.append({'backend': backend, 'actualOutput': str(path), 'outputSHA256': hashlib.sha256(path.read_bytes()).hexdigest(),
                     'actualProducedFile': str(produced), 'producedFileSHA256': hashlib.sha256(produced.read_bytes()).hexdigest()})

old_single = call('old-single-JSON-control', 'single', source)
check('old full single JSON bytes unchanged', old_single.encode('ascii') == (P / 'tools/fixtures/single-file/single-before.json').read_bytes())
old_normalize = call('old-normalize-control', 'normalize', source)
check('old full normalize bytes still modal', old_normalize.encode('ascii') == (P / 'tools/fixtures/single-file/normalize-before.ts').read_bytes() and '[Mixed-Mode Order]' in old_normalize)
call('old-legacy-information-refusal', 'legacy', source, code=2, output=files / 'no-legacy.ts', error='information')

def document_text(n, kind, refs, matrices, frequencies, modes=None, info=None, noise_ref=60, version='2.1'):
    text = f'[Version] {version}\n# Hz {kind} RI R {noise_ref:g}\n[Number of Ports] {n}\n'
    if n == 2:
        text += '[Two-Port Data Order] 12_21\n'
    text += f'[Number of Frequencies] {len(frequencies)}\n[Reference] ' + ' '.join(str(x) for x in refs) + '\n'
    if modes:
        text += '[Mixed-Mode Order] ' + ' '.join(modes) + '\n'
    if info:
        text += '[Begin Information]\n' + '\n'.join(info) + '\n[End Information]\n'
    return text + '[Network Data]\n' + ''.join(str(f) + ' ' + ' '.join(str(v) for z in matrix for v in [z['re'], z['im']]) + '\n' for f, matrix in zip(frequencies, matrices)) + '[End]\n'

# Unpaired S3 has no cross-coupling, so the full expected matrix is exact
# rational without introducing an artificial sqrt2 numerical reference.
unpaired_raw = [[{'re': x, 'im': 0} for x in [1/8, 0, 0, 0, 1/4, 1/8, 0, 1/16, 1/2]]]
unpaired_expected = [[{'re': x, 'im': 0} for x in [15/32, -5/32, 0, -3/32, 9/32, 0, 0, 0, 1/8]]]
unpaired = fresh('unpaired-S3.ts', document_text(3, 'S', [50, 50, 100], unpaired_raw, [3000000], ['S3', 'C1,2', 'D1,2'], ['unpaired source']))
unpaired_out = files / 'unpaired-restored.ts'
content = call('unpaired-export', 'single-file', unpaired, output=unpaired_out)
canonical('unpaired-export', content, 3, 'S', [3000000], [50, 50, 100], unpaired_expected, ['unpaired source'], 60)
network('unpaired readback', json.loads(call('unpaired-readback', 'dump', unpaired_out)), 3, 'S', [3000000], [50, 50, 100], unpaired_expected, [])
for kind, modal_diagonal, standard_diagonal in [('Z', [200, 50], 100), ('Y', [0.005, 0.02], 0.01)]:
    raw = [[{'re': x, 'im': 0} for x in [modal_diagonal[0], 0, 0, modal_diagonal[1]]]]
    wanted = [[{'re': x, 'im': 0} for x in [standard_diagonal, 0, 0, standard_diagonal]]]
    path = fresh('physical-' + kind + '.ts', document_text(2, kind, [50, 50], raw, [1000000], ['D1,2', 'C1,2'], ['physical ' + kind]))
    target = files / ('single-' + kind + '.ts')
    value = call('physical-' + kind, 'single-file', path, output=target)
    canonical('physical-' + kind, value, 2, kind, [1000000], [50, 50], wanted, ['physical ' + kind], 60)
    network('physical-' + kind + ': readback', json.loads(call('physical-' + kind + '-readback', 'dump', target)), 2, kind, [1000000], [50, 50], wanted, [])

legacy = fresh('already-single.s2p', '# MHz S RI R 50 75\n1 0.125 0 0.25 0.125 0.0625 0 0.5 0\n2 0.25 0 0.125 0.0625 0.25 0 0.375 0\n')
normalized = call('legacy-normalize-control', 'normalize', legacy)
converted = call('legacy-single-file', 'single-file', legacy)
check('already-single legacy canonical output unchanged', normalized == converted and '[Mixed-Mode Order]' not in converted)
noisy_text = '[Version] 2.1\n# Hz S RI R 50\n[Number of Ports] 2\n[Two-Port Data Order] 12_21\n[Number of Frequencies] 2\n[Reference] 75 100\n[Number of Noise Frequencies] 1\n[Begin Information]\nalready single-ended noise source\n[End Information]\n[Network Data]\n1000000 0 0 0 0 0.5 0 0 0\n2000000 0 0 0 0 0.25 0 0 0\n[Noise Data]\n0 0 0 0 25\n[End]\n'
noisy = fresh('already-single-noisy.ts', noisy_text)
old_noisy = call('old-noisy-normalize', 'normalize', noisy)
noisy_out = files / 'noisy-preserved.ts'
value = call('single-noisy-retained', 'single-file', noisy, output=noisy_out)
check('no basis change retains entire noisy document', value == old_noisy and '[Noise Data]' in value and 'already single-ended noise source' in value)
meta = json.loads(call('single-noisy-readback', 'inspect', noisy_out))
check('all original noisy conditions', meta == {'ports': 2, 'parameter': 'S', 'points': 2, 'frequency_hz': FREQUENCIES,
      'reference_ohms': [75, 100], 'noise_reference_ohms': 50, 'mixed_mode_order': [], 'information': ['already single-ended noise source'],
      'noise': [{'frequency_hz': 0, 'minimum_figure_db': 0, 'gamma_opt': {'re': 0, 'im': 0}, 'resistance_ohms': 25}]})
mixed_noisy_text = noisy_text.replace('[Reference] 75 100', '[Reference] 50 50\n[Mixed-Mode Order] D1,2 C1,2')
mixed_noisy = fresh('mixed-with-noise.ts', mixed_noisy_text)
call('old-mixed-noise-parser-control', 'inspect', mixed_noisy)
call('reject-mixed-noise', 'single-file', mixed_noisy, code=2, output=files / 'no-mixed-noise.ts', error='cannot transform mixed-mode noise')
for i, query in enumerate([{'pairs': [[0, 1]]}, {'parameter': 'Z'}, {'drop_noise': True},
                           {'left_file': 'never-read-third-file.ts'}, {'ports': 3}]):
    reason = 'unknown single-file option' if i < 4 else 'conflicts with header'
    call('reject-option-' + str(i), 'single-file', source, query, files / f'no-option-{i}.ts', 2, reason)
occupied = fresh('occupied.ts', 'preserve occupied output\n')
call('occupied-output', 'single-file', source, output=occupied, code=2, error='EEXIST')
call('same-path-output', 'single-file', source, output=source, code=2, error='EEXIST')
call('missing-parent', 'single-file', source, output=files / 'absent-directory/out.ts', code=2, error='ENOENT')
for path, digest in inputs.items():
    check('preserved original/test/output:' + Path(path).name, hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest)

receipt = {'status': 'passed', 'actualCLIProcesses': len(calls), 'receivingChecks': len(checks), 'checkNames': checks,
           'oracle': 'Exact Fractions from original modal values and IBIS normalized-wave U=B/sqrt2; all Sse=B^T*Smm*B/2 coordinates, independent canonical decoding and downstream hypot/log10/VSWR',
           'productionBugClaimed': False, 'existingPublicTransformationAcknowledged': True,
           'packageExecutionsConsumed': packages,
           'actualTestInputCopies': [{'originalWorkingPath': str(source_path), 'originalWorkingSHA256': hashlib.sha256(source_bytes).hexdigest(),
                                     'actualTestCopy': str(source), 'actualTestCopySHA256': hashlib.sha256(source.read_bytes()).hexdigest(),
                                     'byteIdentical': source.read_bytes() == source_bytes}],
           'sourceWorkingBytesSHA256': {name: hashlib.sha256((P / name).read_bytes()).hexdigest() for name in ['cmd/bridge/main.mbt', 'tools/touchstone.mjs', 'examples/single_file/main.mbt', 'tools/verify-single-file.py']},
           'actualBridge': {'path': str(P / '_build/js/release/build/cmd/bridge/bridge.js'), 'sha256': hashlib.sha256((P / '_build/js/release/build/cmd/bridge/bridge.js').read_bytes()).hexdigest()},
           'calls': calls, 'inputSHA256': inputs, 'externalAdoptionClaimed': False, 'nativeRuntimeClaimed': False}
evidence.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'status': 'passed', 'actualCLIProcesses': len(calls), 'receivingChecks': len(checks), 'evidence': str(evidence)}))
