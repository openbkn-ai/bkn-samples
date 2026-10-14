# 安装实现与开发工具

客户和伙伴使用一键体验或离线包导入，操作见[安装与验收指南](../docs/openbkn-hand-import-guide_cn.md)。本目录不是独立安装入口。

标准 hooks 使用下列脚本完成安装和验证：

| 用途 | 脚本 |
| --- | --- |
| 数据加载 | `load_sample_data.py`（由 `db/load_supply.py` 调用） |
| 知识网络导入与资源绑定 | `import_kn.py`、`setup_catalog.py`、`bind_kn_resources.py` |
| 指标、函数和 Skill 发布 | `power_layer.py`、`register_native_function_toolbox.py`、`register_skills.py` |
| 平台验收 | `smoke_test.py`、`power_layer.py` |

`fn/` 是原生业务函数实现，由注册脚本打包发布。`config.example.yaml` 是开发参考，标准安装 hooks 自动生成运行配置。`verify_sample.py` 校验源码交付契约。

开发检查可在样例目录执行：

```sh
PYTHONPATH=tools python -m pytest tools/tests -q
```

离线检查不能代替实际安装与 MCP 业务验收；评测说明见 [BKN-Eval](../bkn-eval/README.md)。
