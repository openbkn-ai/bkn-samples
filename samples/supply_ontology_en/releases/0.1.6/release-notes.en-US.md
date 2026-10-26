# 0.1.6: align allocation with combined BOM classification

The English allocator now uses the same alt_method/group/priority classifier as
BOM filtering, native fact acquisition and the Chinese allocator. Invalid
priority-zero replacement rows fail explicitly even when called outside material
assurance. New bilingual direct-allocation regression cases cover this path.
Locked source data and valid baseline results remain unchanged. This new candidate
version preserves the earlier local 0.1.5 package identity. Runtime and original
historical-receipt acceptance remain pending; no stable catalog admission.
