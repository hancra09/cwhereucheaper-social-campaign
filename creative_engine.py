"""Approved Heart/photographic creative style; standalone cloud authoring, no paid API."""
from pathlib import Path
import json,math,re,hashlib,subprocess,os,shutil
ROOT=Path(__file__).parent
ASSETS=ROOT/'creative-assets'
VERSION='creative-v2'
VOICE='af_heart'
W,H=1080,1920
NAVY='#071B36';BLUE='#326FD1';YELLOW='#FFE65A';CREAM='#F5F2E9';PINK='#F24C92';WHITE='#FFFFFF';GREY='#A8B7CC'
FONT_REGULAR=Path('/System/Library/Fonts/Supplemental/Arial.ttf')
FONT_BOLD=Path('/System/Library/Fonts/Supplemental/Arial Bold.ttf')
if not FONT_REGULAR.exists():
 FONT_REGULAR=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf');FONT_BOLD=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')

def font(n,bold=False):return ImageFont.truetype(str(FONT_BOLD if bold else FONT_REGULAR),n)
def text(im,s,xy,n=60,color=NAVY,bold=False,anchor=None):ImageDraw.Draw(im).text(xy,s,font=font(n,bold),fill=color,anchor=anchor)
def rr(im,box,fill,r=32,outline=None,width=1):ImageDraw.Draw(im).rounded_rectangle(box,r,fill=fill,outline=outline,width=width)
def ease(x):return 1-(1-max(0,min(1,x)))**3
def photo(im,asset,box,scale=1):
 x,y,w,h=box; ratio=min(w/asset.width,h/asset.height)*scale
 a=asset.resize((round(asset.width*ratio),round(asset.height*ratio)),Image.Resampling.LANCZOS)
 im.paste(a,(round(x+(w-a.width)/2),round(y+h-a.height)),a)
def header(im,dark=False):
 text(im,'CWHEREUCHEAPER', (88,105),38,WHITE if dark else NAVY,True)
 rr(im,(88,177,515,226),YELLOW,22);text(im,'ILLUSTRATIVE EXAMPLE',(301,202),25,NAVY,True,'mm')
 text(im,'Generic AI product visuals • not a retailer offer',(88,1714),27,GREY if dark else '#5B6470')
 # Safe-area progress cue reinforces pace without frame numbers.
def stamp(im,s,color=BLUE):
 rr(im,(90,1450,990,1580),color,36)
 n=47
 while ImageDraw.Draw(im).textbbox((0,0),s,font=font(n,True))[2]>830:n-=1
 text(im,s,(540,1515),n,WHITE,True,'mm')
