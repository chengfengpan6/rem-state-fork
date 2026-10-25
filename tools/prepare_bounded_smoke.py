"""Prepare the predeclared formation-only diagnostic; never calls a model."""
from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rem_harness.data import generate_tape, evidence_map, planted_evidence_map, planted_map_diagnostics
from rem_harness.models import default_v2_config, validate_config, expected_call_breakdown

def prepare():
    root=Path(__file__).resolve().parents[1]
    candidates=[]
    selected=None
    for seed in range(20261025,20261125):
        tape=generate_tape(seed,3,1,allow_partial_post=True)
        e=evidence_map([x.observed_record() for x in tape[:3]])
        p=planted_evidence_map(e)
        diagnostics=planted_map_diagnostics(e,p)
        eligible=diagnostics['rendered_nonzero'] and diagnostics['rendered_mse_strictly_increased']
        candidates.append({'seed':seed,'eligible':eligible,**diagnostics})
        if eligible:
            selected=seed
            break
    if selected is None: raise RuntimeError('No eligible history in predeclared search; revise plan before any live call')
    cfg=default_v2_config()
    cfg.update(seeds=[selected],post_rounds=1,map_update_interval=1,formation_call_cap=32,
               per_branch_call_cap=20,max_calls=272,solo_map_readouts=3,nominal_map_readouts=3)
    cfg['audit']={'mode':'split','at_fork':True,'interval':3,'architectures':['team','solo','nomessage']}
    cfg['probes']['enabled']=False
    cfg['branches']=[{'id':f'team_{c}','architecture':'team','condition':c} for c in ('P','E','H','R0','RU')]
    cfg['branches'].append({'id':'team_R0rep','architecture':'team','condition':'R0'})
    for architecture in ('solo','nomessage','nominal'):
        cfg['branches'].extend({'id':f'{architecture}_{c}','architecture':architecture,'condition':c} for c in ('H','R0'))
    validate_config(cfg)
    plan=expected_call_breakdown(cfg)
    assert plan['total']==219, plan
    assert all(x['total']<=20 for x in plan['branches_per_seed'].values())
    selection={'plan':'docs/run_plan_2026-10-25.md','selection_uses':'formation tape only; no future or LLM response criterion',
               'selected_seed':selected,'candidates_examined':candidates,'call_plan':plan}
    (root/'configs/bounded_v2_smoke.json').write_text(json.dumps(cfg,indent=2)+'\n',encoding='utf-8')
    (root/'docs/bounded_v2_selection.json').write_text(json.dumps(selection,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(selection,indent=2))

if __name__=='__main__':prepare()
