"""Authenticated, persistent Accord application."""
import asyncio
import io
import json
import logging
import os
import re
import secrets
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Annotated
from fastapi import Body, Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import Field
from . import workflow
from .detectors import scan
from .domain import Asset, Cue, Model, Project, Proposal, StorySpec, digest, uid
from .integrations import ClickHouse, Gemini
from .store import Conflict, MediaStore, Store
from .validators.parsers import parse_srt, parse_vtt, seconds_to_srt_timecode

app = FastAPI(title="Accord", version="2.0.0")
store, media_store, analytics, gemini = Store(), MediaStore(), ClickHouse(), Gemini()
locks = defaultdict(asyncio.Lock)
bearer = HTTPBearer(auto_error=False)
log = logging.getLogger("storyparity")

def reviewer(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]):
    token = os.getenv("STORYPARITY_REVIEWER_TOKEN", "")
    if len(token) < 24:
        raise HTTPException(503, "Reviewer authentication is not configured")
    if not credentials or not secrets.compare_digest(credentials.credentials, token):
        raise HTTPException(401, "Reviewer sign-in required", headers={"WWW-Authenticate":"Bearer"})
    return "reviewer"

Auth = Annotated[str, Depends(reviewer)]

@app.exception_handler(Conflict)
async def conflict_handler(request, exc):
    return JSONResponse(status_code=409, content={"detail":str(exc)})

@app.exception_handler(ValueError)
async def validation_handler(request, exc):
    return JSONResponse(status_code=422, content={"detail":str(exc)})

@app.exception_handler(KeyError)
async def missing_handler(request, exc):
    return JSONResponse(status_code=404, content={"detail":"Resource not found"})

def load(project_id):
    if len(project_id)!=32 or any(c not in "0123456789abcdef" for c in project_id):
        raise HTTPException(404,"Project not found")
    return store.get(project_id)

def public(project):
    value=project.model_dump(mode="json")
    for proposal,data in zip(project.proposals,value["proposals"]):
        data["approval_digest"]=proposal.approval_digest()
        data.pop("snapshots",None)
    value["proposal_previews"]={p.id:[a.model_dump(mode="json") for a in p.snapshots] for p in project.proposals if p.status=="APPLIED"}
    value["spec_digest"]=digest(project.spec.model_dump()) if project.spec else None
    return value

class NewProject(Model):
    title: str=Field(min_length=1,max_length=150)
    script: str=Field(min_length=1,max_length=100000)
class Revision(Model):
    revision: int=Field(ge=1)
class Approve(Revision):
    digest: str=Field(min_length=64,max_length=64)
class Investigate(Revision):
    finding_ids: list[str]=Field(min_length=1,max_length=25)
class EditProposal(Revision):
    proposal: Proposal

def check(project,revision):
    if project.revision!=revision:
        raise Conflict("Project changed; reload before continuing")

async def verify_and_save(project):
    expected=project.revision
    try:
        snapshot=uid()
        await asyncio.to_thread(analytics.index,project,snapshot)
        assets,trace=await analytics.snapshot(project,snapshot)
        checked=project.model_copy(deep=True)
        checked.assets=assets
        project.findings=scan(checked)
        project.snapshot_id=snapshot
        project.indexed_revision=expected+1
        project.status="FINDINGS_OPEN" if project.findings else "VERIFIED"
        project.record("verification_completed",query=trace,finding_count=len(project.findings))
    except Exception:
        project.status="VERIFICATION_PENDING"
        project.record("verification_failed",reason="Indexing or MCP verification failed; retry verification")
        store.save(project,expected)
        log.exception("Verification failed for %s",project.id)
        raise HTTPException(503,"Saved changes await verification. Restore the database connection and retry scan.")
    store.save(project,expected)

@app.get("/api/health")
async def health():
    return {"service":"Accord","status":"ready","version":"2.0.0"}
@app.get("/api/session")
async def session(actor: Auth):
    return {"actor":actor,"google_configured":bool(os.getenv("GOOGLE_CLOUD_PROJECT")),"clickhouse_configured":bool(os.getenv("CLICKHOUSE_HOST")),"store":"firestore" if store.cloud else "sqlite"}
@app.get("/api/projects")
async def projects(actor: Auth):
    return store.list()
@app.post("/api/projects")
async def create(data:NewProject,actor:Auth):
    project=Project(**data.model_dump())
    project.record("project_created",actor)
    store.save(project,None)
    return public(project)
@app.get("/api/projects/{project_id}")
async def get_project(project_id:str,actor:Auth):
    return public(load(project_id))