def render(t):
 cuts=NARRATION["cuts"]
 k=next((i for i in range(6) if cuts[i]<=t<cuts[i+1]),5)
 u=(t-cuts[k])/(cuts[k+1]-cuts[k]);pop=ease(u*4)
 dark=k in [0,3,5];im=Image.new('RGB',(W,H),NAVY if dark else CREAM);d=ImageDraw.Draw(im)
 header(im,dark)
 if not CFG.get("comparison") and k<5:
  generic(im,k,u,pop,dark)
  progress(im,t,dark)
  return im
 if k==0:
  text(im,CFG['comparison']['hook'],(88,310),85,WHITE,True)
  text(im,'WINS?',(88,410),150,YELLOW,True)
  photo(im,pair,(120,620+35*(1-pop),840,720),1+0.015*math.sin(t*2))
  rr(im,(95,1280,495,1405),BLUE);rr(im,(585,1280,985,1405),PINK)
  text(im,CFG['comparison']['small_tag'],(295,1343),47,WHITE,True,'mm');text(im,CFG['comparison']['large_tag'],(785,1343),47,WHITE,True,'mm')
  stamp(im,'My trolley has trust issues.',BLUE)
 elif k==1:
  text(im,CFG['comparison']['small_heading'],(88,315),78,NAVY,True)
  text(im,CFG['comparison']['small_price'],(88,416),87,BLUE,True)
  photo(im,left,(125+40*(1-pop),590,370,680),1+0.02*u)
  rr(im,(500,625,990,1195),WHITE,38)
  text(im,CFG['comparison']['small_formula'],(745,725),47,NAVY,True,'mm')
  text(im,CFG['comparison']['small_unit'],(745,900),120,BLUE,True,'mm');text(im,CFG['comparison']['unit_label'],(745,1015),39,NAVY,True,'mm')
  stamp(im,'Compare equal quantities.')
 elif k==2:
  text(im,CFG['comparison']['large_heading'],(88,315),78,NAVY,True)
  text(im,CFG['comparison']['large_price'],(88,416),87,BLUE,True)
  photo(im,right,(115+30*(1-pop),575,400,720),1+0.018*u)
  rr(im,(525,625,990,1195),WHITE,38)
  text(im,CFG['comparison']['large_formula'],(758,725),47,NAVY,True,'mm')
  text(im,CFG['comparison']['large_unit'],(758,900),120,NAVY,True,'mm');text(im,CFG['comparison']['unit_label'],(758,1015),39,NAVY,True,'mm')
  stamp(im,'Same basis. Clear comparison.')
 elif k==3:
  text(im,CFG['comparison']['winner_heading'],(88,315),86,WHITE,True)
  text(im,CFG['comparison']['winner_line'],(88,420),88,YELLOW,True)
  rr(im,(88,600,512,1285),'#173B64',40,BLUE,4);rr(im,(568,600,992,1285),'#142B49')
  photo(im,left,(130,625,320,430));photo(im,right,(620,625,320,430))
  text(im,CFG['comparison']['small_result'],(300,1160),62,YELLOW,True,'mm');text(im,CFG['comparison']['large_result'],(780,1160),62,WHITE,True,'mm')
  # Difference grows in front of the eye instead of becoming a static text slide.
  rr(im,(100,1340,100+round(880*max(.03,pop)),1405),YELLOW,20)
  stamp(im,CFG['comparison']['punchline'])
 elif k==4:
  text(im,'ONE LAST',(88,315),94,NAVY,True)
  text(im,'CHECK.',(88,420),145,BLUE,True)
  for i,(a,b) in enumerate([('SAME BRAND','Check the maker.'),('SAME VARIANT','Check the product type.'),('RIGHT UNIT','Compare per litre or per kg.')]):
   y=650+i*230;rr(im,(88,y,992,y+190),WHITE)
   rr(im,(125,y+52,210,y+137),BLUE,22)
   ImageDraw.Draw(im).line([(145,y+95),(161,y+112),(190,y+77)],fill=WHITE,width=9,joint='curve')
   text(im,a,(250,y+43),48,NAVY,True);text(im,b,(250,y+112),36,'#526176')
  stamp(im,'Your wallet deserves fewer plot twists.')
 else:
  text(im,'YOUR NEXT SHOP.',(88,315),88,WHITE,True)
  text(im,'CLEARER CHOICES.',(88,425),79,YELLOW,True)
  y=650-round(24*pop);rr(im,(62,y-20,1018,y+568),BLUE,32)
  shot=web.resize((920,518),Image.Resampling.LANCZOS);im.paste(shot,(80,y))
  if CFG.get('response_request'):
   text(im,'Website image captured 12 Nov 2026',(540,1205),31,WHITE,False,'mm')
  rr(im,(100,1260,980,1380),YELLOW,60)
  text(im,'Compare before checkout',(540,1320),52,NAVY,True,'mm')
  text(im,'cwhereucheaper.co.za',(540,1490),61,WHITE,True,'mm')
  text(im,'Start your next price check.',(540,1585),42,GREY,False,'mm')
 progress(im,t,dark)
 return im


def progress(im,t,dark):
 d=ImageDraw.Draw(im);d.rectangle((88,1630,992,1638),fill='#3B4C64' if dark else '#CFD7E1');d.rectangle((88,1630,88+int(904*t/TOTAL),1638),fill=YELLOW if dark else BLUE)


def wrapped(im,value,xy,width,max_height,size=70,color=NAVY,bold=True):
 draw=ImageDraw.Draw(im)
 while size>=30:
  lines=[];line=''
  for word in value.split():
   candidate=(line+' '+word).strip()
   if draw.textbbox((0,0),candidate,font=font(size,bold))[2]>width and line:
    lines.append(line);line=word
   else:line=candidate
  if line:lines.append(line)
  if len(lines)*int(size*1.2)<=max_height:break
  size-=2
 if len(lines)*int(size*1.2)>max_height:raise ValueError('Text cannot fit safely')
 for j,line in enumerate(lines):text(im,line,(xy[0],xy[1]+j*int(size*1.2)),size,color,bold)


