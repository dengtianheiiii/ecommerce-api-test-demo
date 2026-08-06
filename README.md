# ecommerce-api-test-demo

一个可直接运行的电商接口自动化测试 Demo，用于展示软件测试中的接口分层、异常场景、测试数据、Allure 报告与 GitHub Actions 基础能力。

> 这是教学型个人项目：仓库自带本地模拟商城接口，因此无需账号、网络或真实数据库也能运行。`db/mysql_client.py` 提供了接入真实 MySQL 环境后的订单数据校验模板。

## 覆盖范围

| 模块 | 覆盖的典型场景 |
| --- | --- |
| 登录 | 正确账号登录、密码错误、缺少参数 |
| 商品 | 关键字搜索、无结果搜索 |
| 购物车 | 添加商品、修改数量、删除商品、库存不足、未登录访问 |
| 订单 | 创建订单、金额计算、库存扣减、重复提交 |
| 数据校验 | 可选 MySQL 订单状态和金额校验 |

当前示例包含 **12 条可执行接口测试**。测试均通过 `requests` 调用 HTTP 接口，而不是直接调用业务函数。

## 技术栈

- Python 3.10+
- pytest + requests
- Allure Pytest
- MySQL Connector（可选：真实环境数据校验）
- GitHub Actions

## 快速运行

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
pytest
```

测试会自动启动 `mock_server.py` 提供的本地模拟商城 API，结束后自动关闭。

生成 Allure 原始结果：

```bash
pytest --alluredir=allure-results
allure serve allure-results
```

如果想单独体验模拟接口，可运行：

```bash
python mock_server.py
```

然后访问 `http://127.0.0.1:8000/health`。

## 项目结构

```text
ecommerce-api-test-demo/
├─ api/                    # HTTP 接口客户端封装
├─ config/                 # 环境配置
├─ data/                   # 测试数据示例
├─ db/                     # MySQL 校验模板
├─ tests/                  # pytest 测试用例
├─ .github/workflows/      # GitHub Actions
├─ mock_server.py           # 可运行的本地模拟商城 API
├─ requirements.txt
└─ README.md
```

## MySQL 数据校验（可选）

复制 `.env.example` 为 `.env` 并补充真实测试数据库信息；安装依赖后可运行带 `db` 标记的测试。示例中的 `MySQLClient` 使用参数化 SQL，避免把订单号直接拼接到查询语句中。

```bash
set RUN_MYSQL_CHECKS=1
set MYSQL_HOST=127.0.0.1
set MYSQL_USER=tester
set MYSQL_PASSWORD=your_password
set MYSQL_DATABASE=mall_test
set ORDER_ID=ORD-1001
pytest -m db
```

真实项目中，请勿提交 `.env`、数据库密码、Token 或真实用户数据。

