"""Make an explicitly edited walkthrough from actual hosted UI captures and Google speech."""
import base64,json,os,subprocess,wave
from pathlib import Path
import google.auth
from google.auth.transport.requests import AuthorizedSession
out=Path('runtime/demo-capture');out.mkdir(exist_ok=True)
segments=[('00-welcome', 'Meet Accord. Keep the story intact across every version.'), ('01-sources', 'Start with your original film and add the versions you want to review. Here we have Spanish subtitles, accessible captions, audio description, a dub transcript, and two shorter edits linked to the Spanish version.'), ('02-spec', 'Accord reads the film and prepares story notes: important facts, names, sounds, dialogue and visual clues. Review these notes against your original, make any adjustments, then approve them. They become the reference for your versions.'), ('03-findings', 'Review brings each issue back to the moment it matters. Here, the original says fourteen survivors, but the Spanish recap says four. Play the scene and see the subtitle alongside the original evidence.'), ('04-defects', 'The same problem has carried into the trailer. Elsewhere, a name appears too early, captions miss a door-lock sound, audio description interrupts dialogue, and a subtitle covers an important code. Accord brings these issues together so they are easier to work through.'), ('05-proposal', 'Choose the issues you want to address and ask for suggested changes. Compare the original and proposed versions side by side. You can edit or reject a suggestion before applying it. In this demonstration, the reviewer adjusts the sound caption and subtitle placement before approving.'), ('06-verified', 'Accord applies the approved changes and checks the updated versions again. When those checks pass, your versions are ready to download together with their review history.'), ('07-evidence', 'Project history keeps the decisions and changes together. You can revisit what happened and open the supporting details when you need them. Gemini, Google ADK and ClickHouse support the review behind the scenes.'), ('08-rollback', 'Need to go back? Undo the changes to restore the previous versions, including the linked recap and trailer. This walkthrough uses an original fictional scene with deliberately introduced issues. Waiting time has been shortened. Accord. Keep the story intact.')]
credentials,project=google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
session=AuthorizedSession(credentials);session.headers['x-goog-user-project']=project
(out/'caption.txt').write_text('Accord demonstration | Original fictional scene | Waiting time shortened',encoding='utf-8')
duration=0
for name,narration in segments:
    audio=out/(name+'.wav');transcript=out/(name+'.txt')
    if not audio.exists() or not transcript.exists() or transcript.read_text(encoding='utf-8')!=narration:
        response=session.post('https://texttospeech.googleapis.com/v1/text:synthesize',json={'input':{'text':narration},'voice':{'languageCode':'en-US','name':'en-US-Standard-D'},'audioConfig':{'audioEncoding':'LINEAR16','speakingRate':1.08}},timeout=60)
        response.raise_for_status();audio.write_bytes(base64.b64decode(response.json()['audioContent']));transcript.write_text(narration,encoding='utf-8')
    with wave.open(str(audio),'rb') as f: duration+=f.getnframes()/f.getframerate()
    if os.getenv('STORYPARITY_AUDIO_ONLY')=='1': continue
    filt="scale=1440:1000,pad=1440:1080:0:0:color=0x101820,drawtext=fontfile='C\\:/Windows/Fonts/arial.ttf':textfile=runtime/demo-capture/caption.txt:fontcolor=white:fontsize=22:x=(w-tw)/2:y=1028"
    subprocess.run(['ffmpeg','-y','-loop','1','-i',str(out/(name+'.png')),'-i',str(audio),'-vf',filt,'-c:v','libx264','-preset','fast','-tune','stillimage','-r','24','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-shortest',str(out/(name+'.mp4'))],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
if os.getenv('STORYPARITY_AUDIO_ONLY')=='1':
    print(json.dumps({'narrationSeconds':round(duration,2),'segments':len(segments)}));raise SystemExit(0)
(out/'concat.txt').write_text('\n'.join("file '"+name+".mp4'" for name,_ in segments),encoding='utf-8')
subprocess.run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(out/'concat.txt'),'-vf','fps=24','-c:v','libx264','-preset','fast','-crf','23','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-movflags','+faststart',str(out/'Accord-walkthrough.mp4')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
(out/'narration.json').write_text(json.dumps(segments,indent=2),encoding='utf-8')
print(json.dumps({'video':str(out/'Accord-walkthrough.mp4'),'seconds':round(duration,2),'actualHostedScreens':True,'editedWaitTime':True}))
