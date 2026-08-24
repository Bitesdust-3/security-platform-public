# Git 开发工作流

本文档用于规范 SecureOps 企业安全运营平台的本地开发、提交和 GitHub 协作流程。

## 分支约定

- `main`：稳定、可演示的主分支。
- `feature/<name>`：新增或完善功能时使用，例如 `feature/report-export`。
- `fix/<name>`：缺陷修复时使用，例如 `fix/risk-trend-timezone`。
- `docs/<name>`：仅修改文档时使用，例如 `docs/deployment-guide`。

个人开发时，应先从最新 `main` 创建功能分支；验证通过后再合并回 `main`。

## 日常开发流程

1. 获取最新代码：`git pull --ff-only origin main`。
2. 创建分支：`git switch -c feature/<name>`。
3. 完成小范围修改，并同步更新相关说明文档。
4. 执行与修改范围对应的测试。
5. 使用 `git status` 和 `git diff --check` 检查待提交内容。
6. 确认 `.env`、数据库、日志、构建目录未进入暂存区。
7. 使用清晰的提交信息提交。
8. 推送分支并创建 Pull Request；通过 CI 后合并。

## 提交前检查

```bash
git status
git diff --check
git diff --cached --check
git ls-files | rg '(^|/)\.env($|\.)|\.(db|sqlite|sqlite3)$|(^|/)logs/'
```

最后一条命令不应输出真实环境配置、数据库文件或日志文件。示例配置文件 `.env.example`、`.env.production.example` 与 `backend/.env.example` 属于可提交文件。

建议在提交前执行：

```bash
PYTHONPATH=backend venv/bin/pytest -q
cd frontend && npm run build
```

若本机未安装依赖，应按 README 的 Docker 或本地开发说明准备环境，不要把 `venv/` 或 `node_modules/` 提交到仓库。

## 提交信息规范

使用 Conventional Commits 风格：

- `feat: add scheduled scan management`
- `fix: handle timezone-aware risk trend timestamps`
- `docs: update Docker deployment guide`
- `test: add MySQL migration integration coverage`
- `chore: prepare initial open-source release`

每个提交应只解决一个明确问题，避免把业务代码、格式化、依赖升级和无关文件混在同一次提交中。

## 敏感信息规则

严禁提交：

- `.env`、`.env.production` 及任何真实环境配置
- JWT 密钥、数据库密码、NVD API Key、访问令牌
- SQLite/MySQL 导出数据、运行日志、扫描结果中的敏感目标信息
- `node_modules/`、`venv/`、构建产物和浏览器测试运行产物

公开仓库只保留脱敏的示例配置文件。发现敏感信息已进入提交历史时，应立即撤销公开访问、轮换相关密钥，并重写受影响历史。

## 首次发布检查清单

- [ ] `.gitignore` 已通过 `git status --ignored` 复核。
- [ ] `README.md` 的部署命令与 Docker 配置一致。
- [ ] 示例环境变量没有真实密钥。
- [ ] 单元测试、前端构建和 Docker Compose 配置检查通过。
- [ ] LICENSE、CHANGELOG、CONTRIBUTING 和核心文档齐全。
- [ ] 截图不包含真实 IP、密码、Token 或企业数据。
