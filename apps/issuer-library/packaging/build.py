"""Build offline executables and pinned runtimes; never execute providers."""
import hashlib
import os
import shutil
import subprocess
import zipfile
from pathlib import Path

from runtime import bundle

APP = Path(__file__).resolve().parents[1]
OUTPUT = APP.parents[1] / 'artifacts/issuer-library'
ENV = os.environ | {'CGO_ENABLED': '0', 'GOTOOLCHAIN': 'local', 'GOPROXY': 'off', 'GOSUMDB': 'off'}
subprocess.run(['python3', str(APP / 'packaging/sync_assets.py')], check=True)
subprocess.run(['go', 'test', './...'], cwd=APP, env=ENV, check=True)
for system, architecture in [('windows', 'amd64'), ('windows', 'arm64'), ('darwin', 'arm64')]:
    target = OUTPUT / f'{system}-{architecture}'
    target.mkdir(parents=True, exist_ok=True)
    executable = target / ('Issuer Library.exe' if system == 'windows' else 'issuer-library')
    flags = '-s -w' + (' -H=windowsgui' if system == 'windows' else '')
    subprocess.run(['go', 'build', '-trimpath', '-buildvcs=false', '-ldflags', flags,
                    '-o', str(executable), '.'], cwd=APP,
                   env=ENV | {'GOOS': system, 'GOARCH': architecture}, check=True)
    bundle(target, architecture if system == "windows" else None)
    shutil.copyfile(APP / 'README.md', target / 'README.md')
    shutil.copyfile(APP / 'web/fonts/OFL.txt', target / 'FONT-LICENSE.txt')
    shutil.copyfile(APP / 'web/icons/LICENSE', target / 'ICON-LICENSE.txt')
    for document in ['DESIGN.md', 'DESIGN-SOURCES.md']:
        shutil.copyfile(APP / document, target / document)
    shutil.copyfile(APP / 'run-manifest.example.json', target / 'run-manifest.example.json')
    if system == 'windows':
        archive = OUTPUT / f'Issuer-Library-{architecture}.zip'
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as archive_handle:
            for file in sorted(target.rglob("*")):
                if file.is_file(): archive_handle.write(file, file.relative_to(target))
        print(archive)
    print(f'{hashlib.sha256(executable.read_bytes()).hexdigest()}  {executable.name} ({system}/{architecture})')
