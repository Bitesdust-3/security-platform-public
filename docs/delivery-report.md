# 项目交付报告

## 项目概况

企业安全运营平台（简化版）面向信息安全专业学习、毕业论文、求职简历和面试展示，提供认证、资产、扫描、漏洞和风险分析能力。

## 技术栈与架构

- Vue 3、Element Plus、Axios、ECharts
- FastAPI、SQLAlchemy、Alembic、JWT、bcrypt
- MySQL 8.4、Docker Compose、Nginx

前端通过 Nginx 访问，Nginx 将 `/api/` 转发到 FastAPI；FastAPI 通过 SQLAlchemy 访问 MySQL，并将扫描结果、漏洞、风险和审计数据持久化。

## 已实现功能

- JWT 登录、注册、当前用户和角色控制
- 资产 CRUD、分页和筛选
- 授权 Nmap 扫描任务及结果同步
- 漏洞管理、CVE/CVSS 校验和统计
- 可解释风险评分、等级和趋势接口
- 日志、审计、登录失败限制和 API 频率限制
- Docker 一键启动和 MySQL 持久化

## 部署验证

- `mysql`：healthy
- `backend`：healthy
- `frontend`：running，当前 Compose 未配置 frontend healthcheck
- 前端：`http://localhost:8080` HTTP 200
- 管理员登录：成功返回 JWT
- 资产、漏洞、风险和审计 API：验证通过
- 未认证资产接口：401
- 普通用户访问管理员审计接口：403
- 数据库密码字段：bcrypt `$2b$` 哈希，未保存明文

## 已知限制

- 前端已提供独立审计日志页面，审计查询仍仅限管理员。
- 前端构建通过，但 Element Plus 和 ECharts 分包仍较大，后续可继续按组件拆分。
- MySQL 历史迁移在全新库上可能需要按部署文档执行一次 Alembic 版本修复。
