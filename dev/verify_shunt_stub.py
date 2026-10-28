"""Independent standard-library ABCD validation of actual MoonBit consumer JSON.

No synthesis/root-finding formula is used. Hand angles come from the independent
pre-implementation acceptance note; complex cases are checked only forwards.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path

PI = math.pi
ANGLE_TOL = 2e-12
GAMMA_TOL = 2e-11
Z_TOL = 1e-10


def angle_error(a: float, b: float) -> float:
    return abs((a - b + PI / 2) % PI - PI / 2)


def pairs_equal(actual, expected) -> bool:
    return any(all(angle_error(a[0], b[0]) <= ANGLE_TOL and
                       angle_error(a[1], b[1]) <= ANGLE_TOL
                       for a, b in zip(actual, order))
               for order in itertools.permutations(expected))


def hand_pairs(name: str, kind: str):
    alpha = math.atan(math.sqrt(2))
    beta = math.atan(1 / math.sqrt(2))
    if name == 'r100':
        distances = [alpha, PI - alpha]
        lengths = [PI - beta, beta] if kind == 'open' else [alpha, PI - alpha]
    elif name == 'r25':
        distances = [beta, PI - beta]
        lengths = [beta, PI - beta] if kind == 'open' else [PI - alpha, alpha]
    elif name in ('quarter_wave', 'complex_hand'):
        distances = ([PI / 2, PI - math.atan(0.5)] if name == 'quarter_wave'
                     else [math.atan(3), 3 * PI / 4])
        lengths = [3 * PI / 4, PI / 4] if kind == 'open' else [PI / 4, 3 * PI / 4]
    else:
        return None
    return list(zip(distances, lengths))


def forward(load: complex, z0: float, theta: float, phi: float, kind: str):
    """Physical ABCD M=P*L, then physical Zin and input Gamma."""
    c, s = math.cos(theta), math.sin(theta)
    bs = math.tan(phi) if kind == 'open' else -1 / math.tan(phi)
    line = ((complex(c), 1j * z0 * s), (1j * s / z0, complex(c)))
    shunt = ((1 + 0j, 0j), (1j * bs / z0, 1 + 0j))
    m = [[sum(shunt[i][k] * line[k][j] for k in range(2))
          for j in range(2)] for i in range(2)]
    zin = (m[0][0] * load + m[0][1]) / (m[1][0] * load + m[1][1])
    gamma = (zin - z0) / (zin + z0)
    return zin, gamma


def complex_value(value):
    return complex(value['re'], value['im'])


def reject_nonfinite(value):
    if isinstance(value, dict):
        for item in value.values():
            reject_nonfinite(item)
    elif isinstance(value, list):
        for item in value:
            reject_nonfinite(item)
    elif isinstance(value, float):
        assert math.isfinite(value), 'nonfinite JSON number'


def validate(path: Path):
    raw = path.read_bytes()
    data = json.loads(raw.decode('utf-8'), parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
    reject_nonfinite(data)
    assert len(data) == 38
    state_counts = {}
    discrete = family_samples = hand = 0
    max_gamma = max_z_error = max_network_delta = 0.0
    keyed = {}
    numeric = {'subnormal_mismatch', 'unresolved_scale', 'rounded_stub_pole', 'strict_tolerance'}
    no_solution = {'short_load', 'reactive_load', 'reactive_negative'}
    for record in data:
        name = record['case']
        result = record['synthesis']
        kind = result['termination']
        key = (name, kind)
        assert kind in ('open', 'short') and key not in keyed
        keyed[key] = result
        expected = ('numerical_limit' if name in numeric else 'no_solution' if name in no_solution
                    else 'already_matched' if name == 'matched' else 'finite')
        assert result['state'] == expected, (key, result['state'], expected)
        state_counts[expected] = state_counts.get(expected, 0) + 1
        assert result['distance_period_radians'] == PI and result['stub_period_radians'] == PI
        assert result['detail']
        solutions = result['solutions']
        checks = record['network_checks']
        load, z0 = complex_value(result['load_ohms']), result['reference_ohms']
        if expected == 'finite':
            assert len(solutions) == len(checks) == 2 and result['free_distance_family'] is None
            assert solutions[0]['distance_radians'] < solutions[1]['distance_radians']
            pairs = [(x['distance_radians'], x['stub_radians']) for x in solutions]
            expected_pairs = hand_pairs(name, kind)
            if expected_pairs is not None:
                assert pairs_equal(pairs, expected_pairs), (key, pairs, expected_pairs)
                hand += 2
            if name == 'zero_distance':
                assert min(angle_error(theta, 0) for theta, _ in pairs) < ANGLE_TOL
            for solution, check in zip(solutions, checks):
                theta, phi = solution['distance_radians'], solution['stub_radians']
                assert 0 <= theta < PI and 0 <= phi < PI
                assert phi != (PI / 2 if kind == 'open' else 0)
                assert solution['distance_lambda_g'] == theta / (2 * PI)
                assert solution['stub_lambda_g'] == phi / (2 * PI)
                assert 0 <= solution['normalized_admittance_error'] <= result['tolerance']
                assert theta == check['distance_radians'] and phi == check['stub_radians']
                discrete += 1
        elif expected == 'already_matched':
            assert not solutions and len(checks) == 5
            family = result['free_distance_family']
            assert family['distance_min_radians'] == 0 and family['distance_max_exclusive_radians'] == PI
            assert family['stub_radians'] == (0 if kind == 'open' else PI / 2)
            assert family['stub_lambda_g'] == (0 if kind == 'open' else 0.25)
            for check in checks:
                assert check['stub_radians'] == family['stub_radians']
            family_samples += len(checks)
        else:
            assert not solutions and not checks and result['free_distance_family'] is None
        for check in checks:
            zin, gamma = forward(load, z0, check['distance_radians'], check['stub_radians'], kind)
            z_error = abs(zin / z0 - 1)
            network_gamma = complex_value(check['s11'])
            delta = abs(network_gamma - gamma)
            assert abs(gamma) <= GAMMA_TOL and z_error <= Z_TOL, (key, zin, gamma)
            assert abs(network_gamma) <= GAMMA_TOL and delta <= GAMMA_TOL, (key, network_gamma, gamma)
            assert abs(check['reflection_magnitude'] - abs(network_gamma)) <= 1e-25
            metrics = check['metrics']
            assert metrics['vswr_state'] == 'finite' and abs(metrics['vswr'] - 1) <= 1e-9
            if network_gamma == 0:
                # Existing derived SignalMetric JSON omits absent Option keys.
                assert metrics['return_loss_infinite'] and metrics.get('return_loss_db') is None
            else:
                assert not metrics['return_loss_infinite'] and math.isfinite(metrics['return_loss_db'])
            max_gamma = max(max_gamma, abs(gamma), abs(network_gamma))
            max_z_error = max(max_z_error, z_error)
            max_network_delta = max(max_network_delta, delta)
    return keyed, {'input': str(path.resolve()), 'inputSha256': hashlib.sha256(raw).hexdigest(),
                   'caseEndTypeResults': len(data), 'states': state_counts,
                   'discreteSolutions': discrete, 'matchedFamilyForwardSamples': family_samples,
                   'handAnglePairs': hand, 'forwardNetworkChecks': discrete + family_samples,
                   'maxReflectionMagnitude': max_gamma, 'maxNormalizedImpedanceError': max_z_error,
                   'maxNetworkVsIndependentGammaDelta': max_network_delta}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    results, reports = [], []
    for path in args.input:
        keyed, report = validate(path)
        results.append(keyed)
        reports.append(report)
    cross_pairs = 0
    for other in results[1:]:
        assert results[0].keys() == other.keys()
        for key, first in results[0].items():
            second = other[key]
            assert first['state'] == second['state']
            if first['state'] == 'finite':
                a = [(s['distance_radians'], s['stub_radians']) for s in first['solutions']]
                b = [(s['distance_radians'], s['stub_radians']) for s in second['solutions']]
                assert pairs_equal(a, b), (key, a, b)
                cross_pairs += 2
    report = {'status': 'passed', 'oracle': 'Python standard-library physical ABCD; no synthesis solver',
              'tolerances': {'angleRadiansModuloPi': ANGLE_TOL, 'reflectionMagnitude': GAMMA_TOL,
                             'normalizedImpedanceError': Z_TOL},
              'runs': reports, 'crossBackendSolutionPairs': cross_pairs,
              'limits': 'Bounded cases, analytical ideal lines; no fabricated hardware or full Double-domain certification'}
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
