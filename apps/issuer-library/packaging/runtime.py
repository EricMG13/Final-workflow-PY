"""Bundle official Python and pinned wheels; verify every downloaded SHA-256."""
import hashlib
import json
import shutil
import urllib.request
import zipfile
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
ROOT = APP.parents[1]
CACHE = ROOT / 'artifacts/issuer-library/runtime-cache'
# The server and the engine share one runtime: pydantic for records, FastAPI and uvicorn for
# the loopback service, the parsers for sources. Versions match uv.lock.
PINS = {'pydantic':'2.14.1','pydantic-core':'2.50.1','annotated-types':'0.8.0',
        'typing-extensions':'4.16.0','typing-inspection':'0.4.4','pypdf':'6.21.2',
        'openpyxl':'3.1.5','et-xmlfile':'2.0.0','fastapi':'0.162.0','starlette':'1.10.0',
        'uvicorn':'0.54.0','python-multipart':'0.0.33','anyio':'4.16.0','idna':'3.20',
        'h11':'0.16.0','click':'8.5.0','annotated-doc':'0.0.5','opentelemetry-api':'1.45.2'}
PYTHON = {'amd64':'d1f04d990aee1253d8569e8e5104e30fa9f5fa830899f14843448872d936a2cf',
          'arm64':'cd992cbfb33be433ff20f150691595efb2862e56f4f1bec684c6077d4775af8e'}
# Double-click start: the windowless interpreter serves the library; errors show a message box.
LAUNCHER = ('@echo off\r\n'
            'start "Issuer Library" "%~dp0engine\\runtime\\pythonw.exe" -I -B -X utf8 -m issuer_library %*\r\n')

def download(url, sha, name):
    CACHE.mkdir(parents=True, exist_ok=True)
    target = CACHE / name
    if not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest()!=sha:
        with urllib.request.urlopen(url,timeout=90) as response:
            raw=response.read(100<<20)
        if hashlib.sha256(raw).hexdigest()!=sha:
            raise ValueError(f'Checksum mismatch: {name}')
        target.write_bytes(raw)
    return target


def bundle(target, architecture):
    engine=target/'engine';engine.mkdir(exist_ok=True)
    for name in ['bridge.py','store.py','catalog.json']:
        shutil.copyfile(APP/'engine'/name,engine/name)
    shutil.copyfile(ROOT/'cases/context/research-minimal.json',engine/'smoke-context.json')
    shutil.copyfile(APP/'packaging/Smoke-test.ps1',target/'Smoke-test.ps1')
    (target/'Issuer Library.cmd').write_bytes(LAUNCHER.encode())
    if (engine/'src').exists(): shutil.rmtree(engine/'src')
    shutil.copytree(ROOT/'src',engine/'src',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    # The launcher reads each module's method from these, relative to the engine folder.
    for name in ['docs/reuse/selected-methods','docs/visualisations','prompts']:
        if (engine/name).exists(): shutil.rmtree(engine/name)
        shutil.copytree(ROOT/name,engine/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    # The front end beside the engine, as the server finds it in the repository.
    if (target/'web').exists(): shutil.rmtree(target/'web')
    shutil.copytree(APP/'web',target/'web')
    runtime=engine/'runtime';runtime.mkdir(exist_ok=True)
    # The same pinned runtime from an earlier build needs no download.
    manifest=engine/'runtime-manifest.json'
    if manifest.exists() and (runtime/'python.exe').exists():
        records=json.loads(manifest.read_text())
        if records['python']['sha256']==PYTHON[architecture] and {k:v['version'] for k,v in records['wheels'].items()}==PINS:
            print('Reusing the pinned Python engine for',architecture,flush=True)
            return
    filename=f'python-3.13.15-embed-{architecture}.zip'
    source=download('https://www.python.org/ftp/python/3.13.15/'+filename,PYTHON[architecture],filename)
    with zipfile.ZipFile(source) as archive: archive.extractall(runtime)
    site=runtime/'Lib/site-packages';site.mkdir(parents=True,exist_ok=True)
    records={'python':{'version':'3.13.15','sha256':PYTHON[architecture]},'wheels':{}}
    tag='win_amd64' if architecture=='amd64' else 'win_arm64'
    for name,version in PINS.items():
        with urllib.request.urlopen(f'https://pypi.org/pypi/{name}/{version}/json',timeout=45) as response:
            metadata=json.load(response)
        matches=[item for item in metadata['urls'] if item['filename'].endswith('.whl') and
                 (item['filename'].endswith('-none-any.whl') or
                  ('-cp313-' in item['filename'] and item['filename'].endswith('-'+tag+'.whl') and '-cp313t-' not in item['filename']))]
        if len(matches)!=1: raise ValueError(f'No unique pinned Windows wheel: {name} {version} {tag}')
        item=matches[0];wheel=download(item['url'],item['digests']['sha256'],item['filename'])
        with zipfile.ZipFile(wheel) as archive: archive.extractall(site)
        records['wheels'][name]={'version':version,'filename':item['filename'],'sha256':item['digests']['sha256']}
    # ..\src puts the server and engine packages on the path of the isolated interpreter.
    (runtime/'python313._pth').write_text('python313.zip\n.\nLib\\site-packages\n..\\src\nimport site\n')
    (engine/'runtime-manifest.json').write_text(json.dumps(records,indent=2)+'\n')
    print('Bundled pinned Python engine for',architecture,flush=True)

if __name__=='__main__':
    import sys
    bundle(Path(sys.argv[1]),sys.argv[2])
