from pathlib import Path
import subprocess,shutil
root=Path.cwd();backup=root/'runtime'/'branding'/'master-before-accord.mp4';backup.parent.mkdir(exist_ok=True)
if not backup.exists():shutil.copy2(root/'demo/master.mp4',backup)
filt="drawbox=x=56:y=75:w=710:h=28:color=0x0c1218:t=fill,drawtext=fontfile='C\\:/Windows/Fonts/arial.ttf':text='Original scene for Accord':x=60:y=79:fontsize=15:fontcolor=0x6d8c92"
r=subprocess.run(['ffmpeg','-y','-i',str(backup),'-vf',filt,'-c:v','libx264','-preset','fast','-crf','23','-c:a','copy','-movflags','+faststart',str(root/'demo/master.mp4')],capture_output=True,text=True)
if r.returncode:raise RuntimeError(r.stderr[-2000:])
print('Demo film rebranded; original audio and story content retained.')
