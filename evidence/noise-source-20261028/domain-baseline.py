import json
import subprocess
from fractions import Fraction
from pathlib import Path
from reproduce import OUT, ROOT, BRIDGE, sha, save

assert not (OUT/'DOMAIN-BASELINE.json').exists()
assert sha(BRIDGE) == json.loads((OUT/'COMPILED-BEFORE.json').read_text())['sha256']
source = [1.0-2.0**-53, 2.0**-26]
margin = 1 - sum(Fraction(x)**2 for x in source)
assert margin < 0
options = OUT/'outside-adjacent.options.json'
save(options, {'source': source, 'figure_db': 3.0})
run = subprocess.run(['node', str(ROOT/'tools/touchstone.mjs'), 'noise', str(OUT/'source-noise.s2p'), '@'+str(options)], cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
(OUT/'outside-adjacent.before.stdout.log').write_text(run.stdout, encoding='utf-8')
(OUT/'outside-adjacent.before.stderr.log').write_text(run.stderr, encoding='utf-8')
save(OUT/'DOMAIN-BASELINE.json', {'source': source, 'exact_margin_fraction': str(margin), 'expected': 'reject: source is strictly outside unit circle', 'exit': run.returncode, 'stdout': run.stdout, 'stderr': run.stderr, 'bridge_sha256': sha(BRIDGE)})
print('exact margin:', margin, 'exit:', run.returncode, 'output:', run.stdout.strip(), run.stderr.strip())
