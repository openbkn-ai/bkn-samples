# 测试集

`scenarios_cn.md` 定义 17 个验收问题，新增从预测到发运的端到端履约链路。`questions.json` 提供 100 题中英对照题库：30 题简单／基础、40 题中等、30 题困难／综合。每题均有稳定 ID 和确定性期望答案；`expected-results.json` 保存 17 个验收基线。在样例根目录依次执行 `python3 tools/verify_industry_links.py`、`python3 iof-reference/tools/verify_reference_instances.py` 和 `python3 bkn-eval/run.py`。

测试集随源码维护，在未来接入平台资源绑定前核验 CSV 与 BKN 模型。
