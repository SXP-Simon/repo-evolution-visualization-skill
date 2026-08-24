#!/usr/bin/env python3
"""
Universal Repository Evolution Data Extractor.
Extracts Git commits, GitHub Star history, contributor avatars, milestones, and logo
into an origin-clean, self-contained JavaScript dataset for Web Visualizer.
"""

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
import urllib.error
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(line_buffering=True)

DEFAULT_BOTS = {
    "dependabot[bot]", "github-actions[bot]", "codex", "anthropic-code-agent[bot]",
    "cto-new[bot]", "renovate[bot]", "snyk-bot", "greenkeeper[bot]", "gitter-badger",
    "imgbot[bot]", "codecov[bot]", "sourcery-ai[bot]", "vercel[bot]"
}

def parse_mailmap(repo_dir: Path) -> dict:
    """Parse .mailmap file if present to resolve contributor identities."""
    mailmap = {}
    mailmap_path = repo_dir / ".mailmap"
    if mailmap_path.exists():
        try:
            with open(mailmap_path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        # Format: Proper Name <proper@email.xx> <commit@email.xx>
                        # or: Proper Name <proper@email.xx> Commit Name <commit@email.xx>
                        m = re.match(r"^([^\<]+)\<([^\>]+)\>(?:\s+([^\<]*)\<([^\>]+)\>)?", line)
                        if m:
                            proper_name = m.group(1).strip()
                            proper_email = m.group(2).strip().lower()
                            commit_email = m.group(4).strip().lower() if m.group(4) else proper_email
                            mailmap[commit_email] = proper_name
                            mailmap[proper_email] = proper_name
        except Exception as e:
            print(f"[-] Warning: Failed to parse .mailmap: {e}", file=sys.stderr)
    return mailmap

def get_git_remote_repo(repo_dir: Path) -> str:
    """Extract owner/repo from git remote origin URL if possible."""
    try:
        url = subprocess.check_output(
            ["git", "remote", "get-url", "origin"],
            cwd=repo_dir, text=True, encoding="utf-8", errors="ignore"
        ).strip()
        m = re.search(r"github\.com[:/]([^/]+)/([^/\.]+)(?:\.git)?", url)
        if m:
            return f"{m.group(1)}/{m.group(2)}"
    except Exception:
        pass
    return ""

def extract_git_commits(repo_dir: Path, mailmap: dict, bot_filter: set) -> tuple[list, list]:
    """Extract all git commits with numstat metrics."""
    print("[1/5] Extracting Git commit history with numstat...")
    cmd = ["git", "log", "--all", "--reverse", "--numstat", "--format=COMMIT|%H|%at|%an|%ae|%s"]
    try:
        raw_log = subprocess.check_output(
            cmd, cwd=repo_dir, text=True, encoding="utf-8", errors="replace"
        )
    except subprocess.CalledProcessError as e:
        print(f"[-] Error: Failed to read git history: {e}", file=sys.stderr)
        sys.exit(1)

    commits = []
    current_commit = None
    contributors_seen = {}

    for line in raw_log.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("COMMIT|"):
            if current_commit:
                commits.append(current_commit)
            parts = line.split("|", 5)
            chash = parts[1]
            timestamp = int(parts[2])
            raw_author = parts[3].strip()
            raw_email = parts[4].strip().lower()
            msg = parts[5].strip() if len(parts) > 5 else ""

            # Check bot
            if raw_author.lower() in bot_filter or raw_email in bot_filter:
                current_commit = None
                continue

            author = mailmap.get(raw_email, mailmap.get(raw_author, raw_author))
            if author.lower() in bot_filter:
                current_commit = None
                continue

            contributors_seen[author] = contributors_seen.get(author, 0) + 1
            current_commit = {
                "hash": chash,
                "timestamp": timestamp,
                "author": author,
                "message": msg,
                "files": []
            }
        elif current_commit is not None:
            # Numstat line: <additions> <deletions> <path>
            parts = line.split("\t")
            if len(parts) >= 3:
                added = int(parts[0]) if parts[0].isdigit() else 0
                deleted = int(parts[1]) if parts[1].isdigit() else 0
                fpath = parts[2].strip()
                current_commit["files"].append({
                    "path": fpath,
                    "added": added,
                    "deleted": deleted
                })

    if current_commit:
        commits.append(current_commit)

    # Sort contributors by commit count descending
    sorted_contributors = [
        k for k, _ in sorted(contributors_seen.items(), key=lambda x: x[1], reverse=True)
    ]
    print(f"  [+] Extracted {len(commits)} commits from {len(sorted_contributors)} human contributors.")
    return commits, sorted_contributors

def fetch_github_stars(github_repo: str, token: str = None) -> list:
    """Fetch GitHub stargazers timestamps via gh CLI or GitHub REST API."""
    print(f"[2/5] Fetching GitHub Star timestamps for '{github_repo}'...")
    if not github_repo:
        print("  [-] No GitHub repository specified. Skipping Star history fetch.")
        return []

    # 1. Try gh CLI first
    try:
        gh_cmd = [
            "gh", "api", f"repos/{github_repo}/stargazers",
            "--paginate",
            "-H", "Accept: application/vnd.github.v3.star+json",
            "--jq", ".[] | {starred_at: .starred_at, user: .user.login}"
        ]
        res = subprocess.run(
            gh_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        if res.returncode == 0 and res.stdout.strip():
            star_events = []
            for line in res.stdout.split("\n"):
                line = line.strip()
                if line:
                    try:
                        item = json.loads(line)
                        iso_t = item.get("starred_at")
                        if iso_t:
                            # Convert ISO-8601 to Unix timestamp
                            import datetime
                            dt = datetime.datetime.fromisoformat(iso_t.replace("Z", "+00:00"))
                            star_events.append({
                                "timestamp": int(dt.timestamp()),
                                "user": item.get("user", "stargazer")
                            })
                    except Exception:
                        pass
            if star_events:
                print(f"  [+] Successfully fetched {len(star_events)} stars via GitHub CLI.")
                return star_events
    except Exception as e:
        print(f"  [-] gh CLI fetch failed ({e}), attempting REST API fallback...", file=sys.stderr)

    # 2. REST API fallback
    headers = {"Accept": "application/vnd.github.v3.star+json", "User-Agent": "RepoEvolutionVisualizer"}
    auth_token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if auth_token:
        headers["Authorization"] = f"token {auth_token}"

    star_events = []
    page = 1
    import datetime
    while page <= 100:  # Cap at 10,000 stars to avoid infinite loops
        url = f"https://api.github.com/repos/{github_repo}/stargazers?per_page=100&page={page}"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if not data:
                    break
                for item in data:
                    iso_t = item.get("starred_at")
                    if iso_t:
                        dt = datetime.datetime.fromisoformat(iso_t.replace("Z", "+00:00"))
                        user_obj = item.get("user") or {}
                        star_events.append({
                            "timestamp": int(dt.timestamp()),
                            "user": user_obj.get("login", "stargazer") if isinstance(user_obj, dict) else "stargazer"
                        })
                if len(data) < 100:
                    break
                page += 1
        except Exception as e:
            print(f"  [-] REST API page {page} error: {e}", file=sys.stderr)
            break

    if star_events:
        print(f"  [+] Successfully fetched {len(star_events)} stars via GitHub REST API.")
    else:
        print("  [-] Could not fetch live star events. Will use synthetic timeline points.")
    return star_events

def extract_git_milestones(repo_dir: Path, commits: list, custom_milestones_file: Path = None) -> list:
    """Extract release tags or load curated milestones."""
    print("[3/5] Compiling repository milestone timeline...")
    if custom_milestones_file and custom_milestones_file.exists():
        try:
            with open(custom_milestones_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and data:
                    print(f"  [+] Loaded {len(data)} curated milestones from {custom_milestones_file.name}.")
                    return data
        except Exception as e:
            print(f"  [-] Failed to load custom milestones file: {e}", file=sys.stderr)

    milestones = []
    # 1. Extract Git tags
    try:
        tag_out = subprocess.check_output(
            ["git", "tag", "-l", "--sort=creatordate", "--format=%(creatordate:unix)|%(refname:short)|%(contents:subject)"],
            cwd=repo_dir, text=True, encoding="utf-8", errors="replace"
        )
        for line in tag_out.split("\n"):
            line = line.strip()
            if line:
                parts = line.split("|", 2)
                if len(parts) >= 2 and parts[0].isdigit():
                    t = int(parts[0])
                    tag_name = parts[1].strip()
                    subject = parts[2].strip() if len(parts) > 2 and parts[2].strip() else f"Release {tag_name}"
                    milestones.append({
                        "timestamp": t,
                        "tag": "版本发布",
                        "title": f"发布 {tag_name}",
                        "desc": subject
                    })
    except Exception:
        pass

    # 2. Add first commit milestone if available
    if commits:
        first_c = commits[0]
        milestones.insert(0, {
            "timestamp": first_c["timestamp"],
            "tag": "项目诞生",
            "title": "创建第一个提交（Init Repo）",
            "desc": first_c["message"] or "项目代码仓库正式建立"
        })

    # Sort milestones by timestamp
    milestones.sort(key=lambda x: x["timestamp"])
    print(f"  [+] Compiled {len(milestones)} milestones.")
    return milestones

def fetch_contributor_avatars(contributors: list, cache_dir: Path) -> dict:
    """Download contributor avatars from GitHub and encode as Base64 Data URIs."""
    print(f"[4/5] Caching and encoding avatars for {len(contributors)} contributors...")
    cache_dir.mkdir(parents=True, exist_ok=True)
    avatars_b64 = {}

    for name in contributors:
        avatar_path = cache_dir / f"{name}.png"
        if not avatar_path.exists():
            # Try fetching from GitHub
            url = f"https://github.com/{name}.png?size=120"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    avatar_path.write_bytes(resp.read())
            except Exception:
                pass

        if avatar_path.exists():
            data = avatar_path.read_bytes()
            avatars_b64[name] = "data:image/png;base64," + base64.b64encode(data).decode("ascii")

    print(f"  [+] Encoded {len(avatars_b64)} avatars as inline Base64 data URIs.")
    return avatars_b64

def find_and_encode_logo(repo_dir: Path, github_repo: str = "", cache_dir: Path = None, token: str = None) -> str:
    """Acquire repository logo with priority: GitHub Org/Repo Avatar -> Local logo file -> Fallback."""
    # 1. Priority 1: Fetch GitHub Repository/Organization Avatar
    if github_repo and cache_dir:
        owner = github_repo.split("/")[0] if "/" in github_repo else github_repo
        gh_logo_path = cache_dir / f"logo_gh_{owner}.png"
        if not gh_logo_path.exists():
            url = f"https://github.com/{owner}.png?size=200"
            try:
                headers = {"User-Agent": "Mozilla/5.0"}
                if token:
                    headers["Authorization"] = f"token {token}"
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    gh_logo_path.write_bytes(resp.read())
            except Exception as e:
                print(f"  [-] GitHub avatar fetch notice: {e}", file=sys.stderr)

        if gh_logo_path.exists() and gh_logo_path.stat().st_size > 0:
            data = gh_logo_path.read_bytes()
            print(f"  [+] Using GitHub repository owner avatar for: '{owner}'")
            return "data:image/png;base64," + base64.b64encode(data).decode("ascii")

    # 2. Priority 2: Local explicit logo file
    logo_candidates = [
        repo_dir / "logo.png",
        repo_dir / "logo.jpg",
        repo_dir / "logo.svg",
        repo_dir / "assets" / "logo.png",
        repo_dir / "docs" / "public" / "logo.png",
        repo_dir / "docs" / "logo.png",
        repo_dir / ".github" / "logo.png"
    ]
    for p in logo_candidates:
        if p.exists():
            mime = "image/svg+xml" if p.suffix == ".svg" else f"image/{p.suffix.lstrip('.')}"
            data = p.read_bytes()
            print(f"  [+] Found local repository logo at: {p.relative_to(repo_dir)}")
            return f"data:{mime};base64," + base64.b64encode(data).decode("ascii")

    return ""

def main():
    parser = argparse.ArgumentParser(description="Extract Git & GitHub evolution dataset for Web Visualizer.")
    parser.add_argument("--repo-path", type=str, default=".", help="Path to local git repository.")
    parser.add_argument("--github-repo", type=str, default="", help="GitHub owner/repo (e.g. SXP-Simon/AstrBot).")
    parser.add_argument("--output-dir", type=str, default="web_visualizer", help="Output directory.")
    parser.add_argument("--milestones-file", type=str, default="", help="Path to custom curated milestones JSON file.")
    parser.add_argument("--token", type=str, default="", help="GitHub Personal Access Token for rate limits.")
    args = parser.parse_args()

    repo_dir = Path(args.repo_path).resolve()
    if not (repo_dir / ".git").exists():
        print(f"[-] Error: '{repo_dir}' is not a valid Git repository.", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    data_js_path = out_dir / "visualizer_data.js"

    github_repo = args.github_repo or get_git_remote_repo(repo_dir)
    mailmap = parse_mailmap(repo_dir)

    commits, contributors = extract_git_commits(repo_dir, mailmap, DEFAULT_BOTS)
    stars = fetch_github_stars(github_repo, args.token)
    milestones = extract_git_milestones(
        repo_dir, commits, Path(args.milestones_file) if args.milestones_file else None
    )

    avatar_cache_dir = out_dir / "avatars_cache"
    avatars_b64 = fetch_contributor_avatars(contributors, avatar_cache_dir)
    logo_b64 = find_and_encode_logo(repo_dir, github_repo, avatar_cache_dir, args.token)

    # Date range string
    date_range = "Evolution Timeline"
    if commits:
        import datetime
        d_start = datetime.date.fromtimestamp(commits[0]["timestamp"])
        d_end = datetime.date.fromtimestamp(commits[-1]["timestamp"])
        date_range = f"{d_start.strftime('%Y.%m.%d')} - {d_end.strftime('%Y.%m.%d')}"

    dataset = {
        "project": {
            "name": repo_dir.name,
            "repo": github_repo or repo_dir.name,
            "dateRange": date_range,
            "totalCommits": len(commits),
            "totalStars": len(stars),
            "totalContributors": len(contributors)
        },
        "logo": logo_b64,
        "contributors": contributors,
        "avatars": avatars_b64,
        "milestones": milestones,
        "stars": stars,
        "commits": commits
    }

    print("[5/5] Writing bundle to visualizer_data.js...")
    with open(data_js_path, "w", encoding="utf-8") as f:
        f.write("window.REPO_DATA = " + json.dumps(dataset, ensure_ascii=False, indent=2) + ";\n")

    print(f"\n[+] Evolution dataset generated successfully!")
    print(f"    - Output Data: {data_js_path} ({data_js_path.stat().st_size / 1024:.1f} KB)")
    print(f"    - Commits: {len(commits)} | Contributors: {len(contributors)} | Stars: {len(stars)} | Milestones: {len(milestones)}")

if __name__ == "__main__":
    main()
