# 布局与文字：防裁切完整版

## 为什么会被"吞一小截"

文本渲染有两套盒子：

1. **字形墨迹（ink）**：字真正画出来的范围。
2. **行盒（line box）**：布局分配的高度，由 `line-height` 决定。

行盒比 ink 小 → 上下切；容器比内容小 → 边缘切；折行估算错误 → 多出一行 → 把整块内容顶出容器（flex 居中时上下各切一半，看起来就是"被吞"）。

同类问题的公开证据：

- Android/Compose：`LineHeightStyle.Trim.Tight` 官方明确警告会切掉高字符；安全组合是 `includeFontPadding = false` + `Trim.Both` + `Mode.Fixed`。<https://developer.android.com/reference/kotlin/androidx/compose/ui/text/style/LineHeightStyle>
- Flutter：`TextStyle(height: 1)` + `ellipsis` 会切掉基线以下（flutter/flutter#153988）；修法是 `TextHeightBehavior(applyHeightToFirstAscent: false)` 或 `StrutStyle(forceStrutHeight: true)`。<https://github.com/flutter/flutter/issues/153988>
- 终端渲染器：行高等于字体度量时下伸部被切，作者修法是 line padding ≥ 1。<https://github.com/Eugeny/tabby/issues/11511>
- 字体度量本身：<https://googlefonts.github.io/gf-guide/metrics.html>、<https://github.com/arrowtype/vertical-metrics>

## 五条铁律

### 1. text 不设 height

```css
/* ❌ 行盒被钉死，ink 一超就切 */
.row-title { height: 17dp; line-height: 17dp; }

/* ✅ 高度由 line-height 决定 */
.row-title { line-height: 18dp; }
```

### 2. 行高比 ≥ 1.35

| 场景 | font-size | line-height |
|---|---|---|
| 正文/歌词 | 13dp | 19–20dp |
| 大字歌词 | 18dp | 25–26dp |
| 标题 | 19dp | 26dp |
| 辅助文字 | 10dp | 15dp |

中文方块字几乎占满 em，西文 1.2 的规则不能直接套。

### 3. 容器容量要算

```
容器高 ≥ 行数 × line-height + 上下 padding + 2dp 余量
```

固定行高容器里的文本必须锁行：

```css
.row-title { lines: 1; }
```

注意：`lines` 是 **style**。`<text lines="1">` 编译不报错但不生效。

### 4. 手动折行按宽度算，不按手感

```js
// 可用宽 = designWidth - 左右 padding - 边框 - 图标/标记占位
const LYRIC_WIDTH = 168
const ON_SIZE = [14.5, 16.5, 18]

function unitsFor(size) {
  // 0.96 是渲染误差余量；宁可少放一个字，也不要多放一个导致二次折行
  return Math.max(6, Math.floor((LYRIC_WIDTH / size) * 0.96))
}
```

反例：可用宽 170dp、字号 14.5dp，`170 / 14.5 = 11.7`，却允许 12 个字 → 每行都多折一行。

多语言混排按显示宽度折算：中文/日文/韩文 1.0，西文 0.55，数字 0.55，全角标点 1.0。

### 5. 固定高度容器里的内容永远 `flex-shrink: 0`

flex 默认允许收缩，行数一多就被压扁，文字先被切。

## 常见"看起来像 bug"的布局

### 一行里元素互相覆盖

`div` 默认 `flex-direction: row`。想竖排必须写：

```css
.page { flex-direction: column; }
```

### 文字居中但整体偏下

字体 ascent > descent，视觉重心偏上。用 `align-items: center` 居中容器，不要用 padding 手调。

### 列表一行多个歌名

`list` 在 9 Pro 上不可靠；改 `div` 容器并显式 `flex-direction: column`：

```css
.list { width: 100%; flex-direction: column; }
.row { width: 100%; height: 36dp; flex-direction: row; align-items: center; }
```

### 分页代替滚动

```js
const PAGE_SIZE = 5
this.view = this.all.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE)
```

固定行高 + 固定条数 = 高度可预测，不会裁切。

## 加载动画（没有 @keyframes）

用定时器换宽度档位 + 省略号：

```js
this.loadTimer = setInterval(() => {
  const step = (this.dotStep + 1) % 4
  this.dots = ['', '·', '··', '···'][step]
  const seq = [20, 40, 60, 80, 60, 40]
  this.loadStep = (this.loadStep + 1) % seq.length
  this.loadWidth = seq[this.loadStep]
}, 320)
```

```html
<div class="loading-track">
  <div class="fill fill-w{{loadWidth}}"></div>
</div>
```

`fill-w0`…`fill-w100` 每档写一条 class。不要动态拼 `width: {{n}}%` 内联样式，部分版本不生效。

真实进度（比如分包接收）用同一个宽度档位体系，向下取整到 10 的倍数，避免显示得比实际多。

## 自检

```bash
python3 scripts/lint_ux.py <项目>/src
```

重点看：text 类设置 height、行高比 < 1.3、估算字数与字号不匹配、固定行高容器未锁行。
