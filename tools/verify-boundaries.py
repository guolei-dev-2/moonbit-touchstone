"""Upper-port regression using NumPy eigvalsh and scikit-rf, not Cholesky.

Run after the JS release build. Synthetic fixtures only; writes a fresh receipt.
The historical reference suites and manufacturer inputs are not rerun.
"""
import argparse
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
import skrf as rf

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--evidence', type=Path, required=True)
args = parser.parse_args()
if args.evidence.exists():
    parser.error('receipt exists; choose a fresh path')
rng = np.random.default_rng(20261027)
records = []
host = subprocess.Popen(['node', 'tools/oracle-host.mjs'], cwd=ROOT,
                        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                        text=True, encoding='utf-8')


def text(net, kind='S'):
    n = net.nports
    lines = ['[Version] 2.1', f'# Hz {kind} RI R 50',
             f'[Number of Ports] {n}', '[Number of Frequencies] 1',
             '[Reference] ' + ' '.join(format(x.real, '.17g') for x in net.z0[0])]
    if n == 2:
        lines.append('[Two-Port Data Order] 12_21')
    lines += ['[Network Data]', '1 ' + ' '.join(format(v, '.17g')
              for z in getattr(net, kind.lower())[0].ravel() for v in [z.real, z.imag]), '[End]']
    return '\n'.join(lines) + '\n'


def ask(raw, command, reject=False, **options):
    query = dict(text=raw, options=dict(command=command, **options))
    host.stdin.write(json.dumps(query) + '\n')
    host.stdin.flush()
    line = host.stdout.readline()
    if not line:
        raise RuntimeError('MoonBit bridge stopped')
    response = json.loads(line)
    # Keep original IPC and input identity, including rejection/first failure.
    records.append(dict(command=command, options=options,
                        inputSHA256=hashlib.sha256(raw.encode()).hexdigest(), response=response))
    assert response['ok'] != reject, response
    return response.get('result')


def mat(d):
    return np.array([complex(z['re'], z['im']) for row in d['values']
                     for z in row]).reshape(-1, d['ports'], d['ports'])


def close(actual, expected):
    delta = float(np.max(np.abs(np.asarray(actual) - expected)))
    np.testing.assert_allclose(actual, expected, rtol=3e-8, atol=3e-9)
    return delta


summary = dict(complete=False, seed=20261027, passivity=[], mixed=[], rejections=0)
failure = None
try:
    tol = 1e-7
    for n in [1, 2, 16, 31, 32]:
        u = np.linalg.qr(rng.normal(size=(n, n)) + 1j*rng.normal(size=(n, n)))[0]
        v = np.linalg.qr(rng.normal(size=(n, n)) + 1j*rng.normal(size=(n, n)))[0]
        for gap in [4*tol, tol/4, 0.0, -tol/4, -4*tol]:
            singular = np.linspace(.1, .7, n)
            singular[-1] = np.sqrt(1-gap)
            s = (u * singular) @ v.conj().T
            h = np.eye(n) - s.conj().T @ s
            eigenvalue = float(np.linalg.eigvalsh(h).min())
            expected = 'passive' if eigenvalue > tol else 'active' if eigenvalue <= -tol else 'boundary'
            actual = ask(text(rf.Network(f=[1], s=s[None], z0=50)), 'diagnostics', tolerance=tol)[0]['passivity']
            assert actual == expected, (n, gap, eigenvalue, actual)
            summary['passivity'].append(dict(ports=n, gap=gap, minimumEigenvalue=eigenvalue, state=actual))
        # Coherent collective excitation can be active with every column norm <1.
        s = np.full((n, n), 2/n, dtype=complex) if n > 4 else np.eye(n, dtype=complex)
        state = 'active' if n > 4 else 'boundary'
        actual = ask(text(rf.Network(f=[1], s=s[None], z0=50)), 'diagnostics', tolerance=tol)[0]['passivity']
        assert actual == state
        summary['passivity'].append(dict(ports=n, fixture='collective gain or lossless', state=actual))
    for n, p in [(31, 15), (32, 16), (32, 1)]:
        perm = rng.permutation(n).tolist()
        pairs = [perm[2*i:2*i+2] for i in range(p)]
        order = sum(pairs, []) + [i for i in range(n) if i not in sum(pairs, [])]
        refs = np.full(n, 60.0)
        for i, pair in enumerate(pairs):
            refs[pair] = 35.0 + 5*i
        s = (rng.normal(size=(1, n, n)) + 1j*rng.normal(size=(1, n, n))) / (5*n)
        net = rf.Network(f=[1], s=s, z0=refs)
        reference = net.copy()
        reference.renumber(order, list(range(n)))
        reference.se2gmm(p)
        for kind in ['S', 'Y', 'Z']:
            out = ask(text(net, kind), 'mixed', pairs=pairs)
            error = close(mat(out['network']), getattr(reference, kind.lower()))
            close(out['network']['reference_ohms'], reference.z0[0].real)
            inverse_error = close(mat(ask(out['text'], 'single')), getattr(net, kind.lower()))
            summary['mixed'].append(dict(ports=n, pairs=p, representation=kind,
                                         maxAbsoluteError=error, inverseMaxAbsoluteError=inverse_error))
    raw = text(rf.Network(f=[1], s=np.zeros((1, 3, 3)), z0=[50, 50, 75]))
    for pairs in [[[0, 0]], [[0, 1], [1, 2]], [[0, 3]], [[0, 2]]]:
        ask(raw, 'mixed', reject=True, pairs=pairs)
        summary['rejections'] += 1
    for tolerance in [0.0, -1e-9, .02]:
        ask(raw, 'diagnostics', reject=True, tolerance=tolerance)
        summary['rejections'] += 1
    summary['complete'] = True
except Exception as exc:
    failure = exc
    summary['failure'] = repr(exc)
finally:
    host.stdin.close()
    host.wait(timeout=10)
    summary['requests'] = len(records)
    summary['versions'] = dict(python=platform.python_version(), numpy=np.__version__, scikit_rf=rf.__version__,
                               node=subprocess.check_output(['node', '--version'], text=True).strip())
    files = sorted(p for p in ROOT.rglob('*') if p.is_file() and
                   not any(x in p.parts for x in ['_build', '.git', '.mooncakes', 'evidence']) and
                   (p.suffix in ['.mbt', '.mbti', '.py', '.mjs'] or p.name in ['moon.mod', 'moon.pkg', '.moonbit-version']))
    summary['sourceSHA256'] = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    summary['bridgeSHA256'] = hashlib.sha256((ROOT/'_build/js/release/build/cmd/bridge/bridge.js').read_bytes()).hexdigest()
    summary['limits'] = ['Synthetic upper-port and boundary cases, not exhaustive numerical certification.',
                         'No vendor data or historical full suite rerun.',
                         'Exact +/-tolerance floating-point cutpoints are not certified.']
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(dict(summary=summary, rawIPC=records), indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in summary.items() if k != 'sourceSHA256'}, indent=2))
if failure:
    raise failure