@app.post("/api/projects/{project_id}/media")
async def upload_media(project_id:str,actor:Auth,file:UploadFile=File(...),revision:int=Form(...)):
    if file.content_type not in {"video/mp4","video/webm","audio/wav","audio/mpeg"}:
        raise HTTPException(415,"Use MP4, WebM, WAV or MP3 master media")
    content=await file.read(20*1024*1024+1)
    if not content or len(content)>20*1024*1024:
        raise HTTPException(413,"Master clip must be nonempty and under 20 MB")
    async with locks[project_id]:
        project=load(project_id); check(project,revision)
        key=uid()
        await asyncio.to_thread(media_store.put,key,content,file.content_type)
        project.media_key,project.media_mime=key,file.content_type
        project.approved_spec_digest=None
        project.status="MASTER_CHANGED"; project.findings=[]; project.snapshot_id=None
        project.record("master_uploaded",actor,sha256=digest(content),bytes=len(content))
        store.save(project,revision)
    return public(project)
@app.get("/api/projects/{project_id}/media")
async def get_media(project_id:str,actor:Auth):
    project=load(project_id)
    if not project.media_key: raise HTTPException(404,"No master media uploaded")
    data=await asyncio.to_thread(media_store.get,project.media_key)
    return Response(data,media_type=project.media_mime,headers={"Cache-Control":"private, no-store"})

@app.post("/api/projects/{project_id}/assets")
async def upload_track(project_id:str,actor:Auth,file:UploadFile=File(...),locale:str=Form(...),kind:str=Form(...),revision:int=Form(...),parent_id:str=Form(""),master_offset:float=Form(0)):
    raw=await file.read(1024*1024+1)
    if len(raw)>1024*1024: raise HTTPException(413,"Track must be under 1 MB")
    try: text=raw.decode("utf-8-sig")
    except UnicodeDecodeError: raise HTTPException(422,"Track must use UTF-8")
    extension=Path(file.filename or "").suffix.lower()
    if extension==".json":
        cue_data=json.loads(text)
        if not isinstance(cue_data,list): raise ValueError("JSON track must be an array of cues")
        cues=[Cue.model_validate(c) for c in cue_data]
    elif extension in {".srt",".vtt"}:
        parsed=(parse_vtt if extension==".vtt" else parse_srt)(text)
        cues=[Cue(id=str(c.index),start=c.start_seconds,end=c.end_seconds,text=c.text) for c in parsed]
    else: raise HTTPException(415,"Use SRT, VTT or JSON cue arrays")
    asset=Asset(name=Path(file.filename or "track").name,locale=locale,kind=kind,parent_id=parent_id or None,master_offset=master_offset,cues=cues)
    async with locks[project_id]:
        project=load(project_id); check(project,revision)
        if asset.parent_id and not any(a.id==asset.parent_id for a in project.assets): raise ValueError("Parent must belong to this project")
        project.assets.append(asset); Project.model_validate(project.model_dump())
        project.status="READY_FOR_SCAN" if project.approved_spec_digest else "INGESTED"
        project.snapshot_id=None; project.findings=[]
        project.record("track_uploaded",actor,asset_id=asset.id,hash=asset.content_hash())
        store.save(project,revision)
    return public(project)

@app.post("/api/projects/{project_id}/extract")
async def extract(project_id:str,data:Revision,actor:Auth):
    async with locks[project_id]:
        project=load(project_id); check(project,data.revision)
        media=await asyncio.to_thread(media_store.get,project.media_key) if project.media_key else None
        try:
            async with asyncio.timeout(120): spec,trace=await gemini.extract(project,media)
        except Exception:
            log.exception("Extraction failed for %s",project.id)
            raise HTTPException(503,"Google Cloud extraction failed; no invented result was substituted")
        project.spec=spec; project.approved_spec_digest=None; project.status="SPEC_REVIEW"; project.snapshot_id=None
        project.record("spec_extracted",actor,**trace); store.save(project,data.revision)
    return public(project)
@app.put("/api/projects/{project_id}/spec")
async def edit_spec(project_id:str,actor:Auth,spec:StorySpec=Body(...),revision:int=Body(...)):
    async with locks[project_id]:
        project=load(project_id); check(project,revision)
        project.spec=spec; project.approved_spec_digest=None; project.status="SPEC_REVIEW"; project.snapshot_id=None
        project.record("spec_edited",actor); store.save(project,revision)
    return public(project)
@app.post("/api/projects/{project_id}/spec/approve")
async def approve_spec(project_id:str,data:Approve,actor:Auth):
    async with locks[project_id]:
        project=load(project_id); check(project,data.revision)
        if not project.spec or digest(project.spec.model_dump())!=data.digest: raise Conflict("The reviewed spec changed")
        project.approved_spec_digest=data.digest; project.status="READY_FOR_SCAN"
        project.record("spec_approved",actor,digest=data.digest); store.save(project,data.revision)
    return public(project)
