# TOS 资源使用说明

## 三桶隔离

- TOS-A：`users/`、`indexes/`、`resumes/`、`generations/`、`audit/`、`metrics/`。存系统数据、用户索引、业务记录、审计和应用计数。
- TOS-B：`users/{user_id}/originals/` 与 `users/{user_id}/generated/`。存原始简历、Word 与 PDF 成品。
- TOS-C：`users/{user_id}/resume-images/` 与 `users/{user_id}/jd-images/`。存 OCR 输入和图像素材。

所有键外层还有项目专属 `TOS_PREFIX`，避免误操作其他项目。三个 Bucket 必须互不相同，部署脚本会检查并按需创建，不会清理任何现有 Bucket。

## 下载与带宽

应用先校验用户所有权，再返回短期 TOS 签名链接。浏览器直接连接 TOS，不经过服务器 1M 出口。签名默认有效 3600 秒，可通过 `TOS_PRESIGN_SECONDS` 调整。

## 用量仪表盘

容量通过实时遍历项目对象汇总；请求次数和流出字节为本应用侧计数，用于趋势与预警。公网签名链接可能被重复使用，因此流出值是估算，最终计费数据以火山引擎控制台为准。三类阈值分别由 `TOS_WARNING_BYTES`、`TOS_WARNING_REQUESTS`、`TOS_WARNING_EGRESS_BYTES` 配置。

## 运维

删除用户时只清理该用户 ID 下的 A/B/C 对象；删除生成记录时只清理对应 Word、PDF 与记录对象。禁止使用 Bucket 全量清空命令。建议在控制台配置生命周期规则，将审计与已删除任务的历史版本按合规周期清理。

