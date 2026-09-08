"""Make an explicitly edited walkthrough from actual hosted UI captures and Google speech."""
import base64,json,os,subprocess,wave
from pathlib import Path
import google.auth
from google.auth.transport.requests import AuthorizedSession
out=Path('runtime/demo-capture');out.mkdir(exist_ok=True)
segments=[
('01-sources','Every audience should get the same story. StoryParity reviews what changed between a master and its localized and accessible versions. This original synthetic scene has six tracks: Spanish subtitles, English captions, audio description, a dub transcript, and linked Spanish recap and trailer versions.'),
('02-spec','Gemini on Google Cloud analyzes the master video, audio, and script. Its candidate specification includes story facts, identity reveals, important sounds, dialogue intervals, and on-screen clues. A reviewer checks and edits those facts before approving the exact version. In this acceptance run, measured source annotations corrected dialogue timing.'),
('03-findings','The approved specification drives bounded checks against actual versioned tracks. The evidence player links each finding to the master timeline and previews the selected subtitle text and placement. These are review candidates with visible evidence, not a general claim that artificial intelligence can certify a translation.'),
('04-defects','Here, fourteen survivors became four, including in the linked recap and trailer. A name appears too early. Captions omit the critical door-lock sound. Audio description overlaps dialogue, and a subtitle covers the access code. All five supported defect classes are present in this deliberately defective test scene.'),
('05-proposal','A real Google ADK investigator reads the approved evidence and current asset versions through tools. The official ClickHouse MCP server queries the private database. Google multilingual embeddings rank related cues with cosine distance. The agent proposes exact multi-asset changes. A reviewer can edit, reject, or approve them; the model cannot authorize its own repair.'),
('06-verified','After approval, the server checks the specification, exact cue identifiers, base hashes, timing, and placement. It snapshots affected assets, applies the changes, reindexes them, and reads them back through MCP. Verified means the current configured checks passed. The delivery export includes corrected tracks and a versioned report.'),
('07-evidence','The activity view preserves approval decisions, actual tool queries, and measured model usage. Cloud state is durable in Firestore and private Cloud Storage. Application data requires the reviewer key. The source, original test inputs, and reproducible validation runners are published with the release.'),
('08-rollback','Rollback checks for later edits before restoring every affected asset and repeating the checks. The original findings return, including the linked derivatives. This edited walkthrough shows real hosted application states; waiting time is omitted. AI investigates. People approve. Checks verify.')]
credentials,project=google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
session=AuthorizedSession(credentials);session.headers['x-goog-user-project']=project
(out/'caption.txt').write_text('Actual hosted UI | Edited walkthrough; wait time omitted | Synthetic source scene',encoding='utf-8')
duration=0
for name,narration in segments:
    response=session.post('https://texttospeech.googleapis.com/v1/text:synthesize',json={'input':{'text':narration},'voice':{'languageCode':'en-US','name':'en-US-Standard-D'},'audioConfig':{'audioEncoding':'LINEAR16','speakingRate':1.08}},timeout=60)
    response.raise_for_status();audio=out/(name+'.wav');audio.write_bytes(base64.b64decode(response.json()['audioContent']))
    with wave.open(str(audio),'rb') as f: duration+=f.getnframes()/f.getframerate()
    filt="scale=1440:1000,pad=1440:1080:0:0:color=0x101820,drawtext=fontfile='C\\:/Windows/Fonts/arial.ttf':textfile=runtime/demo-capture/caption.txt:fontcolor=white:fontsize=22:x=(w-tw)/2:y=1028"
    subprocess.run(['ffmpeg','-y','-loop','1','-i',str(out/(name+'.png')),'-i',str(audio),'-vf',filt,'-c:v','libx264','-preset','fast','-tune','stillimage','-r','24','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-shortest',str(out/(name+'.mp4'))],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
(out/'concat.txt').write_text('\n'.join("file '"+name+".mp4'" for name,_ in segments),encoding='utf-8')
subprocess.run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(out/'concat.txt'),'-c','copy','-movflags','+faststart',str(out/'StoryParity-walkthrough.mp4')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
(out/'narration.json').write_text(json.dumps(segments,indent=2),encoding='utf-8')
print(json.dumps({'video':str(out/'StoryParity-walkthrough.mp4'),'seconds':round(duration,2),'actualHostedScreens':True,'editedWaitTime':True}))
