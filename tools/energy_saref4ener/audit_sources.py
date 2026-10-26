"""Verify fixed upstream bytes and produce a named RDF inventory without fetching imports."""
import hashlib,json,shutil
from pathlib import Path
from rdflib import Graph,URIRef,RDF,RDFS,OWL
ROOT=Path(__file__).resolve().parents[2]
REFERENCE=Path(__file__).resolve().parent/'reference'


def audit():
    lock=json.loads((REFERENCE/'source-lock.json').read_text());inventories=[]
    for source in lock['sources']:
        path=REFERENCE/source['path'];assert hashlib.sha256(path.read_bytes()).hexdigest()==source['sha256']
        graph=Graph().parse(path,format='turtle')
        def terms(kind):
            return sorted({str(s) for s in graph.subjects(RDF.type,kind) if isinstance(s,URIRef)})
        classes=terms(OWL.Class);objects=terms(OWL.ObjectProperty);data=terms(OWL.DatatypeProperty)
        inventories.append({'source':source['path'],'sha256':source['sha256'],'classes':classes,'object_properties':objects,'datatype_properties':data,'anonymous_class_expressions':len({s for s in graph.subjects(RDF.type,OWL.Class) if not isinstance(s,URIRef)}),'labels':{iri:sorted({str(s) for s in graph.objects(URIRef(iri),RDFS.label)}) for iri in classes}})
    for license in json.loads((REFERENCE/'license-lock.json').read_text())['licenses']:
        assert hashlib.sha256((REFERENCE/license['file']).read_bytes()).hexdigest()==license['sha256']
    (REFERENCE/'inventory.json').write_text(json.dumps({'modules':inventories},ensure_ascii=False,indent=2)+'\n')
    for language in ('en-us','zh-cn'):
        target=ROOT/'samples'/('energy-saref4ener-'+language)/'saref-reference'
        shutil.copytree(REFERENCE,target,dirs_exist_ok=True)
    print(json.dumps([{'source':m['source'],'classes':len(m['classes']),'object_properties':len(m['object_properties']),'datatype_properties':len(m['datatype_properties'])} for m in inventories]))


if __name__=='__main__':audit()
