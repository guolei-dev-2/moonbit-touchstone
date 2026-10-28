"""Reproduce the frozen NXP download outside distributed project directories."""
from pathlib import Path
import argparse
import hashlib
import subprocess
import urllib.parse
import zipfile

URL = 'https://www.nxp.com/downloads/en/s-parameters/BFU530W_Spar.zip'
EXPECTED = '981d4f80f7ee35d273ce7917708c9f8ffded52372e71dff0ec57f99e41f78928'
MEMBER = 'BFU530W_03V3_001mA_SP.s2p'
p = argparse.ArgumentParser()
p.add_argument('new_private_directory',type=Path)
a = p.parse_args()
a.new_private_directory.mkdir(parents=True,exist_ok=False)
archive = a.new_private_directory/'BFU530W_Spar.zip'
command=['curl.exe','--fail','--location','--max-time','30','--dump-header',str(a.new_private_directory/'download.headers.txt'),'--output',str(archive),URL]
subprocess.run(command,check=True)
assert hashlib.sha256(archive.read_bytes()).hexdigest()==EXPECTED,'Upstream bytes changed; do not silently replace expected data'
with zipfile.ZipFile(archive) as z: data=z.read(MEMBER)
with (a.new_private_directory/MEMBER).open('xb') as f:f.write(data)
print('Downloaded fixed first-party data. Keep this private directory out of distribution; NXP content is not MIT project code.')
