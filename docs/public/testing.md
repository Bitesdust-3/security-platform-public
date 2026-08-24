# 测试与验证说明

## 单元测试

```bash
PYTHONPATH=backend venv/bin/pytest -q
```

单元测试使用SQLite内存数据库，扫描任务会在测试中显式禁用外部Celery Broker，确保测试不依赖Redis。

## MySQL迁移集成测试

设置一个专用、可丢弃的测试数据库连接串后执行：

```bash
MYSQL_TEST_DATABASE_URL=mysql+pymysql://user:password@127.0.0.1:3306/security_platform_ci \
  PYTHONPATH=backend venv/bin/pytest -q tests/test_mysql_migration_integration.py -m integration
```

该测试只检查全新MySQL的Alembic迁移和核心表，不使用开发数据卷。

## 浏览器测试

Playwright测试位于 `frontend/e2e/`。不会在没有明确授权账号时执行登录流程：

```bash
cd frontend
npm install
npx playwright install chromium
E2E_BASE_URL=http://127.0.0.1:8080 \
E2E_USERNAME=<authorized-test-user> \
E2E_PASSWORD=<authorized-test-password> \
npm run test:e2e
```

测试账号和密码不得提交到仓库。