@app.post("/api/projects/{project_id}/scan")
async def scan_project(project_id:str,data:Revision,actor:Auth):
    async with locks[project_id]:
        project=load(project_id); check(project,data.revision)
        if not project.spec or project.approved_spec_digest!=digest(project.spec.model_dump()): raise ValueError("Approve the current specification first")
        if not project.assets: raise ValueError("Upload at least one downstream track")
        await verify_and_save(project)
    return public(project)
@app.post("/api/projects/{project_id}/investigate")
async def investigate(project_id:str,data:Investigate,actor:Auth):
    async with locks[project_id]:
        project=load(project_id); check(project,data.revision)
        if not project.snapshot_id or project.status not in {"FINDINGS_OPEN","PROPOSAL_REVIEW"}: raise ValueError("Scan current assets first")
        try:
            proposal,trace=await gemini.investigate(project,data.finding_ids,analytics,project.snapshot_id)
            workflow.validate_proposal(project,proposal)
        except Exception:
            log.exception("Investigation failed for %s",project.id)
            raise HTTPException(503,"Investigation did not produce a valid evidence-backed patch; no changes were applied")
        project.proposals.append(proposal); project.status="PROPOSAL_REVIEW"
        project.record("investigation_completed",actor,proposal_id=proposal.id,trace=trace)
        store.save(project,data.revision)
    return public(project)

def proposal_of(project,proposal_id):
    proposal=next((p for p in project.proposals if p.id==proposal_id),None)
    if not proposal: raise HTTPException(404,"Proposal not found")
    return proposal
@app.put("/api/projects/{project_id}/proposals/{proposal_id}")
async def edit_proposal(project_id:str,proposal_id:str,data:EditProposal,actor:Auth):
    async with locks[project_id]:
        project=load(project_id); check(project,data.revision)
        old=proposal_of(project,proposal_id)
        if old.status!="PROPOSED": raise ValueError("Only pending proposals may be edited")
        new=Proposal(id=old.id,finding_ids=old.finding_ids,spec_digest=old.spec_digest,changes=data.proposal.changes,rationale=data.proposal.rationale,uncertainty=data.proposal.uncertainty)
        workflow.validate_proposal(project,new)
        project.proposals=[new if p.id==proposal_id else p for p in project.proposals]
        project.record("proposal_edited",actor,proposal_id=proposal_id); store.save(project,data.revision)
    return public(project)
@app.post("/api/projects/{project_id}/proposals/{proposal_id}/reject")
async def reject(project_id:str,proposal_id:str,data:Revision,actor:Auth):
    async with locks[project_id]:
        project=load(project_id); check(project,data.revision); proposal=proposal_of(project,proposal_id)
        if proposal.status!="PROPOSED": raise ValueError("Only pending proposals may be rejected")
        proposal.status="REJECTED"; project.record("proposal_rejected",actor,proposal_id=proposal_id); store.save(project,data.revision)
    return public(project)
@app.post("/api/projects/{project_id}/proposals/{proposal_id}/apply")
async def apply_patch(project_id:str,proposal_id:str,data:Approve,actor:Auth):
    async with locks[project_id]:
        project=load(project_id); check(project,data.revision)
        workflow.apply(project,proposal_of(project,proposal_id),data.digest,actor)
        store.save(project,data.revision); await verify_and_save(project)
    return public(project)
@app.post("/api/projects/{project_id}/proposals/{proposal_id}/rollback")
async def rollback(project_id:str,proposal_id:str,data:Revision,actor:Auth):
    async with locks[project_id]:
        project=load(project_id); check(project,data.revision)
        workflow.rollback(project,proposal_of(project,proposal_id),actor)
        store.save(project,data.revision); await verify_and_save(project)
    return public(project)
@app.get("/api/projects/{project_id}/export")
async def export(project_id:str,actor:Auth):
    project=load(project_id); buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,"w",zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("delivery-report.json",json.dumps(public(project),ensure_ascii=False,indent=2))
        archive.writestr("README.txt",f"Accord delivery snapshot\nStatus: {project.status}\nUnresolved findings: {len(project.findings)}\nTriage evidence, not accessibility certification. JSON tracks preserve placement; SRT does not.\n")
        for asset in project.assets:
            archive.writestr(f"tracks/{asset.id}.json",asset.model_dump_json(indent=2))
            srt="\n\n".join(f"{i}\n{seconds_to_srt_timecode(c.start)} --> {seconds_to_srt_timecode(c.end)}\n{c.text}" for i,c in enumerate(sorted(asset.cues,key=lambda c:c.start),1))
            archive.writestr(f"tracks/{asset.id}.srt",srt+"\n")
    return Response(buffer.getvalue(),media_type="application/zip",headers={"Content-Disposition":f'attachment; filename="accord-{project.id}.zip"'})

static=Path(os.getenv("STATIC_DIR",str(Path(__file__).resolve().parents[2]/"frontend"/"dist")))
if static.is_dir(): app.mount("/",StaticFiles(directory=static,html=True),name="web")
