# 0.1.7: business-scenario test set, Skill and experience cards

This release follows the new [business PRD](../../docs/PRD.md). The earlier 50 questions keep their meaning and reference answers but are rewritten in the business language of a sports editor, team analyst or tournament data steward, with the calculation rules moved into the PRD and the knowledge network description. Adds the "World Cup history analysis" Skill and 15 experience cards; every question is answered with Cypher, with no functions or metrics, so the Community edition can use all of it.

The generic SQL tool is no longer registered, and the 10 name fields that the match and team-appearance objects lacked (tournament, match, stage, group, stadium, city, country, team, opponent and result) are now modeled, matching the English package. Data are unchanged.

Follow the existing uninstall/install workflow to replace an installed package; uninstall removes the sample's data and owned resources, so preserve any required changes first. Acceptance results are recorded separately and do not guarantee model answer accuracy.
