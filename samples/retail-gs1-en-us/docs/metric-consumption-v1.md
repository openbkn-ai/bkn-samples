# Object Metrics V1 consumption acceptance

Discover published metric IDs and explicit versions from the owner object type's
related_metrics returned by get_object_types, then confirm identity against its
definition. Do not construct IDs from names or omit the version.

Use the query in tools/assets/metrics-consumption-examples.json with MCP query_metric,
adding the actual kn_id, metric_id, version and response_format=json. Supply examples
cover a total and warehouse Top 5; follow next_cursor before claiming complete results.
Snapshot metrics select the documented identity and preserve source dates and units;
they do not represent live reconstruction or sums across dates.

Adapt your MCP framework to call(tool_name, arguments), returning decoded business JSON
and raising tool errors. tools/metric_consumer.py provides query_all for complete pages,
metric_result for an intentional single-page Top 5, and participants_all for a selected
entry advertising participants. Keep the original query and server bucket_key when
calling drill_through_metric. Never invent bucket keys or cursors.

Retain model units and source business dates. Prefer display_value for exact display;
decode JSON text with json.loads(text, parse_float=Decimal) to retain decimal precision.
Partial results, warnings, unavailable data and unread pages are not complete success.
Unknown and no-data results are not zero. Participants reflect the current evaluation,
not historical audit records or per-row contribution allocation.

MCP App clients may show the platform analysis component. Other clients must still
return accurate text or tables. This sample adds no separate metric frontend. Local
contract/data checks do not establish real OpenBKN 0.2.1 MCP acceptance.
