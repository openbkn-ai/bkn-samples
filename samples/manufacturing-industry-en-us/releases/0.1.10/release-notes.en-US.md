# 0.1.10: the Machine Scheduling app, checked as a business user would (OpenBKN 0.2.2)

Data and actions are the same as in 0.1.9. The sample's Machine Scheduling app (机台排产 in the Chinese sample) and its four rule functions change, so a production lead sees on opening where the problems are and why.

- **Bars**: an operation's bar shows its work order and operation (e.g. "WO-2703-06 5-axis finish milling"), a maintenance work order's bar its number; the hover card adds the operation or maintenance plan and the status. The Gantt shows ten days from the base date by default, wide enough for the order and operation on a two-day bar (long English operation names are cut short there and shown in full in the hover card); zoom and the base date show other days.
- **First screen**: the base date opens on 2027-03-01, the first day of the March schedule, and the Gantt is taller, so most machines show at once.
- **Rule order and names**: work order kit, machine capability, operator qualification and shift, changeover, in that order; the English app shows Work order kit, Machine capability, Operator qualification and shift and Changeover instead of the function names.
- **Faster rule functions**: each rule reads its tables in parallel, so the four rules answer within Workshop's time limit even on a slow platform.
- **One language**: rule conclusions and check details (columns, groups, texts) are always in the sample's own language, whatever Studio's interface language; codes in the English sample (setup class CAST_IRON, capability status suspended, machine status under_repair) read as English words, and the changeover text names the previous operation by work order and operation. The English app shows statuses as Not started, In progress, Completed and so on.
- **Reuse**: the app file carries the knowledge network's current name; exported and imported as a new app (same environment, another name), the four rule functions are found again by toolbox and function name and complete their checks, without the original environment's IDs.
- Upgrading from 0.1.9 means uninstalling 0.1.9 first. The 50 existing bkn-eval answers are unchanged.
