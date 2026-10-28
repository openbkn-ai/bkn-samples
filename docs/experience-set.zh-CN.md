# 样例体验集标准

样例安装成功后，用户还需要一组能直接验证效果的问题。体验集从样例已有的评测问题集和答案集里抽取题目，配上参考答案和适用页面。Studio 在智能问答、数据查询和图探索页面中逐题提供：用户点击体验后，题目填入页面已有的输入框；结果出来后，再与参考答案对比并确认对错。

- Schema：[`installer/schemas/experience-set.schema.json`](../installer/schemas/experience-set.schema.json)
- 校验：[`installer/experience_set.py`](../installer/experience_set.py)
- 在线核验：[`tools/acceptance/experience_set.py`](../tools/acceptance/experience_set.py)
- 首批样例：[供应链（中文）](../samples/supply_ontology_hand/experience/experience-set.yaml)、[供应链（英文）](../samples/supply_ontology_en/experience/experience-set.yaml)

## 位置与声明

体验集放在样例目录的 `experience/experience-set.yaml`，并在 `sample.yaml` 中声明：

```yaml
spec:
  studio:
    experienceSet: experience/experience-set.yaml
```

发布包不包含 `bkn-eval/`，所以体验集自带题目、参考答案和期望值，安装后不依赖评测目录。`metadata.source` 记录来源答案集，仓库测试据此检查两者是否一致。体验集的语言必须与样例的 `metadata.language` 相同。

## 格式

```yaml
apiVersion: samples.openbkn.ai/v1alpha1
kind: ExperienceSet
metadata:
  language: zh-CN
  source:
    answerSet: bkn-eval/baselines/2026-10-12-business-rules-v2/answer-set-v3.yaml
    setId: supply-business-rules-v3
spec:
  businessDate: '2026-08-25'        # 答案成立的冻结业务日期，Studio 随题展示
  cases:                            # 顺序即体验顺序
  - id: R-05                        # 来源答案集中的题号
    title: 物料被哪些产品使用        # 卡片标题，不超过 40 字
    explanation: 从物料沿 BOM 关系反查产品，替代料位置也算使用。
    question: 物料 321-000569 被哪些产品使用？      # 与来源一字不差
    answer: 物料 321-000569 被 P61-000328、P61-000331、P61-000351 三个产品使用。
    expected: {product_codes: [P61-000328, P61-000331, P61-000351]}   # 与来源一字不差
    surfaces: [agent, query, graph]
    cypher:
      query: |-                     # 列名与 expected 字段同名
        MATCH (p:...)-[...]->(m:... {material_code: '321-000569'})
        RETURN DISTINCT p.material_number AS product_codes
      graph: |-                     # MATCH/WHERE 模式，图探索补全后画出匹配结果
        MATCH (p:...)-[:...]->(b:...)-[:...]->(m:... {material_code: '321-000569'})
        WHERE b.bom_level >= 1
```

## 规则

1. **只抽取，不改写。** `question` 和 `expected` 必须与来源答案集完全一致，`id` 必须存在于来源中。来源金标更新后，仓库测试会提示体验集需要同步。
2. **参考答案写给人看。** `answer` 是一句完整的业务结论，必须写出 `expected` 中的每个数值和编码；是/否标记不强制出现原词，但结论里要说清楚。
3. **按页面选题。** 每道题都可以在智能问答中体验，所以 `surfaces` 必须包含 `agent`。
   - `query`（数据查询）：答案能由对象属性过滤、固定的关系路径和 count/sum 算出，不依赖业务函数口径。必须提供 `cypher.query`，返回列与 `expected` 字段同名。
   - `graph`（图探索）：答案是从具名节点出发、经关系连到的一小组实体，在画布上一眼能看懂。必须提供 `cypher.graph`：不带 `RETURN` 的 `MATCH`/`WHERE` 模式，由图探索补全并画出，匹配不超过 50 条路径。
   - 需要函数或 Skill 推理的题（可售、齐套、交期、多单争用）只放在 `agent`。
