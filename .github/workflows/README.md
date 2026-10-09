# DeepSeek Code Review

- 规则：[REVIEW_RULES.md](../REVIEW_RULES.md)
- 工作流：[automation-deepseek-review.yml](automation-deepseek-review.yml)
- 确定性控制器：[deepseek_review.py](../scripts/deepseek_review.py)
- 参考：[foundry #1985](https://github.com/openbkn-ai/bkn-foundry/pull/1985)、[studio #814](https://github.com/openbkn-ai/bkn-studio/pull/814)

## 配置

1. 人工审阅引入变更，将规则、脚本和工作流合入默认分支。首次引入时 plan 会明确报告默认分支缺少可信文件，verdict 会失败并说明本轮未经 AI 审核；不会回退运行 PR 中的脚本，也不会冒充审核通过。合入后新 PR 或手动触发才是实际验证入口；首次启用的人工审核与合并由维护者决定。
2. 设置仓库 Actions Secret `DEEPSEEK_API_KEY`。不提交 key 文件，不使用 Claude OAuth token。模型与复核请求发往 DeepSeek；关闭 Action 的额外行内评论分类，避免该阶段使用 Anthropic 默认地址。
3. 如需 AI 审核作为强制门槛，要求最终 `verdict` 检查通过（以 GitHub 实际 check 名称为准），并启用新提交后的旧批准失效。不要把只有 `plan` 成功当审核通过。
4. 允许 GitHub Actions 创建/批准 PR，或配置 `REVIEW_APP_ID`、`REVIEW_APP_LOGIN` variables 和 `REVIEW_APP_PRIVATE_KEY` Secret。`REVIEW_APP_LOGIN` 是审核 App 的完整 bot 登录名（如 `my-reviewer[bot]`），用于验证历史状态的作者；配置 App 时必须填写。没有 App 时使用 workflow token；批准被平台拒绝会改贴评论，明确没有 APPROVED 状态。

建议合并保护同时要求至少一个批准、新提交撤销旧批准、最终 `verdict` 和现有 sample-contract 检查通过。这里是配置建议，尚未修改 GitHub 保护设置；AI 批准不替代人工合并决定。

四阶段中，review/verify 使用只读 GitHub token；verdict 的确定性脚本才有表态权限。API key 只传给模型 Action。外部 fork、draft、关闭 PR 和不具权限的评论触发均不调用模型。新提交自动复评，不沿用旧提交的批准。

verdict 使用 `always()` 汇总：计划失败、取消、无有效计划或首次启用都不能通过最终检查。fork/draft 的 PR 事件同样不会通过自动审核门槛。无需审核的普通评论事件不调用模型或发出表态。不能把 skipped 的审核 job 视为批准。

## 结论

| 情况 | PR 表态与最终检查 |
| --- | --- |
| 首次启用、计划失败或没有有效计划 | Summary 说明未审核；最终检查失败，不发批准 |
| 完整评审，没有确认阻塞 | APPROVE；最终检查通过 |
| 独立复核确认阻塞 | REQUEST_CHANGES；最终检查失败 |
| 待确认意见 | 作为提示，不阻断 |
| 模型错误、输出缺失或未覆盖 | COMMENT 说明未完成；最终检查失败 |
| 阻塞复核缺失或无效 | COMMENT 说明未完成；最终检查失败 |
| 某条阻塞无法完成核实 | COMMENT 说明未完成；保留问题，最终检查失败 |
| PR head/base 在运行中变化 | 丢弃旧结论；检查失败，当前提交需重评 |
| GitHub 拒绝 APPROVE | 改贴评论；完整无阻塞的最终检查仍可通过，但没有批准状态 |

中间 JSON artifact 保留 7 天。结果包含固定 head/base、规则 revision 和证据位置；不得复制凭据值。完整文件清单超过 500 或 GitHub 返回不完整时停止审核，需拆分 PR。本文未声称已执行 AI review，真实验证需规则进入默认分支及 Secret 配置完成后进行。

未关闭问题保存在评审正文的 `deepseek-sample-state` 状态块中，不依赖短期 artifact。plan 只接受 github-actions 或配置的审核 App 发布的状态；verify 每轮核实旧问题和新发现，只有有证据证明已修复或不成立才关闭。复核失败保留状态，不能批准。问题上限 20，超过时要求拆分，不静默丢弃。待确认项首轮最多两条，复评最多一条。

现有 sample-contract CI 与发布工作流保持独立；AI 批准不能代替候选制品实际安装验收，不能自动触发合并或发布。
