import json, os
T='/home/claude/partner/wk/tapes'
cr={}; cr.update({'img/'+k:v for k,v in json.load(open('img/credits.json')).items()}); cr.update({'img2/'+k:v for k,v in json.load(open('img2/credits.json')).items()})
def c(p):
    v=cr.get(p); 
    return f"{v['artist']} / {v['src']} ({v['license']})" if v else None
V={
'A':dict(name='JAL1628',tag='REAL FAA TRANSCRIPT  ·  VOICES RECREATED',tag_color=[25,70,150],fiction=False,
  cover=('img2/ajal_1.jpg','JAPAN AIR 1628:\nTHE UFO TAPE'),comment='COMMENT "UNKNOWN TO US" IF YOU\'D DEVIATE TOO',
  center=('img2/ajal_0.jpg','JAPAN AIR LINES 1628 · BOEING 747 CARGO','NOV. 17, 1986 · OVER ALASKA'),
  smalls=[('jal/memo.jpg','FAA MEMO, 1987',0.3),('jal/p22-02c.jpg','FAA RADAR REPLAY',0.5),('img2/acock_1.jpg','747 COCKPIT AT NIGHT',0.5),('img2/asky_0.jpg','NIGHT SKY',0.5)],
  extra_credit='FAA public record · plane: a JAL 747, not the actual one',
  cards=['THE CAPTAIN SAID\\NONE WAS TWICE\\NTHE SIZE OF AN\\NAIRCRAFT CARRIER','THE FAA\'S ANSWER:\\NA "SPLIT RADAR\\NRETURN" OF HIS\\NOWN PLANE'],intro='REAL FAA\\NTRANSCRIPT'),
'B':dict(name='LockedInside',cover=('img/f4.jpg','SHE LOCKED\nTHE DOOR'),comment='COMMENT "RACHEL" FOR PART 2',
  center=('img/f4.jpg','911 CALL · BIRCH HOLLOW ROAD','CALLER: RACHEL, 31'),
  smalls=[('img/f2.jpg','THE HOUSE',0.5),('img/f5.jpg','911',0.5),('img2/chall_1.jpg','UPSTAIRS HALL',0.5),('img/f1.jpg','DOWNSTAIRS',0.5)],
  cards=['OFFICERS ARRIVED\\N2 MINUTES LATER','THE BATHROOM DOOR\\NWAS STILL LOCKED','FROM THE INSIDE','RACHEL WAS GONE']),
'C':dict(name='BabyMonitor',cover=('img2/cmon_2.jpg','THE BABY\nMONITOR CALL'),comment='COMMENT "LILY" FOR PART 2',
  center=('img2/cmon_2.jpg','911 CALL · 22 CARVER LANE','CALLER: THE BABYSITTER'),
  smalls=[('img/f3.jpg','THE HOUSE',0.5),('img2/cmon_0.jpg','THE MONITOR',0.5),('img2/estair_1.jpg','THE STAIRS',0.5),('img2/chall_0.jpg','THE NURSERY HALL',0.5)],
  cards=['THE BABY WAS SAFE\\NIN HER CRIB','NO ONE ELSE WAS\\NIN THE HOUSE','BUT THE MONITOR\\NIN THE NURSERY...','WAS GONE']),
'D':dict(name='LastVoicemails',cover=('img2/dcar_2.jpg','HER LAST\nVOICEMAILS'),comment='COMMENT "CALL HER BACK" FOR PART 2',
  center=('img2/droad_0.jpg','4 VOICEMAILS · ROUTE 9','FROM: MEGAN  ·  TO: JESS'),
  smalls=[('img2/dphone_2.jpg','HER PHONE',0.5),('img2/dtruck_1.jpg','THE TRUCK',0.5),('img2/dcar_1.jpg','ROUTE 9',0.5),('img2/dphone_0.jpg','12:34 A.M.',0.5)],
  cards=['HER CAR WAS FOUND\\NTHE NEXT MORNING','DOORS STILL LOCKED.\\NKEYS IN THE IGNITION.','THE LAST MESSAGE\\NCAME FROM\\NHER PHONE']),
'E':dict(name='WelfareCheck',cover=('img2/estair_0.jpg','UNIT 12 NEVER\nCAME BACK'),comment='COMMENT "DON\'T UNCOVER THEM" FOR PART 2',
  center=('img2/epol_0.jpg','POLICE RADIO · UNIT 12','WELFARE CHECK · 61 HOLLIS ROAD'),
  smalls=[('img2/epol_1.jpg','UNIT 12',0.5),('img2/ekit_1.jpg','THE KITCHEN',0.5),('img2/estair_0.jpg','THE STAIRS',0.5),('img2/ekit_0.jpg','THE HOUSE',0.5)],
  cards=['BACKUP FOUND HIS\\NCRUISER RUNNING','EVERY MIRROR IN\\NTHE HOUSE...','WAS UNCOVERED','UNIT 12 WAS\\NNEVER FOUND']),
'F':dict(name='MileMarker113',cover=('img2/ffog_2.jpg','MILE\nMARKER 113'),comment='COMMENT "113" FOR PART 2',
  center=('img2/ftruck_1.jpg','CB RADIO · CHANNEL 19','I-80 WESTBOUND · MILE MARKER 113'),
  smalls=[('img2/ffog_0.jpg','I-80, 3 A.M.',0.5),('img2/ftruck_0.jpg','THE SHOULDER',0.5),('img2/ftruck_2.jpg','10 MILES BACK',0.5),('img2/ffog_2.jpg','MILE 113',0.5)],
  cards=['HIS TRUCK WAS FOUND\\NAT MILE MARKER 113','ENGINE RUNNING.\\NDOOR OPEN.','HIS CB WAS\\NSTILL KEYED...','SOMEONE\\NWAS HUMMING']),
'G':dict(name='InterviewRoom2',cover=('img2/gmine_0.jpg','HE SET THE\nTABLE FOR SIX'),comment='COMMENT "SEVEN" FOR PART 2',
  center=('img2/gtape_0.jpg','INTERVIEW ROOM 2 · TAPE 1','SUBJECT: JOHN DOE'),
  smalls=[('img2/gwood_0.jpg','PELL WOODS',0.5),('img2/gmine_0.jpg','THE HILLSIDE',0.5),('img2/gmine_2.jpg','THE DOOR',0.5),('img2/gwood_1.jpg','1 A.M.',0.5)],
  cards=['SEARCH TEAMS FOUND\\NA DOOR IN THE HILL','BEHIND IT:\\NSTAIRS GOING DOWN','DETECTIVE COLE\\NWENT IN FIRST','HE NEVER\\NCAME BACK UP']),
}
import re
REP=[('Nine one one','911'),('sixteen twenty-eight','1628'),('one-five-five-zero','1550'),('Four eighteen','418'),('twenty-two','22'),
 ('Eleven forty-two P.M.','11:42 P.M.'),('Eleven fifty-eight P.M.','11:58 P.M.'),('Twelve twenty-one A.M.','12:21 A.M.'),('Twelve thirty-four A.M.','12:34 A.M.'),
 ('Three fifteen A.M.','3:15 A.M.'),('Unit twelve','Unit 12'),('sixty-one','61'),('one-nine','1-9'),('on eighty','on 80'),('one-thirteen','113'),('at one A.M.','at 1 A.M.'),
 ('Copy, twelve','Copy, 12'),('Twelve,','12,'),('Twelve?','12?'),('Twelve, respond','12, respond'),('twelve','12')]
