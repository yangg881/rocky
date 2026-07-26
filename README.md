# 职达简历

多用户 AI 岗位 JD 简历适配系统。提供基础简历管理、岗位解析、忠于事实的 AI 改写、Word/PDF 导出、个人历史与独立管理员后台。

## 架构

- FastAPI 单服务，用户端和管理端同源交付
- TOS-A 存系统 JSON 数据和应用计数
- TOS-B 存原始简历与生成文件
- TOS-C 存简历/JD 截图和图像素材
- SenseNova 使用 OpenAI 兼容接口，统一 Bearer API Key
- 服务只监听 `127.0.0.1` 自动空闲端口，由 Nginx 暴露 `/resume-ai/`

## 部署

1. 将项目放入独立目录 `/opt/jd-resume-ai`。
2. 复制 `.env.example` 为 `.env` 并填写三组独立 Bucket、SenseNova Key、管理员账号密码和随机 JWT Secret。
3. 执行 `chmod +x deploy.sh && ./deploy.sh`。
4. 根据服务器现有 Nginx 结构，仅增加 `/resume-ai/` 反向代理到 `.runtime-port` 中记录的本地端口。
5. 执行 `scripts/self_test.py` 完成线上验收。

## 安全说明

需求指定的“仅凭用户名重置密码”流程无法证明账号所有权，任何知道用户名的人都能重置该用户密码。系统按需求实现，但正式开放给不受信任公众前，建议增加恢复码或人工审核流程。

所有密钥只允许出现在服务器 `.env` 中；`.env` 已加入 `.gitignore`。请定期轮换服务器密码、TOS 密钥、SenseNova Key 与 JWT Secret。

