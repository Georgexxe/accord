"""Test actual multilingual embedding ranking and ADK on existing synthetic acceptance data."""
import asyncio,json
from pathlib import Path
from app.domain import Project
from app.integrations import ClickHouse,Gemini

async def main():
    data={k:v for k,v in json.loads(Path('runtime/live-delivery/rollback.json').read_text()).items() if k!='spec_digest'}
    data['proposals']=[]
    project=Project.model_validate(data)
    snapshot=project.snapshot_id
    proposal,ledger=await Gemini().investigate(project,[f.id for f in project.findings],ClickHouse(),snapshot)
    assert any('cosineDistance' in e.get('sql','') for e in ledger),'Model must use actual semantic tool'
    Path('runtime/live-semantic.json').write_text(json.dumps({'proposal':proposal.model_dump(),'trace':ledger},indent=2),encoding='utf-8')
    print(json.dumps({'status':'PASS','changes':len(proposal.changes),'semantic_tool_used':True,'trace_events':len(ledger)}))
asyncio.run(main())
