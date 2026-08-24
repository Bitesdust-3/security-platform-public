# 数据库设计

核心表包括 `users`、`roles`、`user_roles`、`assets`、`asset_services`、`scan_tasks`、`scan_results`、`scan_schedules`、`vulnerabilities`、`asset_vulnerabilities`、`cve_intelligence`、`security_reports` 和 `audit_logs`。

- 用户与角色为多对多关系；扫描任务、巡检计划和报告记录创建者。
- 资产保存 IP、主机名、环境、重要性、状态和服务；IP、状态、类型等字段建立索引。
- 扫描任务保存目标、状态、摘要和创建者，扫描结果保存标准化服务发现数据。
- 漏洞支持 CVE、CVSS、严重等级、状态，并通过 `asset_vulnerabilities` 关联资产和风险分数。
- `scan_schedules` 保存周期、下次执行时间和状态，执行历史通过 `scan_tasks.schedule_id` 追溯。
- `cve_intelligence` 保存 NVD 同步的 CVE、CVSS、产品、参考链接和原始数据，与业务漏洞表分离。
- `security_reports` 保存按周期生成的统计快照、风险分布、趋势和整改建议。
- 审计日志记录认证、资产、扫描和漏洞等关键操作。

数据库迁移使用 Alembic；Docker 后端入口启动时执行 `alembic upgrade head`。报告模块迁移版本为 `c3d4e5f6a7b8`。

```bash
docker compose -f docker/docker-compose.yml --env-file .env run --rm backend alembic upgrade head
```
