# 0.2.2 — Independent known-field preservation

Local unpublished candidate. Requires OpenBKN >=0.2.1 <0.3.0; PR183 remains on hold.

Preserves known quantities and market value when intraday cost ordering is ambiguous; uses the USD reporting identity without requiring an external FX row. Missing non-USD FX retains local values. Collects independent quote/FX evidence, and compares caches only where reconstructed values are known. Retains2 snapshot metrics,3 read-only functions and1 investigation Skill; source facts and original100-question gold are unchanged.

Earlier0.2.0/0.2.1 runs were stopped with complete audit records; they are not completed three-round acceptance. Actual results for this candidate must be reported separately.
