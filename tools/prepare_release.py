#!/usr/bin/env python3
"""Prepare local beta artifacts and checksums. Never publishes or creates a tag."""
import gzip
import hashlib
import io
import os
import subprocess
import tarfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
os.chdir(root)
version='0.9.0-beta';prefix='veil-for-zen-'+version
out=root/'dist';out.mkdir(exist_ok=True)
# A fixed epoch makes repeated source archives byte-for-byte reproducible.
epoch=int(os.environ.get('SOURCE_DATE_EPOCH','1793577600'))
os.environ['SOURCE_DATE_EPOCH']=str(epoch)
subprocess.run([os.sys.executable,'tools/build.py','--wheel'],check=True)
files=[]
for base in ['veil_for_zen','packaging','tools','tests','docs']:
    files.extend(p for p in (root/base).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and 'src' not in p.relative_to(root).parts and 'pkg' not in p.relative_to(root).parts)
files.extend(root/name for name in ['README.md','CHANGELOG.md','CONTRIBUTING.md','pyproject.toml','requirements.txt','.gitignore','studio.py'])
files.extend(root/name for name in ['LICENSE','NOTICE.md'])
archive=out/(prefix+'.tar.gz')
with archive.open('wb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=epoch) as zipped,tarfile.open(fileobj=zipped,mode='w') as tar:
    for path in sorted(files):
        rel=path.relative_to(root)
        if path.is_symlink(): raise ValueError('Symlink in release: '+str(rel))
        content=path.read_bytes();info=tarfile.TarInfo(prefix+'/'+str(rel))
        info.size=len(content);info.mtime=epoch;info.uid=info.gid=0;info.uname=info.gname=''
        info.mode=0o755 if os.access(path,os.X_OK) else 0o644
        tar.addfile(info,io.BytesIO(content))
sha=hashlib.sha256(archive.read_bytes()).hexdigest()
(out/'PKGBUILD').write_text((root/'packaging/PKGBUILD').read_text().replace('PENDING_SOURCE_ARCHIVE',sha))
artifacts=[archive,out/'PKGBUILD',*sorted(out.glob('*.whl'))]
(out/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in artifacts))
print('Local beta artifacts ready. Clean-desktop validation is deferred; publishing requires authorization.')
