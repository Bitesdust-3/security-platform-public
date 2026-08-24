# 部署说明

开发/演示环境：

```bash
cp .env.example .env
docker compose -f docker/docker-compose.yml --env-file .env up --build -d
```

生产模拟环境：

```bash
cp .env.production.example .env.production
# 编辑 .env.production，设置数据库密码、根密码、随机 JWT_SECRET_KEY 和实际 CORS_ORIGINS
docker compose -f docker/docker-compose.yml --env-file .env.production up --build -d
```

生产配置必须使用 `ENVIRONMENT=production` 和 `SEED_DEMO_DATA=false`。`.env.production` 只保存在部署主机，不得提交 Git。

前端默认地址为 `http://localhost:8080`。Compose 启动 MySQL、Redis、FastAPI、Celery Worker、Celery Beat 和 Nginx 前端，使用 `mysql_data`、`redis_data` 持久化数据，并通过健康检查控制启动顺序。Docker 环境明确注入 MySQL `DATABASE_URL`；生产环境不会回退到SQLite。MySQL 创建 `security_platform` 数据库和 `security_user` 应用账号；后端入口会执行 Alembic 迁移，设置 `SEED_DEMO_DATA=true` 可生成演示数据。

在当前 MySQL 8.4 全新库上，历史迁移 `2c3e63c28071` 的表重建可能触发外键兼容问题。若入口迁移失败，确认数据库为空后执行一次：

```bash
docker compose -f docker/docker-compose.yml --env-file .env stop backend
docker compose -f docker/docker-compose.yml --env-file .env run --rm --no-deps backend sh -c 'cd /app/backend && alembic stamp 2c3e63c28071 && alembic upgrade head'
docker compose -f docker/docker-compose.yml --env-file .env up -d backend frontend
```

该处理只修正 Alembic 版本记录，不修改业务表数据；生产环境应在独立迁移窗口执行并先备份数据库。

不要提交 `.env`。生产环境应配置 HTTPS、反向代理和集中式日志/限流存储。

```bash
curl http://localhost:8080/health
```

查看服务状态和日志：

```bash
docker compose -f docker/docker-compose.yml --env-file .env ps
docker compose -f docker/docker-compose.yml --env-file .env logs -f backend
```

若本机没有 Docker Compose 插件或 MySQL 服务，请在完整 Docker 主机执行上述命令，并区分配置校验与真实容器验证结果。
