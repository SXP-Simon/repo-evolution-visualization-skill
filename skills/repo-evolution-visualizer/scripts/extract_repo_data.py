#!/usr/bin/env python3
"""
Universal Repository Evolution Data Extractor.
Extracts Git commits, GitHub Star history, contributor avatars, milestones, and logo
into an origin-clean, self-contained JavaScript dataset for Web Visualizer.

Features robust, safe author deduplication, explicit user_mapping & .mailmap priority,
GitHub verified noreply extraction, unmapped contributor diagnostics, and starter templates.
"""

import argparse
import base64
import hashlib
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
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

DEFAULT_BOTS = {
    "dependabot[bot]", "github-actions[bot]", "codex", "anthropic-code-agent[bot]",
    "cto-new[bot]", "renovate[bot]", "snyk-bot", "greenkeeper[bot]", "gitter-badger",
    "imgbot[bot]", "codecov[bot]", "sourcery-ai[bot]", "vercel[bot]"
}

def check_environment_health() -> None:
    """Check availability of optional toolchain and print friendly setup hints."""
    has_git = shutil.which("git") is not None
    has_gh = shutil.which("gh") is not None

    if not has_git:
        print("[-] Error: 'git' is not found in system PATH.", file=sys.stderr)
        print("    -> Install Git: winget install --id Git.Git (Windows) | brew install git (macOS) | apt install git (Linux)", file=sys.stderr)

    if not has_gh and not os.environ.get("GITHUB_TOKEN") and not os.environ.get("GH_TOKEN"):
        print("[*] Note: GitHub CLI ('gh') or GITHUB_TOKEN not detected.", file=sys.stderr)
        print("    -> For live Star curves and higher rate limits, run 'gh auth login' or install: winget install GitHub.cli (Windows) | brew install gh (macOS)")
        print("    -> (Offline fallback: A smooth simulated growth curve will be generated automatically if unauthenticated)\n", file=sys.stderr)

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
                        # Format: Proper Name <proper@email.xx> Commit Name <commit@email.xx>
                        m = re.match(r"^([^\<]+)\<([^\>]+)\>(?:\s+([^\<]*)\<([^\>]+)\>)?", line)
                        if m:
                            proper_name = m.group(1).strip()
                            proper_email = m.group(2).strip().lower()
                            commit_name = m.group(3).strip() if m.group(3) else ""
                            commit_email = m.group(4).strip().lower() if m.group(4) else proper_email
                            mailmap[commit_email] = proper_name
                            mailmap[proper_email] = proper_name
                            if commit_name:
                                mailmap[commit_name.lower()] = proper_name
        except Exception as e:
            print(f"[-] Warning: Failed to parse .mailmap: {e}", file=sys.stderr)
    return mailmap

def parse_user_mapping(custom_file: Path = None, repo_dir: Path = None) -> dict:
    """Parse user_mapping.json if present to unify author aliases to canonical GitHub usernames.
    
    Supports two JSON formats:
    1. Group format: {"CanonicalUser": ["alias1", "alias2", "email1@..."]}
    2. Direct alias format: {"alias1": "CanonicalUser", "email1@...": "CanonicalUser"}
    """
    candidates = []
    if custom_file:
        candidates.append(Path(custom_file))
    if repo_dir:
        candidates.extend([
            repo_dir / "user_mapping.json",
            repo_dir / "author_mapping.json",
            repo_dir / ".github" / "user_mapping.json"
        ])

    mapping = {}
    for p in candidates:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        for k, v in data.items():
                            if isinstance(v, list):
                                # Group format: Canonical -> [aliases]
                                canonical = k.strip()
                                for alias in v:
                                    mapping[str(alias).strip().lower()] = canonical
                            elif isinstance(v, str):
                                # Direct alias format: alias -> Canonical
                                mapping[str(k).strip().lower()] = v.strip()
                print(f"  [+] Loaded authoritative user mapping rules from '{p.name}' ({len(mapping)} aliases mapped).")
                break
            except Exception as e:
                print(f"[-] Warning: Failed to load user mapping from {p}: {e}", file=sys.stderr)
    return mapping

