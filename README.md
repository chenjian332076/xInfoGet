# xInfoGet - X 每日技术深度资讯

从 X (Twitter) 自动抓取互联网行业领袖的深度技术见解，过滤营销垃圾内容，仅保留含高质量文章链接的推文，生成结构化中文日报。

## 核心关注方向

- **AI 发展深度见解** — CEO/CTO/研究员的一手观点和战略分析
- **AI 工作提效实践** — 真实的工具使用方法、工作流改进案例
- **技术新思路** — 创新架构、开发范式变革

## 可信来源

优先搜索以下行业领袖和机构：

| 来源 | 身份 |
|------|------|
| @sama | Sam Altman, OpenAI CEO |
| @karpathy | Andrej Karpathy, AI 研究 |
| @AnthropicAI | Anthropic / Claude |
| @OpenAI | OpenAI 官方 |
| @ylecun | Yann LeCun, Meta AI |
| @rauchg | Guillermo Rauch, Vercel CEO |
| @AndrewYNg | Andrew Ng, AI 教育 |

## 内容过滤规则

严格排除以下类型：
- 骗订阅/骗关注（"XX 页 PDF"、"DM me"）
- 空洞营销（"每月多赚 $XX"）
- replies/likes 异常比 > 0.5 的水军推文
- 无文章链接的空泛内容

## 报告目录

每日报告存放在 [reports/](./reports/) 目录下，格式为 `report_YYYY-MM-DD.md`。

| 日期 | 报告 |
|------|------|
| 2026-04-18 | [report_2026-04-18.md](./reports/report_2026-04-18.md) |

## 工作方式

通过 Cursor IDE 内置浏览器（MCP Browser）自动化完成：

1. 登录 X 平台
2. 按可信来源和话题关键词搜索（`filter:links` + `min_faves` 过滤）
3. 提取推文数据并应用质量过滤规则
4. 用 WebFetch 验证文章链接的实际内容深度
5. 生成结构化 Markdown 日报

## License

MIT
