"""Fresh-file GT audit acceptance: hand values, raw bytes, replay and CSV.

No historical fixture, receipt, product gain command or RF library supplies
expected values. The real CLI still executes the compiled MoonBit calculation.
"""
import argparse
import copy
import csv
from fractions import Fraction
import hashlib
import io
import json
import math
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
HEADERS = ('point,frequency_hz,gain,gain_db,state,start_hz,end_hz,minimum_db,'
           'maximum_db,below_minimum,above_maximum,sample_status,report_status,'
           'range_covered').split(',')
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--evidence', type=Path, required=True)
args = parser.parse_args()
assert not args.evidence.exists(), 'Choose a fresh evidence path'
args.evidence.parent.mkdir(parents=True, exist_ok=True)
WORK = args.evidence.with_name(args.evidence.stem + '-cases')
WORK.mkdir(exist_ok=False)
commands = []
checks = []


def sha(data):
    return hashlib.sha256(data).hexdigest()


def check(label, condition):
    assert condition, label
    checks.append(label)


def call(label, command, source, options, code, output=None):
    option_arg = '@' + str(options) if isinstance(options, Path) else json.dumps(options)
    argv = ['node', str(ROOT / 'tools/touchstone.mjs'), command, str(source), option_arg]
    if output is not None:
        argv.append(str(output))
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=30)
    number = len(commands) + 1
    (WORK / f'{number:02d}.stdout.log').write_bytes(result.stdout)
    (WORK / f'{number:02d}.stderr.log').write_bytes(result.stderr)
    commands.append({'label': label, 'command': argv, 'exitCode': result.returncode,
                     'expectedExitCode': code, 'stdoutSha256': sha(result.stdout),
                     'stderrSha256': sha(result.stderr)})
    check(label + ': exact exit', result.returncode == code)
    check(label + ': stdout/stderr contract',
          (not result.stdout and bool(result.stderr)) if code == 2 else not result.stderr)
    if output is not None and code != 2:
        check(label + ': file output only', not result.stdout and output.is_file())
        return output.read_bytes()
    return result.stdout


def save_json(name, value):
    path = WORK / name
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='ascii')
    return path


def state_counts(result, finite, zero, singular):
    counts = result['report']['state_counts']
    expected = {'finite': finite, 'zero': zero, 'singular': singular,
                'underflow': 0, 'overflow': 0}
    return set(counts) <= set(expected) and all(counts.get(k, 0) == n for k, n in expected.items())


def mismatch(label, source, saved, kind, input_match):
    result = json.loads(call(label, 'gain-review', source, saved, 5))
    check(label + ': mismatch classification', result['status'] == kind
          and result['input_match'] == input_match)
    if not input_match:
        check(label + ': no network parse or result comparison',
              result['result_match'] is None and result['current_result'] is None
              and result['current_status'] is None and result['changed_sections'] == [])
    else:
        check(label + ': result compared', result['result_match'] is False)
    return result


