# 食品供应链追溯与召回

虚构食品流通业务样例。覆盖到货检验、仓店流转、销售退货、效期预留、共享库存履约、未来补货及召回处置。需要OpenBKN >=0.2.1 <0.3.0。

在OpenBKN0.2.1及以上通过首页导入[0.1.0固定离线包](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-retail-gs1-zh-cn-v0.1.0)并安装，再打开知识网络。[正式包验收凭证](releases/0.1.0/verification.json)绑定精确归档。后续官方目录PR保持未合并，目前使用离线导入；中英文是两个独立sample。

[PRD](docs/PRD.zh-CN.md) · [Business contract](docs/business-contract.md) · [BKN ontology](docs/ontology.md) · [GS1 sources/license](docs/standard-sources.md).

15个有数据的对象类、30条外键关系、3个概念分组，3个函数、2个已记录快照指标、1个调查Skill。默认观察日2027-02-28，业务数据覆盖2026-11至2027-03。未知不是零，计划不当作已实现；不自动执行业务操作。

每语言100题，基础30/中等40/复杂30，逐题对应PRD的10个场景。题库与答案仅供开发验收，不进入运行包。通过确定性开发校验后仅一次正式子智能体问答，保留首次失败，100%作为目标按实际结果报告。

2026-10-20首轮结果：中文95/100，英文96/100，原始分数保留。其后经授权将修正版安装8081，仅定向复测原未通过题：英文4/4、中文5/5通过，全部执行及证据收尾完成。去重代码修复已实际生效，题目/输出契约也已澄清；未再次全量跑，不能称修订版全量100%。[首轮验收](verification/acceptance-20261020.json) · [定向复测](verification/targeted-retest-20261020.json) · [详细分析](../../docs/retail-gs1-acceptance.zh-CN.md)。
