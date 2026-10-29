#!/usr/bin/env python3
"""Independent finite-Cartesian DB package/file receivers; stdlib only."""
import argparse
from decimal import Decimal, localcontext
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
assert not evidence.exists(), 'Use a fresh evidence path; preserve earlier attempts'
evidence.parent.mkdir(parents=True, exist_ok=True)
files = evidence.with_suffix('').with_name(evidence.stem + '-cases')
files.mkdir(exist_ok=False)
checks = 0
calls = []
inputs = {}


def check(condition, message):
    global checks
    checks += 1
    if not condition:
        raise AssertionError(message)


def close(actual, expected, message):
    check(isinstance(actual, (int, float)) and math.isfinite(actual), message + ': finite')
    if expected == 0:
        check(actual == 0, message + ': exact zero')
    else:
        check(abs(actual / expected - 1) < 5e-13, message + ': independent value')


def fresh(name, text):
    path = files / name
    with path.open('x', encoding='ascii', newline='') as stream:
        stream.write(text)
    inputs[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    return path


def cli(label, command, path, query=None, output=None, error=None):
    args = ['node', 'tools/touchstone.mjs', command, str(path), json.dumps(query or {})]
    if output is not None:
        args.append(str(output))
    result = subprocess.run(args, cwd=P, capture_output=True)
    stem = f'{len(calls) + 1:02d}-{label}'
    (files / (stem + '.stdout.txt')).write_bytes(result.stdout)
    (files / (stem + '.stderr.txt')).write_bytes(result.stderr)
    calls.append({'case': label, 'command': args, 'exitCode': result.returncode,
                  'stdout': str((files / (stem + '.stdout.txt')).relative_to(evidence.parent)),
                  'stderr': str((files / (stem + '.stderr.txt')).relative_to(evidence.parent)),
                  'stdoutSHA256': hashlib.sha256(result.stdout).hexdigest(),
                  'stderrSHA256': hashlib.sha256(result.stderr).hexdigest()})
    check(result.returncode == (2 if error else 0), label + ': exit')
    if error:
        check(error in result.stderr.decode('utf-8'), label + ': explicit error')
        check(result.stdout == b'', label + ': no partial stdout')
        if output is not None:
            check(not output.exists(), label + ': no partial output file')
        return None
    check(result.stderr == b'', label + ': clean stderr')
    if output is not None:
        check(result.stdout == b'', label + ': output only in file')
        return output.read_text(encoding='ascii')
    return result.stdout.decode('ascii')


def network_description(value, ports, parameter, refs, frequencies, matrices, dumped=False):
    keys = {'ports', 'parameter', 'reference_ohms', 'frequency_hz', 'values'}
    if dumped:
        keys.add('mixed_mode_order')
        check(value['mixed_mode_order'] == [], 'single-ended order')
    check(set(value) == keys, 'complete network schema')
    check(value['ports'] == ports and value['parameter'] == parameter, 'ports/quantity')
    check(value['reference_ohms'] == refs, 'all references')
    check(value['frequency_hz'] == frequencies, 'all ordered Hz frequencies')
    check(len(value['values']) == len(matrices), 'all matrix records')
    for p, matrix in enumerate(matrices):
        check(len(value['values'][p]) == ports * ports, 'all matrix coordinates')
        for k, (re, im) in enumerate(matrix):
            check(set(value['values'][p][k]) == {'re', 'im'}, 'complex component schema')
            close(value['values'][p][k]['re'], re, f'record{p} element{k} real')
            close(value['values'][p][k]['im'], im, f'record{p} element{k} imaginary')


def dump(label, path, ports, parameter, refs, frequencies, matrices):
    value = json.loads(cli(label, 'dump', path, {'ports': ports}))
    network_description(value, ports, parameter, refs, frequencies, matrices, dumped=True)
    return value


with localcontext() as context:
    context.prec = 90
    diagonal = float(Decimal(10) ** (Decimal(6168) / 20) / Decimal(2).sqrt())

source = [
    [(1.6e308, 1.6e308), (0.1, 0.2), (-1.6e308, 1.6e308), (-0.3, 0.4)],
    [(1.7e308, -1.7e308), (-0.2, -0.1), (-1.6e308, -1.6e308), (0.4, -0.3)],
]
decoded = [[(diagonal, diagonal)], [(-diagonal, -diagonal)]]
info = ['synthetic finite Cartesian DB example']
public_text = '[Version] 2.1\n# MHz Z DB R 50\n[Number of Ports] 1\n[Number of Frequencies] 2\n[Reference] 75\n[Begin Information]\nsynthetic finite Cartesian DB example\n[End Information]\n[Network Data]\n1 6168 45\n2 6168 -135\n[End]\n'


def independent_legacy_fields(text):
    lines = text.splitlines()
    check(lines[0] == '# MHZ S DB R 50 75', 'legacy units/parameter/format/references')
    check(len(lines) == 3, 'two complete legacy records')
    for p, line in enumerate(lines[1:]):
        fields = list(map(float, line.split()))
        check(len(fields) == 9 and fields[0] == p + 1, 'legacy MHz/order/record width')
        # Legacy two-port serialization is S11,S21,S12,S22; source is row-major.
        for j, k in enumerate([0, 2, 1, 3]):
            re, im = source[p][k]
            with localcontext() as context:
                context.prec = 90
                r, i = Decimal.from_float(re), Decimal.from_float(im)
                expected_db = float(10 * (r * r + i * i).log10())
            check(abs(fields[1 + 2 * j] - expected_db) < 2e-11, 'independent DB field')
            check(abs(fields[2 + 2 * j] - math.degrees(math.atan2(im, re))) < 1e-12,
                  'independent quadrant angle')


package_receipts = []
for backend in ['js', 'wasm-gc']:
    path = P / f'_build/ci/db-example-{backend}.json'
    value = json.loads(path.read_text(encoding='utf-8-sig'))
    check(set(value) == {'db_input_text', 'decoded', 'canonical_ri', 'information',
                         'source_network', 'legacy_db'}, 'complete public receiver output')
    check(value['db_input_text'] == public_text, 'handwritten package input')
    check(value['information'] == info, 'package information preserved')
    network_description(value['decoded'], 1, 'Z', [75], [1e6, 2e6], decoded)
    network_description(value['source_network'], 2, 'S', [50, 75], [1e6, 2e6], source)
    input_path = fresh(f'package-{backend}-input.ts', value['db_input_text'])
    dump(f'{backend}-db-file', input_path, 1, 'Z', [75], [1e6, 2e6], decoded)
    canonical = fresh(f'package-{backend}-canonical.ts', value['canonical_ri'])
    check('[Begin Information]\n' + info[0] + '\n[End Information]' in value['canonical_ri'],
          'canonical metadata text')
    dump(f'{backend}-canonical-file', canonical, 1, 'Z', [75], [1e6, 2e6], decoded)
    legacy = fresh(f'package-{backend}-writer.s2p', value['legacy_db'])
    independent_legacy_fields(value['legacy_db'])
    dump(f'{backend}-writer-file', legacy, 2, 'S', [50, 75], [1e6, 2e6], source)
    package_receipts.append({'backend': backend, 'output': str(path),
                             'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})

# Fresh arbitrary-file receivers do not rely on either package output.
quadrants = [(diagonal, diagonal), (-diagonal, diagonal), (-diagonal, -diagonal),
             (diagonal, -diagonal), (diagonal, diagonal)]
qtext = '# MHz S DB R 50\n' + ''.join(
    f'{p + 1} 6168 {angle}\n' for p, angle in enumerate([45, 135, 225, -45, 405]))
qfile = fresh('fresh-quadrants.s1p', qtext)
qmat = [[z] for z in quadrants]
dump('fresh-legacy-quadrants', qfile, 1, 'S', [50], [1e6, 2e6, 3e6, 4e6, 5e6], qmat)
normalized = files / 'fresh-normalized.ts'
normal_text = cli('fresh-normalize', 'normalize', qfile, output=normalized)
check('# Hz S RI R 50' in normal_text, 'canonical Hz/RI output')
dump('fresh-normalized-readback', normalized, 1, 'S', [50], [1e6, 2e6, 3e6, 4e6, 5e6], qmat)

for version in ['2.0', '2.1']:
    vtext = public_text.replace('[Version] 2.1', '[Version] ' + version)
    vfile = fresh(f'fresh-version-{version}.ts', vtext)
    dump('version-' + version, vfile, 1, 'Z', [75], [1e6, 2e6], decoded)
    meta = json.loads(cli('metadata-' + version, 'inspect', vfile))
    check(meta == {'ports': 1, 'parameter': 'Z', 'points': 2, 'frequency_hz': [1e6, 2e6],
                   'reference_ohms': [75], 'noise': [], 'noise_reference_ohms': 50,
                   'mixed_mode_order': [], 'information': info}, 'complete document metadata')

zfile = fresh('legacy-normalized-z.s1p', '# kHz Z DB R 0.25\n1000 6168 45\n')
dump('legacy-Z-SI-normalization', zfile, 1, 'Z', [0.25], [1e6],
     [[(diagonal * 0.25, diagonal * 0.25)]])

ri = '[Version] 2.1\n# Hz S RI R 50\n[Number of Ports] 2\n[Two-Port Data Order] 12_21\n[Number of Frequencies] 2\n[Reference] 50 75\n[Network Data]\n'
ri += ''.join(str((p + 1) * 1000000) + ' ' + ' '.join(str(x) for z in matrix for x in z)
              + '\n' for p, matrix in enumerate(source)) + '[End]\n'
rifile = fresh('fresh-writer-source.ts', ri)
written = files / 'fresh-written.s2p'
written_text = cli('fresh-writer', 'legacy', rifile, {'format': 'DB', 'unit': 'MHz'}, written)
independent_legacy_fields(written_text)
dump('fresh-writer-readback', written, 2, 'S', [50, 75], [1e6, 2e6], source)

ordinary = fresh('ordinary.s1p', '# MHz S DB R 50\n1 -20 0\n')
ordinary_dump = dump('ordinary-input', ordinary, 1, 'S', [50], [1e6], [[(0.1, 0.0)]])
ordinary_output = cli('ordinary-output', 'legacy', ordinary, {'format': 'DB', 'unit': 'MHz'})
check(ordinary_output == '# MHZ S DB R 50\n1 -20 0\n', 'old ordinary golden bytes')
tiny = fresh('underflow-control.s1p', '# Hz S DB R 50\n1 -1e308 45\n')
dump('existing-underflow', tiny, 1, 'S', [50], [1], [[(0.0, 0.0)]])

for index, record in enumerate(['6168 0', '6168 90', '6168 180', '6200 45', '1e308 45',
                                'NaN 45', 'Infinity 45']):
    invalid = fresh(f'invalid-db-{index}.s1p', '# Hz S DB R 50\n1 ' + record + '\n')
    cli(f'reject-db-{index}', 'normalize', invalid, output=files / f'no-db-{index}.ts',
        error='non-finite numeric field' if index >= 5 else 'invalid magnitude')
negative = fresh('negative-ma.s1p', '# Hz S MA R 50\n1 -1 45\n')
cli('reject-negative-MA', 'normalize', negative, output=files / 'no-negative.ts', error='invalid magnitude')
cli('reject-radial-MA-output', 'legacy', rifile, {'format': 'MA'}, files / 'no-ma.ts',
    error='non-finite formatted value')
zero = fresh('zero.s1p', '# Hz S RI R 50\n1 0 0\n')
cli('reject-zero-DB-output', 'legacy', zero, {'format': 'DB'}, files / 'no-zero.ts',
    error='zero magnitude cannot be encoded as finite DB')

occupied = fresh('occupied.ts', 'preserve occupied output\n')
occupied_before = occupied.read_bytes()
result = subprocess.run(['node', 'tools/touchstone.mjs', 'legacy', str(rifile),
                         json.dumps({'format': 'DB'}), str(occupied)], cwd=P, capture_output=True)
stem = f'{len(calls) + 1:02d}-exclusive-output'
for stream in ['stdout', 'stderr']:
    (files / (stem + '.' + stream + '.txt')).write_bytes(getattr(result, stream))
calls.append({'case': 'exclusive-output', 'command': result.args, 'exitCode': result.returncode,
              'stdout': str((files / (stem + '.stdout.txt')).relative_to(evidence.parent)),
              'stderr': str((files / (stem + '.stderr.txt')).relative_to(evidence.parent)),
              'stdoutSHA256': hashlib.sha256(result.stdout).hexdigest(),
              'stderrSHA256': hashlib.sha256(result.stderr).hexdigest()})
check(result.returncode == 2 and b'EEXIST' in result.stderr, 'exclusive output error')
check(result.stdout == b'' and occupied.read_bytes() == occupied_before, 'occupied bytes preserved')
for path, digest in inputs.items():
    check(hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, 'input bytes preserved')

receipt = {'status': 'passed', 'actualCLIProcesses': len(calls), 'checks': checks,
           'oracle': 'Independent 90-digit Decimal radial log/power and exact quadrant factors from handwritten inputs; all matrix fields/metadata consumed',
           'independentComponent': diagonal, 'packageExecutionsConsumed': package_receipts,
           'sourceWorkingBytesSHA256': {name: hashlib.sha256((P / name).read_bytes()).hexdigest()
                                       for name in ['text.mbt', 'db_cartesian_test.mbt',
                                                    'examples/db_cartesian/main.mbt', 'tools/verify-db-cartesian.py']},
           'actualBridge': {'path': str(P / '_build/js/release/build/cmd/bridge/bridge.js'),
                            'sha256': hashlib.sha256((P / '_build/js/release/build/cmd/bridge/bridge.js').read_bytes()).hexdigest()},
           'calls': calls, 'inputSHA256': inputs,
           'externalAdoptionClaimed': False, 'wholeBinary64TheoremClaimed': False,
           'preserved': ['ordinary DB golden bytes', 'degree periods', 'metadata/units/order',
                         'true Cartesian overflow errors', 'MA radial boundary', 'zero DB rejection',
                         'existing DB underflow', 'exclusive output and original inputs']}
evidence.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'status': 'passed', 'actualCLIProcesses': len(calls), 'checks': checks,
                  'evidence': str(evidence)}))
