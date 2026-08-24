#!/usr/bin/env python3
"""
AI-Automated End-to-End Visualizer Pipeline:
Extracts data -> Renders Animation -> Records WebM -> Converts directly to Ultra-HD H.264 MP4.
Zero manual screen clicks required.
"""

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

def find_browser_executable() -> Path:
    """Find installed Chrome or Edge executable on Windows/macOS/Linux."""
    candidates = [
        # Windows Chrome / Edge
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        Path(os.environ.get("LOCALAPPDATA", "")) / r"Google\Chrome\Application\chrome.exe",
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
        # Linux / macOS
        Path("/usr/bin/google-chrome"),
        Path("/usr/bin/chromium"),
        Path("/usr/bin/chromium-browser"),
        Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge")
    ]
    for c in candidates:
        if c and c.exists():
            return c
    # Fallback to PATH search
    for name in ["google-chrome", "chrome", "chromium", "msedge"]:
        p = shutil.which(name)
        if p:
            return Path(p)
    return None

def main():
    parser = argparse.ArgumentParser(description="Automated Headless Video Exporter (WebM -> H.264 MP4)")
    parser.add_argument("--repo-path", type=str, default=".", help="Target Git repository path.")
    parser.add_argument("--github-repo", type=str, default="", help="GitHub owner/repo (optional).")
    parser.add_argument("--output-dir", type=str, default="output_visualizer", help="Output directory.")
    parser.add_argument("--speed", type=float, default=3.0, help="Simulation playback speed multiplier (default: 3x).")
    parser.add_argument("--output-mp4", type=str, default="", help="Final MP4 output file path.")
    parser.add_argument("--milestones-file", type=str, default="", help="Path to custom curated milestones JSON.")
    parser.add_argument("--token", type=str, default="", help="GitHub Access Token.")
    args = parser.parse_args()

    repo_dir = Path(args.repo_path).resolve()
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    script_dir = Path(__file__).resolve().parent
    skill_dir = script_dir.parent
    template_html = skill_dir / "templates" / "visualizer_template.html"
    index_html = out_dir / "index.html"

    final_mp4 = Path(args.output_mp4).resolve() if args.output_mp4 else out_dir / f"{repo_dir.name}_evolution.mp4"

    print("==============================================================================")
    print("  Repository Evolution Visualizer - Automated MP4 Pipeline")
    print("==============================================================================")
    print(f"[*] Target Repo: {repo_dir}")
    print(f"[*] Output MP4:  {final_mp4}")
    print()

    # Step 1: Extract Data
    print("[1/4] Extracting repository evolution dataset...")
    extractor_script = script_dir / "extract_repo_data.py"
    extract_cmd = [
        sys.executable, str(extractor_script),
        "--repo-path", str(repo_dir),
        "--output-dir", str(out_dir)
    ]
    if args.github_repo:
        extract_cmd.extend(["--github-repo", args.github_repo])
    if args.milestones_file:
        extract_cmd.extend(["--milestones-file", args.milestones_file])
    if args.token:
        extract_cmd.extend(["--token", args.token])

    subprocess.run(extract_cmd, check=True)

    # Step 2: Deploy Template
    print("[2/4] Deploying visualizer template...")
    shutil.copy(template_html, index_html)

    # Step 3: Record Animation
    print(f"[3/4] Launching automated recording at {args.speed}x speed...")
    browser_exe = find_browser_executable()
    downloads_dir = Path(os.environ.get("USERPROFILE", "")) / "Downloads"

    # Capture baseline of downloads directory
    before_files = set(downloads_dir.glob("repo_evolution_auto_*.webm")) if downloads_dir.exists() else set()
    local_before_files = set(out_dir.glob("repo_evolution_auto_*.webm"))

    target_url = f"{index_html.as_uri()}?autorecord=1&speed={args.speed}"

    if browser_exe:
        print(f"  [+] Using browser: {browser_exe}")
        # Launch browser with auto-recording URL
        browser_cmd = [
            str(browser_exe),
            "--new-window",
            "--window-size=1920,1080",
            "--autoplay-policy=no-user-gesture-required",
            target_url
        ]
        proc = subprocess.Popen(browser_cmd)
    else:
        print("  [-] Browser executable not found directly, opening with default web handler...")
        import webbrowser
        webbrowser.open(target_url)
        proc = None

    print("  [*] Waiting for simulation recording to complete and download WebM...")
    downloaded_webm = None
    start_time = time.time()
    max_wait = 180  # 3 minutes max

    while time.time() - start_time < max_wait:
        time.sleep(1.5)
        # Check Downloads directory
        if downloads_dir.exists():
            now_files = set(downloads_dir.glob("repo_evolution_auto_*.webm"))
            diff = now_files - before_files
            if diff:
                downloaded_webm = sorted(list(diff), key=lambda p: p.stat().st_mtime, reverse=True)[0]
                break

        # Check Output directory
        now_local = set(out_dir.glob("repo_evolution_auto_*.webm"))
        diff_local = now_local - local_before_files
        if diff_local:
            downloaded_webm = sorted(list(diff_local), key=lambda p: p.stat().st_mtime, reverse=True)[0]
            break

    if proc:
        try:
            proc.terminate()
        except Exception:
            pass

    if not downloaded_webm or not downloaded_webm.exists():
        print("[-] Error: Automated recording timed out or WebM file was not received.", file=sys.stderr)
        sys.exit(1)

    print(f"  [+] Captured WebM recording: {downloaded_webm} ({downloaded_webm.stat().st_size / 1024:.1f} KB)")

    # Step 4: Convert to H.264 MP4 with FFmpeg
    print("[4/4] Converting WebM to ultra-clear H.264 MP4 (CRF 14, 60FPS)...")
    ffmpeg_exe = shutil.which("ffmpeg") or "ffmpeg"
    ffmpeg_cmd = [
        ffmpeg_exe, "-y",
        "-i", str(downloaded_webm),
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "14",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(final_mp4)
    ]

    res = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[-] FFmpeg conversion failed: {res.stderr}", file=sys.stderr)
        sys.exit(1)

    print()
    print("==============================================================================")
    print(f"[OK] Evolution MP4 video successfully generated!")
    print(f"     File: {final_mp4} ({final_mp4.stat().st_size / 1024 / 1024:.2f} MB)")
    print("==============================================================================")

if __name__ == "__main__":
    main()
