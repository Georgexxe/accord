"""Create original, explicitly synthetic fictional media with Google Cloud speech.

Run through deploy/local_cloud.py. No fabricated model analysis is saved.
The generated master, scripts and injected-error tracks are input fixtures only.
"""
import base64
import io
import json
import math
import os
import subprocess
import wave
from pathlib import Path
import google.auth
from google.auth.transport.requests import AuthorizedSession
import numpy as np
from PIL import Image,ImageDraw,ImageFont

out=Path('demo');out.mkdir(exist_ok=True)
rate=24000;duration=60
audio=np.zeros(rate*duration,dtype=np.float32)
credentials,project=google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
session=AuthorizedSession(credentials)
session.headers['x-goog-user-project']=project
lines=[(3,'The airlock is sealed. We have one chance.'),(10,'There are fourteen survivors.'),(30,'I am Captain Mara.'),(40,'Do not open it.'),(50,'Use the code on the screen.')]
spoken=[]
for start,text in lines:
    response=session.post('https://texttospeech.googleapis.com/v1/text:synthesize',json={'input':{'text':text},'voice':{'languageCode':'en-US','name':'en-US-Standard-D'},'audioConfig':{'audioEncoding':'LINEAR16','sampleRateHertz':rate,'speakingRate':.9}},timeout=60)
    if response.status_code!=200: raise RuntimeError('Google Cloud speech synthesis failed: '+str(response.status_code)+' '+response.json().get('error',{}).get('message',''))
    with wave.open(io.BytesIO(base64.b64decode(response.json()['audioContent'])),'rb') as wav:
        samples=np.frombuffer(wav.readframes(wav.getnframes()),dtype='<i2').astype(np.float32)/32768
    audio[int(start*rate):int(start*rate)+len(samples)]+=samples
    spoken.append({'start':start,'end':round(start+len(samples)/rate,3),'text':text})
# Original procedural door-lock clack + warning tone, not stock audio.
rng=np.random.default_rng(14)
for start in [20,20.18]:
    n=int(.1*rate);t=np.arange(n)/rate
    audio[int(start*rate):int(start*rate)+n]+=.4*rng.normal(size=n)*np.exp(-t*40)
for start in [20.45,20.8]:
    n=int(.18*rate);t=np.arange(n)/rate
    audio[int(start*rate):int(start*rate)+n]+=.18*np.sin(2*np.pi*880*t)*np.sin(np.pi*t/.18)
with wave.open(str(out/'master.wav'),'wb') as wav:
    wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(rate);wav.writeframes((np.clip(audio,-1,1)*30000).astype('<i2').tobytes())
font_path='C:/Windows/Fonts/arial.ttf'
def font(size): return ImageFont.truetype(font_path,size)
fps=6;width,height=1280,720
ffmpeg=os.getenv('FFMPEG','ffmpeg')
proc=subprocess.Popen([ffmpeg,'-y','-f','rawvideo','-vcodec','rawvideo','-pix_fmt','rgb24','-s',f'{width}x{height}','-r',str(fps),'-i','-','-i',str(out/'master.wav'),'-c:v','libx264','-preset','fast','-crf','25','-pix_fmt','yuv420p','-r','24','-c:a','aac','-b:a','128k','-shortest','-movflags','+faststart',str(out/'master.mp4')],stdin=subprocess.PIPE,stderr=subprocess.DEVNULL)
for frame in range(duration*fps):
    t=frame/fps
    image=Image.new('RGB',(width,height),(12,18,24));draw=ImageDraw.Draw(image)
    # Original animated airlock set, camera dolly and moving signal lights.
    vanishing=(640,310)
    for x in [-500,-100,250,1030,1380,1780]: draw.line([vanishing,(x,720)],fill=(34,51,59),width=3)
    for k in range(7):
        y=320+((k*75+t*12)%430);draw.line([(0,y),(width,y)],fill=(27,40,46),width=2)
    draw.rounded_rectangle((385,130,895,565),radius=25,fill=(28,40,49),outline=(71,94,102),width=5)
    gap=0 if t<20 else min(15,(t-20)*20)
    draw.line([(640-gap,140),(640-gap,555)],fill=(6,12,17),width=8)
    lamp=(162,198,116) if t<20 else (237,115,88)
    draw.rectangle((595,150,685,164),fill=lamp)
    draw.text((60,42),'PROTOCOL KEPLER-9',font=font(25),fill=(192,216,213))
    draw.text((60,79),'Original synthetic scene / StoryParity evaluation input',font=font(15),fill=(109,140,146))
    draw.text((1110,45),f'{t:05.1f}s',font=font(20),fill=(144,169,165))
    # Anonymous silhouette until the intentional reveal.
    draw.ellipse((165,278,215,328),fill=(109,129,139));draw.rounded_rectangle((151,321,230,495),radius=20,fill=(67,86,100))
    draw.line([(168,485),(153,590)],fill=(67,86,100),width=20);draw.line([(211,485),(229,590)],fill=(67,86,100),width=20)
    if 9<=t<16:
        draw.rounded_rectangle((790,240,1180,385),radius=12,fill=(16,39,39),outline=(127,170,135),width=2)
        draw.text((817,260),'SURVIVOR MANIFEST',font=font(20),fill=(165,199,167))
        draw.text((817,305),'14 CONFIRMED',font=font(38),fill=(201,235,171))
    if 20<=t<24: draw.text((470,210),'AIRLOCK LOCKED',font=font(27),fill=(237,132,106))
    if t>=30: draw.text((108,235),'CAPTAIN MARA',font=font(22),fill=(191,218,197))
    if 50<=t<55:
        draw.rectangle((384,504,896,612),fill=(199,217,184))
        draw.text((420,523),'ACCESS CODE: 7319',font=font(37),fill=(20,32,27))
    # Captions are separate tracks, never burned into the source.
    proc.stdin.write(image.tobytes())
