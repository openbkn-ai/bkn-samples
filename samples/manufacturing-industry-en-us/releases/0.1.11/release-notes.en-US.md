# 0.1.11: rule checks answer faster (OpenBKN 0.2.2)

Data, the Machine Scheduling app (机台排产 in the Chinese sample) and the two adjust actions are the same as in 0.1.10.

- **Faster rule checks**: when Workshop calls the four rule functions and the two adjust functions through the toolbox, outside a conversation, they read objects through the ontology query API directly and no longer touch the sandbox's built-in BKN reader. Before, each such call left an empty directory in the sandbox's shared workspace, which the sandbox scans before and after every call, so checks got slower the more they ran. Inside a conversation they read as before. The results are unchanged.
- Upgrading from 0.1.10 means uninstalling 0.1.10 first. The 50 existing bkn-eval answers are unchanged.
