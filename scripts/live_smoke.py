"""Live integration evidence. Uses real Vertex Gemini and official ClickHouse MCP."""
import asyncio
import json
from pathlib import Path
from app.domain import Asset,Cue,Project,digest,uid
from app.integrations import ClickHouse,Gemini
from app.detectors import scan

async def main():
    project=Project(title='StoryParity live integration smoke',script='Original fictional test scene. From 1.0 to 5.0 seconds, the captain says: There are 14 survivors. No other dialogue or numbers occur.',assets=[Asset(name='Spanish episode',locale='es',kind='SUBTITLE',cues=[Cue(id='1',start=1,end=5,text='Hay 4 supervivientes.')])])
    google,db=Gemini(),ClickHouse()
    spec,extraction=await google.extract(project,None)
    project.spec=spec;project.approved_spec_digest=digest(spec.model_dump())
    snapshot=uid();await asyncio.to_thread(db.index,project,snapshot)
    assets,trace=await db.snapshot(project,snapshot)
    false_query=await db.query(f"SELECT cue_id FROM storyparity_cues WHERE project_id='{project.id}' AND snapshot='{snapshot}' AND 1=0")
    assert false_query['rows']==[]
    project.findings=scan(project)
    assert project.findings,'Expected numeric review candidate from actual extracted story spec'
    proposal,ledger=await google.investigate(project,[f.id for f in project.findings],db,snapshot)
    report={'project_id':project.id,'extraction':extraction,'spec':spec.model_dump(),'mcp_snapshot':trace,'false_predicate':false_query,'proposal':proposal.model_dump(),'agent_trace':ledger}
    out=Path('runtime/live-smoke.json');out.parent.mkdir(exist_ok=True);out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'status':'PASS','real_assets':len(assets),'false_predicate_rows':0,'findings':len(project.findings),'model_tool_calls':len(ledger),'evidence':str(out)}))
asyncio.run(main())
