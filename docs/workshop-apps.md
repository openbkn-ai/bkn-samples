# Workshop apps in a sample

A sample can bring Workshop apps that open on its own knowledge network right after installation. The same file is how an app moves to a customer environment: export it from the app list, import it there.

## What an app file is

An app file (`<name>.app.yaml`) is the app's draft exactly as the app list exports it.

- `dependencies.knowledgeNetwork` names the network the app is built on.
- `sources[].objectType`, action IDs (`…operations[].action.id`) and field names point at that network's object types, actions and properties by ID.
- Rule functions (`pages[…].layers[].ruleTools[]` and `scheduleModel.tasks[].rules[]`) name their function by `tool.boxName` (toolbox name) and `tool.toolName` (function name). An export also carries `tool.box` / `tool.tool`, the IDs in the environment it came from. They are not used elsewhere: Workshop calls the function of the same toolbox and function name when the IDs are not found there.
- `app.id` is the exported app's ID. Importing or installing gives the new app its own.

## Adding an app to a sample

1. Install the sample, and build the app in Workshop on the sample's knowledge network, for example with the resource scheduling workbench wizard.
2. In the app list, export it.
3. Save the file as `samples/<sample>/workshop/apps/<name>.app.yaml`. The installer accepts an export as it is. Keeping the repository copy free of environment IDs is tidier: delete `app.id` and the `box` / `tool` lines.
4. A sample in another language gets its own app, built on that sample's network with copy in that language.

The installer checks every file:

- `apiVersion` is `workshop.openbkn.ai/v1`;
- the app has a name of at most 128 characters;
- `dependencies.knowledgeNetwork.id` is the sample's knowledge network;
- there is at least one page;
- every rule function has `boxName` and `toolName`.

Two apps of one sample cannot share a name.

## Installation and removal

- Packages carry the `workshop/` folder and declare the capability `sample.workshop-apps`; a sample service without it rejects the package before downloading.
- After the platform checks pass, the installer:
  1. looks each rule function up by toolbox name and function name, only in the toolboxes this installation created, and writes their IDs in; if one is missing, the installation fails before any app is created, and the error names the missing functions;
  2. creates each app on the sample's network with the file as its draft;
  3. publishes it, so its pages open from the app list;
  4. keeps the app IDs in the installation record (`workshopApps`), written after every change.
- Installing again, or retrying a failed installation, first deletes the recorded apps and any app of the same name on the sample's network, then creates them again.
- Uninstalling deletes the recorded apps first, then the knowledge network they are built on.
- The installing administrator needs permission to create Workshop apps.
- Workshop is part of the professional edition. On a platform without it, every Workshop route answers 404. The installer then installs the sample without its apps, and diagnostics record the skipped step.

## Reusing an app in a customer environment (for FDEs)

### 1. Export

In the app list, open the app's menu and export it. You get the draft as `<app id>.app.yaml`. A sample's app is also in the sample repository under `workshop/apps/`.

### 2. Prepare the customer environment

The app reads and writes only what its file names. Before importing, the customer environment needs:

- **A knowledge network with the same IDs.** Each `sources[].objectType`, with the properties the app uses (look for `field`, `startField`, `resourceField`, `barFields`, `popoverFields`, `pairs` and the like), must exist under the same ID. For the supply app this is the forecast, plan, production line and line stoppage object types, plus product for the line check. Installing the sample gives you all of them; on a customer's own network, create or map them first.
- **The actions the app runs.** These are the `action.id` values under `operations`, for example `<network>_kitplan_create` and `<network>_kitplan_adjust` for the supply app. Each must exist on that network with the parameters the file maps.
- **The rule functions.** Each must be mounted in a toolbox whose name is the file's `boxName` and enabled under the file's `toolName`, for example `供应链原生计算函数` / `齐套检查` and `产线可生产` (zh) or `Supply_EN_Functions` / `Kit_Check` and `Line_Can_Build` (en). A function that cannot be found shows as "could not check" on the page, and the scenario cannot be applied.

### 3. Import

