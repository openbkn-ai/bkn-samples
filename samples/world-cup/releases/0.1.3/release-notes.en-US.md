# 0.1.3

- Online and offline installations use the product-provisioned sample database server, with separate databases and accounts for each sample.
- The complete offline package contains sample data and resources; no sample OCI image or manual node import is required.
- Uninstallation removes owned resources and preserves history and other samples.

Requires the OpenBKN 0.2.0 patch providing the shared sample database capability. Uninstall an existing sample before installing this version; in-place migration is not supported.
