# 样例自带的 Workshop 应用

样例可以自带 Workshop 应用，安装后直接在样例自己的知识网络上打开使用。把应用带到客户环境用的也是同一个文件：在应用列表里导出，再到客户环境导入。

## 应用文件是什么

应用文件（`<名称>.app.yaml`）就是应用列表导出的应用草稿，原样保存。

- `dependencies.knowledgeNetwork` 指应用所基于的知识网络。
- `sources[].objectType`、行动 ID（`…operations[].action.id`）和各字段名，按 ID 指向该网络的对象类、行动和属性。
- 规则函数（`pages[…].layers[].ruleTools[]` 和 `scheduleModel.tasks[].rules[]`）用 `tool.boxName`（工具箱名）和 `tool.toolName`（函数名）指明。导出文件还带着 `tool.box` / `tool.tool`，也就是原环境里的 ID。这些 ID 换了环境就没用了：在新环境里找不到这些 ID 时，Workshop 会按工具箱名和函数名调用同名函数。
- `app.id` 是导出时那个应用的 ID，导入或安装时会给新应用分配新的 ID。

## 给样例加应用

1. 安装样例后，在应用工坊里基于样例的知识网络建好应用，例如用“资源排程工作台”向导。
2. 在应用列表里导出。
3. 保存为 `samples/<样例>/workshop/apps/<名称>.app.yaml`。安装器可以直接用导出文件。仓库里的副本最好不带环境 ID：删掉 `app.id` 和规则函数里的 `box` / `tool` 两行。
4. 其他语言的样例各带一份，在该样例的网络上建，文案用该语言。

安装器逐个检查：

- `apiVersion` 为 `workshop.openbkn.ai/v1`；
- 应用有名称，不超过 128 个字符；
- `dependencies.knowledgeNetwork.id` 是样例的知识网络；
- 至少有一个页面；
- 每个规则函数都写了 `boxName` 和 `toolName`。

同一样例的应用不能重名。

## 安装与卸载

- 安装包带上 `workshop/` 目录，并声明能力 `sample.workshop-apps`；不支持该能力的样例服务会在下载前拒绝这个包。
- 平台检查通过后，安装器依次：
  1. 只在本次安装创建的工具箱里，按工具箱名和函数名查出每个规则函数的 ID，写进应用；找不到函数就在创建任何应用之前失败，并报出缺少哪些函数。
  2. 在样例网络上逐个创建应用，把文件写为草稿。
  3. 发布应用，使其页面能从应用列表打开。
  4. 把应用 ID 记在安装记录（`workshopApps`）里，每次变更后立即写入。
- 再次安装或重试失败的安装时，先删除记录中的应用和样例网络上的同名应用，再重新创建。
- 卸载时先删除记录中的应用，再删除它们所在的知识网络。
- 安装的管理员需要有创建 Workshop 应用的权限。
- Workshop 属于专业版。平台没有 Workshop 时，它的所有接口都返回 404，安装器就安装样例而不带应用，诊断日志记下跳过了这一步。

## 在客户环境复用应用（给 FDE）

### 1. 导出

在应用列表里打开应用的菜单，选择导出，得到 `<应用 ID>.app.yaml`。样例的应用也可以直接用仓库里 `workshop/apps/` 下的文件。

### 2. 准备客户环境

应用只读写文件里写到的东西。导入前，客户环境要具备：

- **同 ID 的知识网络对象。** 每个 `sources[].objectType` 及应用用到的属性都要存在，ID 相同。应用用到的属性见 `field`、`startField`、`resourceField`、`barFields`、`popoverFields`、`pairs` 等。供应链应用用到需求预测单、齐套排产计划、产线、停线窗口，产线检查还要用到产品。装上样例就全有；用客户自己的网络时，先建好或对应好这些对象类。
- **应用会执行的行动。** 即 `operations` 下的 `action.id`，例如供应链应用的 `<网络>_kitplan_create` 和 `<网络>_kitplan_adjust`。它们要在该网络上存在，且参数与文件中的映射一致。
- **规则函数。** 要挂载在名称等于文件中 `boxName` 的工具箱里，并以 `toolName` 的名称启用。中文样例是 `供应链原生计算函数` / `齐套检查`、`产线可生产`，英文样例是 `Supply_EN_Functions` / `Kit_Check`、`Line_Can_Build`。找不到函数时，页面上显示“未能校验”，方案不能采用。

### 3. 导入