1. In the app list, choose **Import** and pick the file.
2. Workshop matches `dependencies.knowledgeNetwork` to a network you can see: by ID, then by name. It checks the object types and actions against that network, and creates a new draft app.
3. Change the name in the file first if an app of that name is already there, so the copy is easy to tell apart.
4. Open the draft from the builder's preview, or publish it so business users can open its pages.

Rule functions are found by toolbox and function name when the page runs, so they need no rebinding after import. Opening the schedule wizard once and saving also rebinds them to the current IDs.

### 4. Fit it to the customer's data

- **Different network or object type IDs:** edit the file before importing. Change `dependencies.knowledgeNetwork.id`, every `objectType`, and the action IDs. Keep field names in step with the customer's properties.
- **Different status values** (for example a cancelled or closed status): change the values in `where`, `doneWhen`, `active` and the `classify` cases together. The page's derived sets, such as the unscheduled demand, depend on them matching.
- **Different labels and language:** page titles, layer labels and computed field labels are plain text in the file. Translate them together with the classify values that filters compare against.
- **Rule functions under other names:** set `boxName` and `toolName` to the customer's toolbox and function names. Both rule-tool lists use them: the Gantt layer's `ruleTools` and `scheduleModel.tasks[].rules`.
- After importing, open both pages, check that the bars show business names, run **Check again** on the scheduling page, and apply one test scenario before handing the app over.

### Manufacturing: Machine Scheduling

The manufacturing samples bring one app each, `workshop/apps/machine-scheduling.app.yaml`: **机台排产** on `manufacturing_industry_zh_cn` and **Machine Scheduling** on `manufacturing_industry_en_us`. It schedules operations and maintenance work orders on production machines and changes those objects directly, so it has a single page and no plan records.

What the customer environment needs, by ID:

- **Scheduled objects:** `manufacturing_operations` (dates `planned_start_date` / `planned_end_date`, machine `planned_machine_id`, `status`, `production_order_id`, `operation_name`, `predecessor_operation_id`) and `maintenance_work_orders` (`planned_start_date` / `planned_end_date`, `machine_id`, `planned_date` as the due date, `status`, `maintenance_plan_id`).
- **Resources and lookups:** `production_machines` (`machine_name`, `work_center_id`), `work_centers` (`work_center_name`), `production_orders` (`due_date`, the operations' target) and `maintenance_plans` (`plan_name`, shown in the hover card), with the relations the file names: the operation's production order and predecessor operation, the machine's work center, the maintenance order's plan.
- **Actions:** `<network>_adjust_operation_schedule` (operation, planned machine, start, end) and `<network>_adjust_maintenance_work_order` (maintenance order, start, end). A maintenance order moves only in time; it stays on its machine's row.
- **Rule functions,** in toolbox `制造业排程规则` (zh) or `Manufacturing_Schedule_Rules` (en): `工单齐套` / `Work_Order_Kit`, `设备能力` / `Machine_Capability`, `人员资质与班次` / `Operator_Qualification_And_Shift`, `换型提示` / `Changeover`. They read the network's material, capability, roster and routing objects themselves; a customer network needs the same object types for them, or functions of its own under these names. On the page the English rules are labelled Work order kit, Machine capability, Operator qualification and shift and Changeover; the label is `name`, the function is `tool.toolName`.

What to change for a customer:

- **Status values:** done is `已完成` (zh) or `completed` (en) in every `doneWhen`. The English app also turns `status` into readable text with the computed field `statusText` (`not_started`, `in_progress`, `completed`, `planned`); keep its cases in step with the customer's values.
- **Window:** the Gantt opens on the base date `2027-03-01` and shows ten days (`daysBefore: 1`, `daysAfter: 8`). Ten days is what gives a two-day bar room for "work order and operation"; set the base date default to the customer's planning start. Users zoom and move the base date for other days.
- **Bar text:** operations show `production_order_id` and `operation_name`, maintenance orders their number; the hover card adds the operation or maintenance plan and the status.
- After importing, run **Check again** once: all four rules should report results, and "not checked" should be 0.
