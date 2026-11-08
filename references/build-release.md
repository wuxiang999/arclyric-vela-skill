# 构建与交付

## 工具链

- 项目锁定 `aiot-toolkit` 版本（例如 `1.2.1-alpha.0`），不要随手升级：编译器行为会变，CSS 支持矩阵也会变。
- `node >= 16` 即可，构建不依赖 Android SDK。
- 出包唯一入口是项目脚本（示例 `tools/build-rpk.sh debug|release`），不要直接 `aiot build`——它会清空 `dist/`。

## 版本号三处同步

| 文件 | 字段 |
|---|---|
| `package.json` | `version` |
| `src/manifest.json` | `versionName` + `versionCode` |
| `android/app/build.gradle.kts` | `versionName` + `versionCode` |

- `versionCode` 每次验证都 +1。**同版本覆盖安装可能被安装器跳过**，表现为"改了代码但设备没变化"。
- 手环端设置页/关于页显示版本号，方便确认装的是新包。

## RPK

```bash
bash tools/build-rpk.sh debug     # 调试签名，快速验证
bash tools/build-rpk.sh release   # 正式签名，交付
```

脚本要做的事：

1. `rm -rf dist` 之外的中间产物，保留交付目录。
2. 调用 `aiot build` / `aiot release`。
3. 把编译器生成的 `com.vendor.app.debug.1.0.1.rpk` 重命名为 `AppName-1.0.1-debug.rpk`。
4. 把交付说明 `README.md` 一起复制进 `dist/`。

## APK

```bash
cd android
pkill -f "[G]radleDaemon" || true
bash ./gradlew :app:assembleRelease :app:assembleDebug \
  --no-daemon --console=plain --max-workers=2 \
  -Dorg.gradle.jvmargs="-Xmx1536m -Dfile.encoding=UTF-8" \
  -Pandroid.aapt2FromMavenOverride=$(which aapt2)
```

- 必须串行低内存，否则容易被系统 SIGKILL。
- `aapt2` 用 Termux 的，不要用 Gradle 下载的（下载会失败）。

## 交付目录

```
dist/
  AppName-1.0.1-release.rpk
  AppName-1.0.1-debug.rpk
  AppName-1.0.1-release.apk
  AppName-1.0.1-debug.apk
  SHA256SUMS.txt
  README.md
```

- `cp -n` 不会覆盖旧文件 → 用 `cp -f`，并删掉旧版本产物。
- 交付前重算 `SHA256SUMS.txt`。
- 安装顺序：先装 Android 伴侣并授权、确保与手环配对，再装 rpk；两边版本要匹配。

## 常见构建报错

| 报错 | 处理 |
|---|---|
| `Style name 'border-left-style' is not supported` | 删掉，只保留 `border-left-width` + `border-left-color` |
| `Component 'text' does not support attribute 'lines'` | `lines` 是 style，写进 CSS |
| `config-watch.json does not exist ...` | 只是 warning；但如果加了该文件导致白屏，就删掉别恢复 |
| `ERR_PNPM_NO_MATCHING_VERSION` | 锁定的 toolkit 版本在镜像里没有，换 registry 或换版本 |
| 打包成功但设备装不上 | versionCode 没升 / 签名不一致 / 包名冲突 |
| Gradle `SIGKILL` | 先杀 daemon，降并发，降 Xmx |
