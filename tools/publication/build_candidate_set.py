"""Build and locally inspect every declared sample in a fixed-source product update."""
import argparse,hashlib,json,shutil,subprocess,tempfile
from pathlib import Path
from installer.contract import discover_sample_dirs,load_sample,read_version
from installer.offline_bundle import OfflinePackages
from installer.remote_installation import RemoteInstallation
from installer.remote_bundle import CAPABILITIES
from installer.studio_api import ApiError
from tools.publication.build_candidate import build,require,ROOT,VERSION


def validate_plan(root,plan):
    require(plan.get('coverage')=='all-source-samples','candidate set must cover all declared source samples')
    require(plan.get('productVersion')==read_version(root),'candidate product differs from source version')
    declared={p.name:load_sample(p) for p in discover_sample_dirs(root)}
    entries=plan.get('candidates',[]);directories=[e['directory'] for e in entries];ids=[e['sampleId'] for e in entries]
    require(len(directories)==len(set(directories)) and len(ids)==len(set(ids)),'duplicate sample in candidate set')
    excluded=plan.get('excluded',[]);skipped=[e['directory'] for e in excluded]
    require(all(isinstance(e.get('reason'),str) and e['reason'].strip() for e in excluded),'every excluded sample needs a reason')
    require(not set(skipped)&set(directories) and len(skipped)==len(set(skipped)),'a sample is both a candidate and excluded')
    covered=set(directories)|set(skipped)
    require(covered==set(declared),'candidate coverage differs: missing='+str(sorted(set(declared)-covered))+', unknown='+str(sorted(covered-set(declared))))
    for entry in entries:
        document=declared[entry['directory']]
        require(entry['sampleId']==document['metadata']['name'],'candidate sample identity differs')
        require(isinstance(entry['version'],str) and VERSION.fullmatch(entry['version']),'invalid candidate version')
        if 'version' in document['metadata']:require(document['metadata']['version']==entry['version'],'declared sample version differs')
    return entries


def build_set(plan_path,output):
    plan=json.loads(plan_path.read_text());entries=validate_plan(ROOT,plan)
    require(not subprocess.check_output(['git','-C',str(ROOT),'status','--porcelain']),'commit all source changes before building the candidate set')
    commit=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    output=output.resolve();require(not output.exists(),'use a new candidate output directory');require(not output.is_relative_to(ROOT),'output must be outside source repository')
    downloads=output/'downloads';downloads.mkdir(parents=True)
    result={'product_version':plan['productVersion'],'source_commit':commit,'status':'candidate-not-platform-verified','coverage':'all-source-samples','candidates':[]}
    for entry in entries:
        folder=build(ROOT/'samples'/entry['directory'],entry['version'],output,shared_database=True)
        report=json.loads((folder/'build.json').read_text());require(not report['source']['workingTreeChanges'] and report['source']['commit']==commit,'candidate source is not fixed')
        archive=folder/'package.tar.gz';digest=report['package']['digest']
        for architecture in ('amd64','arm64'):
            with tempfile.TemporaryDirectory() as temporary:
                state=Path(temporary);runtime=RemoteInstallation(ROOT,state,plan['productVersion'],architecture,sorted(CAPABILITIES),'local.test/executor@sha256:'+'a'*64)
                imported=OfflinePackages(ROOT,state,runtime).import_package(archive,'admin')
                require(imported['packageDigest']==digest and imported['version']==entry['version'],'offline import identity differs')
                require(not (state/(entry['sampleId']+'.json')).exists(),'inspection must not run installation hooks')
        with tempfile.TemporaryDirectory() as temporary:
            state=Path(temporary);runtime=RemoteInstallation(ROOT,state,'0.2.0','amd64',sorted(CAPABILITIES),'local.test/executor@sha256:'+'a'*64)
            try:OfflinePackages(ROOT,state,runtime).import_package(archive,'admin')
            except ApiError as error:require('incompatible platform version' in str(error.__cause__),'old product rejected for an unexpected reason')
            else:raise ValueError('0.2.0 accepted a 0.2.1 candidate')
        filename=entry['sampleId']+'-'+entry['version']+'-package.tar.gz';shutil.copyfile(archive,downloads/filename)
        result['candidates'].append({**entry,'sample':entry['sampleId'],'file':filename,'package_digest':digest,'size':archive.stat().st_size,'source':report['source'],'offline_import_checks':{'amd64':'metadata-and-integrity-passed','arm64':'metadata-and-integrity-passed','product_0.2.0':'rejected'},'platform_acceptance':'not-run'})
        print(entry['sampleId'],entry['version'],digest,flush=True)
    skipped={e['directory'] for e in plan.get('excluded',[])}
    require({e['sampleId'] for e in result['candidates']}=={load_sample(p)['metadata']['name'] for p in discover_sample_dirs(ROOT) if p.name not in skipped},'post-build coverage differs')
    (downloads/'SHA256SUMS').write_text(''.join(e['package_digest'].removeprefix('sha256:')+'  '+e['file']+'\n' for e in result['candidates']))
    excluded=''.join(f"\n- {e['directory']}: {e['reason']}" for e in plan.get('excluded',[]))
    result['excluded']=plan.get('excluded',[])
    (downloads/'candidate-index.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    (downloads/'README.md').write_text(f'''# OpenBKN {plan['productVersion']} candidate set

{len(result['candidates'])} samples are offered; every other source sample is excluded with a reason:{excluded or ' none.'}

Import a matching *-package.tar.gz directly
into a fixed OpenBKN 0.2.1 test instance with the shared sample database. Verify
SHA256SUMS first; do not unpack and repack. No sample-specific data image is needed.
Each file is a fixed-source candidate; no successful platform proof is fabricated.
Local archive/schema/compatibility checks do not execute installation hooks or
prove native amd64/arm64 execution. Actual OpenBKN install/retry/uninstall/MCP and
business acceptance remain pending. Existing installations require uninstall then
install; no in-place migration. The 0.2.0 catalog and historical assets are unchanged.
''')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,default=ROOT/'tools/publication/candidates-0.2.1.json');p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    build_set(args.plan,args.output)
