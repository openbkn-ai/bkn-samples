# World Cup · version 0.1.0

These notes describe the first packaged World Cup release. Dynamic catalog publication still requires the fixed artifact and fresh-install evidence.

## Contents

- Bundles the 27 CSV files from the locked Joshua C. Fjelstul World Cup data revision and verifies their checksums before loading.
- Ships the OpenBKN-standard BKN directory with 27 object types, 29 relation types and 4 concept groups.
- Provides cross-table query scenarios and the existing SQL execution tool.
- Uses the existing MariaDB preparation, discovery, knowledge network import and binding, capability publication and verification flow.

## Limitations

- Data is licensed under CC-BY-SA 4.0 and includes the required attribution.
- Installation requires an administrator and a working platform; questions also require a configured model.
- Only the bundled image version is supported. Upgrade and uninstall are not available.