failure = None
try:
    # Row-major S11,S12,S21,S22 with explicit 12_21 order. All quantities are
    # real here. S12=S22=GL=0, so GT=(1-GS^2)*S21^2/(1-S11*GS)^2.
    pairs = [(0, 2), (0, 0), (2, 1), (0, 1)]
    gs = Fraction(1, 2)
    expected = []
    for s11, s21 in pairs:
        denominator = (1 - s11 * gs) ** 2
        expected.append((1 - gs * gs) * s21 * s21 / denominator if denominator else None)
    check('independent exact hand values', expected == [Fraction(3), Fraction(0), None, Fraction(3, 4)])
    lines = ['[Version] 2.1', '# Hz S RI R 50', '[Number of Ports] 2',
             '[Number of Frequencies] 4', '[Two-Port Data Order] 12_21', '[Network Data]']
    lines += [f'{(i + 1) * 1000000000} {s11} 0 0 0 {s21} 0 0 0'
              for i, (s11, s21) in enumerate(pairs)]
    lines += ['[End]', '']
    raw = '\r\n'.join(lines).encode('ascii')
    source = WORK / 'fresh gain input.ts'
    source.write_bytes(raw)
    options = {'source': [0.5, 0], 'load': [0, 0], 'start_hz': 1e9, 'end_hz': 4e9,
               'minimum_db': -2, 'maximum_db': 5}
    receipt_path = WORK / 'recorded fail.json'
    receipt_bytes = call('record sampled fail', 'gain-record', source, options, 3, receipt_path)
    receipt = json.loads(receipt_bytes)
    check('receipt v1 envelope', set(receipt) == {'schema', 'input', 'request', 'result'}
          and receipt['schema'] == 'touchstone.gain-receipt.v1')
    check('actual CRLF byte identity', receipt['input'] == {'sha256': sha(raw), 'bytes': len(raw)})
    check('effective recorded conditions', receipt['request']['command'] == 'gain-check'
          and receipt['request']['terminal_mode'] == 'gamma'
          and all(receipt['request'][key] == value for key, value in options.items()))
    result = receipt['result']
    check('independent summary', result['status'] == result['report']['status'] == 'fail'
          and result['report']['sample_count'] == 4 and state_counts(result, 2, 1, 1)
          and result['report']['below_minimum_count'] == 1
          and result['report']['above_maximum_count'] == 0
          and result['report']['range_covered'] is True)
    replay = json.loads(call('reproduce sampled fail', 'gain-review', source, receipt_path, 0))
    check('reproduced is distinct from sampled pass', replay['status'] == 'reproduced'
          and replay['recorded_status'] == replay['current_status'] == 'fail'
          and replay['input_match'] is True and replay['result_match'] is True
          and replay['current_result'] == result and replay['changed_sections'] == [])

    csv_path = WORK / 'sampled fail.csv'
    csv_bytes = call('export sampled fail CSV', 'gain-csv', source, options, 3, csv_path)
    check('raw CSV wire bytes', csv_bytes.endswith(b'\n') and b'\r' not in csv_bytes
          and not csv_bytes.startswith(b'\xef\xbb\xbf'))
    reader = csv.DictReader(io.StringIO(csv_bytes.decode('ascii'), newline=''))
    rows = list(reader)
    check('complete CSV schema and rows', reader.fieldnames == HEADERS and len(rows) == 4
          and all(set(row) == set(HEADERS) and None not in row.values() for row in rows))
    for i, (row, gain, state, disposition) in enumerate(zip(
            rows, expected, ['finite', 'zero', 'singular', 'finite'],
            ['pass', 'fail', 'unknown', 'pass'])):
        check(f'row {i}: original sample and band', int(row['point']) == i
              and float(row['frequency_hz']) == (i + 1) * 1e9
              and float(row['start_hz']) == 1e9 and float(row['end_hz']) == 4e9
              and float(row['minimum_db']) == -2 and float(row['maximum_db']) == 5
              and row['report_status'] == 'fail' and row['range_covered'] == 'true')
        check(f'row {i}: independent state', row['state'] == state and row['sample_status'] == disposition)
        if gain is None:
            check(f'row {i}: undefined is blank and unknown', all(row[key] == ''
                  for key in ['gain', 'gain_db', 'below_minimum', 'above_maximum']))
        elif gain == 0:
            check(f'row {i}: exact zero is not undefined', float(row['gain']) == 0 and row['gain_db'] == ''
                  and row['below_minimum'] == 'true' and row['above_maximum'] == 'false')
        else:
            check(f'row {i}: independent GT and dB',
                  math.isclose(float(row['gain']), float(gain), rel_tol=2e-12, abs_tol=2e-12)
                  and math.isclose(float(row['gain_db']), 10 * math.log10(float(gain)),
                                   rel_tol=2e-12, abs_tol=2e-12)
                  and row['below_minimum'] == row['above_maximum'] == 'false')

    lf_source = WORK / 'equivalent LF.ts'
    lf_source.write_bytes(raw.replace(b'\r\n', b'\n'))
    mismatch('equivalent network different raw bytes', lf_source, receipt_path, 'input_mismatch', False)
    invalid = WORK / 'same size invalid network.ts'
    invalid.write_bytes(b'X' + raw[1:])
    check('invalid mutation preserves length', invalid.stat().st_size == len(raw))
    mismatch('identity precedes invalid network parse', invalid, receipt_path, 'input_mismatch', False)

    changed = copy.deepcopy(receipt)
    changed['result']['status'] = 'pass'
    compared = mismatch('result status tamper', source, save_json('changed result.json', changed),
                        'result_mismatch', True)
    check('result status tamper independent truth', compared['current_status'] == 'fail'
          and compared['changed_sections'] == ['status'])
    changed = copy.deepcopy(receipt)
    changed['request']['source'] = [0, 0]
    compared = mismatch('source condition tamper', source, save_json('changed condition.json', changed),
                        'result_mismatch', True)
    check('source condition recomputed instead of trusted',
          set(compared['changed_sections']) == {'matching', 'report'}
          and compared['current_result']['matching']['source'] == [0, 0]
          and state_counts(compared['current_result'], 3, 1, 0)
          and compared['current_result']['report']['above_maximum_count'] == 1)

    for command, output, original in [('gain-record', receipt_path, receipt_bytes),
                                      ('gain-csv', csv_path, csv_bytes)]:
        call(command + ' occupied output', command, source, options, 2, output)
        check(command + ': existing output preserved byte-for-byte', output.read_bytes() == original)
    check('original input preserved byte-for-byte', source.read_bytes() == raw)
except Exception as exc:
    failure = exc
finally:
    report = {'status': 'passed' if failure is None else 'failed',
              'failure': repr(failure) if failure is not None else None,
              'oracle': 'Fresh handwritten four-point S network; exact Fraction power formula, math.log10, hashlib and csv.DictReader; no historical receipt/fixture or product result supplies expected gains',
              'actualCLIProcesses': len(commands), 'checks': checks, 'commands': commands,
              'sourceSha256': {name: sha((ROOT / name).read_bytes()) for name in
                               ['tools/verify-gain-file-chain.py', 'tools/touchstone.mjs',
                                'cmd/bridge/main.mbt', 'gain.mbt', 'gain_csv.mbt']},
              'compiledBridgeSha256': sha((ROOT / '_build/js/release/build/cmd/bridge/bridge.js').read_bytes()),
              'artifacts': [{'path': str(path), 'sha256': sha(path.read_bytes())}
                            for path in sorted(WORK.iterdir()) if path.is_file()]}
    args.evidence.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: report[key] for key in ['status', 'failure', 'actualCLIProcesses']}
                     | {'checkCount': len(checks)}, indent=2))
if failure is not None:
    raise failure
