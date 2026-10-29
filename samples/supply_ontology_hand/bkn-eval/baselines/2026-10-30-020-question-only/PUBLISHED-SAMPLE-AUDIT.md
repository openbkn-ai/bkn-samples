# 供应链 Sample 题集与运行包隔离审计

审计对象：官方 sample-supply-chain-v0.1.14、对应源码提交和本地020候选0.1.16。官方包摘要已经与官方SHA256SUMS核对。

## 已确认

- 官方0.1.14面向021（>=0.2.1 <0.3.0），不能替代020维护包。
- 原始v1和current-v2均为50题，没有public_rules/evaluation_policy；不能笼统宣称所有官方题集都泄露规则。
- 确定性v3面向被测Agent声明evaluation_policy，并在题干写入库存净算、仓范围、替代选择等提示。这是已披露口径的另一套任务，不适合原客户题目的盲测。
- 指南的预检直接给出606-000989标准交期14天，与F-07重合。评测指南、README及历史成绩只能供组织者读取，不应进入待测上下文。
- 官方运行包排除了bkn-eval，但experience/experience-set.yaml有23个体验卡片，每个包含question/answer/expected，且与核心题重叠。体验演示与盲测需要建立访问隔离；材料存在不等于历史Agent实际读过。
- 源码中答案、历史答卷与题目共存属于维护资料，禁止将整个仓库挂给被测Agent。

## 020修订边界

- 0.1.16运行包共81文件，不含experience、bkn-eval、测试、历史答案。
- 独立题目包仅含客户原始50题和必要业务日期；每次只挂载当批10题。
- 业务规则保留在BKN平台本体、函数和Skill中；直连路径只可访问数据库元数据与数据。
- 当前答案与评估口径仅供评估者，待全部答卷冻结后使用。历史资料保留在维护仓库，不放入当前交付包。
- 新模型测试不继承旧公共规则试验成绩；原题的歧义与数据库支持的不同解释单独标注。

## 发布状态

020修订包已在正式0.2.0本地环境安装，54项确定性调用通过；本轮纯题目模型测试仍进行中，尚未公开发布。021问题已记录，是否同时修订021发布线等待范围确认；不得把020源码覆盖到021主线。

完整来源、官方提交、包摘要及路径见published-sample-audit.json。

## samples目录横向静态检查

当前官方main提交f4008399a4b922b5a5c8273a0662b7be18950b3e下，共清点12个Sample目录的30个题目JSON/YAML文件（包括历史、专题与映射文件，不代表30套正式盲测）。

- 中英制造业questions.json各100题，每条直接包含expected_answer。示例MFG-001询问制造基地，同时附SITE-SZ-01。整份文件不能作为被测Agent题目输入；现有run.py用于确定性验收，文件共存本身不证明曾泄露给LLM。
- 中英金融questions.json各100题包含evidence_sql、evidence_tables、evidence_views、required_relations。例如FIN-001附发行方JOIN查询，等于给出解题路径。基于元数据自行判断的盲测应去掉这些字段。
- 中英供应链frozen/deterministic历史纸包含evaluation_policy；英文当前原始50题仅questions/id/question，不能将历史披露规则试验与原始盲测等同。
- 世界杯scoring和required_objects给出排名规则及对象选择等提示，属于带口径任务协议；若做纯问题盲测应另行导出并在报告说明。输出字段、单位、日期有些是必要任务条件，不能仅凭字段名判成答案泄露。
- 能源、零售含scope/output_contract等字段，静态清点不足以断言业务泄露，需要逐题区分用户条件与评估者提示。本次未对它们作全量语义结论或修改发布。

本次实际修改和020安装验证范围仍为中文供应链。其余发现提供复核证据，不宣称已经修复或发布。完整清单见sample-question-inventory.json及sample-question-examples.json。
