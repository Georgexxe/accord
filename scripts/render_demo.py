"""Make an explicitly edited walkthrough from actual hosted UI captures and Google speech."""
import base64,json,os,subprocess,wave,sys
from pathlib import Path
import google.auth
from google.auth.transport.requests import AuthorizedSession
out=Path('runtime/demo-capture');out.mkdir(exist_ok=True)
segments=[('00-welcome', "A film can tell one story in English, and a slightly different one in its subtitles. That's the problem Accord helps you catch."), ('01-sources', "Here's The Last Lantern, a short we made for this demo. Fourteen passengers are waiting at a station. We've added subtitles, captions, and a couple of shorter edits. Let's see what changed between them."), ('02-spec', "First, we check the story notes. How many passengers are waiting? When do we learn the courier's name? Does the bell matter? Accord suggests these notes from the film, and we check them before using them as a reference."), ('03-findings', 'Look at this subtitle. It says four passengers, but the original says fourteen. The line from the film is right beside it, so we can check the difference ourselves.'), ('04-defects', 'The same mistake has reached the recap and trailer. There are other problems too: a missing bell caption, a name revealed too early, and a subtitle covering the platform sign.'), ('05-proposal', "Now let's look at the suggested fix. We can switch between Before and After and see the caption on the film. That makes it much easier to judge whether the change actually works."), ('05b-editor', 'If something still feels wrong, we can edit it here. Change the wording, adjust when it appears, or move it out of the way. We decide what gets applied.'), ('06-verified', 'Once we approve, Accord updates the tracks and checks them again. In this run, all seven issues are cleared. The revised files are ready to download.'), ('07-evidence', 'The history keeps a record of what was checked and what we approved. Behind that, Gemini investigates using evidence stored in ClickHouse. We also tested a separate lighthouse scene to check the workflow on a different story.'), ('08-rollback', "And if we need to go back, Undo restores the earlier versions, including the recap and trailer. That's Accord: a way to catch changes to the story, check the fix, and keep the final decision with the reviewer.")]
VOICE="en-GB-Chirp3-HD-Charon"
session=None
duration=0
for name,narration in segments:
    audio=out/(name+'.wav');transcript=out/(name+'.txt');voice_file=out/(name+'.voice.txt')
    if not audio.exists() or not transcript.exists() or transcript.read_text(encoding='utf-8')!=narration or not voice_file.exists() or voice_file.read_text()!=VOICE:
        if session is None:
            credentials,project=google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
            session=AuthorizedSession(credentials);session.headers['x-goog-user-project']=project
        response=session.post('https://texttospeech.googleapis.com/v1/text:synthesize',json={'input':{'text':narration},'voice':{'languageCode':'en-GB','name':VOICE},'audioConfig':{'audioEncoding':'LINEAR16','sampleRateHertz':24000}},timeout=60)
        response.raise_for_status();audio.write_bytes(base64.b64decode(response.json()['audioContent']));transcript.write_text(narration,encoding='utf-8');voice_file.write_text(VOICE)
    with wave.open(str(audio),'rb') as f: length=f.getnframes()/f.getframerate();duration+=length
    if os.getenv('STORYPARITY_AUDIO_ONLY')=='1': continue
    selected=os.getenv('STORYPARITY_RENDER_ONLY','')
    if selected and name not in selected.split(','):continue
    filt="scale=1440:1000"
    screen=out/(name+'-clean-screen.mp4')
    inputs=['-i',str(screen)] if screen.exists() else ['-loop','1','-i',str(out/(name+'.png'))]
    subprocess.run(['ffmpeg','-y',*inputs,'-i',str(audio),'-vf',filt+',tpad=stop_mode=clone:stop_duration=60','-c:v','libx264','-preset','fast','-threads','2','-r','24','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-t',str(length+.5),str(out/(name+'.mp4'))],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
if os.getenv('STORYPARITY_AUDIO_ONLY')=='1':
    print(json.dumps({'narrationSeconds':round(duration,2),'segments':len(segments)}));raise SystemExit(0)
(out/'concat.txt').write_text('\n'.join("file '"+name+".mp4'" for name,_ in segments),encoding='utf-8')
subprocess.run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(out/'concat.txt'),'-vf','fps=24','-c:v','libx264','-preset','fast','-threads','2','-crf','23','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-movflags','+faststart',str(out/'Accord-walkthrough.mp4')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
subprocess.run([sys.executable,str(Path(__file__).with_name('validate_video.py')),str(out/'Accord-walkthrough.mp4')],check=True)
(out/'narration.json').write_text(json.dumps(segments,indent=2),encoding='utf-8')
print(json.dumps({'video':str(out/'Accord-walkthrough.mp4'),'seconds':round(duration,2),'actualHostedScreens':True,'editedWaitTime':True}))
