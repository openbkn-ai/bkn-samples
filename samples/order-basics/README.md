# Order basics

A minimal independent sample using the existing `openbkn.ai/sample-install.v1` profile. Synthetic data: three products, four orders, eight ordered units and a joined order amount of 750.

The package creates two data-backed object types and one order-to-product relation. It intentionally declares no functions, metrics or Skills. The supply-chain sample provides those components.

Install through **One-click onboarding** on the OpenBKN homepage: refresh the official catalog, select **订单入门** (Order Basics) and click **Install**. After verification completes, open the knowledge network and inspect the four orders and their products.

If the catalog is unreachable, download this sample's `package.tar.gz` from [Releases](https://github.com/openbkn-ai/bkn-samples/releases), then choose **Import offline package** and install it. The referenced data image must be available to the target cluster; ask the administrator to prepare it for restricted networks. Users do not need to run build commands.

To install a new version, uninstall the old sample first. Uninstallation removes sample data and user edits; deleting a cached package does not uninstall resources.

## Developer notes

Build the data image with `docker build -f db/Dockerfile .` from this directory. The fixed base image supplies the existing MariaDB initialization dispatcher; it selects this sample by manifest identity. Build the package with the repository's candidate tool. The shared installer and Studio require no sample-specific changes.