def fetch_github_contributors_list(github_repo: str, token: str = None) -> tuple[dict, dict]:
    """Fetch official GitHub contributors list to build safe, exact case-insensitive login mappings.
    
    Returns:
        (known_logins_map, login_to_avatar_url)
    """
    if not github_repo:
        return {}, {}

    known_logins = {}
    login_to_avatar_url = {}

    headers = {"User-Agent": "RepoEvolutionVisualizer"}
    auth_token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if auth_token:
        headers["Authorization"] = f"token {auth_token}"

    # 1. Try gh CLI first
    try:
        gh_cmd = ["gh", "api", f"repos/{github_repo}/contributors", "--paginate", "--jq", ".[] | {login: .login, avatar_url: .avatar_url}"]
        res = subprocess.run(gh_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if res.returncode == 0 and res.stdout.strip():
            for line in res.stdout.split("\n"):
                line = line.strip()
                if line:
                    try:
                        item = json.loads(line)
                        login = item.get("login")
                        av = item.get("avatar_url")
                        if login:
                            known_logins[login.lower()] = login
                            if av:
                                login_to_avatar_url[login] = av
                    except Exception:
                        pass
    except Exception:
        pass

    # 2. REST API fallback
    if not known_logins:
        try:
            url = f"https://api.github.com/repos/{github_repo}/contributors?per_page=100"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if isinstance(data, list):
                    for item in data:
                        login = item.get("login")
                        av = item.get("avatar_url")
                        if login:
                            known_logins[login.lower()] = login
                            if av:
                                login_to_avatar_url[login] = av
        except Exception:
            pass

    if known_logins:
        print(f"  [+] Discovered {len(known_logins)} official GitHub repository contributors.")

    return known_logins, login_to_avatar_url

def clean_author_name(name: str) -> str:
    """Normalize raw git author name by stripping machine names and format anomalies."""
    if not name:
        return "developer"
    # Strip email if embedded in name e.g. "Name <email@...>"
    name = re.sub(r"<[^>]+>", "", name).strip()
    # Strip machine/hostname noise e.g. "Simon (Simon's MacBook Pro)", "admin@DESKTOP-12345"
    name = re.sub(r"\s*\([^\)]*macbook[^\)]*\)", "", name, flags=re.IGNORECASE).strip()
    name = re.sub(r"\s*\([^\)]*desktop[^\)]*\)", "", name, flags=re.IGNORECASE).strip()
    name = re.sub(r"\s*\([^\)]*laptop[^\)]*\)", "", name, flags=re.IGNORECASE).strip()
    name = re.sub(r"\s*\[bot\]", "[bot]", name, flags=re.IGNORECASE).strip()
    return name or "developer"

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

def extract_git_commits(
    repo_dir: Path,
    mailmap: dict,
    user_mapping: dict,
    known_gh_logins: dict,
    bot_filter: set
) -> tuple[list, list, dict, dict]:
    """Extract all git commits with numstat metrics and safe author deduplication.
    
    Returns:
        (commits, sorted_contributors, author_primary_email, unmapped_authors)
    """
    print("[1/5] Extracting Git commit history with numstat and safe identity deduplication...")
    cmd = [
        "git", "-c", "i18n.logOutputEncoding=utf-8", "log",
        "--encoding=utf-8", "--all", "--reverse", "--numstat",
        "--format=COMMIT|%H|%at|%an|%ae|%s"
    ]
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
    author_emails = {}
    unmapped_authors = {}  # canonical_name -> set(emails)

    def resolve_author(raw_name: str, raw_email: str) -> tuple[str, bool]:
        name_clean = clean_author_name(raw_name)
        name_lower = name_clean.lower()
        email_lower = raw_email.lower()

        # 1. Custom user_mapping.json priority (Highest Authority)
        if email_lower in user_mapping:
            return user_mapping[email_lower], True
        if name_lower in user_mapping:
            return user_mapping[name_lower], True

        # 2. .mailmap priority (Standard Git Authority)
        if email_lower in mailmap:
            return mailmap[email_lower], True
        if name_lower in mailmap:
            return mailmap[name_lower], True

        # 3. GitHub Verified No-Reply Email (e.g. 12345+username@users.noreply.github.com)
        noreply_match = re.search(r"(?:[0-9]+\+)?([^@]+)@users\.noreply\.github\.com", email_lower)
        if noreply_match:
            nr_user = noreply_match.group(1)
            canonical = known_gh_logins.get(nr_user.lower(), nr_user)
            return canonical, True

        # 4. Exact match against known GitHub contributors (case-insensitive safe mapping)
        if name_lower in known_gh_logins:
            return known_gh_logins[name_lower], True

        # 5. Unmapped alias fallback (Safe, no blind guessing)
        return name_clean, False

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

            # Check bot filter on raw info
            if raw_author.lower() in bot_filter or raw_email in bot_filter:
                current_commit = None
                continue

            author, is_mapped = resolve_author(raw_author, raw_email)
            if author.lower() in bot_filter:
                current_commit = None
                continue

            contributors_seen[author] = contributors_seen.get(author, 0) + 1
            if author not in author_emails and raw_email:
                author_emails[author] = raw_email

            if not is_mapped:
                if author not in unmapped_authors:
                    unmapped_authors[author] = set()
                if raw_email:
                    unmapped_authors[author].add(raw_email)

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
    print(f"  [+] Extracted {len(commits)} commits from {len(sorted_contributors)} unique contributors.")
    return commits, sorted_contributors, author_emails, unmapped_authors

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
                            import datetime
                            dt = datetime.datetime.fromisoformat(iso_t.replace("Z", "+00:00"))
                            star_events.append({
                                "timestamp": int(dt.timestamp()),
                                "user": item.get("user", "stargazer")
                            })
                    except Exception:
                        pass
            if star_events:
                for idx, event in enumerate(star_events):
                    event["count"] = idx + 1
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
        for idx, event in enumerate(star_events):
            event["count"] = idx + 1
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
            ["git", "-c", "i18n.logOutputEncoding=utf-8", "tag", "-l", "--sort=creatordate", "--format=%(creatordate:unix)|%(refname:short)|%(contents:subject)"],
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

def fetch_contributor_avatars(
    contributors: list,
    cache_dir: Path,
    login_to_avatar_url: dict = None,
    author_emails: dict = None
) -> dict:
    """Download contributor avatars with multi-tier fallback: GitHub API URL -> GitHub Login -> Gravatar -> SVG Badge."""
    print(f"[4/5] Caching and encoding avatars for {len(contributors)} contributors...")
    cache_dir.mkdir(parents=True, exist_ok=True)
    avatars_b64 = {}
    login_to_avatar_url = login_to_avatar_url or {}
    author_emails = author_emails or {}

    for name in contributors:
        avatar_path = cache_dir / f"{name}.png"
        if not avatar_path.exists() or avatar_path.stat().st_size == 0:
            downloaded = False
            # Priority 1: GitHub API direct avatar URL
            if name in login_to_avatar_url:
                try:
                    url = login_to_avatar_url[name]
                    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=6) as resp:
                        avatar_path.write_bytes(resp.read())
                        downloaded = True
                except Exception:
                    pass

            # Priority 2: Standard GitHub username avatar
            if not downloaded:
                url = f"https://github.com/{name}.png?size=120"
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=6) as resp:
                        avatar_path.write_bytes(resp.read())
                        downloaded = True
                except Exception:
                    pass

            # Priority 3: Gravatar via author's email hash
            if not downloaded and name in author_emails:
                email = author_emails[name].strip().lower()
                if email and "@" in email:
                    md5_hash = hashlib.md5(email.encode("utf-8")).hexdigest()
                    gravatar_url = f"https://www.gravatar.com/avatar/{md5_hash}?d=404&s=120"
                    try:
                        req = urllib.request.Request(gravatar_url, headers={"User-Agent": "Mozilla/5.0"})
                        with urllib.request.urlopen(req, timeout=6) as resp:
                            avatar_path.write_bytes(resp.read())
                            downloaded = True
                    except Exception:
                        pass

        if not avatar_path.exists() or avatar_path.stat().st_size == 0:
            # Priority 4: Generate crisp, deterministic hand-drawn SVG letter badge
            initial = (name[:2] if len(name) >= 2 else name).upper()
            colors = ["#4ecdc4", "#ff6b6b", "#ffd93d", "#6c5ce7", "#a8e6cf", "#ff8b94"]
            bg = colors[sum(ord(c) for c in name) % len(colors)]
            svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" width="120" height="120" viewBox="0 0 120 120">
  <circle cx="60" cy="60" r="56" fill="{bg}" stroke="#2c2c2c" stroke-width="4" stroke-dasharray="4,4"/>
  <text x="50%" y="54%" dominant-baseline="middle" text-anchor="middle" font-family="sans-serif" font-size="42" font-weight="900" fill="#2c2c2c">{initial}</text>
