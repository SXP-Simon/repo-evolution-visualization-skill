# 架构模块分类与聚类配置指南 (Architectural Module Classification Guide)

本文档说明如何为不同的开源项目（如 Python 后端、TypeScript 前端、Rust 系统库、Go 微服务等）自定义手绘架构模块聚类。

---

## 1. 为什么需要架构模块聚类？

传统的代码演化工具（如 Gource）往往将所有文件按照完整目录树平铺展开，导致大型项目中数十个深层子文件夹在屏幕上杂乱无章，难以看清系统的顶层架构演变。

本工作流采用 **“手绘架构核心辐射拓扑（Architectural Clustered Hub-and-Spoke Topology）”**：
- 中央为 **项目内核徽章（Repository Core Logo Hub）**；
- 周围环绕 **6 个具象化的顶层业务与系统模块卡片（Module Clusters）**；
- 所有代码文件的持久散点（Sunflower Phyllotaxis）自然聚类在对应的架构模块周围。

---

## 2. 动态架构模块聚类原理

系统完全支持由 AI Agent 根据代码仓库真实的顶级目录结构（例如 `src`, `components`, `pkg`, `api`, `crates`, `docs` 等）自适应生成 4 ~ 6 个架构模块，或由系统全自动动态聚类。

### 模块数据结构示例（`modules.json`）
```json
[
  { "id": "core", "name": "核心调度", "x": -170, "y": -90, "color": "#4ecdc4", "pattern": "core" },
  { "id": "engine", "name": "运算引擎", "x": 170, "y": -90, "color": "#ff6b6b", "pattern": "engine" },
  { "id": "ui", "name": "用户界面", "x": 200, "y: 110, "color": "#ffd93d", "pattern": "ui" },
  { "id": "adapters", "name": "适配拓展", "x": -200, "y": 110, "color": "#4ecdc4", "pattern": "adapter" },
  { "id": "storage", "name": "数据持久", "x": 0, "y": 190, "color": "#ff6b6b", "pattern": "db" },
  { "id": "docs", "name": "配置文档", "x": 0, "y": -190, "color": "#ffd93d", "pattern": "doc" }
]
```

---

## 3. 多语言项目映射范例

在 `index.html` 的 `mapFileToModule(filePath)` 函数中，可根据项目特点调整关键字规则：

### 3.1 前端 Web 项目（React / Vue / Next.js）
```javascript
function mapFileToModule(filePath) {
  const lower = filePath.toLowerCase();
  if (lower.includes("page") || lower.includes("route") || lower.includes("app")) return MODULE_CLUSTERS[0]; // 页面路由
  if (lower.includes("component") || lower.includes("hook") || lower.includes("ui")) return MODULE_CLUSTERS[1]; // UI 组件
  if (lower.includes("style") || lower.includes("theme") || lower.endsWith(".css") || lower.endsWith(".scss")) return MODULE_CLUSTERS[2]; // 样式主题
  if (lower.includes("api") || lower.includes("service") || lower.includes("client")) return MODULE_CLUSTERS[3]; // 数据请求
  if (lower.includes("util") || lower.includes("store") || lower.includes("state") || lower.includes("lib")) return MODULE_CLUSTERS[4]; // 状态工具
  if (lower.includes("doc") || lower.endsWith(".md") || lower.endsWith(".json")) return MODULE_CLUSTERS[5]; // 文档配置
  return MODULE_CLUSTERS[0];
}
```

### 3.2 系统与后端项目（Rust / Go / Java / Python）
```javascript
function mapFileToModule(filePath) {
  const lower = filePath.toLowerCase();
  if (lower.includes("server") || lower.includes("controller") || lower.includes("cmd") || lower.includes("main")) return MODULE_CLUSTERS[0]; // 调度入口
  if (lower.includes("domain") || lower.includes("service") || lower.includes("handler") || lower.includes("logic")) return MODULE_CLUSTERS[1]; // 核心引擎
  if (lower.includes("view") || lower.includes("template") || lower.includes("dto") || lower.includes("proto")) return MODULE_CLUSTERS[2]; // 协议/视图
  if (lower.includes("driver") || lower.includes("adapter") || lower.includes("plugin") || lower.includes("client")) return MODULE_CLUSTERS[3]; // 外部适配
  if (lower.includes("db") || lower.includes("storage") || lower.includes("dao") || lower.includes("config")) return MODULE_CLUSTERS[4]; // 存储底座
  if (lower.includes("doc") || lower.includes("test") || lower.endsWith(".md") || lower.endsWith(".toml")) return MODULE_CLUSTERS[5]; // 文档测试
  return MODULE_CLUSTERS[0];
}
```

---

## 4. 最佳实践建议

1. **模块数量控制在 4 ~ 8 个**：过多会导致中心画布拥挤，过少则无法区分层次；
2. **名称避免冷冰冰的路径名**：使用直观通俗的业务中文名称（如“分析引擎”、“平台适配”而非 `src/domain/v2`）；
3. **颜色交错搭配**：使用 `#4ecdc4`（绿松石）、`#ff6b6b`（珊瑚红）、`#ffd93d`（明黄）三色交替，保持生动的手绘涂鸦氛围。
