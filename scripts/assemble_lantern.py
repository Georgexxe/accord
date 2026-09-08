"""Assemble original Veo animation, Google speech, and original synthesized sound."""
import argparse,base64,json,subprocess,wave
from pathlib import Path
import numpy as np
import requests

ROOT=Path('runtime/lantern');RATE=24000
LINES=[('passengers',9,'en-US-Standard-F','There are fourteen passengers still waiting. We cannot leave them in the dark.'),('platform',17,'en-US-Standard-D','Then take the lantern to platform seven. Go when the bell rings.'),('name',33,'en-US-Standard-F',"My name is Mira. Tell them we're coming."),('home',42,'en-US-Standard-D','They can see us now.')]
HARBOR=[('flashes',2,'en-US-Standard-F',"Two flashes. That's the signal for home."),('steady',10,'en-US-Standard-F','Keep the light steady until they reach the harbor.')]

def ff(*args):subprocess.run(['ffmpeg','-y','-v','error',*map(str,args)],check=True)
def wav(path,data):
 with wave.open(str(path),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(RATE);w.writeframes((np.clip(data,-.98,.98)*32767).astype('<i2').tobytes())
def audio(lines,length,session,name):
 n=int(length*RATE);t=np.arange(n)/RATE;rng=np.random.default_rng(41)
 mix=rng.normal(0,.006,n)
 # An original sparse sustained chord bed, below dialogue.
 for f in [146.83,220,293.66]:mix+=.008*np.sin(2*np.pi*f*t)*np.sin(np.pi*np.minimum(t/length,1))**2
 records=[]
 for key,start,voice,text in lines:
  path=ROOT/(key+'.wav')
  if not path.exists():
   r=session.post('https://texttospeech.googleapis.com/v1/text:synthesize',json={'input':{'text':text},'voice':{'languageCode':'en-US','name':voice},'audioConfig':{'audioEncoding':'LINEAR16','sampleRateHertz':RATE,'speakingRate':1.07}},timeout=90);r.raise_for_status();path.write_bytes(base64.b64decode(r.json()['audioContent']))
  with wave.open(str(path),'rb') as w:voice_data=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(float)/32768
  end=start+len(voice_data)/RATE;assert end<length
  a=int(start*RATE);mix[a:a+len(voice_data)]+=voice_data*.9
  records.append({'start':start,'end':round(end,3),'text':text,'voice':voice})
 bells=[25,26,27] if name=='lantern' else [8,8.8]
 for start in bells:
  bt=np.arange(int(1.8*RATE))/RATE
  sound=(np.sin(2*np.pi*880*bt)+.45*np.sin(2*np.pi*1327*bt)+.2*np.sin(2*np.pi*2107*bt))*.17*np.exp(-3*bt)
  a=int(start*RATE);mix[a:a+len(sound)]+=sound[:min(len(sound),n-a)]
 wav(ROOT/(name+'-mix.wav'),mix)
 (ROOT/(name+'-dialogue.json')).write_text(json.dumps(records,indent=2),encoding='utf-8')
 return records

def film(names,mix,target,sign=False):
 clips=[]
 for i,name in enumerate(names):
  output=ROOT/(name+'-edit.mp4');filters='fps=24,scale=1280:720,setsar=1'
  if sign and name=='signal':
   filters+=",drawbox=x=820:y=504:w=345:h=86:color=0x132c38:t=fill,drawbox=x=820:y=504:w=345:h=86:color=0xd6bc71:t=3,drawtext=fontfile='C\\:/Windows/Fonts/arial.ttf':text='PLATFORM 7':fontsize=34:fontcolor=0xffe7a1:x=854:y=529"
  if sign and i==0:
   filters+=",drawtext=fontfile='C\\:/Windows/Fonts/georgia.ttf':text='THE LAST LANTERN':fontsize=30:fontcolor=0xffe5ab:x=56:y=52:enable='lt(t,3)'"
  ff('-i',ROOT/(name+'.mp4'),'-t',8,'-an','-vf',filters,'-c:v','libx264','-preset','fast','-crf',26,'-maxrate','2800k','-bufsize','5600k',output);clips.append(output.name)
 (ROOT/'film-concat.txt').write_text('\n'.join("file '"+s+"'" for s in clips))
 target.parent.mkdir(parents=True,exist_ok=True)
 ff('-f','concat','-safe',0,'-i',ROOT/'film-concat.txt','-i',ROOT/(mix+'-mix.wav'),'-map','0:v','-map','1:a','-c:v','copy','-c:a','aac','-b:a','160k','-shortest','-movflags','+faststart',target)
 check=subprocess.run(['ffmpeg','-v','error','-i',str(target),'-f','null','-'],capture_output=True,text=True,check=True)
 assert not check.stderr.strip(),check.stderr

def main():
 p=argparse.ArgumentParser();p.add_argument('--gcloud',required=True);p.add_argument('--audio-only',action='store_true');p.add_argument('--main-only',action='store_true');a=p.parse_args()
 token=subprocess.run([a.gcloud,'auth','print-access-token'],capture_output=True,text=True,check=True).stdout.strip();session=requests.Session();session.headers.update(Authorization='Bearer '+token,**{'x-goog-user-project':'project-ca8af2fe-5aff-496a-bd8'})
 audio(LINES,48,session,'lantern');audio(HARBOR,16,session,'harbor');print('Original dialogue and soundtrack complete',flush=True)
 if not a.audio_only:
  film(['arrival','promise','keeper','bell','signal','home'],'lantern',Path('demo/lantern/master.mp4'),True)
  if not a.main_only:film(['harbor','harbor_signal'],'harbor',Path('demo/harbor/master.mp4'))
  print('Selected original films assembled and decoded successfully',flush=True)
if __name__=='__main__':main()
