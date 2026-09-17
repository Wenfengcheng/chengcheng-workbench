import json,sys
from pathlib import Path
p=Path(__file__).parents[1]/'runtime'/'migration-inventory.json';d=json.loads(p.read_text(encoding='utf-8'))
errors=[];chains=d.get('chains',[])
if len(chains)!=6:errors.append('expected six chains')
if d.get('openClawRuntimeAllowedAfterCutover') is not False:errors.append('OpenClaw must be disabled after cutover')
ids=set()
for c in chains:
 if c.get('id') in ids:errors.append('duplicate chain '+c.get('id',''))
 ids.add(c.get('id'))
 if not c.get('migrationState'):errors.append(c.get('id','?')+': no state')
 if not c.get('scoutAutomation'):errors.append(c.get('id','?')+': no Scout mapping')
 if c.get('migrationState')!='READY_FOR_PACKAGE_RELOCATION_TEST' and not c.get('blockers'):errors.append(c.get('id','?')+': blocked state without blockers')
if errors:print('\n'.join(errors),file=sys.stderr);raise SystemExit(1)
print(f'PASS: {len(chains)} chains inventoried; OpenClaw forbidden after cutover; blockers explicit')
