# 库存履约与采购分析

版本1.1.1：Agent按Skill编排，业务组合函数通过OSDK执行，包内脚本仅离线解释函数结果。使用版本独立的render_v111.py，避免平台overwrite=false复用旧脚本。正反例见tests/trigger-cases.json；禁止包内持有凭据。
