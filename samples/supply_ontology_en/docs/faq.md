# FAQ

**What does this sample include?** Orders, forecasts, BOMs, inventory and procurement data, with a dedicated database, knowledge network, metrics and functions.

**Are the names real?** No. People and companies are fictional. Geographic names and technical models are retained where relevant.

**How should identifiers be handled?** Treat business keys as opaque strings. Keep leading zeroes and suffixes intact when querying or linking records.

**Does stock coverage promise delivery?** Stock-only calculations exclude POs and do not establish a deadline commitment. Dated checks require explicit business/need dates and confirmed existing supply. Real-world capacity and transport are outside this fixture.

**Can the agent read the answer set?** The evaluated agent cannot. It uses published MCP data and functions. The separate judge and CSV oracle can read evaluation material.

**How is accuracy verified?** Evaluate the exact installed package through MCP. Require 50/50 core questions and 4/4 calendar checks, with successful calls and complete evidence. Keep execution records locally.
