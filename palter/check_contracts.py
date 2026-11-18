"""Offline publication gate; no application, database or provider initialization."""
import hashlib
import json
from pathlib import Path
from .model_contracts import CURRENT_PREFIX,check_published


def main():
    folder=Path(__file__).parent/'prefixes'
    manifest=json.loads((folder/'manifest.json').read_text())
    issues=[name+': immutable hash mismatch' for name,digest in manifest.items()
            if hashlib.sha256((folder/name).read_bytes()).hexdigest()!=digest]
    issues+=check_published(json.loads((folder/CURRENT_PREFIX).read_text()))
    print(json.dumps({'prefix':CURRENT_PREFIX,'artifacts':len(manifest),'passed':not issues,'issues':issues}))
    return int(bool(issues))


if __name__=='__main__':raise SystemExit(main())
