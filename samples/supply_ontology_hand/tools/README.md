# 工具入口

请按上级目录的[导入指南](../docs/openbkn-hand-import-guide_cn.md)执行，不需要逐个阅读本目录脚本。

| 步骤 | 命令入口 |
| --- | --- |
| 1. 环境检查 | `preflight.py` |
| 2. 数据加载 | `load_sample_data.py` |
| 3. 知识网络导入 | `import_kn.py` |
| 4. 目录扫描 | `setup_catalog.py` |
| 5. 绑定与冒烟 | `bind_kn_resources.py`、`smoke_test.py` |
| 6. 能力发布 | `power_layer.py`、`register_native_function_toolbox.py`、`register_skills.py` |

`fn/` 是原生业务函数实现；它由注册脚本打包发布，不是独立的客户操作入口。正式评测见 `../bkn-eval/`。
