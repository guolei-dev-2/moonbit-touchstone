"""Download one first-party NXP model archive for local verification only.

The manufacturer archive/data are NOT MIT project files.  raw-not-for-package
must be excluded from distributed source/evidence packages.  Reproduction
refuses an unexpected source hash when an expected digest is supplied.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import urllib.request
import urllib.parse
import zipfile

HERE = Path(__file__).resolve().parent
URL = 'https://www.nxp.com/downloads/en/s-parameters/BFU530W_Spar.zip'
parser = argparse.ArgumentParser()
parser.add_argument('--expected-sha256')
args = parser.parse_args()
private = Path('D:/CodexLocal/ban/work/portfolio-progress-20261027/private-reference-inputs/touchstone-breadth-20261027')
private.mkdir(parents=True, exist_ok=True)
target = private/'BFU530W_Spar.zip'
if target.exists(): raise FileExistsError(target)
request = urllib.request.Request(URL, headers={'User-Agent':'MoonTouchstone-local-reference/0.3'})
with urllib.request.urlopen(request, timeout=30) as response:
    final_url = response.geturl()
    assert urllib.parse.urlparse(final_url).hostname in ['www.nxp.com', 'nxp.com']
    data = response.read(2_000_001)
    assert len(data) <= 2_000_000
    status = response.status
    headers = dict(response.headers.items())
digest = hashlib.sha256(data).hexdigest()
if args.expected_sha256 and digest != args.expected_sha256:
    raise ValueError('NXP source changed; review rather than replacing expected data')
with target.open('xb') as f: f.write(data)
with zipfile.ZipFile(target) as z:
    entries = [dict(path=x.filename, bytes=x.file_size, crc32=f'{x.CRC:08x}',
                    sha256=hashlib.sha256(z.read(x)).hexdigest())
               for x in z.infolist() if not x.is_dir()]
report = dict(sourceURL=URL, finalURL=final_url, httpStatus=status, httpHeaders=headers,
              retrievedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              bytes=len(data), sha256=digest, entries=entries,
              manufacturer='NXP Semiconductors', device='BFU530W',
              productURL='https://www.nxp.com/products/radio-frequency-rf/legacy-rf/legacy-rf-wideband-transistors/npn-wideband-silicon-rf-transistor:BFU530W',
              modelListing='S-parameters 40 MHz - 6 GHz; rev1.0; 2019-04-23',
              termsURL='https://www.nxp.com/pages/terms-of-use:TERMSOFUSE',
              redistributionPermissionConfirmed=False, includedInProjectMIT=False,
              distributionExcludeDirectory=str(private))
with (HERE/'DOWNLOAD.json').open('x',encoding='utf-8',newline='\n') as f:
    json.dump(report,f,ensure_ascii=False,indent=2); f.write('\n')
print(json.dumps(report,ensure_ascii=False))