1. 在应用列表里选择“导入”，选中文件。
2. Workshop 按 `dependencies.knowledgeNetwork` 在你能看到的网络里先按 ID、再按名称匹配，对照该网络检查对象类和行动，然后新建一个草稿应用。
3. 如果同名应用已经存在，先改文件里的名称，方便区分。
4. 在构建器里用预览打开草稿；要让业务用户使用，就发布它。

规则函数在页面运行时按工具箱名和函数名查找，导入后不用重新绑定。打开一次排程向导并保存，也会把它们重新绑定到当前环境的 ID。

### 4. 改成客户自己的数据

- **网络或对象类 ID 不同：** 导入前修改文件中的 `dependencies.knowledgeNetwork.id`、每个 `objectType` 和行动 ID，字段名与客户的属性保持一致。
- **状态取值不同**（例如“已取消”“已关闭”）：同时改 `where`、`doneWhen`、`active` 和 `classify` 各个分支的取值。待排需求等派生数据靠这些取值互相对上。
- **文案和语言不同：** 页面标题、图层名称和计算字段名称都是文件里的普通文本。翻译时连同筛选条件要比较的分类取值一起改。
- **规则函数名称不同：** 把 `boxName` 和 `toolName` 改成客户的工具箱名和函数名，甘特图层的 `ruleTools` 和 `scheduleModel.tasks[].rules` 两处都要改。
- 导入后打开两页，确认计划条显示的是业务名称；在排程页点“重新检查”，并试着采用一个测试方案，再把应用交给客户。

### 制造业：机台排产

制造业样例各带一个应用 `workshop/apps/machine-scheduling.app.yaml`：中文网络 `manufacturing_industry_zh_cn` 上的 **机台排产**，英文网络 `manufacturing_industry_en_us` 上的 **Machine Scheduling**。它把工序和维修工单排到生产设备上，直接修改这两种对象，所以只有一页，没有计划记录。

客户环境需要（按 ID）：

- **调度对象：** `manufacturing_operations`（日期 `planned_start_date` / `planned_end_date`，机台 `planned_machine_id`，`status`，`production_order_id`，`operation_name`，`predecessor_operation_id`）和 `maintenance_work_orders`（`planned_start_date` / `planned_end_date`，`machine_id`，应保养日 `planned_date`，`status`，`maintenance_plan_id`）。
- **资源和关联：** `production_machines`（`machine_name`、`work_center_id`）、`work_centers`（`work_center_name`）、`production_orders`（`due_date`，工序的目标）和 `maintenance_plans`（`plan_name`，悬停卡片里显示），以及文件里用到的关系：工序的生产工单、前序工序，设备的工作中心，维修工单的保养计划。
- **行动：** `<网络>_adjust_operation_schedule`（工序、计划机台、开始、结束）和 `<网络>_adjust_maintenance_work_order`（维修工单、开始、结束）。维修工单只能改时间，留在本设备那一行。
- **规则函数**，在工具箱 `制造业排程规则`（中文）或 `Manufacturing_Schedule_Rules`（英文）里：`工单齐套` / `Work_Order_Kit`、`设备能力` / `Machine_Capability`、`人员资质与班次` / `Operator_Qualification_And_Shift`、`换型提示` / `Changeover`。它们自己读网络里的物料、能力、排班和工艺对象；客户网络需要相同的对象类，或者用同名的函数换成客户自己的。英文应用页面上的规则名称是 Work order kit、Machine capability、Operator qualification and shift、Changeover：页面名称是 `name`，函数是 `tool.toolName`。

按客户要改的地方：

- **状态取值：** 每个 `doneWhen` 里的已完成是 `已完成`（中文）或 `completed`（英文）。英文应用另用计算字段 `statusText` 把 `status` 显示成可读文字（`not_started`、`in_progress`、`completed`、`planned`），要和客户的取值一起改。
- **时间范围：** 甘特从基准日期 `2027-03-01` 打开，显示十天（`daysBefore: 1`、`daysAfter: 8`）。十天才能让两天的工序条放下“工单号 + 工序名”；把基准日期默认值改成客户的计划起始日。其他日子用缩放和基准日期查看。
- **计划条文字：** 工序显示 `production_order_id` 和 `operation_name`，维修工单显示工单号；悬停卡片补充工序名或保养计划名和状态。
- 导入后点一次“重新检查”：四个规则都应有结果，“未能校验”为 0。
