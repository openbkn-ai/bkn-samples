# AI review for sample pull requests

The concise review policy lives in [.github/REVIEW_RULES.md](../../.github/REVIEW_RULES.md).
DeepSeek reviews installation correctness, update safety, version integrity and
pluggable compatibility. Only source-backed findings confirmed by an independent
verification pass request changes. Advisory questions do not block.

The workflow follows Foundry PR #1985 and Studio PR #814: plan, review, verify,
then a deterministic verdict. It uses Claude Code Action with the DeepSeek
Anthropic-compatible endpoint and `deepseek-v4-pro`.

Each ready, same-repository PR update is reviewed, including data and skill
Markdown. Maintainers can request another round using `/review`, `@deepseek`, or
the compatible `@claude` command. Rules/controllers come from the default branch;
PR source is inspected as Git objects without executing it. Missing or incomplete
reviews and stale commit results cannot approve. Humans decide whether to merge.

Unresolved findings persist in reviews authored by the configured reviewer bot.
Every round independently verifies both old and new findings. Only source-backed
proof of a fix or an incorrect finding closes it; incomplete verification keeps
the finding and fails the final check. Advisory output is capped at two items on
the first round and one on later rounds by the deterministic controller.

The final verdict always runs. Failed or missing plans fail the gate. On first
installation, missing trusted files on the default branch are reported explicitly
and the gate fails without executing PR controllers; maintainers must review the
initial installation themselves.

See the [workflow setup](../../.github/workflows/README.md) and
[Chinese overview](sample-pr-review-rules_cn.md). The independent sample-release
protocol and actual platform verification remain separate implementation work.
