"""Compare a public MoonBit module consumer and real file CLI; stdlib oracle."""
import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--moon', default='moon')
    args = parser.parse_args()
    assert not args.evidence.exists(), 'choose a new evidence path'
    work = args.evidence.with_suffix('.cases')
    work.mkdir(parents=True, exist_ok=False)
    sources = ['examples/one_port_metrics/main.mbt', 'examples/one_port_metrics/moon.pkg', 'analysis.mbt', 'conversion.mbt', 'versioned.mbt', 'cmd/bridge/main.mbt', 'tools/touchstone.mjs', 'tools/verify-one-port-consumer.py']
    bridge = ROOT/'_build/js/release/build/cmd/bridge/bridge.js'
    report = {'complete': False, 'failure': None, 'sourceSHA256': {p: sha(ROOT/p) for p in sources}, 'bridgeSHA256': sha(bridge), 'commands': [], 'checks': [], 'moduleRuntimeExecutions': 0, 'fileCLINodeProcesses': 0, 'pairedSamples': 0, 'oldCollectionsRerun': False, 'newManufacturerInputs': 0, 'oracle': 'Independent scalar Gamma=(Z-50)/(Z+50), input physical ohms; magnitude/log and documented finite/infinite/active state conventions', 'tolerance': {'relative': 2e-12, 'absolute': 2e-12}}

    def run(name, command):
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
        for stream in ['stdout', 'stderr']:
            (work/(name+'.'+stream+'.log')).write_text(getattr(result, stream), encoding='utf-8')
        report['commands'].append({'name': name, 'command': command, 'exitCode': result.returncode, 'stdout': str(work/(name+'.stdout.log')), 'stderr': str(work/(name+'.stderr.log'))})
        assert result.returncode == 0, (name, result.stdout, result.stderr)
        return json.loads(result.stdout)

    def close(actual, expected):
        assert isinstance(actual, (int, float)) and not isinstance(actual, bool) and math.isfinite(actual)
        assert math.isclose(actual, expected, rel_tol=2e-12, abs_tol=2e-12), (actual, expected)

    try:
        report['moduleRuntimeExecutions'] += 1
        api = run('module', [args.moon, 'run', 'examples/one_port_metrics', '--target', 'js'])
        report['checks'].append('Public-module example imports, parses and executes metrics(0,0) on JS')
        text = api['input_text']
        input_path = work/'same-input.s1p'
        input_path.write_bytes(text.encode('ascii'))
        assert input_path.read_bytes() == text.encode('ascii')
        report['inputSHA256'] = sha(input_path)
        report['inputBytes'] = len(input_path.read_bytes())
        report['checks'].append('The file CLI receives the exact ASCII input emitted by the module consumer')
        report['fileCLINodeProcesses'] += 1
        cli = run('file-cli', ['node', str(ROOT/'tools/touchstone.mjs'), 'metrics', str(input_path), '{"input":0,"output":0}'])
        assert cli == api['metrics']
        report['checks'].append('Complete parsed metric JSON arrays match, including omitted Option fields and all states')
        loads = [0j, 50+0j, 150+0j, -150+0j, 50+50j]
        assert len(cli) == len(loads) == 5
        report['pairedSamples'] = len(cli)
        expected = []
        for i, (row, load) in enumerate(zip(cli, loads)):
            gamma = (load-50)/(load+50)
            magnitude = abs(gamma)
            close(row['frequency_hz'], (i+1)*1e9)
            close(row['reflection_magnitude'], magnitude)
            close(row['transmission_magnitude'], magnitude)
            infinite_loss = magnitude == 0
            assert row['return_loss_infinite'] == row['insertion_loss_infinite'] == infinite_loss
            for field in ['return_loss_db', 'insertion_loss_db']:
                if infinite_loss:
                    assert field not in row
                else:
                    close(row[field], -20*math.log10(magnitude))
            state = 'finite' if magnitude < 1 else ('infinite' if magnitude == 1 else 'active')
            assert row['vswr_state'] == state
            if state == 'finite':
                close(row['vswr'], (1+magnitude)/(1-magnitude))
            else:
                assert 'vswr' not in row
            expected.append({'frequency_hz': (i+1)*1e9, 'impedance_ohms': [load.real, load.imag], 'gamma': [gamma.real, gamma.imag], 'magnitude': magnitude, 'infiniteLoss': infinite_loss, 'vswrState': state})
        report['independentExpected'] = expected
        report['checks'].extend(['All five physical-ohm reflection magnitudes and sample frequencies match independent scalar relations', 'Finite dB and infinite-loss flags/omitted fields match independent expected values', 'Finite, unit-circle infinite and active undefined VSWR values/states/omitted fields remain distinct'])
        report['complete'] = True
    except Exception as error:
        report['failure'] = repr(error)
        raise
    finally:
        report['consumerChecks'] = len(report['checks'])
        args.evidence.parent.mkdir(parents=True, exist_ok=True)
        args.evidence.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print(json.dumps({'complete': True, 'moduleRuntimeExecutions': report['moduleRuntimeExecutions'], 'fileCLINodeProcesses': report['fileCLINodeProcesses'], 'pairedSamples': report['pairedSamples'], 'consumerChecks': report['consumerChecks']}))


if __name__ == '__main__':
    main()
