"""User-authorized headless Edge acceptance. Default mode makes no paid calls."""

import argparse
import json
from pathlib import Path
import tempfile
import threading

from palter.deepseek import DeepSeek, Settings, ROOT
from palter.server import Application, Server


def recorded_selection(payload):
    records = json.loads(payload["messages"][-1]["content"])["observations"]
    return {"model": "test-double", "choices": [{"finish_reason": "stop", "message": {"content": json.dumps({"observation_ids": [r["id"] for r in records[:2]]})}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 10, "prompt_cache_hit_tokens": 20, "prompt_cache_miss_tokens": 80}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", help="Use an already running local server")
    parser.add_argument("--live-review", action="store_true", help="Explicitly permit one real, paid review on that server")
    parser.add_argument("--output", type=Path, default=ROOT / ".local/verification/browser")
    args = parser.parse_args()
    if args.live_review and not args.base_url:
        parser.error("--live-review requires an explicit local --base-url")
    if args.base_url and not args.base_url.startswith(("http://127.0.0.1:", "http://localhost:")):
        parser.error("Only a local demo server is allowed")
    from playwright.sync_api import sync_playwright, expect
    args.output.mkdir(parents=True, exist_ok=True)
    report = {"browser": "Edge headless", "live_review": args.live_review, "cases": [], "screenshots": [], "page_errors": []}
    server = None
    with tempfile.TemporaryDirectory(prefix="palter-browser-") as directory:
        if args.base_url:
            base = args.base_url.rstrip("/")
        else:
            app = Application(Path(directory)/"browser.db", DeepSeek(Settings(api_key="browser-test-key"), recorded_selection))
            server = Server(("127.0.0.1", 0), app)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(channel="msedge", headless=True, chromium_sandbox=True)
                context = browser.new_context(viewport={"width":1440,"height":1000}, locale="zh-CN")
                page = context.new_page()
                page.set_default_timeout(10000)
                page.on("pageerror", lambda error: report["page_errors"].append(str(error)))

                def current():
                    response = page.request.get(base+"/api/session")
                    assert response.ok
                    data = response.json()
                    view = data["view"]
                    if view:
                        for key in ("events", "knowledge", "locations", "letter_custody"):
                            assert key not in view, f"Hidden field in player payload: {key}"
                    return view

                def settled():
                    expect(page.locator("#new-game")).to_be_enabled()

                def screenshot(name):
                    path = args.output / name
                    page.screenshot(path=str(path), full_page=True)
                    report["screenshots"].append(str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path))

                def fresh():
                    page.locator("#new-game").click()
                    expect(page.locator('[data-command="confirm"]')).to_be_visible()
                    settled()
                    page.locator('[data-command="confirm"]').click()
                    expect(page.locator('[data-command="ready"]')).to_be_visible()
                    before = current()
                    assert before["beat"] == 0 and before["phase"] == "reading"
                    page.reload()
                    expect(page.locator('[data-command="ready"]')).to_be_visible()
                    assert current() == before
                    page.locator('[data-command="ready"]').click()
                    expect(page.locator("#action-form")).to_be_visible()
                    settled()

                def action(kind, target="", double=False):
                    before = current()
                    page.locator(f'[data-action="{kind}"]').click()
                    page.locator("#target").select_option(target)
                    assert current()["beat"] == before["beat"], "Selecting an action advanced time"
                    if double:
                        page.locator('#action-form button[type="submit"]').dblclick()
                    else:
                        page.locator('#action-form button[type="submit"]').click()
                    settled()
                    after = current()
                    assert after["beat"] == before["beat"]+1, f"Action advanced {after['beat']-before['beat']} beats"
                    return after

                page.goto(base)
                expect(page.locator("#new-game")).to_be_enabled()
                page.locator("#new-game").click()
                expect(page.locator('[data-command="confirm"]')).to_be_visible()
                screenshot("introduction-desktop.png")
                # Start the first case from the displayed introduction.
                page.locator('[data-command="confirm"]').click()
                expect(page.locator('[data-command="ready"]')).to_be_visible()
                page.locator('[data-command="ready"]').click()
                settled()
                assert current()["beat"] == 0
                action("follow","B")
                before = current()
                page.locator('[data-command="pause"]').click()
                expect(page.locator('[data-command="resume"]')).to_be_visible()
                page.reload()
                expect(page.locator('[data-command="resume"]')).to_be_visible()
                assert current()["beat"] == before["beat"]
                assert current()["observations"] == before["observations"]
                page.locator('[data-command="resume"]').click()
                settled()
                action("inspect","drawer")
                before = current()
                page.reload()
                expect(page.locator("#action-form")).to_be_visible()
                settled()
                assert current() == before, "Active refresh changed committed progress"
                screenshot("active-desktop.png")
                page.set_viewport_size({"width":390,"height":844})
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "Mobile layout overflows horizontally"
                expect(page.locator('#action-form button[type="submit"]')).to_be_visible()
                screenshot("active-mobile.png")
                page.set_viewport_size({"width":1440,"height":1000})
                if not args.base_url or args.live_review:
                    before = current()
                    with page.expect_response(lambda response: response.url.endswith("/review"), timeout=35000) as response:
                        page.locator("#review").click()
                    result = response.value.json()
                    assert result["status"] == "completed", result["status"]
                    settled()
                    after = current()
                    assert after["beat"] == before["beat"] and after["observations"] == before["observations"]
                    assert after["review"]["records"]
                    expect(page.locator(".review-record")).to_have_count(len(after["review"]["records"]))
                    for record in after["review"]["records"]:
                        expect(page.locator(".review-record").filter(has_text=record["text"])).to_be_visible()
                    screenshot("review-desktop.png")
                    report["review_usage"] = after["review"]["reported_usage"]
                action("take","letter")
                action("move","hall")
                action("wait")
                action("wait")
                expect(page.get_by_role("heading", name="如期交接", exact=True)).to_be_visible()
                assert current()["outcome"]["id"] == "delivered"
                screenshot("outcome-desktop.png")
                first_id = current()["id"]
                report["cases"].append("delivered, pause/resume, reload, mobile layout, review isolation")

                fresh()
                for kind,target in [("wait",""),("wait",""),("wait",""),("move","study"),("inspect","drawer"),("take","letter")]:
                    action(kind,target)
                expect(page.get_by_role("heading",name="只差一步",exact=True)).to_be_visible()
                assert current()["outcome"]["id"] == "incomplete"
                report["cases"].append("incomplete")

                fresh()
                action("wait",double=True)
                for _ in range(5):
                    action("wait")
                expect(page.get_by_role("heading",name="未解的去向",exact=True)).to_be_visible()
                assert current()["outcome"]["id"] == "not_found"
                report["cases"].append("not_found and native double click")

                fresh()
                # The server commits, but the browser loses the response.
                saved = []
                def lose_response(route):
                    response = route.fetch()
                    saved.append(response.json())
                    route.abort("failed")
                page.route("**/commands",lose_response,times=1)
                page.locator('[data-action="wait"]').click()
                page.locator("#target").select_option("")
                page.locator('#action-form button[type="submit"]').click()
                expect(page.locator("#recovery")).to_be_visible()
                expect(page.locator("#new-game")).to_be_disabled()
                expect(page.locator("#retry")).to_be_enabled()
                expect(page.locator('#action-form button[type="submit"]')).to_be_disabled()
                assert saved and saved[0]["view"]["beat"] == 1
                page.locator("#retry").click()
                settled()
                assert current()["beat"] == 1
                assert current()["observations"] == saved[0]["view"]["observations"]
                report["cases"].append("lost response recovery without duplicate beat")
                page.locator("#history").select_option(first_id)
                expect(page.locator(".archive-banner")).to_be_visible()
                expect(page.locator("#action-form")).to_have_count(0)
                report["cases"].append("archived game replay is read-only")
                assert not report["page_errors"], report["page_errors"]
                context.close()
                browser.close()
        finally:
            if server:
                server.shutdown()
                server.server_close()
                thread.join(3)
    (args.output/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
