# 0.1.18: remove the Skills object type

Remove only the `skills` / `Skills` object type from the Chinese supply-chain model. Compared with 0.1.17, there are 11 object types instead of 12, with the same 14 relations and business data. Every remaining business object has a resource mapping. Registration, publication, mounting and verification of the two Skills remain unchanged. Other samples are unchanged.

Source changes do not remove objects from existing installations. To change versions, preserve required data and user changes, then use the standard uninstall/install flow. Uninstall removes sample data and owned resources. There is no in-place migration or automatic online cleanup.

A fixed candidate still requires fresh-install acceptance before publication. This note does not claim publication or installation on 8081.

Installation, binding, function/Skill registration and verification scripts also use optional subprocess diagnostics, preserving execution and receipt protocols. Older installers fall back to the original execution. Rebuild this changed candidate; the earlier 0.1.18 model check is not fresh-install acceptance of this package.
