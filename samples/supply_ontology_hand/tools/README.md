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

### 结构化结论证据（源码候选）

`bom_shared_list` 原生 Function 可选输出 `trace_evidence`：仅声明给定产品、层级和替代料规则下的公共物料集合及数量。业务校验与 5,000 行保护由本样例负责；`fn/trace_evidence.py` 不声明库存、齐套或可接单。无效或不完整结果不输出声明，零交集有效。

该声明需配合 Foundry 的 `function_result_evidence/v1` 接入及管理员对实际工具版本、代码哈希的明确批准；旧平台仍可使用原有业务结果。这里没有发布、重新注册 Function、修改已有制品或自动启用 Trace。代码更新后需另行发布新候选并重新核对批准哈希。
