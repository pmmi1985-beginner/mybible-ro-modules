"""Build registry.json for the staged MyBible modules.

Standard library only. Run as:
    python make_registry.py <staging> <GH_USER> <REPO_NAME> <BRANCH>
"""
import datetime
import hashlib
import json
import re
import sqlite3
import sys
import urllib.parse
from pathlib import Path

staging = Path(sys.argv[1])
gh_user = sys.argv[2]
repo = sys.argv[3]
branch = sys.argv[4]

base = f"https://raw.githubusercontent.com/{gh_user}/{repo}/{branch}/"
state_path = staging / ".state.json"
state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
today = datetime.date.today().isoformat()
modules, problems = [], []

for f in sorted(staging.glob("*.SQLite3")):
    sha = hashlib.sha256(f.read_bytes()).hexdigest()
    con = sqlite3.connect(f"file:{f}?mode=ro", uri=True)
    try:
        info = dict(con.execute("SELECT name, value FROM info").fetchall())
    except sqlite3.Error as e:
        problems.append(f"{f.name}: no usable info table ({e})")
        continue
    finally:
        con.close()
    desc = info.get("description")
    lang = info.get("language") or (
        re.search(r"-([a-z]{2,3})(?:[.\-]|$)", f.stem) or [None, None])[1]
    if not desc or not lang:
        problems.append(f"{f.name}: description={desc!r} language={lang!r}")
        continue
    prev = state.get(f.name)
    if prev and prev["sha256"] == sha:
        date, note = prev["update_date"], prev["update_info"]
    else:
        date, note = today, ("updated" if prev else "initial")
    state[f.name] = {"sha256": sha, "update_date": date, "update_info": note}
    modules.append({
        "download_url": base + urllib.parse.quote(f.name),
        "file_name": f.name,
        "language_code": lang,
        "description": desc,
        "update_date": date,
        "update_info": note,
    })

if problems:
    print("STOP, cannot build registry:\n" + "\n".join(problems))
    sys.exit(1)

registry = {
    "url": base + "registry.json",
    "file_name": "registry.json",
    "description": "Romanian MyBible modules",
    "modules": modules,
}
(staging / "registry.json").write_text(
    json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
print(f"OK: {len(modules)} modules")
