# 0.2.5 — publication metadata correction

Supersedes 0.2.4 for official catalog registration. Corrects the release description and declares the actual package requirements, including `execution.function` and `execution.skill`. Requires OpenBKN >=0.2.1 <0.3.0. Install with the standard shared-MariaDB sample workflow.

Business data, native ontology, 3 functions, 2 recorded-snapshot metrics, 1 Skill and evaluation questions/answers are unchanged from 0.2.4. Each language retains 20 tables and 78,356 synthetic records. Existing 0.2.4 Release assets remain immutable.

This patch is checked through fixed-package import, fresh installation and execution-capability compatibility gates. It does not rerun the 100-question banks or the previous four-path regression. The original single-pass financial-field scores remain EN 96/100 and ZH 96/100; the earlier four-path regression passed 4/4, and 0.2.4 representative technical checks passed 16/16. These historical results are not new 0.2.5 model-accuracy measurements. See the matching Release acceptance.json for actual installation results, deployed runtime and validation limits.
