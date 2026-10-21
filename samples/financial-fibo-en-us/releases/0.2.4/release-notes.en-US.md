# 0.2.4 — unpublished candidate

Fix optional observation batching to accept the JSON object strings advertised by the installed capability schema, while retaining SDK object compatibility. Reject malformed or nonobject JSON, duplicate JSON keys and duplicate normalized scopes before loading sources. Financial formulas, facts, questions, reference answers, required arguments, outputs and resource bounds are unchanged from the sealed 0.2.3 source. The 0.2.3 partial run is preserved without scoring.

This candidate requires OpenBKN >=0.2.1 <0.3.0. The original public single pass scored 96/100 financial fields per language; after platform fixes the four specified historical tool paths passed, with complete evidence. No full-bank rerun or blind-accuracy claim. This is a source PR only; publish a fixed package through a separate reviewed workflow after source merge.
