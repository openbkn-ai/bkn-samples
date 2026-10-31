# Frequently asked questions

**Does this include current tournaments?** The snapshot ends with men’s 2022 and women’s 2019. No later results are implied.

**Why do team appearances exceed match counts?** Each match has two team appearance records. Count matches at match grain.

**How do agents query the sample?** With Cypher over the published object model, guided by the World Cup history analysis Skill. There is no SQL tool and no custom function.

**Why can capacity ordering be incorrect?** Source values are text. Convert capacities to integers before comparing them.

**Why is WC-1999 player-appearance coverage zero?** Those detail rows are absent from this locked snapshot. Other tables still contain its matches, goals and squads.

**Are unsuccessful shootout kicks goalkeeper saves?** Not necessarily. Report recorded kick outcomes rather than an unsupported save count.
