"""Deterministic PR planning and verdict; the model only writes JSON findings."""

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

MARKER = "<!-- deepseek-sample-review -->"
STATE_RE = re.compile(r"<!-- deepseek-sample-state:\s*(\{.*?\})\s*-->", re.S)
TRUSTED = {"OWNER", "MEMBER", "COLLABORATOR"}
MAX_FILES = 500
MAX_BLOCKERS = 20
STATUS_CONTEXT = "sample-ai-review"


def gh(*args, payload=None):
    command = ["gh", *args]
    if payload is not None:
        command += ["--input", "-"]
    return subprocess.check_output(command, input=json.dumps(payload).encode() if payload is not None else None)


def api(path, **kwargs):
    return json.loads(gh("api", path, **kwargs))


def pages(path):
    result = []
    for page in range(1, 101):
        batch = api(f"{path}?per_page=100&page={page}")
        result.extend(batch)
        if len(batch) < 100:
            return result
    raise ValueError("GitHub response exceeds pagination limit")


def write(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def output(name, value):
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as stream:
        stream.write(f"{name}={value}\n")


def number(value):
    if not re.fullmatch(r"[1-9][0-9]*", str(value)):
        raise ValueError("Invalid PR number")
    return str(value)


def publish_status(repo, head, state, description):
    if not re.fullmatch(r"[0-9a-f]{40}", head):
        raise ValueError("Invalid status commit ID")
    target_url = f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{repo}/actions/runs/{os.environ['GITHUB_RUN_ID']}"
    gh("api", "--method", "POST", f"repos/{repo}/statuses/{head}",
       payload={"state": state, "context": STATUS_CONTEXT,
                "description": description, "target_url": target_url})


def status():
    repo, pr = os.environ["GH_REPO"], number(os.environ["PR_NUMBER"])
    head, base = os.environ["REVIEW_HEAD"], os.environ["REVIEW_BASE"]
    current = api(f"repos/{repo}/pulls/{pr}")
    if current["state"] != "open" or current["head"]["sha"] != head:
        print("Review target changed or closed; no status posted to the new commit.")
        return 1
    decision = os.environ.get("REVIEW_DECISION", "error")
    if current["base"]["sha"] != base or current["draft"] or current["base"]["ref"] != "main":
        decision = "error"
    descriptions = {"success": "完整审核通过，没有确认阻塞",
                    "failure": "独立复核确认存在阻塞",
                    "error": "审核未完成或结果过期，请复评"}
    if decision not in descriptions:
        decision = "error"
    publish_status(repo, head, decision, descriptions[decision])
    return 0 if decision == "success" else 1


def plan():
    repo, pr = os.environ["GH_REPO"], number(os.environ["PR_NUMBER"])
    output("eligible", "false")
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    comment = event.get("comment")
    if comment and (comment.get("author_association") not in TRUSTED or
                    comment.get("user", {}).get("type") == "Bot" or
                    not any(t in comment.get("body", "") for t in ("/review", "@deepseek", "@claude"))):
        return
    metadata = api(f"repos/{repo}/pulls/{pr}")
    eligible = (metadata["state"] == "open" and not metadata["draft"]
                and metadata["base"]["ref"] == "main"
                and (metadata["head"].get("repo") or {}).get("full_name") == repo)
    if not eligible:
        return
    head, base = metadata["head"]["sha"], metadata["base"]["sha"]
    if any(not re.fullmatch(r"[0-9a-f]{40}", ref) for ref in (head, base)):
        raise ValueError("Invalid PR commit IDs")
    output("head", head)
    output("base", base)
    publish_status(repo, head, "pending", "正在审核此提交")
    files = pages(f"repos/{repo}/pulls/{pr}/files")
    if len(files) != metadata["changed_files"] or len(files) > MAX_FILES:
        raise ValueError("File list incomplete or exceeds 500; split the PR before review")
    reviews = pages(f"repos/{repo}/pulls/{pr}/reviews")
    comments = pages(f"repos/{repo}/issues/{pr}/comments")
    inline = pages(f"repos/{repo}/pulls/{pr}/comments")
    current = api(f"repos/{repo}/pulls/{pr}")
    if current["head"]["sha"] != head or current["base"]["sha"] != base:
        raise ValueError("PR changed while planning; retry against the current commit")
    reviewers = {"github-actions[bot]"}
    if os.environ.get("REVIEW_APP_ID") and not os.environ.get("REVIEW_APP_LOGIN"):
        raise ValueError("Reviewer App requires REVIEW_APP_LOGIN to authenticate persisted state")
    if os.environ.get("REVIEW_APP_LOGIN"):
        reviewers.add(os.environ["REVIEW_APP_LOGIN"])
    history = sorted(
        [r for r in reviews + comments if r.get("user", {}).get("type") == "Bot"
         and r["user"]["login"] in reviewers and MARKER in (r.get("body") or "")],
        key=lambda r: r.get("submitted_at") or r.get("created_at") or "")
    carried = []
    for previous in reversed(history):
        state = STATE_RE.search(previous.get("body") or "")
        if state:
            blob = json.loads(state.group(1))
            if not isinstance(blob, dict) or blob.get("v") != 1 or not isinstance(blob.get("open"), list):
                raise ValueError("Invalid persisted blocker state")
            carried = blob["open"]
            if len(carried) > MAX_BLOCKERS:
                raise ValueError("Too many unresolved blockers; split the PR")
            for item in carried:
                validate_blocker(item)
                if item.get("key") != blocker_key(item) or type(item.get("verified")) is not bool:
                    raise ValueError("Invalid persisted blocker identity")
            break
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    subprocess.run(["git", "fetch", "--no-tags", "origin", head, base], check=True)
    diff_base = subprocess.check_output(["git", "merge-base", base, head], text=True).strip()
    snapshot = {"repo": repo, "pr": int(pr), "head": head, "base": base,
                "diffBase": diff_base,
                "rulesRevision": revision, "title": metadata["title"], "body": metadata.get("body") or "",
                "files": [{"path": f["filename"], "previousPath": f.get("previous_filename"), "status": f["status"]} for f in files],
                "carried": carried, "priorRounds": len(history),
                "priorReviews": [{"body": r["body"], "state": r.get("state", "COMMENT"), "commit": r.get("commit_id")} for r in history[-30:]],
                "comments": [{"author": c["user"]["login"], "body": c["body"]} for c in comments[-50:]],
                "inlineComments": [{"path": c["path"], "line": c["line"], "body": c["body"]} for c in inline[-50:]]}
    write("review-data/plan.json", snapshot)
    output("rules_revision", revision)
    output("eligible", "true")


def load_result(path):
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Result must be an object")
    return value


def validate_blocker(item):
    if not isinstance(item, dict) or not isinstance(item.get("file"), str) or not item["file"].strip():
        raise ValueError("Blocker needs a source file")
    if type(item.get("line")) is not int or item["line"] < 1:
        raise ValueError("Blocker needs a source line")
    if any(not isinstance(item.get(k), str) or not item[k].strip() for k in ("what", "scenario")):
        raise ValueError("Blocker needs a concrete failure scenario")
    if not isinstance(item.get("evidence"), list) or not item["evidence"] or any(not isinstance(e, str) or not re.search(r":[1-9][0-9]*\b", e) for e in item["evidence"]):
        raise ValueError("Blocker needs source evidence")


def blocker_key(item):
    text = "\n".join(" ".join(item[k].split()) for k in ("file", "what", "scenario"))
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def findings(path, snapshot):
    data = load_result(path)
    if data.get("head") != snapshot["head"] or data.get("status") != "completed":
        raise ValueError("Review missing, incomplete or for a different commit")
    for name in ("summary", "not_covered", "external_not_covered"):
        if not isinstance(data.get(name), str):
            raise ValueError("Invalid review summary or coverage")
    for name in ("blockers", "unconfirmed"):
        if not isinstance(data.get(name), list):
            raise ValueError("Invalid findings list")
    changed = {f["path"] for f in snapshot["files"]}
    for item in data["blockers"]:
        validate_blocker(item)
        if item["file"] not in changed:
            raise ValueError("Blocker must point to a changed file")
    for item in data["unconfirmed"]:
        if not isinstance(item, dict) or not isinstance(item.get("what"), str):
            raise ValueError("Invalid advisory finding")
    return data


def candidates(snapshot, data):
    items = []
    seen = set()
    for item in snapshot.get("carried", []) + data["blockers"]:
        key = blocker_key(item)
        if key in seen:
            continue
        seen.add(key)
        items.append({**item, "key": key, "id": f"blocker#{len(items)}",
                      "verified": item.get("verified", False) if item in snapshot.get("carried", []) else False})
    if len(items) > MAX_BLOCKERS:
        raise ValueError("Too many blockers; split the PR, no blocker may be silently truncated")
    return items


def collect():
    snapshot = load_result("review-data/plan.json")
    data = findings("review-data/findings.json", snapshot)
    items = candidates(snapshot, data)
    write("review-data/blockers.json", items)
    output("count", len(items))


def trim(value, size=350):
    return " ".join(str(value).split())[:size]


def verdict():
    output("decision", "error")
    repo, pr = os.environ["GH_REPO"], number(os.environ["PR_NUMBER"])
    snapshot = load_result("review-data/plan.json")
    if snapshot.get("repo") != repo or snapshot.get("pr") != int(pr):
        raise ValueError("Wrong review snapshot")
    lines = [MARKER, f"## DeepSeek 审核 · `{snapshot['head'][:12]}`", ""]
    action, complete, confirmed = "COMMENT", True, []
    unresolved = snapshot.get("carried", []).copy()
    try:
        data = findings("review-data/findings.json", snapshot)
        pending = candidates(snapshot, data)
        unresolved = pending.copy()
        if os.environ.get("REVIEW_RESULT") != "success" or os.environ.get("VERIFY_RESULT") != "success":
            raise ValueError("Review or verification job did not finish successfully")
        lines += [trim(data["summary"], 500), ""]
        if data["not_covered"].strip():
            complete = False
            lines += ["未覆盖：" + trim(data["not_covered"]), ""]
        if data["external_not_covered"].strip():
            # Release assets and OCI image bytes are intentionally outside the
            # source-only review. Fixed digests, publication checks and fresh
            # installation evidence bind them; disclose that boundary separately.
            lines += ["未覆盖（外部制品，已由摘要与独立验收绑定）：" + trim(data["external_not_covered"]), ""]
        if pending:
            verified = load_result("review-data/verified.json")
            items = verified.get("verdicts")
            if verified.get("head") != snapshot["head"] or not isinstance(items, list):
                raise ValueError("Missing verification for this commit")
            expected = {b["id"] for b in pending}
            ids = [v.get("id") for v in items if isinstance(v, dict)]
            if len(ids) != len(items) or len(ids) != len(set(ids)) or set(ids) != expected:
                raise ValueError("Verification must cover every blocker exactly once")
            for v in items:
                if v.get("status") not in {"confirmed", "refuted", "unverified"} or not isinstance(v.get("reason"), str) or not v["reason"].strip():
                    raise ValueError("Invalid verification evidence")
                if not isinstance(v.get("evidence"), list) or any(not isinstance(e, str) or not re.search(r":[1-9][0-9]*\b", e) for e in v["evidence"]):
                    raise ValueError("Invalid verification source locations")
                if v["status"] != "unverified" and not v["evidence"]:
                    raise ValueError("Confirmed or refuted blocker needs source evidence")
            decisions = {v["id"]: v for v in items}
            unresolved = []
            for b in pending:
                decision = decisions[b["id"]]
                if decision["status"] == "confirmed":
                    b = {**b, "verified": True}
                    confirmed.append(b)
                    unresolved.append(b)
                elif decision["status"] == "unverified":
                    complete = False
                    unresolved.append(b)
                    lines += [f"- 尚未核实 `{b['key']}`：{trim(decision['reason'])}"]
                else:
                    lines += [f"- 已关闭 `{b['key']}`：{trim(decision['reason'])}"]
        if confirmed:
            lines += ["### 经独立复核的阻塞项", ""]
            for b in confirmed:
                lines += [f"- `{b['key']}` `{b['file']}:{b['line']}`：{trim(b['what'])} {trim(b['scenario'])}"]
        cap = 1 if snapshot.get("priorRounds") else 2
        for u in data["unconfirmed"][:cap]:
            lines += [f"- 待确认（不阻断）：{trim(u.get('file', ''))} {trim(u['what'])}"]
    except (ValueError, OSError, KeyError, TypeError, IndexError):
        complete = False
        lines += ["本轮未完成有效审核或阻塞项复核，不能据此批准。请查看运行日志并回复 `/review` 重试。"]
        if unresolved:
            lines += [f"保留 {len(unresolved)} 条待复核问题，下一轮继续核实。"]
    if complete:
        action = "REQUEST_CHANGES" if confirmed else "APPROVE"
    lines += ["", "旧阻塞项须经复核确认已修复或不成立才关闭；可回复说明理由并加 `/review`。新提交自动复评，合并由人决定。"]
    state = [{k: b[k] for k in ("key", "file", "line", "what", "scenario", "evidence", "verified")} for b in unresolved]
    blob = json.dumps({"v": 1, "open": state}, ensure_ascii=False).replace("-->", "--\\u003e")
    lines += [f"<!-- deepseek-sample-state: {blob} -->"]
    body = "\n".join(lines)
    Path("verdict.md").write_text(body, encoding="utf-8")
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as stream:
        stream.write(body + "\n")
    current = api(f"repos/{repo}/pulls/{pr}")
    if current["state"] != "open":
        print("PR closed; no review posted.")
        return 0
    if current["draft"] or current["head"]["sha"] != snapshot["head"] or current["base"]["sha"] != snapshot["base"]:
        print("PR changed during review; discarded stale verdict.")
        return 1
    payload = {"commit_id": snapshot["head"], "event": action, "body": body}
    try:
        gh("api", "--method", "POST", f"repos/{repo}/pulls/{pr}/reviews", payload=payload)
    except subprocess.CalledProcessError:
        if action != "APPROVE":
            raise
        gh("api", "--method", "POST", f"repos/{repo}/issues/{pr}/comments",
           payload={"body": body + "\n\nGitHub 未允许本身份批准，已改贴评论；没有 APPROVED 状态。"})
    decision = "success" if complete and not confirmed else "failure" if complete else "error"
    output("decision", decision)
    return 0 if decision == "success" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["plan", "collect", "verdict", "status"])
    args = parser.parse_args()
    result = {"plan": plan, "collect": collect, "verdict": verdict, "status": status}[args.stage]()
    raise SystemExit(result or 0)
