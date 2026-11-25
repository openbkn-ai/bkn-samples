# 0.1.12: brings the 产线三维孪生 (3D production line twin) app (OpenBKN 0.2.2)

The data, rule functions, actions and the 机台排产 app are the same as in 0.1.11.

- **New app 产线三维孪生** (`workshop/apps/line-twin.app.yaml`): one page for a shop floor lead. Figures for machines, running, needing attention, queued operations and open maintenance; a 3D shop floor with the machines placed by plant and work centre, a three-colour light for running, idle and needing attention, crates on a pallet for the queued operations, turned by dragging and zoomed with the wheel; click a machine (or pick it in the list on the right) for its operations and maintenance work orders. All of it is read from the machines, operations and maintenance work orders on the knowledge network and their relations.
- The 3D shop floor is the custom component `x-ai.lineTwin`. Its package is in `workshop/components/ai-lineTwin/` and its source in `workshop/component-sources/ai-lineTwin/`. Installing creates the app, uploads the package into it, then publishes it. This needs a sample service that uploads component packages (capability `sample.workshop-components`); a service without it rejects this version before downloading. On a platform without Workshop the sample installs without its apps.
- To upgrade from 0.1.11, uninstall 0.1.11 first. The 50 bkn-eval answers are unchanged.