</svg>'''
            avatars_b64[name] = "data:image/svg+xml;base64," + base64.b64encode(svg_content.encode("utf-8")).decode("ascii")
        else:
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
            print(f"  [+] Using local repository logo from '{p.name}'")
            return f"data:{mime};base64," + base64.b64encode(data).decode("ascii")

    # 3. Fallback: Hand-drawn repo icon badge
    svg_fallback = '''<svg xmlns="http://www.w3.org/2000/svg" width="120" height="120" viewBox="0 0 24 24" fill="none" stroke="#2c2c2c" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z"/>
  <path d="M6 6h10"/>
  <path d="M6 10h10"/>
</svg>'''
    return "data:image/svg+xml;base64," + base64.b64encode(svg_fallback.encode("utf-8")).decode("ascii")

def main():
    parser = argparse.ArgumentParser(description="Extract Git & GitHub evolution dataset for Web Visualizer.")
    parser.add_argument("--repo-path", default=".", help="Path to target Git repository")
    parser.add_argument("--github-repo", default="", help="GitHub 'owner/repo' identifier")
    parser.add_argument("--project-title", default="", help="Project showcase title")
    parser.add_argument("--core-label", default="核心代码", help="Center hub badge label")
    parser.add_argument("--output-dir", default="./web_visualizer", help="Output directory for visualizer files")
    parser.add_argument("--milestones-file", default="", help="Optional JSON file with curated milestones")
    parser.add_argument("--modules-file", default="", help="Optional JSON file with architecture modules")
    parser.add_argument("--user-mapping", default="", help="Optional JSON file with author alias mappings")
    parser.add_argument("--token", default="", help="GitHub Personal Access Token for higher rate limits")
    args = parser.parse_args()

    check_environment_health()

    repo_dir = Path(args.repo_path).resolve()
    if not (repo_dir / ".git").exists():
        print(f"[-] Error: '{repo_dir}' is not a valid Git repository.", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    data_js_path = out_dir / "visualizer_data.js"

    github_repo = args.github_repo or get_git_remote_repo(repo_dir)
    mailmap = parse_mailmap(repo_dir)
    user_mapping = parse_user_mapping(Path(args.user_mapping) if args.user_mapping else None, repo_dir)
    known_gh_logins, login_to_avatar_url = fetch_github_contributors_list(github_repo, args.token)

    # Auto-detect title from README.md if not explicitly specified
    project_title = args.project_title
    if not project_title:
        readme_candidates = [repo_dir / "README.md", repo_dir / "readme.md", repo_dir / "README.zh-CN.md", repo_dir / "README.zh.md"]
        for rm in readme_candidates:
            if rm.exists():
                try:
                    for line in rm.read_text(encoding="utf-8", errors="ignore").split("\n"):
                        line = line.strip()
                        if line.startswith("# "):
                            clean_t = re.sub(r"[#\*\!\[\]\(\)]", "", line).strip()
                            clean_t = re.sub(r"^\s*[:\-\_]+\s*", "", clean_t)
                            if clean_t:
                                project_title = clean_t
                                print(f"  [+] Auto-detected project title from README: '{project_title}'")
                                break
                    if project_title:
                        break
                except Exception:
                    pass
    if not project_title:
        project_title = repo_dir.name

    commits, contributors, author_emails, unmapped_authors = extract_git_commits(
        repo_dir, mailmap, user_mapping, known_gh_logins, DEFAULT_BOTS
    )

    # Diagnostics & Suggested user_mapping.json generation
    if unmapped_authors:
        print(f"\n[!] 💡 Contributor Identity Notice: Detected {len(unmapped_authors)} author alias(es) not mapped to official GitHub handles:")
        suggested_mapping = {}
        for author_name, emails in list(unmapped_authors.items())[:15]:
            email_list = list(emails)
            preview = f" (email: {email_list[0]})" if email_list else ""
            print(f"    - '{author_name}'{preview}")
            suggested_mapping[author_name] = [author_name] + email_list

        suggested_path = out_dir / "user_mapping.suggested.json"
        try:
            with open(suggested_path, "w", encoding="utf-8") as f:
                json.dump(suggested_mapping, f, ensure_ascii=False, indent=2)
            print(f"    -> Generated starter template at: {suggested_path}")
            print("    -> Tip: To unify aliases and fetch real GitHub avatars, configure 'user_mapping.json' in your repository!\n")
        except Exception:
            pass

    stars = fetch_github_stars(github_repo, args.token)
    milestones = extract_git_milestones(
        repo_dir, commits, Path(args.milestones_file) if args.milestones_file else None
    )

    avatar_cache_dir = out_dir / "avatars_cache"
    avatars_b64 = fetch_contributor_avatars(contributors, avatar_cache_dir, login_to_avatar_url, author_emails)
    logo_b64 = find_and_encode_logo(repo_dir, github_repo, avatar_cache_dir, args.token)

    # Custom modules if provided
    modules_data = None
    if args.modules_file and Path(args.modules_file).exists():
        try:
            with open(args.modules_file, "r", encoding="utf-8") as f:
                modules_data = json.load(f)
                print(f"  [+] Loaded custom architecture modules from {args.modules_file}")
        except Exception as e:
            print(f"  [-] Failed to load modules file: {e}", file=sys.stderr)

    # Date range string
    date_range = "Evolution Timeline"
    if commits:
        import datetime
        d_start = datetime.date.fromtimestamp(commits[0]["timestamp"])
        d_end = datetime.date.fromtimestamp(commits[-1]["timestamp"])
        date_range = f"{d_start.strftime('%Y.%m.%d')} - {d_end.strftime('%Y.%m.%d')}"

    dataset = {
        "project": {
            "name": project_title,
            "coreLabel": args.core_label,
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
    if modules_data:
        dataset["modules"] = modules_data

    print("[5/5] Writing bundle to visualizer_data.js...")
    with open(data_js_path, "w", encoding="utf-8") as f:
        f.write("window.REPO_DATA = " + json.dumps(dataset, ensure_ascii=False, indent=2) + ";\n")

    print(f"\n[+] Evolution dataset generated successfully!")
    print(f"    - Output Data: {data_js_path} ({data_js_path.stat().st_size / 1024:.1f} KB)")
    print(f"    - Commits: {len(commits)} | Contributors: {len(contributors)} | Stars: {len(stars)} | Milestones: {len(milestones)}")

if __name__ == "__main__":
    main()
