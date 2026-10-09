# DeepSeek Code Review

- 规则：[REVIEW_RULES.md](../REVIEW_RULES.md)
- 工作流：[automation-deepseek-review.yml](automation-deepseek-review.yml)
- 确定性控制器：[deepseek_review.py](../scripts/deepseek_review.py)
- 参考：[foundry #1985](https://github.com/openbkn-ai/bkn-foundry/pull/1985)、[studio #814](https://github.com/openbkn-ai/bkn-studio/pull/814)

## 配置

1. 人工审阅引入变更，将规则、脚本和工作流合入 main。自动入口使用 `pull_request_target`，首次引入 PR 不会采用 PR 内新增的审核工作流；没有 `sample-ai-review` 状态代表尚未完成 AI 审核。首次启用的人工审核与合并由维护者决定。工作流安装后再用新 PR 或 main 上的手动入口验证；若可信规则或脚本缺失，会明确报告未完成，不回退运行 PR 文件。
2. 设置仓库 Actions Secret `DEEPSEEK_API_KEY`。不提交 key 文件，不使用 Claude OAuth token。模型与复核请求发往 DeepSeek；关闭 Action 的额外行内评论分类，避免该阶段使用 Anthropic 默认地址。
3. 如需 AI 审核作为强制门槛，要求提交状态 `sample-ai-review` 通过，并启用新提交后的旧批准失效。不要要求原生 `verdict` job 作为审核门槛：评论与手动运行的 job 属于 main，而统一状态显式绑定被审核的 PR head SHA。先完成真实运行，使该状态出现在 GitHub 可选检查列表中，再配置保护。
4. 允许 GitHub Actions 创建/批准 PR，或配置 `REVIEW_APP_ID`、`REVIEW_APP_LOGIN` variables 和 `REVIEW_APP_PRIVATE_KEY` Secret。`REVIEW_APP_LOGIN` 是审核 App 的完整 bot 登录名（如 `my-reviewer[bot]`），用于验证历史状态的作者；配置 App 时必须填写。没有 App 时使用 workflow token；批准被平台拒绝会改贴评论，明确没有 APPROVED 状态。

建议合并保护同时要求至少一个批准、新提交撤销旧批准、`sample-ai-review` 和现有 sample-contract 检查通过，并要求分支与 main 保持最新。这里是配置建议，尚未修改 GitHub 保护设置；AI 批准不替代人工合并决定。

自动入口来自 main 的 `pull_request_target`；顶层 `issue_comment` 同样采用默认分支，手动入口只支持选择 main。不使用 PR 行内评论事件触发工作流，行内意见及作者解释仍会读取；请在 PR 顶层评论中写 `/review`、`@deepseek` 或 `@claude`。全部入口只支持以 main 为目标的同仓非 draft PR。

review/verify 使用只读 GitHub token；可信 plan 脚本只能发布 pending 状态，verdict 的确定性脚本发布最终状态与 PR 表态。API key 只传给模型 Action。PR 内容始终只作为 Git 对象读取，不签出或运行；不加载 PR 中的 hook、工具或审核脚本。外部 fork、draft、关闭 PR 和不具权限的评论触发均不调用模型。新提交自动复评，不沿用旧提交的批准。

plan 确定目标 SHA 后先发布 `sample-ai-review: pending`，防止同一提交复评时沿用旧成功。verdict 使用 `always()` 汇总并发布 success/failure/error：计划失败、取消或结果缺失不能写 success；若计划未能获得目标提交或运行被强制取消，状态保持缺失或 pending，同样不满足门槛。无需审核的普通评论事件不调用模型或改变提交状态。不能把 skipped 的审核 job 视为批准。

## 结论

| 情况 | PR 表态与最终检查 |
| --- | --- |
| 首次启用或没有目标提交 | 状态缺失；不发批准，不满足审核门槛 |
| 计划失败或没有有效结果 | error；不发批准 |
| 完整评审，没有确认阻塞 | APPROVE；success |
| 独立复核确认阻塞 | REQUEST_CHANGES；failure |
| 待确认意见 | 作为提示，不阻断 |
| 模型错误、输出缺失或未覆盖 | COMMENT 说明未完成；最终检查失败 |
| 阻塞复核缺失或无效 | COMMENT 说明未完成；最终检查失败 |
| 某条阻塞无法完成核实 | COMMENT 说明未完成；保留问题，最终检查失败 |
| PR head/base 在运行中变化 | 丢弃旧结论；不向新 head 写状态，同一 head 的 base 变化写 error，需重评 |
| GitHub 拒绝 APPROVE | 改贴评论；完整无阻塞的最终检查仍可通过，但没有批准状态 |

中间 JSON artifact 保留 7 天。结果包含固定 head/base、规则 revision 和证据位置；不得复制凭据值。完整文件清单超过 500 或 GitHub 返回不完整时停止审核，需拆分 PR。本文未声称已执行 AI review，真实验证需规则进入默认分支及 Secret 配置完成后进行。

未关闭问题保存在评审正文的 `deepseek-sample-state` 状态块中，不依赖短期 artifact。plan 只接受 github-actions 或配置的审核 App 发布的状态；verify 每轮核实旧问题和新发现，只有有证据证明已修复或不成立才关闭。复核失败保留状态，不能批准。问题上限 20，超过时要求拆分，不静默丢弃。待确认项首轮最多两条，复评最多一条。

现有 sample-contract CI 与发布工作流保持独立；AI 批准不能代替候选制品实际安装验收，不能自动触发合并或发布。

## 启用验收

用一个小型同仓 PR 验证：开启后应出现绑定 head SHA 的 pending 状态，完整审核后转为 success/failure/error。在不推新提交的情况下于顶层评论写 `/review`，确认同一 head 的状态重新进入 pending 并更新最终结果。记录运行链接、提交 SHA 和实际结论后，再启用 `sample-ai-review` 保护门槛。
