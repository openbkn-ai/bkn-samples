"""Dated settlement evidence rollups. Transfers accumulate; the last event supplies state."""
def create_views(db,current='2027-02-28',actual='actual'):
 # Parameters are fixed local metadata; never interpolate user-supplied SQL.
 assert current=='2027-02-28' and actual in ('actual','实际')
 columns='event_id,instruction_id,event_date,event_status,cumulative_quantity AS settled_quantity,failure_reason,view_kind,known_date'
 db.execute(f'''CREATE VIEW settlement_state AS
 WITH dated AS (
   SELECT e.*,SUM(settled_quantity) OVER (PARTITION BY instruction_id) AS cumulative_quantity,
   ROW_NUMBER() OVER (PARTITION BY instruction_id ORDER BY event_date DESC,event_sequence DESC) AS ordinal
   FROM settlement_events e
   WHERE event_date<='{current}' AND known_date<='{current}' AND view_kind='{actual}'
 ) SELECT {columns} FROM dated WHERE ordinal=1''')
 db.execute(f'''CREATE VIEW settlement_month_end AS
 WITH dated AS (
  SELECT e.*,SUM(e.settled_quantity) OVER (PARTITION BY e.instruction_id) AS cumulative_quantity,
  ROW_NUMBER() OVER (PARTITION BY e.instruction_id ORDER BY e.event_date DESC,e.event_sequence DESC) AS ordinal
  FROM settlement_events e
  JOIN settlement_instructions si USING(instruction_id)
  JOIN securities_transactions t USING(trade_id)
  WHERE e.event_date<=date(t.trade_date,'start of month','+1 month','-1 day')
  AND e.known_date<=MIN('{current}',date(t.trade_date,'start of month','+1 month','-1 day'))
  AND (date(t.trade_date,'start of month','+1 month','-1 day')>'{current}' OR e.view_kind='{actual}')
 ) SELECT {columns} FROM dated WHERE ordinal=1''')
