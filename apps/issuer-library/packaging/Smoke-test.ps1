# Offline Windows runtime and CP-OS review smoke. Never starts a model run.
$ErrorActionPreference = 'Stop'
$Python = 'C:\Program Files\Statestreet\Python313\python.exe'
$Bridge = Join-Path $PSScriptRoot 'engine\bridge.py'
$Store = Join-Path $PSScriptRoot 'engine\store.py'
$TemporaryRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('IssuerLibrarySmoke-' + [char]0xE9 + '-' + [guid]::NewGuid().ToString('N'))
try {
  New-Item -ItemType Directory -Path $TemporaryRoot | Out-Null
  $Script = @'
import hashlib,json,pathlib,sys
root=pathlib.Path(sys.argv[1]);engine=pathlib.Path(sys.argv[2]);sys.path[:0]=[str(engine.parent/'lib'),str(engine/'src')]
from deploy_workflow.platform_io import locks
folder=root/'intake'/('web-'+'a'*32);folder.mkdir(parents=True);(root/'runs').mkdir()
(folder/'context.json').write_bytes((engine/'smoke-context.json').read_bytes())
raw=b'Synthetic offline Windows source. This is not issuer analysis.'
(folder/'sources').mkdir();(folder/'sources'/'source.txt').write_bytes(raw)
job={'id':folder.name,'workspace':str(root),'config':'sol-medium','cap_usd':'10.00','modules':[],'max_turns':32,'sources':[{'path':'source.txt','sha256':hashlib.sha256(raw).hexdigest()}]}
(folder/'job.json').write_text(json.dumps(job))
a=(root/'lock').open('a+b');b=(root/'lock').open('a+b')
try:
 locks.flock(a,locks.LOCK_EX|locks.LOCK_NB)
 try:locks.flock(b,locks.LOCK_EX|locks.LOCK_NB)
 except BlockingIOError:pass
 else:raise AssertionError('Windows lock did not exclude another writer')
finally:a.close();b.close()
print('ready')
'@
  $Prepared = & $Python -I -B -X utf8 -c $Script $TemporaryRoot (Join-Path $PSScriptRoot 'engine')
  if ($LASTEXITCODE -ne 0) { throw 'Packaged Python import/locking test failed' }
  $Job = Join-Path $TemporaryRoot 'intake\web-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
  $Response = & $Python -I -B -X utf8 $Bridge review $Job
  if ($LASTEXITCODE -ne 0) { throw "CP-OS offline review failed: $Response" }
  $Review = $Response | ConvertFrom-Json
  if (-not $Review.ok) { throw 'Review was refused' }
  if (Test-Path (Join-Path $Job 'start-authorization.md')) { throw 'Review unexpectedly authorised execution' }
  if ((Get-ChildItem (Join-Path $TemporaryRoot 'runs')).Count -ne 0) { throw 'Review unexpectedly created an execution run' }
  # What every page load runs, over a handoff a Windows code page could not print.
  $Handoff = Join-Path $TemporaryRoot 'runs\smoke-001\CP-0.md'
  New-Item -ItemType Directory -Path (Split-Path $Handoff) | Out-Null
  [System.IO.File]::WriteAllText($Handoff, ("# CP-0`n`n## Findings`n`nNet debt " + [char]0x2265 + " 0.`n"), (New-Object System.Text.UTF8Encoding($false)))
  $Library = '{"issues":[],"real":[{"id":"smoke-001","name":"Smoke","artifacts":[]}]}' | & $Python -I -B -X utf8 $Store $TemporaryRoot
  if ($LASTEXITCODE -ne 0) { throw 'Reading the workspace failed' }
  if (-not ($Library | ConvertFrom-Json).runs.'smoke-001'.modules.'CP-0') { throw 'The workspace read lost its handoff' }
  Write-Host 'PASS: packaged Python, Windows locking, existing context validator, workspace read and offline CP-OS review. No provider call was made.'
} finally {
  if (Test-Path $TemporaryRoot) { Remove-Item -Recurse -Force $TemporaryRoot }
}
