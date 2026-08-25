# Runs the Cradle Explorer backend with reliable restart-on-change.
#
# Deliberately does NOT use `uvicorn --reload`: during development its
# Windows multiprocessing-based reloader got stuck mid-restart twice in a
# row - it logs "Reloading..." but the old worker process's creation
# timestamp never changes, so it silently keeps serving pre-edit code
# until manually killed. `watchfiles`'s CLI restarts the whole process via
# plain subprocess kill/relaunch instead, which doesn't have that failure
# mode.
#
# Only watches for *.py changes (--filter python): viz/*.html|css|js are
# already served with Cache-Control: no-store (see server.py's
# NoCacheStaticFiles) and need no process restart to pick up edits, only
# a browser refresh - restarting uvicorn for those would just add several
# seconds of downtime for no reason.
#
# Usage (from anywhere):
#   powershell -File scripts/run_explorer.ps1

Set-Location (Join-Path $PSScriptRoot "..")

& .venv\Scripts\python.exe -m watchfiles --filter python `
  "$(Resolve-Path .venv\Scripts\python.exe) -m uvicorn server:app --app-dir viz --port 8743" `
  viz src plugins
