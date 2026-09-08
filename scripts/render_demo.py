"""Make an explicitly edited walkthrough from actual hosted UI captures and Google speech."""
import base64,json,os,subprocess,wave
from pathlib import Path
import google.auth
from google.auth.transport.requests import AuthorizedSession
out=Path('runtime/demo-capture');out.mkdir(exist_ok=True)
segments=[('00-welcome', 'Meet Accord. Keep the story intact across every version.'), ('01-sources', 'This is The Last Lantern, an original animated short made for this demonstration. A courier brings a light to a mountain station, where fourteen passengers are waiting. Here are the subtitles, accessible captions, dub transcript, and linked recap and trailer.'), ('02-spec', 'Accord reads the film and prepares story notes. The reviewer checks the passenger count, the warning bell, when the courier introduces herself, and the platform sign. Approved notes become the reference for each version.'), ('03-findings', 'The Spanish subtitle says four passengers instead of fourteen. Accord brings the issue back to the original moment, with the source evidence beside the film.'), ('04-defects', 'That error also appears in the recap and trailer. Other test versions miss the warning bell, reveal the courier’s name early, overlap dialogue with audio description, or cover the platform sign.'), ('05-proposal', 'Ask for suggested changes, then watch the difference. Before and After preview the actual caption text, timing and placement on the film. Nothing is applied until the reviewer approves.'), ('05b-editor', 'Adjust a suggestion with ordinary text and timing fields. Move a caption away from the sign. The connected versions show which files the proposal changes. The reviewer stays in control.'), ('06-verified', 'After approval, Accord applies the reviewed changes and checks the updated tracks again. This run has no remaining findings. The corrected versions and review history are ready to download.'), ('07-evidence', 'The investigation uses Gemini, Google ADK and the official ClickHouse MCP server. History retains the evidence and decisions. A separate original lighthouse scene was also tested, alongside clean controls. These are bounded demonstration results.'), ('08-rollback', 'Undo restores the previous versions, including the recap and trailer. This recording uses the actual hosted app, original AI-assisted animation, and deliberately introduced test issues. Waiting time has been shortened. Accord. Keep the story intact.')]
credentials,project=google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
session=AuthorizedSession(credentials);session.headers['x-goog-user-project']=project
(out/'caption.txt').write_text('Accord demonstration | Original AI-assisted animation | Waiting time shortened',encoding='utf-8')
duration=0
for name,narration in segments:
    audio=out/(name+'.wav');transcript=out/(name+'.txt')
    if not audio.exists() or not transcript.exists() or transcript.read_text(encoding='utf-8')!=narration:
        response=session.post('https://texttospeech.googleapis.com/v1/text:synthesize',json={'input':{'text':narration},'voice':{'languageCode':'en-US','name':'en-US-Standard-D'},'audioConfig':{'audioEncoding':'LINEAR16','speakingRate':1.08}},timeout=60)
        response.raise_for_status();audio.write_bytes(base64.b64decode(response.json()['audioContent']));transcript.write_text(narration,encoding='utf-8')
    with wave.open(str(audio),'rb') as f: length=f.getnframes()/f.getframerate();duration+=length
    if os.getenv('STORYPARITY_AUDIO_ONLY')=='1': continue
    filt="scale=1440:1000,pad=1440:1080:0:0:color=0x101820,drawtext=fontfile='C\\:/Windows/Fonts/arial.ttf':textfile=runtime/demo-capture/caption.txt:fontcolor=white:fontsize=22:x=(w-tw)/2:y=1028"
    screen=out/(name+'-screen.mp4')
    inputs=['-i',str(screen)] if screen.exists() else ['-loop','1','-i',str(out/(name+'.png'))]
    subprocess.run(['ffmpeg','-y',*inputs,'-i',str(audio),'-vf',filt+',tpad=stop_mode=clone:stop_duration=60','-c:v','libx264','-preset','fast','-threads','2','-r','24','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-t',str(length+.5),str(out/(name+'.mp4'))],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
if os.getenv('STORYPARITY_AUDIO_ONLY')=='1':
    print(json.dumps({'narrationSeconds':round(duration,2),'segments':len(segments)}));raise SystemExit(0)
(out/'concat.txt').write_text('\n'.join("file '"+name+".mp4'" for name,_ in segments),encoding='utf-8')
subprocess.run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(out/'concat.txt'),'-vf','fps=24','-c:v','libx264','-preset','fast','-threads','2','-crf','23','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-movflags','+faststart',str(out/'Accord-walkthrough.mp4')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
(out/'narration.json').write_text(json.dumps(segments,indent=2),encoding='utf-8')
print(json.dumps({'video':str(out/'Accord-walkthrough.mp4'),'seconds':round(duration,2),'actualHostedScreens':True,'editedWaitTime':True}))
