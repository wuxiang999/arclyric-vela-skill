# 手环 ↔ 手机通道

## 架构

```
手环快应用 (@system.interconnect)
        ↕  小米运动健康
Android 伴侣 App (XMS Wearable SDK: com.xiaomi.xms.wearable)
        ↕
        音乐服务 / 词库 / 网络
```

不要在手环端直连 BLE。手环没有扬声器，音频由手机播放，手环只做控制与显示。

## 包名与签名

- 手环 `manifest.json.package` 必须等于 Android `applicationId`。
- 两边必须**同一签名**。
- 任一不符：能发现设备、能建通道，但消息发不出去或收不到，日志只会给你 `sendMessage failed`。

## 协议

```json
{ "v": 1, "type": "lyrics.chunk", "ts": 1730000000000,
  "payload": { "id": "song-1", "index": 0, "total": 11, "text": "..." } }
```

- `v` 版本号，`type` 必填，`payload` 可为空对象。
- 所有字符串 UTF-8，不要塞二进制。
- 手机→手环的 `data` 必须对象，统一包一层：

```js
// 手环端发送
connect.send({
  data: {
    data: JSON.stringify(envelope)
  }
})
```

```kotlin
// 手机端接收
val text = String(bytes, Charsets.UTF_8).trim()
```

## 分包与回执

手环 JS 堆小、通信缓冲小：

| 内容 | 大小 | 节奏 |
|---|---|---|
| 歌词分片 | ~100 字/包 | 发一包，等一包 ACK（超时也推进，不重试整首） |
| 词库上报 | ~300 字/包 | 间隔 ~90ms |
| 单条状态 | 极小 | 直接发，失败自愈 |

```js
// 手环：逐包回执
transport.send(protocol.envelope('ack', {
  for: 'chunk', id: id, i: index, ok: true
}))
```

```kotlin
// 手机：收到 ack 才发下一包，超时也推进
private fun sendPendingPacket() {
    if (pendingIndex >= total) return finishPending(total)
    val index = pendingIndex
    transmit(packets[index])
    handler.postDelayed({
        if (pendingIndex == index) {   // 没等到回执
            pendingIndex++             // 推进，不整首重发
            sendPendingPacket()
        }
    }, PACKET_TIMEOUT_MS)
}
```

组装侧要按 `id + total + index` 拼，超时清理（15s），并丢弃旧歌迟到的分片：

```js
if (!state.mock && state.currentSong &&
    (title + '|' + artist) !== state.currentSong) {
  return   // 迟到的旧歌歌词，绝不覆盖当前歌
}
```

## 节点自愈

`sendMessage` 连续失败通常意味着节点已失效（手环断连、通道被系统回收）。必须作废重连：

```kotlin
private var failures = 0L

messageApi.sendMessage(id, bytes)
    .addOnSuccessListener { failures = 0 }
    .addOnFailureListener { error ->
        failures++
        if (failures <= 2 || failures % 20L == 0L) onStatus("发送失败：${error.message}")
        if (failures >= 3L) reset("连接疑似失效，重新建立通道")
    }

private fun reset(reason: String) {
    val id = nodeId
    registered = false
    nodeId = null
    connecting = false
    failures = 0
    lastAttempt = 0L
    if (id != null) runCatching { messageApi.removeListener(id) }
    onStatus(reason)
}
```

`ensureConnected` 每 2 秒检查一次，`lastAttempt` 控制重试间隔，重连后重新 `register`。

## 播放状态

- 手机监听 `MediaSession` / `PlaybackState`，把手环需要的字段压成 STATE 消息：标题、歌手、专辑、时长、位置、是否播放。
- 手环本地按 `anchorAt` 推算进度。
- **必须守卫** `lastPositionUpdateTime`：

```kotlin
val updatedAt = state.lastPositionUpdateTime
val position = if (updatedAt in 1..System.currentTimeMillis()) {
    state.position + if (state.state == STATE_PLAYING) {
        SystemClock.elapsedRealtime() - state.lastPositionUpdateTime
    } else 0L
} else state.position
```

`lastPositionUpdateTime == 0` 时直接把时间戳当偏移，delta 会变成天文数字，暂停瞬间跳到结尾。

## 排错日志对照

| 日志 | 含义 |
|---|---|
| `发现设备：小米手环9 Pro` | 节点发现 OK |
| `消息通道已就绪` | 注册 OK |
| `歌词已发送（11 包，手环未回执）` | 手机发出，手环没回 ACK → 手环端没收到或没解析 |
| `发送失败：sendMessage failed` | 节点失效 / 包名签名不符 / 手环 App 未在前台 |
| 全程没有 `手环已连上` | 手环→手机方向没通，先查手环端 `connect.send` 的 `data` 结构 |
| `词库请求没有回应` | 同上，或手环端处理 `library.request` 时异常 |

## 调试手段

- 手机端做一个日志页（内存环形缓冲 + 定时刷新），不要只靠 logcat。
- 手环端加轻量 `debug.mark(tag, msg)`，把关键生命周期和收发记到 storage，异常时可导出。
- 双向 ping/pong：手机每 10s 发 ping，手环回 pong，任一方向断都能在 20s 内发现。
