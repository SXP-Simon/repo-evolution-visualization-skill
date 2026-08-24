# GitHub 权限与数据提取凭证指南 (Permissions & Tokens Guide)

本文档详细说明在不同环境与权限配置下，如何配置 GitHub Token 与 Git 访问权限，以确保数据提取工具能完整抓取 Star 演化历史、贡献者头像与发布里程碑。

---

## 1. 为什么需要 GitHub 权限？

本工作流包含四项核心数据源：

| 数据项 | 数据源 | 所需权限 / 工具 | 说明 |
| :--- | :--- | :--- | :--- |
| **Git 提交历史** | 本地 `.git` 目录 | 本地文件读取权限 | `git log --numstat`，无需网络权限 |
| **Star 增长时间线** | GitHub API `/stargazers` | GitHub CLI 或 API Token | 需要时间戳字段（`application/vnd.github.v3.star+json`） |
| **贡献者高清头像** | GitHub 用户头像 API | 公网网络访问 | 自动下载并内联转码为 Base64 |
| **版本标签与 Release** | 本地 Git Tag / GitHub API | 本地 Git 或 API 读取 | 提取版本发布与变更描述 |

---

## 2. GitHub CLI 认证方式（推荐，零配置）

如果你本地已安装并登录了官方 [GitHub CLI (`gh`)](https://cli.github.com/)，本工具会自动检测并调用 `gh api`，**无需手动复制任何 Token**！

### 验证与登录命令：
```bash
# 1. 检查登录状态
gh auth status

# 2. 如果未登录，执行交互式登录
gh auth login
```
在提示中选择：
- **What account do you want to log into?** $\rightarrow$ `GitHub.com`
- **What is your preferred protocol for Git operations?** $\rightarrow$ `HTTPS`
- **Authenticate Git with your GitHub credentials?** $\rightarrow$ `Yes`
- **How would you like to authenticate?** $\rightarrow$ `Login with a web browser`

---

## 3. GitHub Personal Access Token (PAT) 方式

在 CI/CD 流水线、无头服务器（Headless Server）或未安装 `gh` CLI 的环境中，可通过环境变量或命令行参数传入 Personal Access Token。

### 3.1 创建 Token 步骤：
1. 访问 GitHub 设置：[GitHub Settings $\rightarrow$ Developer settings $\rightarrow$ Personal access tokens $\rightarrow$ Tokens (classic)](https://github.com/settings/tokens)；
2. 点击 **Generate new token (classic)**；
3. **Note** 填写：`repo-evolution-visualizer`；
4. **Expiration** 选择需要的有效期（如 30 天或 90 天）；
5. **Scopes 权限勾选**：
   - 对于公开开源仓库（Public Repo）：**只需勾选 `public_repo` 与 `read:user`**；
   - 对于私有内部仓库（Private Repo）：需勾选完整的 **`repo`** 权限；
6. 点击 **Generate token** 并复制生成的字符串（形如 `ghp_xxxxxxxxxxxx`）。

### 3.2 注入 Token 的方式：

#### 方式 A：设置环境变量（推荐）
- **PowerShell (Windows)**:
  ```powershell
  $env:GITHUB_TOKEN = "ghp_your_personal_access_token_here"
  ```
- **Bash / Zsh (Linux / macOS)**:
  ```bash
  export GITHUB_TOKEN="ghp_your_personal_access_token_here"
  ```

#### 方式 B：作为命令行参数传入
```bash
python extract_repo_data.py --repo-path "C:\path\to\repo" --github-repo "owner/repo" --token "ghp_your_token"
```

---

## 4. API 速率限制（Rate Limits）说明

| 模式 | 速率限制 | 说明 |
| :--- | :--- | :--- |
| **未认证（匿名请求）** | 60 次 / 小时 | 仅能拉取约 6,000 个 Star，容易触发 403 限流 |
| **已认证（gh / Token）** | 5,000 次 / 小时 | 可无缝拉取 50 万个 Star，满足绝大多数仓库需求 |

---

## 5. 离线 / 纯内网环境运行（Offline Fallback）

如果在无法连接 GitHub 的纯内网或私有 Git 服务器环境中运行：
1. 本工具会自动检测网络连接状态；
2. 即使 GitHub API 无法访问，数据提取器会**自动基于 Git 提交时间轴生成平滑的模拟 Star 增长曲线**；
3. 贡献者头像会自动生成彩色字母微缩勋章（Initials Badge）；
4. **确保在完全无外网连接的情况下，依然能够 100% 成功生成并流畅运行完整的演化可视化页面**！
