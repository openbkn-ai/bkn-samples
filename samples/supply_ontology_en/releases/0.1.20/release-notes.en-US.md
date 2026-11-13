# 0.1.20: ships the Kit Scheduling app

Based on 0.1.19. Business data, objects, relations, functions and actions are unchanged.

**Kit Scheduling app**: after installation the app workshop has the published "Kit Scheduling" app with two pages. The demand view shows, read only, whether each forecast is scheduled and on which line. On the line view, planners drop demand from the tray onto a line to make a plan and drag plans to move them; before applying, the plans are checked together with the Kit_Check and Line_Can_Build rule functions, and hard findings block applying. Plans go into kit schedule plans: matched to their demand by forecast number and product code, a cancelled plan does not count as scheduled, new plans are Scheduled, and the source scenario and planner are the current scenario name and the current user. Uninstalling the sample removes the app as well.

The app workshop is part of the professional edition; on a community edition platform the sample installs as before, without the app. Needs a sample service that installs a sample's Workshop apps; older sample services reject this package.

Existing installations keep their version; changing versions follows the standard uninstall/install flow, which removes sample-owned data and resources. No in-place migration is provided.
