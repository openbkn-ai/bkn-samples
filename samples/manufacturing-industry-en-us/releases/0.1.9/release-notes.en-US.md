# 0.1.9: the Machine Scheduling app comes with the sample (OpenBKN 0.2.2)

After installation, Machine Scheduling (机台排产 in the Chinese sample) opens from the Workshop app list, with nothing to build. Data, rule functions and actions are the same as in 0.1.8.

- **App**: made with the resource scheduling workbench wizard on the sample's network and changing the scheduled objects directly. Operations and maintenance work orders share production machines, grouped by work centre; completed tasks are left out of the checks; an operation's target is its work order's due date and a maintenance work order's is its due date for maintenance; operations follow their predecessor operations.
- **Rules**: the results of the four rule functions (work order kit, machine capability, operator qualification and shift, changeover) are marked and counted with the built-in checks; hard constraints block applying.
- **Applying**: drag an operation to another day or machine; a maintenance work order belongs to its machine and moves only in time on its row; applying runs "Adjust operation schedule" or "Adjust maintenance work order" to write it back.
- The app is created and published on installation and deleted on uninstallation; its rule functions are looked up by name in the rules toolbox this installation created (Manufacturing_Schedule_Rules in the English sample, 制造业排程规则 in the Chinese one). This needs a sample service with sample apps (capability `sample.workshop-apps`); on a platform without Workshop the sample installs without the app.
- Upgrading from 0.1.8 means uninstalling 0.1.8 first. The 50 existing bkn-eval answers are unchanged.
