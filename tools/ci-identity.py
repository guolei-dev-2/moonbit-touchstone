"""Record actual tool versions and source identity for the current CI checkout."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()


def command(*argv):
    return subprocess.check_output(argv, cwd=ROOT, text=True, encoding='utf-8').strip()


compiler = command('moonc', '-v')
pinned = (ROOT / '.moonbit-version').read_text(encoding='utf-8').strip()
assert compiler.split()[0] == 'v' + pinned, (compiler, pinned)
paths = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode('utf-8').split('\0')
sources = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
           for name in paths if name}
result = {
    'recordedAtUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'commit': command('git', 'rev-parse', 'HEAD'),
    'gitTree': command('git', 'rev-parse', 'HEAD^{tree}'),
    'moon': command('moon', 'version', '--all'),
    'moonc': compiler,
    'node': command('node', '--version'),
    'python': platform.python_version(),
    'platform': platform.platform(),
    'requirementsSha256': hashlib.sha256((ROOT / 'tools/requirements.txt').read_bytes()).hexdigest(),
    'sourceSha256': sources,
}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps({key: value for key, value in result.items() if key != 'sourceSha256'}, indent=2))