def generic(im,k,u,pop,dark):
 color=WHITE if dark else NAVY
 if k==0:
  wrapped(im,CFG['title'].upper(),(88,305),904,325,84,WHITE)
  photo(im,pair,(110,650+25*(1-pop),860,730),1+.018*u)
  stamp(im,CFG['hook_card'])
 elif k in (1,2,3):
  labels=['THE SHOPPING CHECK','LOOK A LITTLE CLOSER','BEFORE YOU CHECK OUT']
  wrapped(im,labels[k-1],(88,300),904,145,76,color)
  rr(im,(88,510,992,970),'#173B64' if dark else WHITE,38)
  wrapped(im,CFG['facts'][k-1],(125,550),830,365,65,color)
  photo(im,pair,(235 if k%2 else 110,1000,720,410),1+.025*u)
  stamp(im,CFG['fact_cards'][k-1])
 else:
  text(im,'ONE LAST',(88,315),94,NAVY,True);text(im,'CHECK.',(88,420),145,BLUE,True)
  for i,(a,b) in enumerate(CFG['checks']):
   y=650+i*230;rr(im,(88,y,992,y+190),WHITE)
   rr(im,(125,y+52,210,y+137),BLUE,22)
   ImageDraw.Draw(im).line([(145,y+95),(161,y+112),(190,y+77)],fill=WHITE,width=9,joint='curve')
   text(im,a,(250,y+43),44,NAVY,True);wrapped(im,b,(250,y+108),690,65,34,'#526176',False)
  stamp(im,CFG['wrap_card'])


