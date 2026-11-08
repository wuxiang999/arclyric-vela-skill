---
name: vela-quickapp
description: 小米 Vela OS 快应用（手环/手表 JS App）开发与排错技能。用于创建项目、写 .ux 页面、manifest 配置、flex 布局、防文字裁切、@system.interconnect 手环↔手机通道、XMS Wearable SDK、aiot-toolkit 打包 rpk、与 Android 伴侣 App 同包名同签名交付。当用户提到 小米手环/手表 快应用、Vela、rpk、aiot-toolkit、designWidth、表盘式 UI、interconnect、穿戴端 App 时使用。
---

# Vela 快应用开发

面向小米手环 / 手表（Vela OS）的 JS 快应用。类 Web 的 `.ux`（template + style + script），Flexbox 布局，`@system.*` 系统接口，产物是 `.rpk`。

## 0. 开工前先确认三件事

1. **目标设备与 designWidth**：手环 9 Pro 是 336×480、`designWidth: 192`（缩放 1.75×）；手表 S5 480、S3/S4 466、REDMI Watch 5 432。以项目 `manifest.json` 为准，别照抄别的项目。
2. **工具链版本**：`package.json` 里的 `aiot-toolkit` 版本决定哪些 CSS/组件可用。版本不同行为会变，遇到"文档说支持但编译报错"以编译器为准。
3. **交付形态**：只出 rpk，还是 rpk + Android 伴侣 App。两者要**同包名、同签名**，否则 `@system.interconnect` 直接连不上。

## 1. 硬约束（违反必炸）

- **组件白名单**：`div list list-item text image input scroll swiper switch slider progress picker stack span marquee barcode qrcode chart image-animator`。禁止任何第三方 UI 库。
- **API 白名单**：`@system.*`（router/app/fetch/storage/device/audio/prompt/sensor/vibrator/network/brightness/volume/battery/geolocation/record/file/crypto/configuration/interconnect/messagecenter）。用哪个就必须在 `manifest.json.features` 里声明。
- **CSS 只认 class 选择器**：不要 `#id`、`.a .b`、`.a > .b`、`:hover`、`::before`、`*`、`[attr]`，不要嵌套、不要 Less/Sass。
- **`div`/`scroll` 默认 `flex-direction: row`**，竖向页面根节点必须显式 `flex-direction: column`。这是"一行多个元素挤在一起"的第一大原因。
- **`<template>` 只能有一个根节点**。
- **`onDestroy` 必须清定时器和监听**。手环内存小，泄漏会白屏重启。
- **`text` 的 `lines` 是 style 不是 attribute**：`<text lines="1">` 编译能过但无效，要写在 CSS 里 `lines: 1;`。

## 2. 项目骨架

```
src/
  manifest.json        # package / router / features / designWidth
  app.ux               # 全局生命周期
  pages/<name>/index.ux
  common/scripts/*.js  # 纯 JS 模块（import 相对路径）
  common/images/*.png  # 只支持 PNG，不支持 SVG
```

`manifest.json` 关键项：

```json
{
  "package": "com.vendor.app",
  "versionName": "1.0.1",
  "versionCode": 2,
  "minPlatformVersion": 1200,
  "deviceTypeList": ["watch"],
  "features": [{ "name": "system.router" }, { "name": "system.interconnect" }],
  "config": { "designWidth": 192, "logLevel": "log" },
  "router": { "entry": "pages/boot", "pages": { "pages/boot": { "component": "index" } } }
}
```

## 3. 布局与文字：防"被吞一小截"

排版问题 90% 出在这几条，写完必须过一遍：

1. **`<text>` 上永远不要设 `height`**，高度交给 `line-height`。
2. **`line-height / font-size ≥ 1.35`**（中文正文建议 1.5，标题 ≥1.3）。1.2 是危险区。
3. **容器高度 ≥ 行数 × line-height + 2~4dp**；flex 子项加 `flex-shrink: 0`。
4. **手动折行的字数必须算**：`floor(可用宽 / 字号 × 0.96)`，不要拍脑袋。估算多 1 个字 → 二次折行 → 撑破容器 → 上下被裁。
5. **固定行高的容器里文本锁一行**：CSS 写 `lines: 1;`。
6. 小数 dp 在 1.75× 缩放下会取整抖动，能取整就取整，不能就多留 1–2dp。

