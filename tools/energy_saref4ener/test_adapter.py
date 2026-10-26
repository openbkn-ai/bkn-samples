"""Boundary checks for complete, typed, managed data loading."""
import datetime,unittest
from decimal import Decimal
from unittest.mock import patch
from tools.energy_saref4ener import managed_execution as adapter

CONTRACT={'object_types':{'events':{'primary_key':'id','fields':{'id':'string','day':'date','quantity':'decimal'}}}}


class ManagedAdapterTest(unittest.TestCase):
    def test_all_pages_and_typed_values_are_preserved(self):
        calls=[]
        def query(**kwargs):
            calls.append(kwargs);start=kwargs['offset'];end=min(start+kwargs['limit'],1200)
            return {'datas':[{'id':str(i),'day':datetime.date(2027,2,28),'quantity':Decimal('3.200000')} for i in range(start,end)],'total_count':1200}
        rows=adapter.load_sources(query,'network',CONTRACT,{})['events']
        self.assertEqual(len(rows),1200);self.assertEqual(len(calls),2)
        self.assertEqual(rows[-1],{'id':'1199','day':'2027-02-28','quantity':'3.200000'})
        self.assertEqual(calls[1]['offset'],1000)

    def test_duplicate_rows_and_short_incomplete_page_fail(self):
        duplicate={'datas':[{'id':'same','day':'2027-02-28','quantity':'1'}]*2,'total_count':2}
        with self.assertRaisesRegex(ValueError,'DUPLICATE_SOURCE_KEY'):
            adapter.load_sources(lambda **_:duplicate,'network',CONTRACT,{})
        with self.assertRaisesRegex(ValueError,'SOURCE_COUNT_MISMATCH'):
            adapter.load_sources(lambda **_:{'datas':[{'id':'one','day':'2027-02-28','quantity':'1'}],'total_count':2},'network',CONTRACT,{})

    def test_source_failures_and_pending_receipts_are_not_empty_success(self):
        for extra in ({'partial':True},{'errors':['unavailable']},{'receipt':{'receipt_status':'pending'}},{'total_count':True}):
            with self.subTest(extra=extra),self.assertRaises(ValueError):
                adapter.load_sources(lambda **_:{'datas':[],**extra},'network',CONTRACT,{})

    def test_dates_and_scope_rejected_before_source_reads(self):
        with self.assertRaises(ValueError):adapter.source_value(datetime.datetime(2027,2,28,12),'date')
        with self.assertRaises(ValueError):adapter.source_value('2027-02-30','date')
        calls=[]
        def execute(*args):raise AssertionError('should not execute')
        def validate(*args):raise ValueError('invalid scope')
        # A dedicated function globals mapping avoids replacing the production validator.
        import types
        controlled=types.FunctionType(execute.__code__,{'validate':validate,'AssertionError':AssertionError})
        with self.assertRaisesRegex(ValueError,'invalid scope'):
            adapter.run_request(lambda **kwargs:calls.append(kwargs),'network',CONTRACT,'test',{},controlled)
        self.assertEqual(calls,[])


if __name__=='__main__':unittest.main()
