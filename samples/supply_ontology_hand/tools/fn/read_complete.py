"""Bounded complete reads for evidence-bearing material assurance functions."""
import json


def read_complete(query, base, rows_from_page, *, page_size=500, max_rows=5000):
    rows=[];cursor=None;cursors=set();seen=set();total=None
    while len(rows)<max_rows:
        request={**base,'limit':min(page_size,max_rows-len(rows))}
        if cursor is not None:request['search_after']=cursor
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
        if not batch:
            if page.get('has_more') is True or (total is not None and len(rows)<total):
                raise ValueError('object query ended before all rows were read')
            return rows
        next_cursor=page.get('search_after') or None
        if next_cursor is not None:
            key=json.dumps(next_cursor,sort_keys=True)
            if key in cursors:raise ValueError('object cursor repeated before completion')
            cursors.add(key);cursor=next_cursor
        else:
            cursor=None
            if len(batch)<request['limit'] and page.get('has_more') is not True and total is None:return rows
        if page.get('has_more') is False:
            if total is not None and len(rows)<total:raise ValueError('object query truncated before total_count')
            return rows
    raise ValueError('object query exceeds complete-read safety bound')
