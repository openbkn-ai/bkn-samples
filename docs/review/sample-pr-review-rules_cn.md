# 样例 PR 的 AI 审核

审核规则只有一份：[.github/REVIEW_RULES.md](../../.github/REVIEW_RULES.md)。AI 检查能否安装体验、更新安全、版本真实性和可插拔兼容；只阻断有源码证据且经过独立复核的问题。

工作流参考 [foundry #1985](https://github.com/openbkn-ai/bkn-foundry/pull/1985) 和 [studio #814](https://github.com/openbkn-ai/bkn-studio/pull/814) 的 DeepSeek 后端与四阶段机制。执行器仍是 Claude Code Action，模型为 `deepseek-v4-pro`，接口为 `https://api.deepseek.com/anthropic`。

每次同仓 PR 开启、重开、转为 ready 或推送新提交都会审；数据、KN JSON、BKN 和 SKILL.md 同样纳入范围。维护者可以评论 `/review`、`@deepseek` 或兼容口令 `@claude` 复评，也可以手动填 PR 号触发。

流程：固定提交和范围 → AI 评审 → 独立复核阻塞项 → 确定性脚本统一表态。无阻塞时批准，有复核通过的阻塞时请求修改；模型失败、没审完、复核缺失或结果过期不批准。待确认意见不阻断。合并由人决定。

吸收 Studio 的简短意见和复评收敛规则，以及 foundry 当前的阻塞项跨轮记录。未关闭问题保存在可信审核 bot 的评审正文中，每轮逐项复核；有证据确认已修复或不成立才关闭，无法核实保留并使最终检查失败。无需手动撤销口令，作者说明理由后用 `/review` 请求核实即可。待确认首轮最多两条、复评最多一条，由脚本控制。

规则和脚本从默认分支读取，PR 内容仅通过 Git 对象核查，不签出或运行 PR 代码。AI 作业的 GitHub token 只读，最终 job 才获得表态权限。运行期间 head 或 base 改变会丢弃过期结论。首期不自动审 fork 和 draft PR。

首次启用须先将规则、脚本和工作流合入默认分支，再配置 `DEEPSEEK_API_KEY`。需要强制门槛时在 GitHub 设置中要求该工作流的最终检查，并启用新提交后的批准失效。GitHub 不允许 Actions 批准时，结果改贴评论，不冒充 APPROVED；也可沿用 reviewer App 的配置。

初版确定性扫描工作流和 CODEOWNERS 占位示例已移除，AI 按简明规则审核，现有契约 CI 继续独立把关。当前 v1alpha1 根 VERSION 保持兼容，独立发布协议、实际安装验收和正式发布门槛是后续交付任务。

详见 [工作流配置说明](../../.github/workflows/README.md)。未运行真实 AI review 或平台安装验收。
