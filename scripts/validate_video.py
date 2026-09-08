"""Check every decoded frame for the gray padding produced by viewport-resize captures."""
import argparse,json,subprocess
import numpy as np

def validate(path):
 command=['ffmpeg','-v','error','-i',str(path),'-vf','scale=144:100','-f','rawvideo','-pix_fmt','rgb24','-']
 proc=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 count=0;bad=[];maximum=0.
 while True:
  data=proc.stdout.read(144*100*3)
  if not data:break
  if len(data)!=144*100*3:raise ValueError('Incomplete decoded frame')
  frame=np.frombuffer(data,dtype=np.uint8).reshape(100,144,3)
  low=frame.min(axis=2);high=frame.max(axis=2)
  fraction=float(((low>118)&(high<142)&((high.astype(int)-low)<8)).mean())
  maximum=max(maximum,fraction)
  if fraction>.15:bad.append(count)
  count+=1
 errors=proc.stderr.read();code=proc.wait()
 report={'framesChecked':count,'distortedFrames':len(bad),'firstDistortedFrame':bad[0] if bad else None,'maxGrayFraction':round(maximum,5),'decodeErrors':bool(errors),'exitCode':code}
 print(json.dumps(report))
 if code or errors or not count or bad:raise SystemExit(1)
 return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('video');validate(p.parse_args().video)
