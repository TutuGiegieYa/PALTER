"""Explicit, bounded live integration check. This command makes paid API calls."""

import argparse
import json
from pathlib import Path
import secrets
import tempfile

from .deepseek import ROOT, RATE_CARD
from .server import Application


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calls", type=int, choices=(1, 2, 3), default=1)
    parser.add_argument("--report", type=Path, default=ROOT / ".local/verification/deepseek-live.json")
    args = parser.parse_args()
    report = {"rate_card": RATE_CARD, "calls": []}
    with tempfile.TemporaryDirectory(prefix="palter-live-") as directory:
        app = Application(Path(directory)/"check.db")
        owner = app.store.session()["id"]
        state = app.store.create_game(owner, {"command_id": secrets.token_hex(12), "expected_game_id": None})
        def command(kind, **extra):
            nonlocal state
            state, receipt = app.store.execute(owner, state["id"], {"command_id": secrets.token_hex(12), "expected_revision": state["revision"], "kind": kind, **extra})
            assert receipt["accepted"]
        command("confirm")
        command("ready")
        for i in range(args.calls):
            if i == 1:
                command("action", action="follow", target="B")
            elif i == 2:
                command("action", action="inspect", target="drawer")
            result = app.review(owner, state["id"], {"command_id": secrets.token_hex(12), "expected_revision": state["revision"]})
            with app.store.transaction(False) as con:
                row = con.execute("SELECT status,model,returned_model,prefix_hash,request_hash,usage,cost_upper_usd,latency_ms,error_code FROM model_calls ORDER BY started DESC LIMIT 1").fetchone()
                record = dict(row) if row else {"status": "not_sent"}
            if record.get("usage"):
                record["usage"] = json.loads(record["usage"])
            record["world_unchanged"] = app.store.state(owner, state["id"]) == state
            report["calls"].append(record)
            if result["status"] != "completed":
                break
    args.report.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    args.report.chmod(0o600)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if len(report["calls"]) != args.calls or any(c["status"] != "completed" or not c["world_unchanged"] for c in report["calls"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
