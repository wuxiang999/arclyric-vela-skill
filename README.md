<div align="center">

# vela-quickapp

**小米 Vela 快应用（手环 / 手表）开发与排错 skill**

给 AI agent 用的 `.ux` 开发知识库 + 静态检查器

<p>
  <a href="https://github.com/wuxiang999">
    <img src="https://avatars.githubusercontent.com/u/182329103?v=4" width="40" height="40" alt="LANHU199">
  </a>
  <br>
  <sub>by <a href="https://github.com/wuxiang999">LANHU199</a></sub>
</p>

</div>

---

## 这是什么

一个 [OpenCode](https://opencode.ai) / Claude Code 风格的 skill（`SKILL.md` + `references/` + `scripts/`），让 agent 在写小米手环 / 手表快应用时，不用每次从官方文档重新猜：

- 哪些组件、API、CSS 真的能用；
- 文字为什么会被裁掉一截，怎么算折行；
- 手环和手机怎么通过 `@system.interconnect` 通信，为什么 `sendMessage failed`；
- 怎么出 RPK / APK，签名和版本号怎么对齐。

知识来自官方文档 + 真机踩坑，不是从文档抄一遍。

## 安装

### OpenCode

```bash
git clone https://github.com/wuxiang999/vela-quickapp.git ~/.agents/skills/vela-quickapp
# 如果 skill 目录不在默认扫描路径，软链一下：
ln -sfn ~/.agents/skills/vela-quickapp ~/.opencode/skills/vela-quickapp
```

skill 在会话启动时扫描，装完开新会话才出现在列表里。

### Claude Code

```bash
git clone https://github.com/wuxiang999/vela-quickapp.git ~/.claude/skills/vela-quickapp
```

## 触发

用户提到这些词时会自动匹配：

> 小米手环 / 手表 / 快应用 / Vela / rpk / aiot-toolkit / designWidth / 表盘式 UI / interconnect / 穿戴端 App

也可以直接说「用 vela-quickapp skill 改播放页」。

## 内容

```
SKILL.md                     路由 + 7 条铁律 + 排错速查表
references/
  platform.md                设备与 designWidth、CSS 支持矩阵、组件可用性
  layout-text.md             防裁切：行盒 vs 墨迹、折行公式、无 keyframes 的加载动画
  interconnect.md            协议、分包回执、节点自愈、日志对照
  build-release.md           rpk / apk、版本三处同步、Gradle 低内存
scripts/
  lint_ux.py                 对 .ux 做静态检查
```

## 静态检查器

```bash
python3 scripts/lint_ux.py /path/to/project/src
python3 scripts/lint_ux.py /path/to/project/src --strict   # warning 也算失败
```

检查项：

| 类别 | 内容 |
|---|---|
| CSS | `@media` / `@keyframes` / `@import`、复合选择器、`border-*-style`、`box-shadow` |
| 模板 | `text` 上误用 `lines` 属性（它必须是 style） |
| 排版 | text 类同时设 `font-size` 和 `height`、`line-height / font-size < 1.3` |
| 布局 | 根容器有多个子节点却没有 `flex-direction` |
| 文件 | `src/config-watch.json` 残留 |

退出码：`0` 通过，`1` 有 error（`--strict` 时 warning 也算）。

## 核心结论（节选）

- `div` / `scroll` 默认 `flex-direction: row`，竖向页面根节点不写 `column` 就会挤成一行；
- `text` 的 `lines` 是 **style 不是 attribute**，写错位置编译能过但不生效；
- 手环 9 Pro 上 `list` / `list-item` / `scroll` / `switch` 不可靠，改 `div` + 手写分页 + 整行胶囊；
- 这个 toolkit 版本没有 `@media` / `@keyframes`，动画只能用 JS 定时器换 class；
- 手动折行必须按 `floor(可用宽 / 字号 × 0.96)` 算，多放一个字就会二次折行、撑破容器；
- `connect.send` 的 `data` 必须是对象，统一 `{ data: { data: <json> } }`；
- 手机侧 `sendMessage` 连败 3 次要作废节点重连，否则永远发不出去；
- 进度推算不守 `lastPositionUpdateTime in 1..now`，暂停会瞬间跳到结尾。

## 来源与许可

- 平台事实与白名单：官方文档 <https://iot.mi.com/vela/quickapp/>，以及官方 `create-vela-workflow`（MIT）的 `.kiro/skills/vela-js-app/` 与 `.claude/rules/`；
- 布局与通信部分为本项目真机踩坑总结，公开依据列在 `references/layout-text.md` 与 `references/interconnect.md`；
- 本仓库自身：[MIT](LICENSE) © 2026 LANHU199。

配套项目：[弧光歌词 ARCLYRIC](https://github.com/wuxiang999/arclyric)
