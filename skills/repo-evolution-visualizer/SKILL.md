---
name: repo-evolution-visualizer
description: >-
  Generate interactive, publication-ready Web Repository Evolution Visualizers in pure Hand-Drawn Doodle style.
  Extracts Git commits, GitHub Star history, contributor avatars, and milestones into a self-contained HTML5/Canvas
  animated dashboard with full-page 25Mbps 60FPS video recording and 1-click H.264 MP4 export.
  Use when the user asks to visualize git repository history, build code evolution graphs, generate anniversary showcase videos,
  or analyze contributor dynamics for any open-source or private Git project.
---

# Repository Evolution Visualizer Skill

This skill teaches the agent how to build an exquisite, interactive, Hand-Drawn Doodle style (手绘涂鸦风) Repository Evolution Visualizer for any Git/GitHub repository.

It generates a standalone, zero-dependency HTML5 application that visualizes code growth, Star history curves, contributor orbits, and plain-language project milestones, and provides full-page 60FPS video recording with 1-click MP4 conversion.

---

## 🏗️ Architecture & Features

1. **Pure Hand-Drawn Doodle Aesthetics (手绘涂鸦风)**:
   - Warm paper-white canvas (`#fffef5`) with subtle notebook grid lines.
   - High-contrast ink borders with dashed pen strokes and hard offset marker shadows (`#ffd93d`, `#ff6b6b`, `#4ecdc4`).
   - Zero emojis on technical module badges.
2. **Architectural Clustered Hub-and-Spoke Topology**:
   - Central repository core logo badge with connecting trunk rays placed strictly underneath.
   - 6 domain modules surrounding the core.
   - Permanent file dots organized by Sunflower Phyllotaxis (golden ratio distribution) around their modules.
3. **Celestial Contributor Constellation**:
   - 360° outer ring of human contributors with slow continuous orbit.
   - Dynamic commit swoops into the center during active commit windows and smooth return upon completion.
4. **Live Metrics & Rich UI Overlay**:
   - Left panel: GitHub Star growth curve (ECharts) + Plain-Language Milestone stream.
   - Right drawer: Contributor real-time race leaderboard.
   - Top bar: Live date counter, total stars, commits, lines added/removed, and active author toast.
5. **Ultra-HD Full-Page Recording (25Mbps 60FPS & CRF 14 MP4)**:
   - Full webpage/tab screen recording via `navigator.mediaDevices.getDisplayMedia`.
   - Auto-restart playback from day 1 upon recording.
   - 1-click drag-and-drop batch converter (`convert_to_mp4.bat`) converting `.webm` to visually lossless H.264 MP4.

---

## 📋 Prerequisites & Permission Verification

Before extracting data, verify the environment and credentials:

1. **Git Repository**: Ensure the target directory contains a valid `.git` history.
2. **GitHub CLI / Access Token** (for Star history and avatars):
   - Check GitHub CLI: `gh auth status`
   - Or verify `GITHUB_TOKEN` in environment: `echo $env:GITHUB_TOKEN`
   - *Reference*: Read [Permissions & Tokens Guide](./references/permissions_and_tokens.md) for details on scope and rate limits.
3. **Python 3.10+**: Requires standard library + `urllib`.
4. **FFmpeg** (optional, for MP4 conversion): `ffmpeg -version`.

---

## 🚀 Execution Workflow

### Step 1: Run Data Extractor

Execute the universal data extraction script:

```bash
python skills/repo-evolution-visualizer/scripts/extract_repo_data.py \
  --repo-path "<PATH_TO_TARGET_REPO>" \
  --github-repo "<OWNER/REPO>" \
  --output-dir "<OUTPUT_DIR>"
```

**What this script does**:
- Parses Git commit log with `numstat` file additions/deletions.
- Merges author identities via `.mailmap` and filters out known bots.
- Fetches Star history with timestamps via `gh api` or GitHub REST API.
- Caches contributor avatars and repository logo as 100% inlined Base64 Data URIs (origin-clean).
- Extracts release tags and compiles initial milestones.
- Writes structured data to `<OUTPUT_DIR>/visualizer_data.js`.

### Step 2: Deploy Visualizer Template

Copy the generalized template into the output folder:

```bash
python -c "
import shutil
from pathlib import Path
template = Path('skills/repo-evolution-visualizer/templates/visualizer_template.html')
target = Path('<OUTPUT_DIR>/index.html')
shutil.copy(template, target)
print(f'Visualizer HTML deployed to {target}')
"
```

### Step 3: (Optional) Curate Plain-Language Milestones & Modules

- If the repository has special domain modules, adjust `mapFileToModule()` according to [Module Classification Guide](./references/module_classification_guide.md).
- To enrich the story with community moments and memorable achievements, provide a custom `milestones.json` following [Milestone Curation Rules](./references/milestone_curation_rules.md).

### Step 4: Launch and Test in Browser

Open `<OUTPUT_DIR>/index.html` in the default browser:

```bash
start "" "<OUTPUT_DIR>/index.html"
```

Verify:
- [ ] Central repository logo badge displays crisply without dashed lines overlapping the logo.
- [ ] Outer contributor ring rotates continuously at 360°.
- [ ] Active developers swoop in on commit and return smoothly to their slots.
- [ ] Multi-file micro-tags appear over pulsing files during commits.
- [ ] Left Star chart curve and milestone feed stream in chronological sync with commits.
- [ ] Right contributor leaderboard tracks additions and sprint badges dynamically.

### Step 5: Full-Page Ultra-HD Recording & MP4 Export

1. In the top navbar, click **【录制整页视频】**.
2. Select the current browser tab in the popup dialog.
3. The visualizer automatically resets to day 1 (0%) and records the entire webpage in 25Mbps 60FPS.
4. When finished, click **【● 停止录制】** to download `astrbot_plugin_fullpage_evolution_*.webm`.
5. Run `skills/repo-evolution-visualizer/scripts/convert_to_mp4.bat` to convert the downloaded `.webm` to publication-ready H.264 MP4 with CRF 14 clarity!

---

## 🛠️ Helper Scripts Index

| Script | Path | Purpose |
| :--- | :--- | :--- |
| **`extract_repo_data.py`** | [scripts/extract_repo_data.py](./scripts/extract_repo_data.py) | Universal Git & GitHub data extractor |
| **`launch_visualizer.py`** | [scripts/launch_visualizer.py](./scripts/launch_visualizer.py) | One-command build and browser launcher |
| **`convert_to_mp4.bat`** | [scripts/convert_to_mp4.bat](./scripts/convert_to_mp4.bat) | 1-click WebM to H.264 MP4 converter |
| **`visualizer_template.html`** | [templates/visualizer_template.html](./templates/visualizer_template.html) | Standalone Hand-Drawn Doodle visualizer |

---

## 📖 Reference Documentation

- [GitHub Permissions & Token Setup](./references/permissions_and_tokens.md)
- [Architectural Module Classification Guide](./references/module_classification_guide.md)
- [Milestone Curation & Plain-Language Copywriting](./references/milestone_curation_rules.md)
