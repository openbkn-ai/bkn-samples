# Workshop apps in a sample

A sample can bring Workshop apps that open on its own knowledge network right after installation.

## Adding an app

1. Install the sample, then build the app in Workshop on the sample's knowledge network, for example with the resource scheduling workbench wizard.
2. Export it from the app list. The export is the app's draft, named `<id>.app.yaml`.
3. Save it as `samples/<sample>/workshop/apps/<name>.app.yaml`. Remove `app.id`, and remove `box` and `tool` from every rule function so that only `boxName` and `toolName` remain. They appear in two places: `pages[…].layers[].ruleTools[].tool` and `scheduleModel.tasks[].rules[].tool`. A sample in another language gets its own app, built on that sample's network with copy in that language.

The installer checks every file:

- `apiVersion` is `workshop.openbkn.ai/v1`;
- the app has a name of at most 128 characters and no `app.id`;
- `dependencies.knowledgeNetwork.id` is the sample's knowledge network;
- there is at least one page;
- every rule function is named by `boxName` and `toolName`, without IDs.

Two apps of one sample cannot share a name.

Object types and actions are referenced by ID; they are the same in every installation of the sample. Toolbox and tool IDs are new on every installation. The installer looks each rule function up by toolbox name and tool name, only in the toolboxes this installation created, and writes their IDs into the app. If a function is missing, the installation fails before any app is created, and the error names the missing functions. Model tools are called by ID only; a sample app should not use them.

## Installation and removal

- Packages carry the `workshop/` folder and declare the capability `sample.workshop-apps`. A sample service without it rejects the package before downloading.
- After the platform checks pass, the installer creates each app on the sample's network with the file as its draft, and publishes it, so its pages open from the app list. The created app IDs are kept in the installation record (`workshopApps`), written after every change.
- Installing again, or retrying a failed installation, first deletes the recorded apps and any app of the same name on the sample's network, then creates them again.
- Uninstalling deletes the recorded apps with the sample's functions and Skills.
- The installer needs the installing administrator to be allowed to create Workshop apps.
- Workshop is part of the professional edition. On a platform without it, every Workshop route answers 404, and the installer then installs the sample without its apps; diagnostics record the skipped step.
