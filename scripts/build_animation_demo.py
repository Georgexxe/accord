"""Build explicitly labelled known-answer tracks for two original animated scenes."""
import json
from pathlib import Path

def cue(id,start,end,text,box=None):
 d=dict(id=id,start=start,end=end,text=text)
 if box:d['box']=box
 return d

def build():
 for scene,title,length in [('lantern','The Last Lantern',48),('harbor','Harbor Lights',16)]:
  root=Path('demo')/scene;root.mkdir(parents=True,exist_ok=True)
  records=json.loads((Path('runtime/lantern')/(scene+'-dialogue.json')).read_text())
  script=title+' — original fictional animated scene. All timing is in seconds.\n'
  for r in records:script+=f"{r['start']:.3f}–{r['end']:.3f}: spoken English dialogue: {r['text']}\n"
  if scene=='lantern':
   script+='0–8: A courier carrying a lantern runs through a rainy mountain station. Her name is not spoken or shown before 33 seconds.\n25–28.8: A warning bell rings three times. This is the signal for the courier to carry the lantern to the platform.\n32–40: A visible wayfinding sign reads PLATFORM 7, in normalized frame region x=.640625, y=.7, width=.26953125, height=.11944444.\n40–48: The train arrives; the lantern has guided it home.\n'
   spec={'invariants':[{'id':'passengers','kind':'NUMBER','description':'Fourteen passengers are waiting.','start':records[0]['start'],'end':records[0]['end'],'value':'14','evidence':records[0]['text']},{'id':'name','kind':'REVEAL','description':'The courier first introduces herself as Mira at 33 seconds.','start':33,'end':records[2]['end'],'value':'Mira','evidence':records[2]['text']},{'id':'bell','kind':'SOUND','description':'The warning bell tells the courier when to go.','start':25,'end':28.8,'value':'bell','aliases':['chime'],'evidence':'Three audible bell strikes at 25, 26 and 27 seconds.'},{'id':'speech','kind':'DIALOGUE','description':'The courier speaks about the waiting passengers.','start':9,'end':records[0]['end'],'value':'dialogue','evidence':records[0]['text']},{'id':'platform-sign','kind':'CLUE','description':'Platform 7 is the destination.','start':32,'end':40,'value':'PLATFORM 7','box':{'x':.640625,'y':.7,'width':.26953125,'height':.11944444},'evidence':'The composed wayfinding sign is visible throughout the signal shot.'}], 'notes':'Human-reviewed known-answer reference for this original film. The extraction output is retained separately; this reference is not presented as unedited model output.'}
   es=[cue('s1',9,15,'Hay 14 pasajeros esperando.'),cue('s2',17,23,'Lleva la luz al andén 7.'),cue('s3',33,39,'Me llamo Mira. Ya vamos.',{'x':.15,'y':.1,'width':.7,'height':.12}),cue('s4',42,46,'Ahora pueden vernos.')]
   sdh=[cue('c1',1,4,'[Footsteps in rain]'),cue('c2',9,15,'14 passengers are still waiting.'),cue('c3',17,23,'Take the lantern to platform 7.'),cue('bell',25,28.8,'[Bell rings three times]'),cue('c4',33,39,'My name is Mira.'),cue('c5',42,46,'They can see us now.')]
   dub=[cue('d1',2,5,'The courier arrives.'),cue('d2',9,15,'14 passengers are still waiting.'),cue('d3',33,39,'My name is Mira.')]
   ad=[cue('a1',4,7,'A courier shelters a lantern from the rain.')]
  else:
   script+='0–8: A keeper turns the lighthouse lens toward a small fishing boat.\n8–9.8: Two clear signal chimes sound as the shutter opens.\nNo identity reveal or readable on-screen text occurs.\n'
   spec={'invariants':[{'id':'flashes','kind':'NUMBER','description':'Two flashes are the signal for home.','start':2,'end':records[0]['end'],'value':'2','evidence':records[0]['text']},{'id':'speech','kind':'DIALOGUE','description':'The keeper describes the signal.','start':2,'end':records[0]['end'],'value':'dialogue','evidence':records[0]['text']},{'id':'chimes','kind':'SOUND','description':'Two signal chimes accompany the shutter.','start':8,'end':9.8,'value':'chime','aliases':['bell'],'evidence':'Two composed chimes at 8 and 8.8 seconds.'}], 'notes':'Independent second scene, human-reviewed known-answer reference.'}
   es=[cue('s1',2,6,'2 destellos. La señal de regreso.'),cue('s2',10,15,'Mantén la luz hasta que lleguen.')]
   sdh=[cue('c1',2,6,'2 flashes. The signal for home.'),cue('bell',8,9.8,'[Two chimes]'),cue('c2',10,15,'Keep the light steady.')]
   dub=[cue('d1',2,6,'2 flashes. The signal for home.')]
   ad=[cue('a1',.1,1.9,'A light sweeps the harbor.')]
  clean=[{'name':'Spanish subtitles','kind':'SUBTITLE','locale':'es','cues':es},{'name':'Accessible captions','kind':'SDH','locale':'en','cues':sdh},{'name':'Dub transcript','kind':'DUB','locale':'en','cues':dub},{'name':'Audio description','kind':'AD','locale':'en','cues':ad}]
  defective=json.loads(json.dumps(clean))
  defective[0]['cues'][0]['text']=defective[0]['cues'][0]['text'].replace('14','4') if scene=='lantern' else defective[0]['cues'][0]['text'].replace('2','3')
  defective[3]['cues'][0]['start']=9 if scene=='lantern' else 2
  defective[3]['cues'][0]['end']=12 if scene=='lantern' else 4
  if scene=='lantern':
   defective[1]['cues']=[c for c in defective[1]['cues'] if c['id']!='bell']
   defective[2]['cues'][0]['text']='Mira arrives.'
   defective[0]['cues'][2]['box']={'x':.55,'y':.7,'width':.4,'height':.15}
  for name,data in [('clean-tracks.json',clean),('test-tracks.json',defective),('reviewed-story-notes.json',spec)]: (root/name).write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')
  (root/'script.txt').write_text(script,encoding='utf-8')
  (root/'README.md').write_text(f'# {title}\n\nOriginal AI-assisted animated scene created for Accord using Google Veo and Google Cloud Text-to-Speech, with original script, editing and synthesized sound. No third-party film excerpt.\n\n`master.mp4` is the original {length}-second film. `clean-tracks.json` contains the known-answer controls. `test-tracks.json` deliberately introduces review defects; these are testing inputs, not errors in a real released translation. `reviewed-story-notes.json` is the explicit human-reviewed reference, not unedited extraction output.\n',encoding='utf-8')
 print('Built two independent known-answer packages')
if __name__=='__main__':build()
