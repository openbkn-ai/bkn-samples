# Supply chain · version 0.1.4

## Changes

- Records the IDs of execution resources created by managed sample installation.
- Supports uninstall and fresh reinstall with the updated sample service and Studio; installation history is retained.
- Retains the existing data, knowledge network, functions, metrics and Skills and fixed database image.

## Limitations

- Uninstall deletes the sample data and user changes to sample resources.
- Existing releases without ownership receipts cannot be automatically uninstalled.
- Installation requires an administrator and compatible OpenBKN 0.2.0 APIs; questions require a configured model.
- This candidate must pass real installation, uninstall and reinstall acceptance before publication.
