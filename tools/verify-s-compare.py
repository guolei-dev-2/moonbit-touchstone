"""Handwritten rational two-original-file S comparison acceptance (stdlib only)."""
import argparse
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

# Frozen handwritten values, NOT dumps or outputs of the product.
BASE = [[('1/8', '0'), ('1/16', '0'), ('1/2', '0'), ('-1/4', '0')],
        [('0', '0'), ('1/16', '1/16'), ('1/4', '0'), ('1/8', '0')]]
CAND = [[('1/8', '0'), ('1/16', '0'), ('-1/2', '0'), ('-1/4', '0')],
        [('0', '0'), ('1/4', '5/16'), ('1/4', '0'), ('1/8', '0')]]
DELTAS = [[(0, 0), (0, 0), (-1, 0), (0, 0)],
          [(0, 0), (F(3, 16), F(4, 16)), (0, 0), (0, 0)]]
NORMS = [[F(0), F(0), F(1), F(0)], [F(0), F(5, 16), F(0), F(0)]]
FREQ = [1000000, 2000000]
REFS = [50, 75]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def check(label, condition):
    assert condition, label
    checks.append(label)


def reject_constant(value):
    raise ValueError('Nonfinite JSON constant: ' + value)


def load(data):
    value = json.loads(data, parse_constant=reject_constant)
    def finite_tree(v):
        if isinstance(v, float):
            assert math.isfinite(v), 'nonfinite JSON number'
        elif isinstance(v, dict):
            for x in v.values():
                finite_tree(x)
        elif isinstance(v, list):
            for x in v:
                finite_tree(x)
    finite_tree(value)
    return value


def raw(name, data):
    path = WORK / name
    path.write_bytes(data)
    originals[path] = sha(data)
    return path


def source(name, matrices=BASE, frequencies=FREQ, references=REFS, parameter='S',
           newline='\n', modes=None, noise=None, unit='Hz', n=2, legacy=False):
    scale = 1000000 if unit == 'MHz' else 1
    if legacy:
        lines = [f'# {unit} {parameter} RI R 50']
    else:
        lines = ['[Version] 2.1', f'# {unit} {parameter} RI R 50',
                 f'[Number of Ports] {n}', f'[Number of Frequencies] {len(frequencies)}',
                 '[Reference] ' + ' '.join(map(str, references))]
        if n == 2:
            lines.append('[Two-Port Data Order] 12_21')
        if modes:
            lines.append('[Mixed-Mode Order] ' + ' '.join(modes))
        if noise:
            lines.append('[Number of Noise Frequencies] ' + str(len(noise)))
        lines.append('[Network Data]')
    for frequency, row in zip(frequencies, matrices):
        # Legacy two-port wire order is 11,21,12,22.
        ordered = [row[i] for i in [0, 2, 1, 3]] if legacy else row
        lines.append(' '.join([str(frequency / scale)] +
                              [str(float(F(v))) for z in ordered for v in z]))
    if noise:
        lines += ['[Noise Data]', *noise]
    if not legacy:
        lines.append('[End]')
    return raw(name, (newline.join(lines) + newline).encode('ascii'))


def call(label, baseline, options, code, output=None, command='s-compare', node_options=()):
    option_text = options if isinstance(options, str) else json.dumps(options)
    argv = ['node', *node_options, str(ROOT / 'tools/touchstone.mjs'), command, str(baseline), option_text]
    if output is not None:
        argv.append(str(output))
    run = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=30)
    index = len(commands) + 1
    (WORK / f'{index:02d}.stdout.log').write_bytes(run.stdout)
    (WORK / f'{index:02d}.stderr.log').write_bytes(run.stderr)
    commands.append({'label': label, 'argv': argv, 'exitCode': run.returncode, 'expectedExitCode': code,
                     'stderr': run.stderr.decode('utf-8', errors='replace')})
    check(label + ': exit', run.returncode == code)
    if code == 2:
        check(label + ': no partial stdout', not run.stdout and bool(run.stderr))
        return None
    check(label + ': no stderr', not run.stderr)
    if output is not None:
        check(label + ': exclusive file report', not run.stdout and output.is_file())
        return load(output.read_bytes())
    check(label + ': stdout report', bool(run.stdout))
    return load(run.stdout)


