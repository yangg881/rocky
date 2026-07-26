# 云端 ↔ 本地 同步机制

**单一事实源 = 本地 git 仓库。** 服务器 `/opt/jd-resume-ai` 是「只读消费端」，
禁止在服务器上直接编辑代码（历史上被手改过，导致 `radar_sources.py` 分叉）。

## 日常改动流程

1. 在本地改代码 → `git add` / `git commit`。
2. 部署到服务器（备份 → 上传 → 逐文件 md5 校验 → import 检查 → 重启 → 冒烟）：
   ```bash
   export SYNC_HOST=115.120.206.64 SYNC_USER=root SYNC_PASSWORD=***   # 建议改用 SYNC_KEY 密钥
   python deploy/sync_to_server.py --restart
   ```
   - 任一文件 md5 不一致 → 中止且不重启，服务器保持原状（备份在 `.deploy-backups/sync-<时间戳>`）。
   - `--dry-run` 只列将推送的文件；不带 `--restart` 只推文件不重启。
3. 随时核对是否一致（只读，检测服务器是否被手改 / 漏部署）：
   ```bash
   python deploy/check_parity.py     # 输出 "in sync: N/N" 或列出 DRIFT/MISSING
   ```

## 同步范围

`sync_to_server.py` 只推送**服务器实际运行的文件**：`app/**`（含 `app/static/` 前端）
加顶层 `config.py / observability.py / security.py / self_test.py / requirements.txt / pyproject.toml`。
不推送：`.env`（仅服务器有）、`data/`、`node_modules/`、`android/`、`src/`、构建产物。

## 凭据与安全

- 凭据只从环境变量读，**不入库**。优先 `SYNC_KEY`（SSH 私钥路径）而非 `SYNC_PASSWORD`。
- 待办（见实施方案 §8）：轮换 root 密码 / TOS / SenseNova / JWT 密钥，SSH 改密钥登录并禁用密码登录。

## Android

Android 不经此脚本部署。改 `android/**` 后需在**装有 JDK 17 + Android SDK 的构建机**上：
`keystore.properties` 就位 → `./gradlew assembleRelease` → 分发签名 APK。
`app/version` 接口的下载地址与版本号仍在服务端配置。
