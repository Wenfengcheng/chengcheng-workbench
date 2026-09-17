import json,sys
from pathlib import Path
root=Path(__file__).parents[1];policy=json.loads((root/'runtime'/'notification-cutover.json').read_text(encoding='utf-8'));bundle=json.loads((root/'automations'/'scout-native-migration.json').read_text(encoding='utf-8'))
errors=[];chains=policy.get('chains',{});autos=bundle.get('automations',[])
if policy.get('targetOwner')!='Microsoft Scout Teams Bot':errors.append('target owner must be Scout Teams Bot')
if policy.get('shadowMode',{}).get('scoutTeamsNotify')!='never':errors.append('shadow must be silent')
if len(chains)!=6 or len(autos)!=6:errors.append('expected six policy chains and six automations')
for auto in autos:
 if auto.get('teamsNotify')!='never':errors.append(auto.get('name','?')+': shadow notification enabled')
 if auto.get('cutoverTeamsNotify') not in {'always','auto'}:errors.append(auto.get('name','?')+': no cutover mode')
for forbidden in ['openclaw-weixin','OpenClaw cron announce','OpenClaw message tool']:
 if forbidden not in policy.get('forbiddenAfterCutover',[]):errors.append('missing forbidden channel '+forbidden)
if errors:print('\n'.join(errors),file=sys.stderr);raise SystemExit(1)
print('PASS: Scout Teams Bot is the sole post-cutover notification owner; shadow remains silent')
