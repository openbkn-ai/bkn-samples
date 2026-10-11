# Order basics

A minimal independent sample using the existing `openbkn.ai/sample-install.v1` profile. Synthetic data: three products, four orders, eight ordered units and a joined order amount of 750.

The package creates two data-backed object types and one order-to-product relation. It intentionally declares no functions, metrics or Skills. The supply-chain sample provides those components.

Build the data image with `docker build -f db/Dockerfile .` from this directory. The fixed base image supplies the existing MariaDB initialization dispatcher; it selects this sample by manifest identity. Build the package with the repository's candidate tool. The shared installer and Studio require no sample-specific changes.

Install into a fresh test environment through the homepage. Open the knowledge network and inspect the four orders and their products. Publishing a new version does not upgrade an existing installation.
