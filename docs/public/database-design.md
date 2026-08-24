# 数据库设计

核心实体包括 `users`、`roles`、`assets`、`asset_services`、`scan_tasks`、`scan_results`、`vulnerabilities`、`asset_vulnerabilities` 和 `audit_logs`。

- 用户和角色：支持基础认证与管理员权限。
- 资产和服务：记录 IP、主机、环境、重要性及开放服务。
- 扫描任务和结果：记录目标、状态、标准化发现结果。
- 漏洞及资产关联：支持漏洞生命周期和风险评分。
- 审计日志：记录关键写操作。

本文件为早期数据库设计记录；当前实际表结构和迁移说明以 [database.md](database.md) 为准。项目通过 Alembic 管理迁移，并在 Docker 后端入口启动时执行升级。
