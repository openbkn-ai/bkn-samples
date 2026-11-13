# 0.1.25: ships the 齐套排产 (kit scheduling) app

Based on 0.1.24. Business data, objects, relations, functions and actions are unchanged.

**齐套排产 (kit scheduling) app**: after installation the app workshop has the published "齐套排产" app with two pages. The demand view shows, read only, whether each forecast is scheduled and on which line. On the line view, planners drop demand from the tray onto a line to make a plan and drag plans to move them; before applying, the plans are checked together with the 齐套检查 (kit check) and 产线可生产 (line can build) rule functions, and hard findings block applying. Plans go into kit schedule plans: matched to their demand by forecast number and product code, a cancelled plan does not count as scheduled, new plans are Scheduled, and the source scenario and planner are the current scenario name and the current user. Uninstalling the sample removes the app as well.

Needs a sample service that installs a sample's Workshop apps; older sample services reject this package.

Existing installations keep their version; changing versions follows the standard uninstall/install flow, which removes sample-owned data and resources. No in-place migration is provided.
