# 平台事实速查

## 设备与 designWidth

| 设备 | 像素 | 形状 | 常见 designWidth |
|---|---|---|---|
| 小米手环 9 Pro | 336×480 | 矩形/跑道 | 192（缩放 1.75×） |
| 小米手环 9 | 192×490 | 跑道 | 192 |
| Xiaomi Watch S5 | 480×480 | 圆 | 480 |
| Watch S3 / S4 / H1 | 466×466 | 圆 | 466 |
| REDMI Watch 5 | 432×514 | 方 | 432 |

逻辑高度 = 像素高 / (像素宽 / designWidth)。9 Pro：480 / 1.75 ≈ **274dp**。算布局前先算这个数，很多"挤"就是固定高度之和超过了它。

## 单位

- `px`：相对 designWidth 的缩放单位（类似 rem），**不是物理像素**。
- `dp`：密度无关单位。项目里统一用一种，别混。
- `%`：相对父容器。
- 盒模型是 `border-box`：`height` 含 padding 和 border，不支持 `box-sizing`。

## CSS 支持矩阵（aiot-toolkit 1.2.x 实测）

| 特性 | 状态 |
|---|---|
| class 选择器 | ✅ |
| 元素 / id / 后代 / 子 / 伪类 / 通配 / 属性选择器 | ❌ |
| 嵌套、Less/Sass | ❌ |
| `@media` | ⚠️ 部分版本支持，先编译验证再用（本项目 1.2.1-alpha.0 不可用） |
| `@keyframes` / `animation` | ❌（动画用 JS 定时器换 class/宽度） |
| `border-left-style` / `border-right-style` | ❌（`border-width` / `border-color` 可以） |
| `border-style: solid` | ✅ |
| `box-shadow` | ❌ |
| `overflow` | ⚠️ 不要依赖它做裁切控制 |
| `position: relative/absolute` | ✅ |
| `flex` / `flex-grow` / `flex-shrink` | ✅ |
| `line-height` / `lines` / `text-overflow` | ✅（`lines` 是 style） |

## 组件可用性（9 Pro 实测）

| 组件 | 结论 |
|---|---|
| `div` / `text` / `image` | 稳定，主力 |
| `list` / `list-item` | 不可靠（布局错乱、点击丢失），建议 `div` + 手写分页 |
| `scroll` | 不可靠，长内容改分页 |
| `switch` / `slider` | 不可靠，改整行胶囊点击 |
| `input` | 可用，但手环输入体验差，尽量少用 |

## 数据对象

| 对象 | 作用域 |
|---|---|
| `public` | 可被外部传入覆盖 |
| `protected` | 可被应用内页面覆盖 |
| `private` | 仅页面内 |
| `data` | 组件级 |

## 生命周期

`onInit → onReady → onShow → onHide → onDestroy`

- 定时器、订阅、监听一律在 `onDestroy` 清理。
- 页面间传参不可靠时（手环常见），改成"本页内联展开"而不是 `router.push` 带参数。

## 存储

`@system.storage` 是 KV，值只能是字符串。存对象要 `JSON.stringify`，读出来要容错解析（空串、旧版本、损坏数据都要有默认值）。