proc.stdin.close()
if proc.wait()!=0: raise RuntimeError('FFmpeg failed')
script='''ORIGINAL FICTIONAL MASTER — PROTOCOL KEPLER-9. Clip is 60 seconds.
Only spoken dialogue and visible evidence establish story facts. Speaker is anonymous until 30 seconds.
03s: The airlock is sealed. We have one chance.
10s: There are fourteen survivors. Display reads 14 CONFIRMED (09–16s).
20s: Metallic door-lock clacks and two warning beeps. AIRLOCK LOCKED appears (20–24s). This sound explains why escape fails and belongs in SDH.
30s: I am Captain Mara. Her name must not appear in downstream tracks before this reveal.
40s: Do not open it.
50s: Use the code on the screen. ACCESS CODE: 7319 appears between 50–55s in normalized box x=.30,y=.70,width=.40,height=.15. Subtitle placement must not cover it.
'''
(out/'master-script.txt').write_text(script,encoding='utf-8')
def cue(id,start,end,text,box=None):
    d={'id':id,'start':start,'end':end,'text':text}
    if box:d['box']=box
    return d
es=[cue('1',3,7,'La esclusa está sellada.'),cue('2',10,14,'Hay 4 supervivientes.'),cue('3',25,29,'Soy la capitana Mara.'),cue('4',40,44,'No la abras.'),cue('5',50,55,'Usa el código de la pantalla.',{'x':.3,'y':.7,'width':.4,'height':.15})]
sdh=[cue(str(i+1),x['start'],max(x['end'],x['start']+3),x['text']) for i,x in enumerate(spoken)]
ad=[cue('1',40.5,44,'She reaches toward the locked door.')]
dub=[cue(str(i+1),x['start'],max(x['end'],x['start']+3),x['text']) for i,x in enumerate(spoken)]
for name,data in [('spanish-errors.json',es),('english-sdh-missing-lock.json',sdh),('english-ad-overlap.json',ad),('english-dub-control.json',dub)]: (out/name).write_text(json.dumps(data,indent=2),encoding='utf-8')
(out/'PROVENANCE.md').write_text('# Original StoryParity evaluation scene\n\nHuman-authored fictional script and programmatically drawn animated scene. Speech generated with Google Cloud Text-to-Speech en-US-Standard-D; door-lock sound synthesized procedurally. No third-party movie footage, stock sound, or non-Google AI service.\n\nTracks deliberately contain known defects. These are test inputs, not evidence of system accuracy. Master speech intervals are measured from generated waveforms in speech-intervals.json.\n',encoding='utf-8')
(out/'speech-intervals.json').write_text(json.dumps(spoken,indent=2),encoding='utf-8')
print(json.dumps({'status':'created','master_bytes':(out/'master.mp4').stat().st_size,'seconds':duration,'speech_intervals':spoken}))
