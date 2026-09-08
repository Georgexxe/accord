import React, {useEffect, useRef, useState} from 'react';

export type Cue = {id:string;start:number;end:number;text:string;box?:{x:number;y:number;width:number;height:number}|null};
export type Asset = {id:string;name:string;kind:string;parent_id?:string|null;master_offset:number;cues:Cue[];revision:number};
export type Change = {asset_id:string;cue_id:string;operation:'REPLACE'|'INSERT'|'DELETE';replacement?:Cue|null;base_hash:string};
export type Proposal = {id:string;status:string;changes:Change[];snapshots:Asset[];rationale:string;[key:string]:any};

export function previewCues(asset:Asset, changes:Change[]):Cue[] {
  const cues=new Map(asset.cues.map(c=>[c.id,c]));
  for(const c of changes.filter(c=>c.asset_id===asset.id)) {
    if(c.operation==='DELETE')cues.delete(c.cue_id);
    else if(c.replacement)cues.set(c.cue_id,c.replacement);
  }
  return [...cues.values()].sort((a,b)=>a.start-b.start);
}

export function ChangePreview({assets,proposal,videoUrl}:{assets:Asset[];proposal:Proposal;videoUrl:string}) {
  const ids=[...new Set(proposal.changes.map(c=>c.asset_id))];
  const [assetId,setAssetId]=useState(ids[0]||'');
  const [mode,setMode]=useState<'before'|'after'>('before');
  const [time,setTime]=useState(0);
  const ref=useRef<HTMLVideoElement>(null);
  useEffect(()=>{setAssetId(ids[0]||'');setMode('before');},[proposal.id]);
  const current=assets.find(a=>a.id===assetId);
  // Applied proposals carry immutable pre-change assets; never use today's cues as history.
  const asset=proposal.status==='APPLIED'?proposal.preview_assets?.find(a=>a.id===assetId):current;
  if(!asset)return <p>The original version is unavailable for this preview.</p>;
  const cues=mode==='before'?asset.cues:previewCues(asset,proposal.changes);
  const active=cues.filter(c=>time>=c.start+asset.master_offset&&time<c.end+asset.master_offset);
  const change=proposal.changes.find(c=>c.asset_id===assetId);
  const original=asset.cues.find(c=>c.id===change?.cue_id);
  const seek=()=>{if(ref.current){ref.current.currentTime=Math.max(0,Math.min(original?.start??Infinity,change?.replacement?.start??Infinity,86400)+asset.master_offset-0.3);ref.current.play().catch(()=>{});}};
  return <div className="change-preview">
    <div className="section-heading"><h3>See the difference</h3><div className="preview-toggle" role="group" aria-label="Preview version">
      <button type="button" className={mode==='before'?'':'secondary'} aria-pressed={mode==='before'} onClick={()=>setMode('before')}>Before</button>
      <button type="button" className={mode==='after'?'':'secondary'} aria-pressed={mode==='after'} onClick={()=>setMode('after')}>After</button>
    </div></div>
    <label>Preview track<select value={assetId} onChange={e=>{setAssetId(e.target.value);ref.current?.pause();setTime(0);if(ref.current)ref.current.currentTime=0;}}>{ids.map(id=><option key={id} value={id}>{assets.find(a=>a.id===id)?.name||id}</option>)}</select></label>
    <div className="comparison-film"><video ref={ref} src={videoUrl} controls onTimeUpdate={e=>setTime(e.currentTarget.currentTime)}/>
      {active.map(c=><div key={c.id} className="comparison-cue" style={c.box?{left:`${c.box.x*100}%`,top:`${c.box.y*100}%`,width:`${c.box.width*100}%`,height:`${c.box.height*100}%`,transform:'none',bottom:'auto'}:undefined}>{c.text}</div>)}
    </div>
    <div className="section-heading"><p>{mode==='before'?'Original cues':'Proposed cues'} · {time.toFixed(1)}s{['DUB','AD'].includes(asset.kind)?' · Text preview; original film audio':''}</p><button type="button" className="secondary" onClick={seek}>Play changed moment</button></div>
  </div>;
}

