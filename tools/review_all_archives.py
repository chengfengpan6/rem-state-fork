"""Review the three archived diagnostics offline, without a model account.

Creates a new output directory, preserves strict failures as evidence, requires
bounded verification/replay to pass, and independently re-derives the results.
Never imports a live provider or starts a run/resume command.
"""
from pathlib import Path
import argparse
import hashlib
import json
import platform
import subprocess
import sys

ARCHIVES = ('luna-targeted-30histories','claude-opus55-30histories','gemini38flash-30histories')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True,help='New directory outside evidence')
    args=parser.parse_args();repo=Path(__file__).resolve().parents[1];out=args.output.resolve()
    if out.exists() or out.is_relative_to((repo/'evidence').resolve()):
        parser.error('Output must be a new directory outside evidence')
    out.mkdir(parents=True)
    report={'schema':'rem-complete-offline-review-1','new_model_calls':0,'python':sys.version,
            'platform':platform.platform(),'tool_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'commands':[],'archives':{},'status':'running'}
    def save():
        (out/'review_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    def command(label,argv,allow_failure=False):
        proc=subprocess.run([sys.executable,*argv],cwd=repo,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        (out/(label+'.txt')).write_text(proc.stdout,encoding='utf-8')
        report['commands'].append({'label':label,'arguments':argv,'exit_code':proc.returncode});save()
        if proc.returncode and not allow_failure:raise RuntimeError(label+' failed; inspect its saved log')
        return proc.returncode
    try:
        command('unit_tests',['-m','unittest','discover','-s','tests','-v'])
        for archive in ARCHIVES:
            path='evidence/'+archive
            strict=out/(archive+'-strict.json');bounded=out/(archive+'-bounded.json');replay=out/(archive+'-replay')
            command(archive+'-strict',['tools/run_targeted.py','verify','--recording',path,'--output',str(strict)],True)
            command(archive+'-bounded',['tools/run_targeted.py','verify','--recording',path,'--float-tolerance','1e-12','--output',str(bounded)])
            bounded_result=json.loads(bounded.read_text(encoding='utf-8'))
            if bounded_result['status']!='verified_complete':raise RuntimeError(archive+' bounded verification incomplete')
            command(archive+'-replay',['tools/run_targeted.py','replay','--recording',path,'--float-tolerance','1e-12','--output',str(replay)])
            replay_result=json.loads((replay/'summary.json').read_text(encoding='utf-8'))
            if replay_result['status']!='completed':raise RuntimeError(archive+' replay incomplete')
            replay_verify=out/(archive+'-replay-verification.json')
            command(archive+'-replay-verification',['tools/run_targeted.py','verify','--recording',str(replay),'--output',str(replay_verify)])
            command(archive+'-analysis',['tools/analyze_targeted.py',path,'--output',str(out/(archive+'-analysis.json'))])
            report['archives'][archive]={'strict':json.loads(strict.read_text(encoding='utf-8'))['status'],
                    'bounded':bounded_result['status'],'checks':bounded_result['checks_total'],
                    'replay':replay_result['status'],'replay_exactness':replay_result['replay_exactness'],
                    'replayed_histories':len(replay_result['history_results'])}
            save()
        command('independent_arithmetic',['tools/recompute_replications.py','--output',str(out/'independent_arithmetic.json')])
        report['status']='all_archives_reviewed_offline';save()
        print(json.dumps({'status':report['status'],'receipt':str(out/'review_receipt.json'),'new_model_calls':0}))
        return 0
    except (RuntimeError,OSError,KeyError,ValueError) as error:
        report['status']='failed';report['error']=str(error);save();print(str(error),file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
