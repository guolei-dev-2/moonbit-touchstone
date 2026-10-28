"""Independent near-unit source NF oracle; Python stdlib only, not runtime code."""
import argparse
import hashlib
import json
import math
import subprocess
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reference(source):
    x, y = map(Fraction, source)
    margin = 1 - x*x - y*y
    result = {'exact_margin_fraction': str(margin)}
    if margin > 0:
        with localcontext() as ctx:
            ctx.prec = 160
            power = Decimal(margin.numerator) / Decimal(margin.denominator)
            # Direct input noise parameters: Fmin=1 dB, Gamma_opt=0,
            # Rn=50 ohm and Zref=50 ohm. No covariance round-trip or hypot.
            factor = Decimal(10)**(Decimal(1)/10) + 4*(1-power)/power
            result['expected_figure_db'] = str(10*factor.log10())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--before', type=Path, help='Optional immutable round-20 BASELINE.json')
    args = parser.parse_args()
    assert not args.evidence.exists(), 'choose a new evidence path'
    cases_dir = args.evidence.with_suffix('.cases')
    cases_dir.mkdir(parents=True, exist_ok=False)
    input_path = ROOT/'examples/noise-source.s2p'
    bridge = ROOT/'_build/js/release/build/cmd/bridge/bridge.js'
    source_paths = ['noise.mbt', 'gain.mbt', 'noise_source_test.mbt', 'cmd/bridge/main.mbt', 'tools/touchstone.mjs', 'tools/verify-noise-source.py', 'examples/noise-source.s2p', 'examples/noise-source-options.json']
    report = {'complete': False, 'failure': None, 'oracle': 'Fraction exact binary64 source components and Decimal precision 160, direct original noise-parameter relation', 'absoluteToleranceDb': 2e-11, 'sourceSHA256': {p: sha(ROOT/p) for p in source_paths}, 'bridgeSHA256': sha(bridge), 'inputSHA256': sha(input_path), 'commands': [], 'checks': [], 'oldCollectionsRerun': False, 'newManufacturerInputs': 0}
    cases = [
        ('matched', [0.0, 0.0]),
        ('rounded-unit-legal', [1.0-2.0**-53, math.nextafter(2.0**-26, 0.0)]),
        ('accepted-near-unit', [0.6, math.nextafter(0.8, 0.0)]),
        ('unit', [1.0, 0.0]),
        ('outside-adjacent', [1.0-2.0**-53, 2.0**-26]),
        ('axis-subnormal-outside', [1.0, math.ulp(0.0)]),
    ]
    outputs = []
    try:
        for name, source in cases:
            ref = reference(source)
            options = cases_dir/(name+'.options.json')
            options.write_text(json.dumps({'source': source, 'figure_db': 3.0})+'\n', encoding='ascii')
            command = ['node', str(ROOT/'tools/touchstone.mjs'), 'noise', str(input_path), '@'+str(options)]
            run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
            stdout_path, stderr_path = cases_dir/(name+'.stdout.log'), cases_dir/(name+'.stderr.log')
            stdout_path.write_text(run.stdout, encoding='utf-8')
            stderr_path.write_text(run.stderr, encoding='utf-8')
            expected_exit = 0 if Fraction(ref['exact_margin_fraction']) > 0 else 2
            row = {'name': name, 'source': source, **ref, 'command': command, 'exitCode': run.returncode, 'expectedExitCode': expected_exit, 'stdout': str(stdout_path), 'stderr': str(stderr_path)}
            report['commands'].append(row)
            assert run.returncode == expected_exit, (name, run.stdout, run.stderr)
            if expected_exit == 0:
                payload = json.loads(run.stdout)
                actual = payload['figure_db'][0]
                assert math.isfinite(actual)
                error = abs(Decimal.from_float(actual) - Decimal(ref['expected_figure_db']))
                assert error < Decimal('2e-11'), (name, actual, ref)
                row.update(actualFigureDb=actual, absoluteErrorDb=str(error))
                outputs.append((name, run.stdout, payload))
            else:
                assert run.stdout == ''
                assert 'noise figure requires |Gamma_source|<1' in run.stderr, (name, run.stderr)
        report['checks'].append('Three finite legal figures agree with independent direct-parameter oracle')
        report['checks'].append('Unit, exact adjacent outside, and axis-plus-subnormal outside sources reject with the domain error')
        shared = [{k: v for k, v in payload.items() if k != 'figure_db'} for _, _, payload in outputs]
        assert all(payload == shared[0] for payload in shared)
        report['checks'].append('Source-independent covariance matrices and circles are identical for all three legal requests')
        report['baselineCompared'] = args.before is not None
        if args.before:
            before = json.loads(args.before.read_text(encoding='utf-8'))
            assert before['input_sha256'] == sha(input_path)
            report['checks'].append('The actual CLI input bytes equal the before-repair input')
            old_matched = next(x for x in before['records'] if x['name'] == 'matched')
            assert outputs[0][1] == old_matched['stdout']
            report['checks'].append('The complete ordinary matched CLI output is byte-identical to before repair')
        report['complete'] = True
    except Exception as error:
        report['failure'] = repr(error)
        raise
    finally:
        report['actualNodeProcesses'] = len(report['commands'])
        report['consumerChecks'] = len(report['checks'])
        args.evidence.parent.mkdir(parents=True, exist_ok=True)
        args.evidence.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print(json.dumps({'complete': report['complete'], 'actualNodeProcesses': report['actualNodeProcesses'], 'consumerChecks': report['consumerChecks']}))


if __name__ == '__main__':
    main()
