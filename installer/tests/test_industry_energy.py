"""Guard complete 0.2.1 coverage, typed recovery and ownership before any import."""
import copy,importlib.util,json,os,re,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tools.publication.build_candidate_set import validate_plan
from tools.publication.build_candidate import included
ROOT=Path(__file__).resolve().parents[2]
PLAN=ROOT/'tools/publication/candidates-0.2.1.json'


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


class IndustryEnergyTest(unittest.TestCase):
    def test_release_plan_covers_every_source_identity_and_missing_samples_fail(self):
        plan=json.loads(PLAN.read_text());self.assertEqual(len(validate_plan(ROOT,plan)),12)
        for name in ('energy-saref4ener-en-us','energy-saref4ener-zh-cn','manufacturing-industry-en-us','manufacturing-industry-zh-cn'):
            changed=copy.deepcopy(plan);changed['candidates']=[e for e in changed['candidates'] if e['sampleId']!=name]
            with self.assertRaisesRegex(ValueError,'coverage differs'):validate_plan(ROOT,changed)
        changed=copy.deepcopy(plan);changed['excluded']=[]
        with self.assertRaisesRegex(ValueError,'coverage differs'):validate_plan(ROOT,changed)
        changed=copy.deepcopy(plan);changed['excluded'][0]['reason']=''
        with self.assertRaisesRegex(ValueError,'needs a reason'):validate_plan(ROOT,changed)
        changed=copy.deepcopy(plan);changed['candidates'].append(changed['candidates'][0])
        with self.assertRaisesRegex(ValueError,'duplicate'):validate_plan(ROOT,changed)

    def test_four_typed_fixtures_match_locked_data_and_model(self):
        for family,count,records in [('manufacturing-industry',40,1529),('energy-saref4ener',15,14787)]:
            for language in ('en-us','zh-cn'):
                root=ROOT/'samples'/(family+'-'+language);db=load(root/'db/database.py',family+language)
                specs,rows,digest=db.fixture();self.assertEqual(len(rows),count);self.assertEqual(sum(map(len,rows.values())),records)
                for table,spec in specs.items():
                    text=(root/'kn/object_types'/(table+'.bkn')).read_text()
                    modeled=dict(re.findall(r'^\| (\w+) \| [^|]+ \| (string|integer|decimal|date|boolean) \|',text,re.M))
                    for field,kind in modeled.items():self.assertEqual(spec['fields'][field],kind)
                    for row in rows[table]:
                        for field,kind in spec['fields'].items():db.cast(row[field],kind)

    def test_manufacturing_conflicting_network_is_never_overwritten(self):
        for lang in ('en-us','zh-cn'):
            root=ROOT/'samples'/('manufacturing-industry-'+lang);module=load(root/'platform/sample_platform.py','manufacturing_'+lang);m=json.loads((root/'sample.yaml').read_text());specs=json.loads((root/'model-contract.json').read_text())['object_types']
            with tempfile.TemporaryDirectory() as temporary:
                input=Path(temporary)/'input.json';output=Path(temporary)/'output.json'
                input.write_text(json.dumps({'sample':m['metadata']['name'],'version':m['metadata']['version'],'knowledgeNetwork':{'id':module.KN},'database':{'name':module.KN},'catalog':{'id':'cat'}}))
                calls=[]
                def cli(*args):
                    calls.append(args);return {'entries':[{'name':name,'id':'res-'+name} for name in specs]}
                existing=subprocess.CompletedProcess([],0,json.dumps({'tags':['human-owned']}),'')
                with patch.dict(os.environ,{'BKN_SAMPLE_INPUT':str(input),'BKN_SAMPLE_OUTPUT':str(output)}),patch('sys.argv',['hook','install']),patch.object(module,'cli',side_effect=cli),patch.object(module.subprocess,'run',return_value=existing):
                    with self.assertRaisesRegex(ValueError,'ownership conflict'):module.main()
                self.assertTrue(all(call[0]=='vega' for call in calls))
                self.assertFalse(output.exists())

    def test_owned_partial_binding_retry_and_conflicts(self):
        for family,filename in [('manufacturing-industry','sample_platform.py'),('energy-saref4ener','network.py')]:
            for lang in ('en-us','zh-cn'):
                path=ROOT/'samples'/(family+'-'+lang)/'platform'/filename
                module=load(path,family+lang+'_bindings')
                bindings={'a':'resource-a','b':'resource-b'}
                objects={'a':{'id':'a','data_source':{'type':'resource','id':'resource-a'}},'b':{'id':'b'}}
                updates=[]
                def cli(*args):
                    if args[2]=='get':return copy.deepcopy(objects[args[4]])
                    self.assertEqual(args[2],'update');table=args[4]
                    objects[table]=json.loads(Path(args[6]).read_text());updates.append(table)
                    return {}
                with patch.object(module,'cli',side_effect=cli):
                    module.bind_resources(bindings,bindings,apply=True)
                    self.assertEqual(updates,['b'])
                    module.bind_resources(bindings,bindings,apply=True)
                    module.bind_resources(bindings,bindings,apply=False)
                    self.assertEqual(updates,['b'])
                    objects['a'].pop('data_source');objects['b']['data_source']['id']='human-resource'
                    with self.assertRaisesRegex(ValueError,'existing binding differs'):module.bind_resources(bindings,bindings,apply=True)
                    self.assertEqual(updates,['b'])
                    objects['b']['data_source']['id']='resource-b'
                    with self.assertRaisesRegex(ValueError,'binding missing'):module.bind_resources(bindings,bindings,apply=False)
                    self.assertEqual(updates,['b'])

    def test_energy_reference_material_is_deliverable_and_hashes_match(self):
        import hashlib
        for lang in ('en-us','zh-cn'):
            root=ROOT/'samples'/('energy-saref4ener-'+lang)
            for lockfile,key in [('source-lock.json','sources'),('license-lock.json','licenses')]:
                lock=json.loads((root/'saref-reference'/lockfile).read_text())
                for entry in lock[key]:
                    path=Path('saref-reference')/entry.get('path',entry.get('file'))
                    self.assertTrue(included(path));self.assertEqual(hashlib.sha256((root/path).read_bytes()).hexdigest(),entry['sha256'])
            self.assertTrue(all(e['matches_historical_freeze'] for e in json.loads((root/'saref-reference/source-lock.json').read_text())['sources']))


if __name__=='__main__':unittest.main()