4. **参考 Cypher 要能在最低支持的平台上运行。** 按样例最低平台版本的 `run_cypher` 子集来写。OpenBKN 0.2.1 不支持 `WITH`、`CASE`、`coalesce` 等函数、关系变量、返回整个节点，以及属性与属性比较；可以改用 `IS NULL`/`OR`、`count(*)`、`count(DISTINCT x.p)`，以及在同一节点汇合的路径。
5. **参考 Cypher 不进输入框。** Studio 只把 `question` 填入页面输入框；参考 Cypher 在结果出来后作为"参考查询"展示。
6. **答案不进 Agent 上下文。** `answer` 和 `expected` 只展示给用户，不能拼进提问或传给 Agent，以保持金标"被测方不可见"的约束。
7. **精选，不全量。** 体验集只收能直观说明能力的代表题，建议 15～25 道，从简单事实到关系，再到业务判断，依次排列。

## 安装后如何读取

安装或重试成功时，安装服务把该版本的体验集记入安装记录；安装包本身不保留。Studio 按当前知识网络读取：

```http
GET /api/studio/samples/experience-sets/{knowledgeNetworkId}
```

已登录用户都可以读取。只有某个样例安装成功、且安装记录中它创建的知识网络（`resources.knowledgeNetworkId`）正是该网络时，才返回 `{sample, version, knowledgeNetwork, experienceSet}`。其他情况，包括手工创建的同名网络、安装失败，或已安装版本没有体验集，都返回 404 `experience_set_unavailable`，Studio 不显示场景体验。体验集只在安装包含它的版本后才可用，已安装的旧版本需要重新安装。

声明了体验集的安装包在 `requires.capabilities` 中要求 `sample.experience-set` 能力。不会记录体验集的旧样例服务在下载前就拒绝这类版本，继续提供上一版本。显式配置了 `platform.capabilities` 列表的运维方，需要加入这一项才能安装这类版本。

## 期望值与查询结果的比对

在线核验和 Studio 都按以下规则比对 `cypher.query` 的结果：

| `expected` 字段 | 比对方式 |
| --- | --- |
| 数值或文本 | 结果只有一行，同名列的值相等；数值按十进制比较，`534.000000` 等于 `534`。 |
| 值列表 | 同名列在所有行中的取值，按集合比较。 |
| 记录列表 | 结果的所有行按记录比较，列名对应记录字段。 |

## 校验

- 离线校验：`python -m unittest installer.tests.test_experience_set`。它检查 Schema、参考答案是否写出了全部期望值、页面声明与 Cypher 是否对应，以及与来源答案集是否一致。样例契约校验（`validate_document`）也会检查声明的体验集，因此发布包导入时同样会校验。
- 在线核验：在已安装该样例的平台上运行，确认每条参考查询都能复现期望值；每个图模式补上 `RETURN count(*)` 后，匹配 1～50 条路径。令牌从环境变量读取，不会输出。

```bash
OPENBKN_TOKEN=<token> python3 tools/acceptance/experience_set.py samples/supply_ontology_hand --base-url http://localhost:8081
```

## 供应链首批体验集

两种语言使用相同的 23 道题。中文版来源为 `business-rules-v3`，它是当前有效且与发布数据一致的金标。`datasets/` 中的 v1 答案集属于 2026-08-13 历史快照，M-07、M-08、M-12 与发布数据不一致，因此不作为来源。英文版来源为其 `datasets/sample-answer-set-v1.yaml`。

| 页面 | 题目 |
| --- | --- |
| 智能问答（23） | 全部题目，其中 F-04、F-15、F-10、S-01、S-04、S-02、S-10、S-07、S-08 只能在问答中体验。 |
| 数据查询（14） | M-04、M-06、M-10、M-12、M-15、F-07、F-01、R-02、R-05、R-07、R-08、F-02、F-14、R-09 |
| 图探索（5） | F-01、R-02、R-05、R-08、R-09 |

R-07（30 个产品、228 条路径）和 R-03、R-04（完整多级 BOM）规模太大，不放在图探索中。2026-10-28 已在本地 8081 的 OpenBKN 0.2.1 后端（`0.2.1-main.20261016154814`）上实测：两种语言的 14 条参考查询全部复现期望值，5 个图模式分别匹配 4～19 条路径。
