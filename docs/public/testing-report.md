# 测试报告

## 已执行验证

- `venv/bin/python -m compileall -q backend/app`：通过。
- `venv/bin/pytest -q`：20 项测试通过。
- `cd frontend && npm run build`：TypeScript 检查和 Vite 生产构建通过。
- `docker compose --env-file .env -f docker/docker-compose.yml config`：Compose 配置通过。
- Alembic 本地迁移已验证到 `c3d4e5f6a7b8`，包含安全报告表。
- `ENVIRONMENT=production` 且缺少 `DATABASE_URL`：启动保护验证通过，不会静默回退到 SQLite。
- `npm ci` 与前端生产构建：通过；锁文件已与 `package.json` 同步。

## 覆盖范围

测试覆盖健康检查、认证、密码哈希、资产 API、扫描任务、Nmap 解析、漏洞 API、风险规则、审计 API 和数据库模型。

## 仍需在目标环境验证

- MySQL 全新数据卷上的完整迁移和数据初始化。
- Docker 中 Nmap 对授权实验目标的真实执行。
- WeasyPrint PDF 导出及中文字体效果。
- 浏览器端完整点击流程和不同屏幕尺寸适配。
