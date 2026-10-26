# Fixed SAREF reference sources

SAREF4ENER 2.1.1 and its directly imported SAREF Core 4.1.1 are semantic references
for this synthetic operational sample. Their version-specific Turtle bytes were
restored from ETSI and exactly match the retained historical SHA-256 freeze.
`source-lock.json` records the URLs and hashes. The official linked Forge licensing
page and each source repository's actual BSD-3-Clause LICENSE are retained;
`license-lock.json` pins each license to a source repository commit and SHA-256.

`inventory.json` records URI-named classes/properties, labels and anonymous-class
counts, produced using RDFLib 7.1.4 without network import resolution. It is a source
inventory, not a claim that all upstream classes are operational BKN tables.
The 15 operational objects, customer/site records and settlement/dispatch rules
are local extensions. They do not assert owl:equivalentClass, ETSI certification,
full OWL reasoning or actual device-control/payment behavior. See the sample's
`docs/bkn-modeling-spec.md` and `docs/business-capability-contract.md` for scope.

Recovery did not retain the original selected-mapping.json. Existing business-model
scope is preserved; this record does not invent a missing class-equivalence mapping.
