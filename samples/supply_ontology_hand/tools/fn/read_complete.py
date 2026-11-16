"""Bounded complete reads for evidence-bearing material assurance functions."""
import json


def _next_cursor(page):
    """The opaque next-page token: the sandbox SDK returns it as ``cursor``, the ontology query API as
    ``paging.next_cursor``. Empty means there are no more rows."""
    paging = page.get('paging')
    cursor = page.get('cursor') or (paging.get('next_cursor') if isinstance(paging, dict) else None)
    return cursor or None


def read_complete(query, base, rows_from_page, *, page_size=500, max_rows=5000):
    """Every row of one object query, page by page.

    Pages after the first follow the opaque cursor the previous page returned: indexed object types refuse
    offset + limit above 10,000, and the supply data has more rows than that. Offset paging is used only by a
    reader that returns no cursor at all."""
    rows=[];cursor=None;cursors=set();seen=set();total=None
    while len(rows)<max_rows:
        request={**base,'limit':min(page_size,max_rows-len(rows))}
        if cursor is not None:request['cursor']=cursor
        else:request['offset']=len(rows)
        page=query(**request)
        if not isinstance(page,dict):raise ValueError('invalid object page')
        if page.get('status') in ('partial','failed','error','incomplete'):
            raise ValueError('incomplete object query')
        count=page.get('total_count')
        if count is not None:
            if type(count) is not int or count<0 or (total is not None and total!=count):
                raise ValueError('invalid or changing object total_count')
            total=count
        batch=rows_from_page(page)
        if len(batch)>request['limit']:raise ValueError('object page exceeds requested limit')
        for row in batch:
            key=json.dumps(row,sort_keys=True,ensure_ascii=False,allow_nan=False)
            if key in seen:raise ValueError('repeated object row prevents a complete read')
            seen.add(key)
        rows.extend(batch)
        if total is not None and len(rows)>total:raise ValueError('object count exceeds total_count')
        if total is not None and len(rows)==total:
            if page.get('has_more') is True:raise ValueError('object page completeness conflicts with total_count')
            return rows
        next_cursor=_next_cursor(page)
        if not batch or (next_cursor is None and cursor is not None):
            # An empty page, or the end of a cursor read: there is nothing more to fetch.
            if page.get('has_more') is True or (total is not None and len(rows)<total):
                raise ValueError('object query ended before all rows were read')
            return rows
        if next_cursor is not None:
            key=json.dumps(next_cursor,sort_keys=True)
            if key in cursors:raise ValueError('object cursor repeated before completion')
            cursors.add(key);cursor=next_cursor
        elif len(batch)<request['limit'] and page.get('has_more') is not True and total is None:return rows
        if page.get('has_more') is False:
            if total is not None and len(rows)<total:raise ValueError('object query truncated before total_count')
            return rows
    raise ValueError('object query exceeds complete-read safety bound')
