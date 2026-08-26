# API 说明

## 健康检查

`GET /api/v1/health`

用于确认后端进程可用，不访问数据库，也不执行扫描操作。

响应示例：

```json
{
  "status": "ok",
  "service": "backend",
  "timestamp": "2026-08-24T00:00:00Z"
}
```

数据库模型设计暂不新增对外 API；相关实体包括用户、角色、资产、扫描任务、漏洞和审计对象，待后续业务模块完成后补充。

## 认证接口

- `POST /api/v1/auth/login`：用户名密码登录，返回 Bearer JWT。
- `GET /api/v1/auth/me`：需要 Bearer JWT，返回当前用户信息。
- `POST /api/v1/auth/users`：需要管理员 Bearer JWT，创建用户。
- `POST /api/v1/auth/register`：注册普通用户，密码使用 bcrypt 哈希保存。
- `POST /api/v1/auth/login`：校验密码并返回 JWT Bearer Token。
- `GET /api/v1/auth/me`：需要 JWT，返回当前用户信息。

## 资产接口

- `GET /api/v1/assets`：分页查询资产，支持关键词、类型、状态和重要性筛选。
- `POST /api/v1/assets`：创建资产，需要管理员权限。
- `GET /api/v1/assets/{asset_id}`：查看资产及服务。
- `PATCH /api/v1/assets/{asset_id}`：部分更新资产，需要管理员权限。
- `PUT /api/v1/assets/{asset_id}`：替换资产，需要管理员权限。
- `DELETE /api/v1/assets/{asset_id}`：停用资产，需要管理员权限，不执行物理删除。
- `POST /api/v1/assets/{asset_id}/services`：添加端口服务。
- `DELETE /api/v1/assets/{asset_id}/services/{service_id}`：删除端口服务。

## 扫描接口

- `POST /api/v1/scans`：创建受控 Nmap 扫描任务。
- `GET /api/v1/scans`：查询扫描任务。
- `GET /api/v1/scans/{scan_id}`：查看任务状态。
- `POST /api/v1/scans/{scan_id}/start`：启动待执行任务。
- `GET /api/v1/scans/{scan_id}/results`：查看标准化扫描结果。

扫描任务字段为 `task_name`、`target`、`scan_type`、`status`、`result_summary` 和 `created_by`。普通用户只能查看自己的任务，管理员可查看全部任务。

## 漏洞接口

- `GET /api/v1/vulnerabilities`：分页查询漏洞，支持严重性和 CVE 筛选。
- `POST /api/v1/vulnerabilities`：创建漏洞。
- `GET /api/v1/vulnerabilities/{vulnerability_id}`：查看漏洞详情。
- `PATCH /api/v1/vulnerabilities/{vulnerability_id}`：更新漏洞。
- `POST /api/v1/vulnerabilities/{vulnerability_id}/assets/{asset_id}`：关联受影响资产并计算风险。
- `PATCH /api/v1/vulnerabilities/{vulnerability_id}/assets/{asset_id}`：更新漏洞状态和复测信息。
- `PUT /api/v1/vulnerabilities/{id}`：管理员更新漏洞状态和信息。
- `DELETE /api/v1/vulnerabilities/{id}`：管理员将漏洞标记为 ignored，不执行物理删除。
- `GET /api/v1/vulnerabilities/statistics`：返回漏洞总数及各严重等级数量。

## 风险接口

- `GET /api/v1/risk/overview`：返回资产、漏洞和风险等级总览。
- `GET /api/v1/risk/assets`：返回高风险资产排名。
- `GET /api/v1/risk/trend`：返回最近 7—90 天的发现与修复趋势。
- `GET /api/v1/risk/rules`：返回当前可解释风险评分规则。
- `GET /api/v1/risk/summary`：返回资产数量、漏洞数量、高危漏洞数量和整体风险评分。
- `GET /api/v1/risk/levels`：返回 critical/high/medium/low 数量。
- `GET /api/v1/risk/top-assets`：返回高风险资产排行。
- `GET /api/v1/risk/trend`：返回按日期聚合的漏洞数量和风险分数。

前端页面通过 `VITE_API_BASE_URL` 配置 API 地址，默认使用 `/api/v1`。

前端页面：登录页、风险总览、资产管理、扫描任务、漏洞管理。认证请求自动添加 Bearer Token，401 响应会清理 Token 并跳转登录页。

## 审计接口

- `GET /api/v1/audit/logs`：管理员分页查询操作审计，可按 action、resource 和 user_id 筛选。

## 自动化巡检接口

- `GET /api/v1/scan-schedules`：查询计划。
- `POST /api/v1/scan-schedules`：创建一次性、每日、每周或 Cron 计划。
- `PATCH /api/v1/scan-schedules/{id}`：修改计划或启停计划。
- `POST /api/v1/scan-schedules/{id}/run`：立即提交一次执行。
- `GET /api/v1/scan-schedules/{id}/history`：查看执行历史。

## CVE 情报接口

- `GET /api/v1/cve`：关键词、严重等级和分页查询 CVE 情报。
- `POST /api/v1/cve/sync`：管理员提交 NVD 增量同步任务。
- `GET /api/v1/cve/{cve_id}`：查看单条情报。
- `POST /api/v1/cve/match`：根据服务名称和版本返回可能匹配结果。

## 安全报告接口

- `POST /api/v1/reports`：管理员根据统计周期生成真实数据报告。
- `GET /api/v1/reports`：按用户权限查询报告列表。
- `GET /api/v1/reports/{id}`：查看报告详情。
- `GET /api/v1/reports/{id}/html`：查看 HTML 报告。
- `GET /api/v1/reports/{id}/pdf`：下载 PDF 报告。

报告快照包含资产、漏洞、CVE 数量、风险等级、扫描统计、Top 高风险资产、Top 漏洞与基于真实统计生成的整改建议。HTML/PDF 导出接口同样执行报告归属校验，不应通过导出路径绕过权限。
