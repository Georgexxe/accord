"""Generate original anime shots with Google Veo. Resumable; never logs credentials."""
import argparse, base64, json, os, subprocess, time
from pathlib import Path
import requests

STYLE = ('Original cinematic 2D anime short, detailed hand-painted backgrounds, finely drawn expressive adult characters, '
         'traditional cel shading, fluid character animation, restrained atmospheric lighting, sophisticated composition, '
         'rainy mountain railway at blue hour, deep indigo and warm amber palette. No existing franchise characters. '
         'No captions, subtitles, logos, watermarks, title cards or text. Full frame 16:9. ')
CHARACTER = ('Mira is an adult woman courier, age 25, with short dark blue bob hair, amber eyes, a mustard-yellow raincoat, '
             'a burgundy scarf, dark trousers and brown boots; she carries one small brass lantern with amber light. ')
SHOTS = [
 ('arrival', 'Wide tracking shot: '+CHARACTER+'She runs along a wet deserted station platform toward a wooden signal house. Rain ripples in puddles, her scarf streams behind her, mountain clouds drift, lantern light reflects on wet wood. She slows and looks up. No talking.'),
 ('promise', 'Medium close-up: '+CHARACTER+'She stops beneath the shelter, raises the lantern and looks toward an older station keeper offscreen. Her determined face softens. Camera gently pushes in. Mouth closed, no talking, rain runs from the roof behind her.'),
 ('keeper', 'Medium shot of an adult male station keeper aged 60, silver hair, neatly trimmed beard, navy railway uniform and round glasses, standing beneath the timber station shelter. He listens, turns toward the distant tracks, and slowly reaches for a brass warning bell cord. Rainy indigo mountains behind him. No talking.'),
 ('bell', 'Close cinematic insert shot: the gloved hand of an older station keeper pulls a rope and a large old brass railway warning bell swings three times under a wooden station roof. Raindrops tremble and fall. A rack focus reveals the distant misty tracks. No talking.'),
 ('signal', 'Low angle tracking shot: '+CHARACTER+'She climbs three wooden steps and lifts her lantern onto an empty signal hook. The lantern ignites an amber reflection across her face, her scarf ripples. A rectangular blank dark station sign hangs on the lower right of the frame. No talking.'),
 ('home', 'Wide cinematic finale: '+CHARACTER+'She stands beside the older silver-haired station keeper in navy uniform under the station roof, seen from behind. A beautiful small train emerges from mountain mist and glides into the platform, amber windows reflected in wet ground. The lantern glows in the foreground. Slow camera pull back, hopeful atmosphere. No talking.'),
 ('harbor', 'A separate original anime scene: an adult woman lighthouse keeper with long auburn braided hair, teal coat and white scarf stands inside a lighthouse at sunrise. She turns a brass lens toward a distant small fishing boat. The beam sweeps through mist, gulls move across the sky. Detailed expressive animation, warm coral and teal palette. No talking.'),
 ('harbor_signal', 'A separate original anime scene: close-up of an adult auburn-braided lighthouse keeper in a teal coat and white scarf opening a brass signal shutter twice. Sunlight flashes out toward a small boat in a turquoise harbor. Camera shifts to her relieved face. Natural flowing animation. No talking.'),
]

def main():
 p=argparse.ArgumentParser();p.add_argument('--gcloud',required=True);p.add_argument('--shots',default='0');p.add_argument('--project',default='project-ca8af2fe-5aff-496a-bd8');a=p.parse_args()
 out=Path('runtime/lantern');out.mkdir(parents=True,exist_ok=True)
 token=subprocess.run([a.gcloud,'auth','print-access-token'],capture_output=True,text=True,check=True).stdout.strip()
 session=requests.Session();session.headers.update(Authorization='Bearer '+token)
 model='veo-3.1-fast-generate-001'
 endpoint=f'https://us-central1-aiplatform.googleapis.com/v1/projects/{a.project}/locations/us-central1/publishers/google/models/{model}'
 for i in map(int,a.shots.split(',')):
  name,action=SHOTS[i];target=out/(name+'.mp4');state=out/(name+'-operation.json')
  if target.exists():print(name+': cached',flush=True);continue
  prompt=STYLE+action
  (out/(name+'-prompt.txt')).write_text(prompt,encoding='utf-8')
  if state.exists():operation=json.loads(state.read_text())['name']
  else:
   r=session.post(endpoint+':predictLongRunning',json={'instances':[{'prompt':prompt}], 'parameters':{'sampleCount':1,'durationSeconds':8,'aspectRatio':'16:9','resolution':'1080p','generateAudio':False,'personGeneration':'allow_adult'}},timeout=90)
   if not r.ok:raise RuntimeError(f'Veo request {r.status_code}: {r.text[:1200]}')
   data=r.json();state.write_text(json.dumps(data),encoding='utf-8');operation=data['name']
  print(name+': generating',flush=True)
  for _ in range(80):
   r=session.post(endpoint+':fetchPredictOperation',json={'operationName':operation},timeout=90);r.raise_for_status();data=r.json()
   if data.get('done'):
    if data.get('error'):raise RuntimeError(str(data['error']))
    videos=data.get('response',{}).get('videos',[])
    if not videos:raise RuntimeError('No video returned: '+json.dumps(data)[:1000])
    item=videos[0]
    if 'bytesBase64Encoded' in item:target.write_bytes(base64.b64decode(item['bytesBase64Encoded']))
    elif 'gcsUri' in item:
     subprocess.run([a.gcloud,'storage','cp',item['gcsUri'],str(target)],check=True)
    else:raise RuntimeError('Unsupported video response keys: '+str(item.keys()))
    print(name+': complete '+str(target.stat().st_size)+' bytes',flush=True);break
   time.sleep(15)
  else:raise RuntimeError('Veo still running; rerun to resume saved operation')

if __name__=='__main__':main()