def disp(t):
    for a,b in REP: t=t.replace(a,b)
    return t
for L,v in V.items():
    s=json.load(open(f'el/{L}_subs.json')); end=s['end']
    for x in s['subs']: x['text']=disp(x['text'])
    cards=[]; t=end+0.3
    for txt in v['cards']:
        cards.append({'t0':round(t,2),'t1':round(t+2.6,2),'text':txt}); t+=2.75
    if v.get('intro'): cards.insert(0,{'t0':0,'t1':1.6,'text':v['intro']})
    total=round(t+0.3,1)
    credits=[c(p) for p,_,_ in v['smalls']]+[c(v['center'][0])]
    if v.get('extra_credit'): credits.insert(0,v['extra_credit'])
    seen=[]; [seen.append(x) for x in credits if x and x not in seen]
    sp={'id':'TAPES_'+v['name'],'header':'THE TAPES','total':total,'bed':0.45,'fiction':v.get('fiction',True),
        'cover':{'img':'tapes/'+v['cover'][0],'title':v['cover'][1],'focus_y':0.5},'comment':v['comment'],
        'center':{'img':'tapes/'+v['center'][0],'cap1':v['center'][1],'cap2':v['center'][2],'credit':'Photos: '+'  ·  '.join(seen)},
        'smalls':[{'img':'tapes/'+p,'label':lab,'focus':f} for p,lab,f in v['smalls']],
        'audio':f'{T}/el/{L}_dialogue.wav','subs':s['subs'],'cards':cards}
    if v.get('tag'): sp['tag']=v['tag']; sp['tag_color']=v['tag_color']
    os.makedirs(f'v_{L}',exist_ok=True); json.dump(sp,open(f'v_{L}/spec.json','w'),indent=1)
    print(L,total,len(seen),'credits')
