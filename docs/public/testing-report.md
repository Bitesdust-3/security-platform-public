# 测试报告

## 已执行验证

- Python 后端测试覆盖认证、资产、扫描、扫描结果处理、漏洞、风险、审计与报告服务。
- 前端执行 `npm run build`，完成 TypeScript 检查和 Vite 生产构建。
- Docker Compose 配置经 `docker compose ... config` 校验，包含 MySQL、Redis、FastAPI、Celery Worker、Celery Beat 与 Nginx 前端。
- Alembic 在全新 MySQL 8.4 环境执行到当前 head，包含结构化扫描结果与报告快照字段迁移。
- `ENVIRONMENT=production` 且缺少 `DATABASE_URL` 时启动保护会阻止服务静默回退到 SQLite。
- 在授权实验环境中验证 Nmap 服务识别、结构化扫描结果保存、CVE 候选匹配、漏洞去重、风险刷新和 PDF 报告生成。
- PDF 报告验证中文字体、Asia/Shanghai 时间、风险分布图、风险资产排行和扫描统计的人类可读展示。

## 覆盖范围

测试覆盖健康检查、认证、密码哈希、资产 API、扫描任务、Nmap 解析、扫描结果处理、漏洞 API、风险规则、审计 API、报告快照和数据库模型。

## 仍需在目标环境验证

- 不同 Linux 发行版与受限网络环境下的 Nmap 可用性。
- 更大规模资产与漏洞数据下的报告分页和查询性能。
- 浏览器端更多屏幕尺寸、网络异常与权限组合的回归覆盖。
