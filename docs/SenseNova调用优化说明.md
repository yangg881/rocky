# SenseNova 调用优化说明

## 官方接口

系统使用官方 OpenAI 兼容 Base URL `https://token.sensenova.cn/v1`，通过 `Authorization: Bearer <API Key>` 鉴权。文本与多模态请求使用 `/chat/completions`，图像生成使用 `/images/generations`。

## 固定模型分工

- `sensenova-6.7-flash-lite`：简历文档/截图结构化、JD 网页清洗与截图 OCR。
- `deepseek-v4-flash`：读取结构化简历和 JD，完成排序、关键词对齐与表述优化。系统提示明确禁止新增公司、岗位、项目、日期、学历、技能、证书和未经提供的数字。
- `sensenova-u1-fast`：保留为商务封面、对比图和宣传配图生成接口；生成后应下载到内存并写入 TOS-C，不在服务器落盘。

## 限流与重试

所有模型共享一个异步并发信号量，默认最大并发 2；请求之间默认至少间隔 1.2 秒。临时失败使用指数退避和随机抖动，默认最多 3 次。相关参数均在 `.env` 中可调。

模型累计调用次数写入 TOS-A 的 `metrics/models.json`，管理员后台实时读取。生产环境不得启用 `AI_MOCK`。

官方文档：https://platform.sensenova.cn/docs

