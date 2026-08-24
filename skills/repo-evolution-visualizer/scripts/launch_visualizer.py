#!/usr/bin/env python3
"""
Launcher script for Repository Evolution Visualizer.
Copies template, generates dataset, and launches default browser.
"""

import argparse
import shutil
import subprocess
import webbrowser
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Build and launch the Web Repository Evolution Visualizer.")
    parser.add_argument("--repo-path", type=str, default=".", help="Target Git repository path.")
    parser.add_argument("--github-repo", type=str, default="", help="GitHub owner/repo (optional).")
    parser.add_argument("--output-dir", type=str, default="web_visualizer", help="Output directory.")
    parser.add_argument("--project-title", type=str, default="", help="Custom project title.")
    parser.add_argument("--core-label", type=str, default="核心代码", help="Center hub badge text.")
    parser.add_argument("--modules-file", type=str, default="", help="Custom architecture modules JSON.")
    parser.add_argument("--milestones-file", type=str, default="", help="Custom milestones JSON file.")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    skill_dir = script_dir.parent
    template_html = skill_dir / "templates" / "visualizer_template.html"

    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    target_html = out_dir / "index.html"

    # Copy HTML template
    if template_html.exists():
        shutil.copy(template_html, target_html)
        print(f"[+] Copied visualizer template to {target_html}")

    # Run extraction script
    extractor_script = script_dir / "extract_repo_data.py"
    cmd = [
        "python", str(extractor_script),
        "--repo-path", args.repo_path,
        "--output-dir", str(out_dir)
    ]
    if args.github_repo:
        cmd.extend(["--github-repo", args.github_repo])
    if args.project_title:
        cmd.extend(["--project-title", args.project_title])
    if args.core_label:
        cmd.extend(["--core-label", args.core_label])
    if args.modules_file:
        cmd.extend(["--modules-file", args.modules_file])
    if args.milestones_file:
        cmd.extend(["--milestones-file", args.milestones_file])

    print(f"[*] Running data extractor: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

    print(f"[+] Opening {target_html} in browser...")
    webbrowser.open(target_html.as_uri())

if __name__ == "__main__":
    main()
