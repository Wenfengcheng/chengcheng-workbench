import json,sys
from pathlib import Path
p=Path(__file__).parents[1]/'automations'/'scout-native-migration.json'
data=json.loads(p.read_text(encoding='utf-8'))
autos=data.get('automations',[])
errors=[]
if len(autos)!=6:errors.append(f'expected 6 automations, got {len(autos)}')
for a in autos:
 name=a.get('name','<unnamed>')
 if a.get('enabled') is not False:errors.append(f'{name}: must be disabled')
 if a.get('teamsNotify')!='never':errors.append(f'{name}: teamsNotify must be never')
 if not a.get('workingDir','').startswith('{{SCOUT_RUNTIME_ROOT}}'):errors.append(f'{name}: invalid workingDir')
 text=json.dumps(a,ensure_ascii=False).lower()
 if '.concordia-client' in text:errors.append(f'{name}: OpenClaw path leak')
 for forbidden in ['m_send_teams_message','openclaw-weixin','cron.add','cron remove']:
  if forbidden in text:errors.append(f'{name}: forbidden runtime dependency {forbidden}')
 if not a.get('skillNames'):errors.append(f'{name}: no skills')
 if not a.get('steps'):errors.append(f'{name}: no steps')
if errors:
 print('\n'.join(errors),file=sys.stderr);raise SystemExit(1)
print(f'PASS: {len(autos)} disabled Scout-native shadow automations; no OpenClaw runtime paths')
