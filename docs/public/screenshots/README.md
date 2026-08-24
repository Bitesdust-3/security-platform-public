# 项目截图规划

本目录只存放真实运行环境截图，不使用模拟图片或设计稿冒充系统截图。

## 推荐截图顺序

1. `01-login.png`：登录页面，隐藏真实密码和敏感环境信息。
2. `02-dashboard.png`：安全总览、风险等级分布、趋势和高风险资产。
3. `03-assets.png`：资产列表、筛选条件和详情抽屉。
4. `04-vulnerabilities.png`：CVE、CVSS、严重等级和漏洞状态。
5. `05-audit.png`：审计日志和操作记录。
6. `06-reports.png`：报告列表、报告详情和导出操作。

当前已生成以上六张真实E2E运行截图，来源为独立 `secureops-e2e` 测试环境；未使用设计稿或模拟图片。

## Demo验收素材

以下截图来自同一独立 E2E 环境，用于展示实际操作状态：

| 文件 | 内容 |
| --- | --- |
| `07-demo-login.png` | Demo 登录页 |
| `08-demo-dashboard.png` | 登录后的 Dashboard |
| `09-demo-assets.png` | 资产列表和详情入口 |
| `10-demo-scans-pending.png` | 扫描任务等待执行 |
| `11-demo-scans-running.png` | Celery 执行中的扫描任务 |
| `12-demo-scans-completed.png` | 扫描完成状态 |
| `13-demo-risk-dashboard.png` | 风险统计和高风险资产排行 |
| `14-demo-vulnerabilities.png` | CVE、CVSS 和严重等级 |
| `15-demo-reports.png` | 安全报告列表和 PDF 入口 |

素材使用独立测试数据库、Redis 和授权目标 `127.0.0.1` 生成，未使用模拟图片或真实生产数据。

截图前准备：

- 使用本地演示账号，不展示密码、JWT、数据库地址或NVD密钥。
- 使用明确标注的实验资产，例如 `127.0.0.1`。
- 在截图中保留 SecureOps Logo 和页面标题，便于产品演示。