export function ChangeEditor({proposal,assets,busy,onSave,onCancel}:{proposal:Proposal;assets:Asset[];busy:boolean;onSave:(p:Proposal)=>Promise<void>;onCancel:()=>void}) {
  const [draft,setDraft]=useState<Proposal>(()=>JSON.parse(JSON.stringify(proposal)));
  const [error,setError]=useState('');
  function edit(index:number,field:string,value:unknown){setDraft(p=>({...p,changes:p.changes.map((c,i)=>i!==index?c:{...c,replacement:{...c.replacement,[field]:value} as Cue})}));}
  async function save(e:React.FormEvent){e.preventDefault();setError('');
    for(const c of draft.changes){if(c.operation==='DELETE')continue;const q=c.replacement;
      if(!q||!q.text.trim()||!Number.isFinite(q.start)||!Number.isFinite(q.end)||q.start<0||q.end<=q.start){setError('Each caption needs text and an end time after its start.');return;}
      if(q.box&&(!Object.values(q.box).every(Number.isFinite)||q.box.x<0||q.box.y<0||q.box.width<=0||q.box.height<=0||q.box.x+q.box.width>1||q.box.y+q.box.height>1)){setError('Keep the caption placement inside the picture.');return;}
    }
    try{await onSave(draft);}catch(e:any){setError(e.message);}
  }
  return <form className="change-editor" onSubmit={save}><h3>Edit suggested changes</h3><p>Save your edits to update the preview and approve them, or cancel to keep the current suggestion.</p>
    {draft.changes.map((c,i)=><fieldset key={`${c.asset_id}-${c.cue_id}`} disabled={busy}><legend>{assets.find(a=>a.id===c.asset_id)?.name} · {c.cue_id}</legend>
      {c.operation==='DELETE'?<p>This cue will be removed.</p>:<>
        <label>Caption text<textarea rows={3} maxLength={4000} required value={c.replacement?.text||''} onChange={e=>edit(i,'text',e.target.value)}/></label>
        <div className="form-row"><label>Start (seconds)<input type="number" min="0" max="86400" step="0.01" required value={Number.isFinite(c.replacement?.start)?c.replacement.start:''} onChange={e=>edit(i,'start',e.target.valueAsNumber)}/></label><label>End (seconds)<input type="number" min="0.01" max="86400" step="0.01" required value={Number.isFinite(c.replacement?.end)?c.replacement.end:''} onChange={e=>edit(i,'end',e.target.valueAsNumber)}/></label></div>
        <label>Placement<select value={c.replacement?.box?'custom':'default'} onChange={e=>edit(i,'box',e.target.value==='default'?null:{x:.15,y:.08,width:.7,height:.14})}><option value="default">Bottom centre</option><option value="custom">Choose position</option></select></label>
        {c.replacement?.box&&<div className="placement-fields">{(['x','y','width','height'] as const).map((key)=><label key={key}>{{x:'Left',y:'Top',width:'Width',height:'Height'}[key]} (%)<input type="number" step="0.1" min={key==='width'||key==='height'?.1:0} max="100" required value={Number.isFinite(c.replacement!.box![key])?Math.round(c.replacement!.box![key]*1000)/10:''} onChange={e=>edit(i,'box',{...c.replacement!.box,[key]:e.target.valueAsNumber/100})}/></label>)}</div>}
      </>}
    </fieldset>)}
    {error&&<p role="alert" className="error">{error}</p>}
    <div className="actions"><button type="submit" disabled={busy}>Save edits</button><button type="button" className="secondary" disabled={busy} onClick={onCancel}>Cancel</button></div>
  </form>;
}

export function VersionImpact({assets,findings,changes=[]}:{assets:Asset[];findings:{asset_id:string}[];changes?:Change[]}) {
  if(!assets.length)return null;
  return <section className="panel version-impact"><h2>Connected versions</h2><p>See where each version comes from and what still needs attention.</p>
    <div className="version-list">{assets.map(a=>{const parent=assets.find(p=>p.id===a.parent_id);const issues=findings.filter(f=>f.asset_id===a.id).length;const edits=changes.filter(c=>c.asset_id===a.id).length;
      return <article key={a.id}><div><small>{parent?`From ${parent.name}`:'From the original film'}</small><strong>{a.name}</strong><small>Version {a.revision}</small></div><div className="version-state"><span className="tag">{issues?`${issues} to review`:'No open findings'}</span>{edits>0&&<span className="tag good">{edits} proposed {edits===1?'change':'changes'}</span>}</div></article>;
    })}</div>
  </section>;
}
