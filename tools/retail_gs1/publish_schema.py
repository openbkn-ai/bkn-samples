import json
from pathlib import Path
from schema import TABLES, NUMERIC, DATES, FKS, LABELS
root=Path(__file__).resolve().parent
contract={'version':'0.1.0','default_as_of_date':'2027-02-28','languages':['en-us','zh-cn'],'object_types':{t:{'primary_key':pk,'name_en':LABELS[t][0],'name_zh':LABELS[t][1],'fields':{f:('date' if f in DATES else 'decimal' if f in NUMERIC else 'string') for f in fields.split()},'foreign_keys':FKS.get(t,{})} for t,(pk,fields) in TABLES.items()}}
(root/'schema-contract.json').write_text(json.dumps(contract,ensure_ascii=False,indent=2)+'\n')
print(root/'schema-contract.json')
