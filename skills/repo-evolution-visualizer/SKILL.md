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

## 📋 Prerequisites & Toolchain Verification (环境自检与依赖矩阵)

This skill is designed to be **ultra-lightweight with zero heavy dependencies**. Python standard library is used for data extraction (0 pip packages required).

| Tool | Role | Required? | Weight | 1-Line Install Command (If Missing) |
| :--- | :--- | :---: | :---: | :--- |
| **`Python 3.10+`** | Data extractor & script runner | **Yes** | Light | Standard library only (**0 pip packages needed**) |
| **`Git`** | Read commit logs & `.mailmap` | **Yes** | Light | **Win**: `winget install --id Git.Git -e`<br>**Mac**: `brew install git`<br>**Linux**: `sudo apt install git` |
| **Modern Browser** | Render Canvas & record video | **Yes** | Built-in | System Chrome / Edge / Firefox |
| **`GitHub CLI (gh)`** | Fetch live Star history & timestamps | *Optional* | Light | **Win**: `winget install --id GitHub.cli -e`<br>**Mac**: `brew install gh`<br>*(Or set `GITHUB_TOKEN` / fallback to smooth curve)* |
| **`FFmpeg`** | Lossless WebM to H.264 MP4 conversion | *Optional* | Light | **Win**: `winget install --id Gyan.FFmpeg -e`<br>**Mac**: `brew install ffmpeg`<br>**Linux**: `sudo apt install ffmpeg`<br>*(If absent, WebM is downloaded directly)* |

> [!TIP]
> If any optional tool is missing, the AI Agent can either run the 1-line install command above or proceed with built-in fallbacks (e.g. smooth simulated Star curves, direct WebM downloads).

---

## 🚀 AI Agent Execution Workflow (Step-by-Step)

When this skill is activated, you (the AI Agent) should autonomously execute the following 4 phases:

### Phase 1: Project Discovery & Title Formulation (自主感知与标题拟定)

1. **Inspect Repository Context**:
   - Read the target repository's `README.md`, manifest (`pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`, etc.), and git remote (`git remote get-url origin`).
   - Understand the project's purpose, core technical highlights, and anniversary/historical context.
2. **Formulate a Compelling Title**:
   - Synthesize a catchy, emotionally resonant, and accurate title for the visualizer (e.g., `从零开始的群分析总结插件（一周年）`, `AstrBot 智能机器人演化志`, `Vue.js 渐进式前端生态十年图鉴`).
   - Determine the central core hub badge text (default: `核心代码` or `项目内核`).

### Phase 2: Milestone Curation & Emotional Copywriting (自主提炼自然中文里程碑)

1. **Extract Key Project Events**:
   - Run `git tag -l --sort=creatordate` to find all release tags.
   - Run `git log --oneline --grep="feat\|release\|PR\|#"` to spot major features and contributor PR merges.
2. **Synthesize Plain-Language Milestones**:
   - Write 15~30 genuine, natural, plain-language milestones into `<OUTPUT_DIR>/milestones.json`.
   - Include contributor shoutouts (`由 @username 贡献...`), PR references (`#123`), and categorized tags (`项目诞生`, `重磅功能`, `社区里程碑`, `生态拓展`, `周年纪念`).
   - *Reference*: Follow [Milestone Curation Rules](./references/milestone_curation_rules.md).

### Phase 3: Author Deduplication & Data Extraction (作者身份去重与数据提取)

1. **Check for Author Aliases (可选/推荐)**:
   - Check if a contributor used multiple names or email addresses in git log.
   - You can create `<OUTPUT_DIR>/user_mapping.json` (or use `.mailmap`) to unify them to their canonical GitHub username:
     ```json
     {
       "CanonicalGitHubUser": ["git_alias_1", "git_alias_2", "committer@email.com"]
     }
     ```
   - *Reference*: Follow [Author Mapping & Alias Deduplication Guide](./references/author_mapping_guide.md).

2. **Execute Data Extraction**:
```bash
python skills/repo-evolution-visualizer/scripts/extract_repo_data.py \
  --repo-path "<PATH_TO_TARGET_REPO>" \
  --github-repo "<OWNER/REPO>" \
  --project-title "<AUTONOMOUSLY_FORMULATED_TITLE>" \
  --milestones-file "<OUTPUT_DIR>/milestones.json" \
  --user-mapping "<OUTPUT_DIR>/user_mapping.json" \
  --output-dir "<OUTPUT_DIR>"
```

Deploy the HTML template:
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

### Phase 4: Verification & Delivery (两种交付模式)

#### Mode A: Interactive Web Dashboard (浏览器交互看板)
Launch the visualizer in the default browser:
```bash
start "" "<OUTPUT_DIR>/index.html"
```
Verify:
- [ ] Brand title and repository name in header match project information dynamically.
- [ ] Central repository logo badge (from GitHub owner avatar or local logo) displays crisply.
- [ ] 360° celestial contributor ring rotates continuously and developers swoop on commit.
- [ ] Milestones and Star curve update in chronological sync with commits.
- [ ] Clicking **【录制整页视频】** records full-page 25Mbps 60FPS video.

#### Mode B: Fully Automated Headless MP4 Export (全自动静默导出 MP4)
If the user requests a ready-to-share MP4 video directly, run:
```bash
python skills/repo-evolution-visualizer/scripts/record_and_export_mp4.py \
  --repo-path "<PATH_TO_TARGET_REPO>" \
  --github-repo "<OWNER/REPO>" \
  --project-title "<AUTONOMOUSLY_FORMULATED_TITLE>" \
  --milestones-file "<OUTPUT_DIR>/milestones.json" \
  --speed 3.0 \
  --output-mp4 "<DESTINATION_PATH.mp4>"
```
This automatically captures the WebM stream and converts it via FFmpeg (CRF 14, H.264) into the final `.mp4` video.

---

## 🛠️ Helper Scripts Index

| Script | Path | Purpose |
| :--- | :--- | :--- |
| **`record_and_export_mp4.py`** | [scripts/record_and_export_mp4.py](./scripts/record_and_export_mp4.py) | **AI-Automated End-to-End MP4 pipeline** (Extract + Render + Convert) |
| **`extract_repo_data.py`** | [scripts/extract_repo_data.py](./scripts/extract_repo_data.py) | Universal Git & GitHub data extractor (Stars, Avatars, Logo, Commits, Deduplication) |
| **`launch_visualizer.py`** | [scripts/launch_visualizer.py](./scripts/launch_visualizer.py) | One-command build and browser launcher |
| **`convert_to_mp4.bat`** | [scripts/convert_to_mp4.bat](./scripts/convert_to_mp4.bat) | 1-click WebM to H.264 MP4 converter |
| **`visualizer_template.html`** | [templates/visualizer_template.html](./templates/visualizer_template.html) | Standalone Hand-Drawn Doodle visualizer |

---

## 📖 Reference Documentation

- [Author Mapping & Alias Deduplication Guide](./references/author_mapping_guide.md)
- [GitHub Permissions & Token Setup](./references/permissions_and_tokens.md)
- [Architectural Module Classification Guide](./references/module_classification_guide.md)
- [Milestone Curation & Plain-Language Copywriting](./references/milestone_curation_rules.md)
