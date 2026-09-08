from pathlib import Path
import subprocess,json,numpy as np
out=Path('runtime/demo-capture');report=[]
for name in ['01-sources','03-findings','05-proposal']:
 p=out/(name+'-screen.mp4')
 raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(p),'-vf','scale=144:100,fps=24','-f','rawvideo','-pix_fmt','rgb24','-'])
 frames=np.frombuffer(raw,dtype=np.uint8).reshape(-1,100,144,3)
 gray=((frames.min(axis=3)>118)&(frames.max(axis=3)<142)&((frames.max(axis=3).astype(int)-frames.min(axis=3))<8)).mean(axis=(1,2))
 good=gray<.15;best=(0,0);start=0
 for i,ok in enumerate(good.tolist()+[False]):
  if not ok:
   if i-start>best[1]-best[0]:best=(start,i)
   start=i+1
 a,b=best;a+=2;b-=2;b=min(b,a+48)
 assert b-a>=12,(name,best)
 subprocess.run(['ffmpeg','-y','-v','error','-ss',str(a/24),'-i',str(p),'-t',str((b-a)/24),'-an','-c:v','libx264','-preset','fast','-threads','2','-crf','20',str(out/(name+'-clean-screen.mp4'))],check=True)
 report.append({'name':name,'start':a/24,'end':b/24,'rejectedFrames':int((~good).sum())})
(out/'clean-capture-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