def number_words(n):
 units=['zero','one','two','three','four','five','six','seven','eight','nine','ten','eleven','twelve','thirteen','fourteen','fifteen','sixteen','seventeen','eighteen','nineteen']
 tens=['','','twenty','thirty','forty','fifty','sixty','seventy','eighty','ninety']
 n=int(n)
 if n<20:return units[n]
 if n<100:return tens[n//10]+('-'+units[n%10] if n%10 else '')
 if n<1000:return units[n//100]+' hundred'+(' and '+number_words(n%100) if n%100 else '')
 if n<1000000:return number_words(n//1000)+' thousand'+(' '+number_words(n%1000) if n%1000 else '')
 raise ValueError('Currency outside reviewed narration range')


def spoken(text):
 def currency(m):
  whole,_,cents=m[1].partition('.')
  result=number_words(whole)+' rand'
  if cents and int(cents):result+=' and '+number_words(cents.ljust(2,'0'))+' cents'
  return result
 return re.sub(r'\bR(\d+(?:\.\d{1,2})?)\b',currency,text)


def theme(item):
 t=(item['title']+' '+item['script']).lower()
 if 'checkout questions' in item['title'].lower():return 'check'
 if any(x in t for x in ('countdown','urgent','timer')):return 'countdown'
 if any(x in t for x in ('bulk','expiry','use-by','waste','storage')):return 'bulk'
 if any(x in t for x in ('delivery','collection','travel','fees')):return 'delivery'
 if any(x in t for x in ('gram','litre','bottle','unit price','pack size')):return 'unit'
 if any(x in t for x in ('basket','trolley')):return 'basket'
 return 'check'


def lesson(item,tag):
 core=re.sub(r'\s*Start your next price check at Cwhereucheaper\.co\.za\.?\s*$','',item['script'],flags=re.I).strip()
 sentences=re.split(r'(?<=[.!?])\s+',core)
 if len(sentences)<3:
  facts=sentences+['Check the final cost before deciding.']*(3-len(sentences))
 else:
  choices=[(abs(len(' '.join(sentences[:i]).split())-len(' '.join(sentences[i:j]).split()))+abs(len(' '.join(sentences[j:]).split())-len(core.split())/3),i,j) for i in range(1,len(sentences)-1) for j in range(i+1,len(sentences))]
  _,i,j=min(choices);facts=[' '.join(sentences[:i]),' '.join(sentences[i:j]),' '.join(sentences[j:])]
 kind=theme(item);selector=int(hashlib.sha256(tag.encode()).hexdigest()[:8],16)
 hooks={
  'unit':['Bigger pack, better deal? My trolley has trust issues.','Shopping maths. The bigger pack is feeling very confident.'],
  'countdown':["That timer doesn't know your shopping list.","A countdown is not your household's financial adviser."],
  'bulk':['Bulk buying? My fridge would like a word.','A bargain is less exciting when the cupboard objects.'],
  'delivery':['A cheap price can have expensive friends.','Delivery fees have entered the chat.'],
  'basket':["One cheap item can't rescue the whole trolley.",'Your trolley has opinions. Your budget has concerns.'],
  'check':["Your basket doesn't get to make all the decisions.",'A quick shopping check. Your wallet deserves a break.']}
 wraps=['Your wallet deserves fewer plot twists.','Give your calculator the final say.','A tiny pause can save a big facepalm.','Your future self might appreciate this one.']
 hook=hooks[kind][selector%len(hooks[kind])];wrap=wraps[(selector//7)%len(wraps)]
 checks={
  'bulk':[('DO I NEED IT?','Choose a useful quantity.'),('CAN I STORE IT?','Check available space.'),('WILL I USE IT?','Check the use-by date.')],
  'countdown':[('ON MY LIST?','Start with your actual needs.'),('RIGHT PRODUCT?','Check the exact item.'),('FINAL COST?','Check the full amount.')],
  'delivery':[('EXACT ITEM','Match the product.'),('DELIVERY + FEES','Add the checkout charges.'),('GETTING IT HOME','Include relevant travel costs.')],
  'unit':[('SAME PRODUCT','Check brand and variant.'),('SAME UNIT','Compare equivalent quantities.'),('FINAL COST','Check the full amount.')],
 }
 cfg={'response_request':bool(item.get('response_request_id')),'title':item['title'],'core':core,'facts':facts,'hook_card':hook,'wrap_card':wrap,'checks':checks.get(kind,[('RIGHT ITEM','Match your household needs.'),('FINAL TOTAL','Include delivery and fees.'),('USEFUL AMOUNT','Avoid buying waste.')]),'fact_cards':['Check the detail.','Compare on the same basis.','Decide from the full picture.'],'asset':'bottles.png' if re.search('millilitre|litre|bottle',core,re.I) else 'pouches.png' if kind=='unit' else 'basket.png','comparison':None}
 cfg['segments']=[hook,*facts,wrap,'Compare before checkout. Your wallet can thank you later.']
 if item['title']=='A small bottle can have a smaller unit price':
  cfg['segments']=["Bigger bottle, better deal? My trolley has trust issues.","In this example, five hundred millilitres for twenty rand is forty rand per litre.","The one-litre bottle? Forty-five rand per litre.","Small bottle, smaller unit price. Big bottle... big confidence.","Match the exact product first. Your wallet deserves fewer plot twists.","Compare before checkout. Your wallet can thank you later."]
  cfg['comparison']={'hook':'WHICH BOTTLE','small_heading':'SMALL BOTTLE','large_heading':'LARGE BOTTLE','small_price':'500 ml = R20','large_price':'1 litre = R45','small_formula':'R20 ÷ 0.5 L','large_formula':'R45 ÷ 1 L','small_unit':'R40','large_unit':'R45','unit_label':'PER LITRE','winner_heading':'THE SMALLER','winner_line':'BOTTLE WINS.','small_result':'R40 / L','large_result':'R45 / L','small_tag':'500 ml  |  R20','large_tag':'1 litre  |  R45','punchline':'Big bottle. Big confidence.'}
 if item['title']=='Price per hundred grams made simple':
  cfg['segments']=["Bigger pack, better deal? My trolley has trust issues.","Here's an example. Thirty rand for five hundred grams is six rand per hundred grams.","Forty-two rand for six hundred grams? Seven rand per hundred grams.","The smaller pack wins this round. Big pack... big confidence.","Match the exact product first. Your wallet deserves fewer plot twists.","Compare before checkout. Your wallet can thank you later."]
  cfg['comparison']={'hook':'WHICH PACK','small_heading':'SMALL PACK','large_heading':'LARGE PACK','small_price':'500 g = R30','large_price':'600 g = R42','small_formula':'R30 ÷ 5','large_formula':'R42 ÷ 6','small_unit':'R6','large_unit':'R7','unit_label':'PER 100 GRAMS','winner_heading':'THE SMALLER','winner_line':'PACK WINS.','small_result':'R6 / 100 g','large_result':'R7 / 100 g','small_tag':'500 g  |  R30','large_tag':'600 g  |  R42','punchline':'Big pack. Big confidence.'}
 return cfg


def model_assets():
 root=Path(os.environ.get('CWUC_VOICE_ASSETS',str(Path.home()/'.cache/cwuc-voice-assets')));root.mkdir(parents=True,exist_ok=True)
 missing=[n for n in ('kokoro-v1.0.onnx','voices-v1.0.bin') if not(root/n).is_file()]
 if missing:
  cmd=['gh','release','download','model-files-v1.1','--repo','thewh1teagle/kokoro-onnx','--dir',str(root)]
  for n in missing:cmd+=['--pattern',n]
  subprocess.run(cmd,check=True,timeout=180)
 return root


def narrate(cfg,work):
 import numpy as np,soundfile as sf,onnxruntime as ort
 from kokoro_onnx import Kokoro
 assets=model_assets();options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
 session=ort.InferenceSession(str(assets/'kokoro-v1.0.onnx'),sess_options=options,providers=['CPUExecutionProvider'])
 engine=Kokoro.from_session(session,str(assets/'voices-v1.0.bin'))
 parts=[];cuts=[0.0];rate=24000
 for segment in cfg['segments']:
  audio,rate=engine.create(spoken(segment),voice=VOICE,lang='en-us',speed=.97,sentence_pause=.29,clause_pause=.12)
  audio=np.concatenate([np.zeros(int(rate*.12),dtype=np.float32),audio,np.zeros(int(rate*.22),dtype=np.float32)])
  parts.append(audio);cuts.append(cuts[-1]+len(audio)/rate)
 if not 18<=cuts[-1]<=42:raise ValueError('Natural narration falls outside 18–42 seconds; manual script review required')
 audio=np.concatenate(parts);peak=float(np.max(np.abs(audio)))
 if not .01<peak<3:raise ValueError('Invalid narration signal')
 audio*=.88/peak;sf.write(work/'narration.wav',audio,rate,subtype='PCM_16')
 return {'voice':VOICE,'speed':.97,'cuts':cuts,'duration':cuts[-1],'script_segments':cfg['segments'],'spoken_segments':[spoken(x) for x in cfg['segments']],'audio_peak':.88}


def render_video(item,tag,destination,work):
 global Image,ImageDraw,ImageFont,CFG,NARRATION,TOTAL,pair,left,right,web
 from PIL import Image,ImageDraw,ImageFont
 work=Path(work);work.mkdir(parents=True,exist_ok=True)
 CFG=lesson(item,tag);NARRATION=narrate(CFG,work);TOTAL=NARRATION['duration']
 pair=Image.open(ASSETS/CFG['asset']).convert('RGBA');split={'pouches.png':540,'bottles.png':515}.get(CFG['asset'],pair.width//2);left=pair.crop((0,0,split,pair.height));right=pair.crop((split,0,pair.width,pair.height));web=Image.open(ASSETS/'website.png').convert('RGB')
 ff=shutil.which('ffmpeg')
 if not ff:
  import imageio_ffmpeg
  ff=imageio_ffmpeg.get_ffmpeg_exe()
 cmd=[ff,'-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s','1080x1920','-r','30','-i','-','-i',str(work/'narration.wav'),'-map','0:v','-map','1:a:0','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-threads','2','-c:a','aac','-b:a','160k','-t',str(TOTAL),'-movflags','+faststart',str(destination)]
 proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
 for old in work.glob('preview-*.jpg'):old.unlink()
 preview_frames={round((NARRATION['cuts'][i]+NARRATION['cuts'][i+1])/2*30) for i in range(6)}
 try:
  for i in range(round(TOTAL*30)):
   im=render(i/30)
   if i in preview_frames:im.save(work/f'preview-{i:04d}.jpg',quality=92)
   proc.stdin.write(im.tobytes())
 finally:proc.stdin.close()
 if proc.wait():raise RuntimeError('Creative video encoding failed')
 subprocess.run([ff,'-v','error','-i',str(destination),'-f','null','-'],check=True,timeout=90)
 sheet=Image.new('RGB',(810,960))
 for i,f in enumerate(sorted(work.glob('preview-*.jpg'))):sheet.paste(Image.open(f).resize((270,480)),((i%3)*270,(i//3)*480))
 sheet.save(work/'contact-sheet.jpg',quality=94)
 meta={**NARRATION,'creative_version':VERSION,'visual_mode':'product photography, animated comparisons and website demonstration','visual_asset':CFG['asset'],'width':1080,'height':1920,'fps':30,'bytes':Path(destination).stat().st_size,'sha256':hashlib.sha256(Path(destination).read_bytes()).hexdigest(),'site_capture_date':'2026-11-12','ai_visual_disclosure':True,'warnings':[]}
 (work/'creative-result.json').write_text(json.dumps(meta,indent=2)+'\n');return meta


if __name__=='__main__':
 import sys
 data=json.loads(Path(sys.argv[1]).read_text());print(json.dumps(render_video(data['content'],data['slot'],Path(sys.argv[2]),Path(sys.argv[3])),indent=2))
