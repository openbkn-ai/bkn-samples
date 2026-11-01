# Sample diagnostics draft releases — 2026-10-31

Historical preparation record. Current publication and acceptance status: [twelve verified diagnostics releases](diagnostics-release-acceptance-20261031.md). The published versions in the README and catalogs remain authoritative.

PR [#236](https://github.com/openbkn-ai/bkn-samples/pull/236) merged as `5fea3c2b01293e6baf9056fed22edd3d2c2e6c59`. The diagnostic hooks changed in all 12 samples offered on OpenBKN 0.2.1, so each needs a new immutable package. Chinese Supply Chain also removes the Skills entity for #217; its Skill files remain included. Order Basics is outside this release.

| Sample | Candidate version | Package SHA-256 |
| --- | --- | --- |
| supply-chain | [0.1.18 draft](https://github.com/openbkn-ai/bkn-samples/releases/tag/untagged-160349bac4ec382fe441) | `f22c334f2bf0dfbbd94cbbd40e38d6a348508b8927bd7445cf3c0438eb716be9` |
| supply-chain-en | [0.1.12 failed draft](https://github.com/openbkn-ai/bkn-samples/releases/tag/untagged-49bf70ee6b08f704aaa8) | `9bb6d0d27cd88501fbc029b6537599654fdb4bbae0a335d118ec899b2c528d86` |
| world-cup | [0.1.8 draft](https://github.com/openbkn-ai/bkn-samples/releases/tag/untagged-1e516dff3d7d763d5c2c) | `21ad47f7079e7788a5a52b6d449d7d448bd35abef9f07a02900fad3e757fa50a` |
| world-cup-en | [0.1.4 draft](https://github.com/openbkn-ai/bkn-samples/releases/tag/untagged-0cf5af9db5b7ac1b67a2) | `aaa94753bc5af7a994af7370cbbea440532fcbccaa24fcd52acf0f334f9c61c8` |
| manufacturing-industry-en-us | [0.1.6 draft](https://github.com/openbkn-ai/bkn-samples/releases/tag/untagged-b5b7e688386d390a8540) | `bb8a773cd33ec80041e045f3df41d163ccde12bc03d296f673ff91022cdcdb9f` |
| manufacturing-industry-zh-cn | [0.1.6 draft](https://github.com/openbkn-ai/bkn-samples/releases/tag/untagged-d38c5a3ec90dfd740fb4) | `277c82d272c373b02bfe92e3fc72f68683d9f988a6601c424b0b359c6db30e74` |
| financial-fibo-en-us | [0.2.8 draft](https://github.com/openbkn-ai/bkn-samples/releases/tag/untagged-c33d50e07e63494ddb0c) | `29e787be8bb1fe860bd188a4d76b2b36f2b39586b73515448a3039a5325216c1` |
| financial-fibo-zh-cn | [0.2.8 draft](https://github.com/openbkn-ai/bkn-samples/releases/tag/untagged-0e520fc22caaea367d94) | `f77afb0f0f86d88fe88ae38bb161296e2f00435c1dfca8a98d70c0b72006cd29` |
| retail-gs1-en-us | [0.1.3 draft](https://github.com/openbkn-ai/bkn-samples/releases/tag/untagged-ed4dd33319018d8e714e) | `92b241d646f07c96a619fdec93133bce9273db09ce55fd9cc15ee9511b2fd180` |
| retail-gs1-zh-cn | [0.1.3 draft](https://github.com/openbkn-ai/bkn-samples/releases/tag/untagged-10bb5c8cf0694ecf0136) | `e5dd8bd1b5fe0e403beca64e8a742ec7b67bfa8641e3bea021471be4a1c4baee` |
| energy-saref4ener-en-us | [0.1.7 draft](https://github.com/openbkn-ai/bkn-samples/releases/tag/untagged-4733b686f25b34a10c20) | `5b4932c44014448abea5a378656b804ef9fae0cf73b4bc50258feefb1c895e0a` |
| energy-saref4ener-zh-cn | [0.1.7 draft](https://github.com/openbkn-ai/bkn-samples/releases/tag/untagged-8eab712996fbf0ddc205) | `192092c4c95b6601d01622685fa2ec2f85c1fe2ba01e3e7b7f3096a07fda2267` |

Draft links require repository permissions that allow viewing draft Releases. Each draft includes the fixed package, `SHA256SUMS`, bilingual release notes and `candidate-checks.json`. No successful platform `verification.json` is included. All uploaded attachments were downloaded again and their SHA-256 digests matched the local files and GitHub asset digests; see the [draft and attachment checks](issue-217-225/draft-release-verification-5fea3c2.json).

All packages were built from the clean merge commit above. The generated manifests match the archive digests. Offline import metadata and integrity checks passed for both architecture declarations, and OpenBKN 0.2.0 correctly rejected the packages. These checks did not execute platform installation hooks and do not certify native execution.

Before publication, follow [the publication standard](candidate-publication.md) and [offline installation acceptance](offline-installation.md) using these exact archives and the installer built from the merged diagnostics code. Record fresh installation, retry, uninstall/reinstall, declared capability checks, cross-sample isolation, offline cleanup and bounded failure recovery. Do not replace this evidence with earlier package acceptance or the separate Supply Chain model experiment.

After acceptance, publish the same archives as new Release attachments, verify the uploaded digests, commit genuine verification metadata, and update the catalog pinned to that retained metadata commit. Update the README release links together with the official catalog. Historical assets remain unchanged.

Existing installations need uninstall followed by installation of the new version; uninstall clears sample-owned data and edits. Installation hooks alone cannot deliver the complete #216 logging changes: the sample service also needs the merged installer runtime.

The merged installer image publishing workflow [completed successfully](https://github.com/openbkn-ai/bkn-samples/actions/runs/41218856454). This confirms runtime artifacts were built, not that the fixed samples were installed or accepted.

## English Supply Chain acceptance failure

On 8081, the fixed 0.1.12 package completed its installer stages, but the independent query of its `skills` object returned HTTP 503, `OntologyQuery.InternalError.CheckPermissionFailed`, with `object type skills has no published data source`. Its other 11 business objects are separate from this invalid object. See the [live failure receipt](issue-217-225/supply-en-0112-acceptance-failure.json). Do not publish this draft or overwrite its recorded archive.

The minimal replacement candidate is 0.1.13: apply the same Skills entity removal already made for Chinese Supply Chain, preserving Skill packages, data, functions and 14 relations. Both language model regressions now require only objects backed by resource mappings. The replacement needs a clean-source build and its own full package acceptance before publication. PR #237 is merged; its draft attachment checks remain historical evidence, not installation acceptance.