def identity(label, value, baseline, candidate):
    check(label + ': report scope', value['kind'] == 's_comparison_report'
          and value['scope'] == 'deterministic_S_only')
    for role, path in [('baseline', baseline), ('candidate', candidate)]:
        payload = path.read_bytes()
        meta = value['sources'][role]
        check(label + ': exact ' + role + ' original bytes',
              meta['sha256'] == sha(payload) and meta['bytes'] == len(payload))
        check(label + ': noise exclusion ' + role, meta['noise_not_compared'] is True)
    condition = value['conditions']
    check(label + ': explicit assumptions',
          condition['pairing'] == 'exact_ordered_parsed_Hz_and_reference_ohms'
          and condition['physical_certification'] is False
          and condition['delta_definition'] == 'candidate_minus_baseline'
          and condition['limit_inclusive'] is True)


def complex_value(value):
    return (value['re'], value['im'])


def expected_pair(z):
    return tuple(float(F(x)) for x in z)


def witness(label, value, point, k, baseline_values, candidate_values, deltas, norms):
    check(label + ': original coordinates', value['point'] == point and value['frequency_hz'] == FREQ[point]
          and value['output'] == k // 2 and value['input'] == k % 2)
    check(label + ': ordered operands and sign',
          complex_value(value['baseline']) == expected_pair(baseline_values[point][k])
          and complex_value(value['candidate']) == expected_pair(candidate_values[point][k])
          and complex_value(value['delta']) == expected_pair(deltas[point][k]))
    check(label + ': exact rational norm', value['absolute_s_delta'] == float(norms[point][k]))


def report(label, value, baseline, candidate, limit, unchanged=False, reverse=False):
    identity(label, value, baseline, candidate)
    a, b = (CAND, BASE) if reverse else (BASE, BASE if unchanged else CAND)
    ds = [[(0, 0)] * 4] * 2 if unchanged else (
        [[(-F(re), -F(im)) for re, im in row] for row in DELTAS] if reverse else DELTAS)
    ns = [[F(0)] * 4] * 2 if unchanged else NORMS
    exceeded = sum(x > F(str(limit)) for row in ns for x in row)
    check(label + ': disposition', value['status'] == ('exceeds' if exceeded else 'within')
          and value['incompatibilities'] == []
          and value['conditions']['maximum_absolute_s_delta'] == limit
          and value['conditions']['physical_alignment_declared'] is True
          and value['conditions']['physical_alignment'] == 'caller_declared_unverified')
    for role in ['baseline', 'candidate']:
        meta = value['sources'][role]
        check(label + ': conditions ' + role, meta['parameter'] == 'S' and meta['ports'] == 2
              and meta['frequency_count'] == 2 and meta['frequency_start_hz'] == 1e6
              and meta['frequency_end_hz'] == 2e6 and meta['reference_ohms'] == REFS
              and meta['mixed_mode_order'] == [])
    comp = value['comparison']
    check(label + ': all eight elements counted', comp['evaluated_elements'] == 8
          and comp['exceeded_elements'] == exceeded and len(comp['per_sij']) == 4)
    witness(label + ' global', comp['maximum'], 0, 0 if unchanged else 2, a, b, ds, ns)
    for k, channel in enumerate(comp['per_sij']):
        point = 1 if k == 1 and not unchanged else 0
        check(label + f': channel {k} full count/order', channel['output'] == k // 2
              and channel['input'] == k % 2 and channel['evaluated_elements'] == 2
              and channel['exceeded_elements'] == sum(row[k] > F(str(limit)) for row in ns))
        witness(label + f' channel {k}', channel['maximum'], point, k, a, b, ds, ns)


failure = None
try:
    baseline = source('baseline LF.ts')
    candidate = source('candidate CRLF.ts', CAND, newline='\r\n')
    q = {'candidate_file': str(candidate), 'maximum_absolute_s_delta': 0.5,
         'physical_alignment_declared': True}
    saved = WORK / 'saved exceeds.json'
    value = call('phase sensitive saved', baseline, q, 3, saved)
    report('phase sensitive', value, baseline, candidate, 0.5)
    for limit, code in [(1, 0), (0, 3), (1e308, 0)]:
        value = call('limit ' + str(limit), baseline, {**q, 'maximum_absolute_s_delta': limit}, code)
        report('limit ' + str(limit), value, baseline, candidate, limit)
    reverse = call('reversed roles', candidate, {**q, 'candidate_file': str(baseline)}, 3)
    report('reversed roles', reverse, candidate, baseline, 0.5, reverse=True)
    same = call('same file zero', baseline, {**q, 'candidate_file': str(baseline), 'maximum_absolute_s_delta': 0}, 0)
    report('same file zero', same, baseline, baseline, 0, unchanged=True)
    duplicate = raw('identical copied bytes.ts', baseline.read_bytes())
    same = call('identical copy zero', baseline, {**q, 'candidate_file': str(duplicate), 'maximum_absolute_s_delta': 0}, 0)
    report('identical copy zero', same, baseline, duplicate, 0, unchanged=True)
    crlf = source('same S CRLF.ts', newline='\r\n')
    same = call('line endings identity difference', baseline, {**q, 'candidate_file': str(crlf), 'maximum_absolute_s_delta': 0}, 0)
    report('line endings', same, baseline, crlf, 0, unchanged=True)
    check('line endings retain distinct identities', same['sources']['baseline']['sha256'] != same['sources']['candidate']['sha256'])
    mhz = source('same parsed Hz.ts', unit='MHz')
    same = call('equivalent parsed Hz grid', baseline, {**q, 'candidate_file': str(mhz), 'maximum_absolute_s_delta': 0}, 0)
    report('parsed Hz', same, baseline, mhz, 0, unchanged=True)
    legacy = source('legacy unchanged.s2p', references=[50, 50], legacy=True)
    v21_equal = source('equal references.ts', references=[50, 50])
    legacy_result = call('legacy filename port inference', v21_equal, {**q, 'candidate_file': str(legacy), 'maximum_absolute_s_delta': 0}, 0)
    identity('legacy', legacy_result, v21_equal, legacy)
    check('legacy comparison full grid', legacy_result['status'] == 'within'
          and legacy_result['comparison']['evaluated_elements'] == 8)

    # Observe actual host opens, rather than merely checking its source spelling.
    open_log = WORK / 'observed opens.json'
    probe = raw('observe-opens.mjs', (
        "import fs from 'node:fs';\nconst open=fs.openSync; const watched="
        + json.dumps([str(baseline), str(candidate)]) + "; const counts={};\n"
        + "fs.openSync=function(p,...a){if(watched.includes(String(p))) counts[p]=(counts[p]||0)+1;return open.call(this,p,...a);};\n"
        + "process.on('exit',()=>fs.writeFileSync(" + json.dumps(str(open_log)) + ",JSON.stringify(counts)));\n").encode())
    observed = call('each distinct source opened once', baseline, q, 3, node_options=('--import', probe.as_uri()))
    report('opened once', observed, baseline, candidate, 0.5)
    check('host read once per original role', load(open_log.read_bytes()) == {str(baseline): 1, str(candidate): 1})

    incompatible = [
        ('port count', source('one port.ts', [[('1/8', '0')], [('0', '0')]], n=1, references=[50]), 'port_count'),
        ('fewer points', source('one point.ts', BASE[:1], FREQ[:1]), 'frequency_count'),
        ('more points', source('three points.ts', [BASE[0], BASE[0], BASE[1]], [1000000, 1500000, 2000000]), 'frequency_count'),
        ('exact grid value', source('next double grid.ts', frequencies=[1000000, math.nextafter(2000000, math.inf)]), 'frequency_grid'),
        ('reference order', source('reversed references.ts', references=[75, 50]), 'reference_ohms'),
        ('exact reference value', source('next double reference.ts', references=[math.nextafter(50, math.inf), 75]), 'reference_ohms'),
        ('non S candidate', source('Z candidate.ts', parameter='Z'), 'non_S_representation'),
        ('mixed candidate', source('modal candidate.ts', references=[50, 50], modes=['D1,2', 'C1,2']), 'mixed_mode'),
    ]
    for label, other, reason in incompatible:
        output = WORK / (label + ' incompatible.json') if label == 'exact grid value' else None
        result = call(label, baseline, {**q, 'candidate_file': str(other)}, 4, output)
        identity(label, result, baseline, other)
        check(label + ': explicit incompatibility and no partial comparison', result['status'] == 'incompatible'
              and reason in result['incompatibilities'] and result['comparison'] is None)
    for label, other, reason in [('non S baseline', source('Y baseline.ts', parameter='Y'), 'non_S_representation'),
                                 ('mixed baseline', source('modal baseline.ts', references=[50, 50], modes=['D1,2', 'C1,2']), 'mixed_mode')]:
        result = call(label, other, {**q, 'candidate_file': str(baseline)}, 4)
        identity(label, result, other, baseline)
        check(label + ': both roles checked', reason in result['incompatibilities'] and result['comparison'] is None)
    for label, declaration in [('missing declaration', None), ('negative declaration', False)]:
        query = {k: v for k, v in q.items() if k != 'physical_alignment_declared'}
        if declaration is not None:
            query['physical_alignment_declared'] = declaration
        result = call(label, baseline, query, 4)
        identity(label, result, baseline, candidate)
        check(label + ': no numerical acceptance', result['status'] == 'incompatible'
              and result['comparison'] is None and 'physical_alignment_not_declared' in result['incompatibilities']
              and result['conditions']['physical_alignment'] == 'not_declared')

    noisy1 = source('noise one.ts', noise=['1000000 1.5 .2 30 10'])
    noisy2 = source('noise two.ts', noise=['1000000 2 .1 20 15', '2000000 2 .1 20 15'])
    for label, first, second, counts in [('noise presence', baseline, noisy1, [0, 1]),
                                         ('noise differing counts', noisy1, noisy2, [1, 2])]:
        result = call(label, first, {**q, 'candidate_file': str(second), 'maximum_absolute_s_delta': 0}, 0)
        report(label, result, first, second, 0, unchanged=True)
        for role, count in zip(['baseline', 'candidate'], counts):
            check(label + ': excluded noise ' + role, result['sources'][role]['noise_record_count'] == count
                  and result['sources'][role]['noise_present'] == bool(count))

    zero_values = [[('0', '0')] * 4] * 2
    tie_values = [[('0', '0'), ('0', '0'), ('0', '0'), ('1/2', '0')],
                  [('1/2', '0'), ('0', '0'), ('0', '0'), ('1/2', '0')]]
    zero_source = source('zero tie base.ts', zero_values)
    tie_source = source('tie revision.ts', tie_values)
    ties = call('tie order across point and channel', zero_source, {**q, 'candidate_file': str(tie_source)}, 0)
    identity('ties', ties, zero_source, tie_source)
    check('ties choose original traversal globally', ties['comparison']['maximum']['point'] == 0
          and ties['comparison']['maximum']['output'] == 1 and ties['comparison']['maximum']['input'] == 1
          and ties['comparison']['per_sij'][0]['maximum']['point'] == 1
          and ties['comparison']['per_sij'][3]['maximum']['point'] == 0
          and ties['comparison']['evaluated_elements'] == 8 and ties['comparison']['exceeded_elements'] == 0)

    # Settled replay gate: same S is insufficient when original bytes differ.
    receipt = call('legacy gain receipt', baseline, {'start_hz': 1e6, 'end_hz': 2e6,
                   'minimum_db': -20, 'maximum_db': 0}, 0, command='gain-record')
    replay = call('legacy changed bytes still mismatch', crlf, receipt, 5, command='gain-review')
    check('gain-review strict identity unchanged', replay['status'] == 'input_mismatch'
          and replay['input_match'] is False and replay['result_match'] is None and replay['current_result'] is None)

    malformed = raw('bad candidate.ts', b'not a Touchstone document\n')
    nonascii = raw('non ASCII.ts', b'# Hz S RI R 50\n\x80\n')
    unsorted = source('not sorted.ts', frequencies=[2000000, 1000000])
    invalid_data = raw('infinite component.ts', baseline.read_bytes().replace(b'0.125', b'1e400', 1))
    no_hint = source('legacy without hint.ts', references=[50, 50], legacy=True)
    invalid_mixed = source('invalid unequal-reference modal.ts', modes=['D1,2', 'C1,2'])
    errors = [
        ('missing limit', {k: v for k, v in q.items() if k != 'maximum_absolute_s_delta'}),
        ('negative limit', {**q, 'maximum_absolute_s_delta': -1}),
        ('null limit', {**q, 'maximum_absolute_s_delta': None}),
        ('string limit', {**q, 'maximum_absolute_s_delta': '0.5'}),
        ('infinite limit', json.dumps(q).replace('0.5', '1e400')),
        ('NaN JSON', json.dumps(q).replace('0.5', 'NaN')),
        ('wrong declaration type', {**q, 'physical_alignment_declared': 'true'}),
        ('null declaration', {**q, 'physical_alignment_declared': None}),
        ('unknown fixture option', {**q, 'left_file': str(WORK / 'must not be opened.ts')}),
        ('identity override', {**q, 'baseline_sha256': '0' * 64}),
        ('fractional candidate hint', {**q, 'candidate_ports': 1.5}),
        ('fractional baseline hint', {**q, 'ports': 1.5}),
        ('missing candidate path', {k: v for k, v in q.items() if k != 'candidate_file'}),
        ('wrong candidate path type', {**q, 'candidate_file': 1}),
        ('empty candidate path', {**q, 'candidate_file': ''}),
        ('missing candidate file', {**q, 'candidate_file': str(WORK / 'missing.ts')}),
        ('candidate directory', {**q, 'candidate_file': str(WORK)}),
        ('malformed candidate', {**q, 'candidate_file': str(malformed)}),
        ('non ASCII candidate', {**q, 'candidate_file': str(nonascii)}),
        ('unsorted grid parse error', {**q, 'candidate_file': str(unsorted)}),
        ('nonfinite parsed value', {**q, 'candidate_file': str(invalid_data)}),
        ('legacy missing hint', {**q, 'candidate_file': str(no_hint)}),
        ('invalid mixed document', {**q, 'candidate_file': str(invalid_mixed)}),
        ('malformed options', '{'), ('array options', '[]'),
    ]
    for label, options in errors:
        target = WORK / (label + ' forbidden.json')
        call(label, baseline, options, 2, target)
        check(label + ': no partial output', not target.exists())
        if label == 'unknown fixture option':
            check('fixture option not consumed', 'left_file' in commands[-1]['stderr'] and 'ENOENT' not in commands[-1]['stderr'])
    for label, first in [('malformed baseline', malformed), ('non ASCII baseline', nonascii),
                         ('missing baseline', WORK / 'missing baseline.ts')]:
        target = WORK / (label + ' forbidden.json')
        call(label, first, q, 2, target)
        check(label + ': no output', not target.exists())
    big = WORK / 'over budget candidate.ts'
    with big.open('wb') as stream:
        stream.seek(64000000)
        stream.write(b' ')
    originals[big] = sha(big.read_bytes())
    target = WORK / 'over budget forbidden.json'
    call('per input byte budget retained', baseline, {**q, 'candidate_file': str(big)}, 2, target)
    check('over budget no output', not target.exists())
    for name, payload in [('options too large.json', b' ' * 1000001), ('options non ASCII.json', b'\x80')]:
        options_path = raw(name, payload)
        target = WORK / (name + '.forbidden')
        call(name, baseline, '@' + str(options_path), 2, target)
        check(name + ': no output', not target.exists())

    huge_negative = source('finite negative huge.ts', [[('-1e308', '0')]], [1000000], [50], n=1)
    huge_positive = source('finite positive huge.ts', [[('1e308', '0')]], [1000000], [50], n=1)
    norm_overflow = source('finite norm overflow.ts', [[('1.7e308', '1.7e308')]], [1000000], [50], n=1)
    zero1 = source('finite zero one port.ts', [[('0', '0')]], [1000000], [50], n=1)
    for label, first, second in [('delta overflow', huge_negative, huge_positive), ('norm overflow', zero1, norm_overflow)]:
        target = WORK / (label + ' forbidden.json')
        call(label, first, {**q, 'candidate_file': str(second)}, 2, target)
        check(label + ': explicit computation error no partial report', not target.exists()
              and 'non-finite delta or magnitude' in commands[-1]['stderr'])
    huge = call('representable huge real delta legal', zero1,
                {**q, 'candidate_file': str(huge_positive), 'maximum_absolute_s_delta': 1e308}, 0)
    identity('representable huge', huge, zero1, huge_positive)
    check('representable huge included equality', huge['status'] == 'within'
          and huge['comparison']['evaluated_elements'] == 1
          and huge['comparison']['maximum']['absolute_s_delta'] == 1e308)

    saved_bytes = saved.read_bytes()
    call('occupied output preserved', baseline, q, 2, saved)
    check('occupied JSON preserved', saved.read_bytes() == saved_bytes)
    for label, target in [('baseline output alias', baseline), ('candidate output alias', candidate)]:
        before = target.read_bytes()
        call(label, baseline, q, 2, target)
        check(label + ': original bytes preserved', target.read_bytes() == before)
    missing_parent = WORK / 'not-created-parent' / 'out.json'
    call('missing output parent', baseline, q, 2, missing_parent)
    check('missing output parent not created', not missing_parent.parent.exists())
    for path, wanted in originals.items():
        check('input preserved: ' + path.name, sha(path.read_bytes()) == wanted)
except Exception as exc:
    failure = exc
finally:
    receipt = {'status': 'passed' if failure is None else 'failed', 'failure': repr(failure) if failure else None,
        'oracle': 'Frozen handwritten two-point 2x2 rational operands; -1 phase-flip delta/norm1 and 3/16+4/16i delta/norm5/16, all other deltas0. No product values used as expected truth.',
        'CLIProcesses': len(commands), 'checks': checks, 'commands': commands,
        'compiledBridgeSha256': sha((ROOT / '_build/js/release/build/cmd/bridge/bridge.js').read_bytes()),
        'sourceSha256': {name: sha((ROOT / name).read_bytes()) for name in
                        ['cmd/bridge/s_compare.mbt', 'cmd/bridge/main.mbt', 'tools/touchstone.mjs',
                         'complex.mbt', 'document.mbt', 'network.mbt', 'tools/verify-s-compare.py']},
        'inputOriginalSHA256': {str(path): wanted for path, wanted in originals.items()},
        'artifacts': [{'path': str(path), 'sha256': sha(path.read_bytes()), 'bytes': path.stat().st_size}
                      for path in sorted(WORK.iterdir()) if path.is_file()]}
    args.evidence.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': receipt['status'], 'failure': receipt['failure'],
                      'CLIProcesses': len(commands), 'checkCount': len(checks)}, indent=2))
if failure is not None:
    raise failure