详细推导、代码片段、各平台同类问题的开源参考见 `references/layout-text.md`。

## 4. 手环 ↔ 手机通道

走 `@system.interconnect`（手环）↔ 小米运动健康 ↔ Android 伴侣（XMS Wearable SDK），**不要自己直连 BLE**。

铁律：

- `connect.send` 的 `data` **必须对象**，统一 `{ data: { data: <JSON 字符串> } }`。
- 协议用 UTF-8 JSON，带 `v` 版本字段；**每条消息都带 type**。
- 手环 JS 堆和通信缓冲都小：单包 ≈100 字、发一包等一包回执；词库上报 300 字/包、间隔 ~90ms。
- 手机侧 `sendMessage` 连续失败 3 次 → 判定节点失效，作废并重新发现注册（否则会永远"发送失败"）。
- 播放进度推算要守 `lastPositionUpdateTime in 1..now`，否则暂停时 delta 变成天文数字，直接跳到结尾。

协议样例、分片/回执、Kotlin 侧实现、排错日志对照见 `references/interconnect.md`。

## 5. 构建与交付

```bash
bash tools/build-rpk.sh debug     # 调试签名
bash tools/build-rpk.sh release   # 正式签名
```

- `aiot build` 会**清空 dist/**，交付目录不要直接用它；用项目脚本包一层。
- 版本号要**三处同步**：`package.json`、`src/manifest.json`（versionName + versionCode）、`android/app/build.gradle.kts`。
- 同版本覆盖安装可能被设备安装器跳过 → 每次验证都升 versionCode。
- Gradle 构建要串行低内存，先 `pkill -f "[G]radleDaemon"`，再加 `--no-daemon --max-workers=2`。

完整命令、签名、APK/RPK 同名交付、常见构建报错见 `references/build-release.md`。

## 6. 排错速查

| 现象 | 先查 |
|---|---|
| 启动白屏 / 白方块闪退 | 删掉可疑的设备配置文件（如 `config-watch.json`）；看 debug 日志卡在哪个生命周期 |
| 一行里多个元素重叠/互盖 | 根容器缺 `flex-direction: column`；或同一行里放了两个块级元素 |
| 文字上下被裁 | text 设了 height、line-height 太紧、容器不够高、折行估算偏大 |
| 文字左右被裁 | 折行字数超了；容器 padding 没算进可用宽 |
| 列表项点不开 | `list/list-item` 在部分机型不可靠；改 `div` + 手写分页，且整行和文字都绑点击 |
| `<switch>` 不响应 | 手环上不可靠；改成整行胶囊，点一下切状态，状态写进文字 |
| 加载动画不跑 | 没有 `@keyframes`；用 JS 定时器换 class / 换宽度档位 |
| 手环收不到手机消息 | 节点失效；手机侧失败计数 + reset + 重新发现；确认 `data` 是对象嵌套 |
| 暂停后进度跳结尾 | 位置推算时 `lastPositionUpdateTime == 0` 未守卫 |
| 改了代码设备没变化 | 版本号没升，安装器跳过了覆盖安装 |

## 7. 自检

运行附带 linter（对 `src/` 全量扫描）：

```bash
python3 scripts/lint_ux.py /path/to/project/src
```

它检查：不支持的 CSS（`@media`/`@keyframes`/复合选择器/`border-*-style`）、`text` 上的 `lines` 属性误用、text 类设 height、行高比过紧、根容器缺 `flex-direction`、`config-watch.json` 残留。`--strict` 时 warning 也退出非 0。

## 来源与许可

- 平台事实与白名单：小米官方文档 <https://iot.mi.com/vela/quickapp/>，以及官方 `create-vela-workflow`（MIT，`templates/.kiro/skills/vela-js-app/` 与 `.claude/rules/`）。
- 布局/文字/通道部分为本项目真机踩坑总结，参考了 Compose `LineHeightStyle`、Flutter `TextHeightBehavior`、Tabby #11511 等公开实现（见 `references/layout-text.md` 链接）。
