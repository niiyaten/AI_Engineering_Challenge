from __future__ import annotations
import argparse,csv,json,re,unicodedata
from pathlib import Path

def norm(s):return re.sub(r'[\s、,。．・「」『』（）()：:／/円%％_-]+','',unicodedata.normalize('NFKC',str(s))).lower()
def main():
 p=argparse.ArgumentParser();p.add_argument('--answers',required=True);p.add_argument('--expected',required=True);p.add_argument('--output',required=True);a=p.parse_args()
 got={int(r['index']):r for r in csv.DictReader(Path(a.answers).open(encoding='utf-8-sig',newline=''))};exp={int(r['index']):r['expected_answer'] for r in csv.DictReader(Path(a.expected).open(encoding='utf-8-sig',newline=''))};rows=[]
 for i,e in exp.items():
  g=got.get(i,{}).get('answer','わからない');ng,ne=norm(g),norm(e);status='exact' if g==e else ('semantic_match' if ng==ne or (len(ng)>3 and (ng in ne or ne in ng)) else ('abstain' if g=='わからない' else 'mismatch'))
  rows.append({'index':i,'status':status,'answer':g,'expected':e})
 summary={'count':len(rows),'exact':sum(r['status']=='exact' for r in rows),'semantic_match':sum(r['status']=='semantic_match' for r in rows),'matched':sum(r['status'] in {'exact','semantic_match'} for r in rows),'mismatch':sum(r['status']=='mismatch' for r in rows),'abstain':sum(r['status']=='abstain' for r in rows),'rows':rows}
 Path(a.output).write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in summary.items() if k!='rows'},ensure_ascii=False))
if __name__=='__main__':main()
