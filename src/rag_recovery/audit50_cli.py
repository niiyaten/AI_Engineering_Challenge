from __future__ import annotations
import argparse,csv,json,os,signal,subprocess,sys,time
from pathlib import Path
from .archive import extract_zip_safely
from .office_crypto import prepare_office_tree
from .pathing import locate_content_root

def readq(p):
 rows=list(csv.DictReader(Path(p).open(encoding='utf-8-sig',newline='')));out=[]
 for r in rows:out.append({'index':int(r['index']),'question':r['question']})
 if len(out)!=50 or len({r['index'] for r in out})!=50:raise ValueError('questions must contain 50 unique rows')
 return out

def worker(root,row,outdir,timeout):
 out=outdir/f"{row['index']:03d}.json";err=outdir/f"{row['index']:03d}.stderr.log";outdir.mkdir(parents=True,exist_ok=True)
 for x in (out,out.with_suffix('.json.tmp')):
  if x.exists():x.unlink()
 cmd=[sys.executable,'-m','rag_recovery.audit50_worker','--prepared-root',str(root),'--index',str(row['index']),'--question',row['question'],'--output-json',str(out)]
 with err.open('w',encoding='utf-8') as ef:
  proc=subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=ef,start_new_session=True)
  deadline=time.monotonic()+timeout
  while time.monotonic()<deadline:
   if out.exists() and out.stat().st_size:
    d=json.loads(out.read_text(encoding='utf-8'))
    if proc.poll() is None:
     try:os.killpg(proc.pid,signal.SIGKILL)
     except ProcessLookupError:pass
    return d
   if proc.poll() is not None:
    raise RuntimeError(f"worker {row['index']} failed rc={proc.returncode}: {err.read_text(encoding='utf-8',errors='replace')[-2000:]}")
   time.sleep(.1)
  try:os.killpg(proc.pid,signal.SIGKILL)
  except ProcessLookupError:pass
  return {'index':row['index'],'question':row['question'],'answered':False,'answer':'わからない','confidence':0.0,'method':'timeout','reason':f'timeout_{timeout}s','route':'timeout','evidence':[],'elapsed_seconds':timeout,'diagnostics':{},'trace':{}}

def main():
 p=argparse.ArgumentParser()
 src=p.add_mutually_exclusive_group(required=True)
 src.add_argument('--prepared-root')
 src.add_argument('--share-zip')
 p.add_argument('--workspace',default='data/work/audit50')
 p.add_argument('--questions',default='questions/audit50_questions.csv')
 p.add_argument('--output-dir',required=True)
 p.add_argument('--question-timeout',type=int,default=240)
 p.add_argument('--resume',action='store_true')
 p.add_argument('--refresh',action='store_true')
 a=p.parse_args()
 office_events=[]
 if a.prepared_root:
  root=Path(a.prepared_root).resolve(); source_mode='prepared_checkpoint'
 else:
  workspace=Path(a.workspace).resolve();workspace.mkdir(parents=True,exist_ok=True)
  extracted=extract_zip_safely(Path(a.share_zip).resolve(),workspace/'extracted',refresh=a.refresh)
  content=locate_content_root(extracted)
  root,office_events=prepare_office_tree(content,workspace/'office')
  unresolved=[e for e in office_events if e.get('status')=='unresolved_encryption']
  if unresolved:raise RuntimeError(f'unresolved encrypted Office documents: {unresolved}')
  source_mode='share_zip_cold_prepare'
 out=Path(a.output_dir).resolve();out.mkdir(parents=True,exist_ok=True);qs=readq(a.questions);wd=out/'workers';results=[];raw=out/'audit50_raw_results.jsonl';evp=out/'audit50_evidence.jsonl'
 start=time.perf_counter()
 with raw.open('w',encoding='utf-8') as rf,evp.open('w',encoding='utf-8') as ef:
  for n,row in enumerate(qs,1):
   existing=wd/f"{row['index']:03d}.json"
   if a.resume and existing.exists(): d=json.loads(existing.read_text(encoding='utf-8'))
   else:d=worker(root,row,wd,a.question_timeout)
   results.append(d);rf.write(json.dumps(d,ensure_ascii=False,default=str)+'\n');rf.flush()
   for e in d.get('evidence',[]):ef.write(json.dumps({'index':row['index'],'question':row['question'],**e},ensure_ascii=False,default=str)+'\n')
   ef.flush();print(f"[{n:02d}/50] index={row['index']} answered={d.get('answered')} route={d.get('route')} method={d.get('method')} elapsed={d.get('elapsed_seconds')}s",flush=True)
 fields=['index','question','answered','answer','confidence','route','method','reason','elapsed_seconds','evidence_count']
 with (out/'audit50_answers.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for d in results:w.writerow({**{k:d.get(k,'') for k in fields},'evidence_count':len(d.get('evidence',[]))})
 ans={int(d['index']):d.get('answer','わからない') if d.get('answered') else 'わからない' for d in results}
 with (out/'predictions.csv').open('w',encoding='utf-8',newline='') as f:
  w=csv.writer(f,lineterminator='\n')
  for i in range(100):w.writerow([i,ans.get(i,'わからない')])
 summary={'cold_start':True,'question_count':50,'answered_count':sum(bool(d.get('answered')) for d in results),'abstained_count':sum(not bool(d.get('answered')) for d in results),'audit_route_count':sum(d.get('route')=='audit_generalization' for d in results),'base_route_count':sum(d.get('route')=='base_recovery' for d in results),'timeout_count':sum(d.get('method')=='timeout' for d in results),'wall_seconds':round(time.perf_counter()-start,3),'question_elapsed_seconds':round(sum(float(d.get('elapsed_seconds',0)) for d in results),3),'runtime_inputs':{'source_mode':source_mode,'prepared_source_tree':str(root),'share_zip':str(Path(a.share_zip).resolve()) if a.share_zip else None,'questions':str(Path(a.questions).resolve()),'fact_catalog':False,'prior_answers':False,'expected_answers':False,'external_api':False},'office_events':office_events}
 (out/'run_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(summary,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
