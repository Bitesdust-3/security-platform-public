# Docker 部署验证记录

验证日期：2026-08-24

## 环境

- Docker Engine 29.1.3
- Docker Compose 2.40.3
- 服务：MySQL 8.4、Redis 7、FastAPI、Celery Worker、Celery Beat、Nginx + Vue 3
- 本次本地 `.env` 使用 `ENVIRONMENT=development`；部署拓扑、MySQL和Redis均按生产结构运行，但不应将本次记录视为生产凭据或生产环境验收。

## 部署步骤

1. 设置构建阶段代理变量，避免Docker构建容器无法访问Debian软件源。
2. 在需要代理的网络中为构建命令显式传入大写 `HTTP_PROXY`、`HTTPS_PROXY` 和 `NO_PROXY`。
3. 执行 `docker compose ... build` 构建 Backend、Worker、Beat 和 Frontend。
4. 执行 `docker compose ... up -d` 重建服务；Backend重建后强制重建Frontend以刷新Nginx上游地址。
5. Backend入口执行 Alembic 升级。
6. 检查服务健康状态、HTTP接口、Redis和Celery。

## 遇到的问题与解决方案

### APT下载在Backend构建阶段停滞

Docker daemon可以通过代理拉取镜像，但Compose解析到的构建参数 `HTTP_PROXY`、`HTTPS_PROXY` 为空；构建容器中的 `apt-get` 没有使用代理。

解决：在构建命令中显式传入大写代理变量。项目Dockerfile和Compose已支持这些build args，因此无需修改业务代码。

### Frontend健康检查误报

Nginx在容器内监听IPv4，`localhost`可能优先解析为IPv6，导致 `wget` 连接被拒绝。

解决：健康检查地址调整为 `http://127.0.0.1:8080/`。

### Backend重建后的Nginx 502

Backend容器重建后，Frontend中Nginx仍缓存旧的Backend容器地址，导致报告PDF请求短暂返回502。

解决：Backend重建后执行：

```bash
docker compose -f docker/docker-compose.yml --env-file .env up -d --force-recreate frontend
```

### WeasyPrint字体缓存告警

PDF首次生成时出现Fontconfig不可写缓存目录告警。通过为非Root运行用户设置可写的 `XDG_CACHE_HOME`，重新构建后告警消失，PDF导出仍保持正常。

## 验证结果

| 项目 | 结果 |
| --- | --- |
| Backend镜像构建 | 通过 |
| Frontend镜像构建 | 通过 |
| MySQL健康检查 | healthy |
| Redis健康检查 | healthy |
| Backend健康检查 | healthy |
| Celery Worker / Beat | healthy |
| Frontend健康检查 | healthy |
| Alembic版本 | `c3d4e5f6a7b8` |
| 数据库表数量 | 14 |
| `security_reports`表 | 已创建 |
| `/api/v1/health` | HTTP 200 |
| 管理员登录 | HTTP 200 |
| 资产、漏洞、风险、报告、审计接口 | HTTP 200 |
| 报告生成 | HTTP 201 |
| PDF导出 | HTTP 200，PDF文件生成成功 |
| Redis `PING` | PONG |
| Celery `inspect ping` | 1 node online |

## 后续生产验收

- 使用独立生产 `.env`，设置 `ENVIRONMENT=production`、强随机JWT密钥和非演示账号密码。
- 使用全新MySQL数据卷重复迁移验证。
- 在明确授权的实验资产上验证一次真实Nmap扫描。
- 不在公开仓库提交代理地址、数据库密码、JWT或NVD密钥。
