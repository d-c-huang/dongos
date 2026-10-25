"""Source-bound C/D guest gate. CLI builds/boots only with explicit flags."""
import argparse,copy,hashlib,json,os,struct,subprocess,sys,time
from pathlib import Path
from tests import p2_runtime_large_build as workload
from tests import p2_pcid_build as base
from tests import run_p2_pcid_qemu as pcid
from tests import run_p2_runtime_large_qemu as large
from tests import p2_bulk_capture as bulk
check,write,sha=base.check,base.write,base.sha
ROOT=Path(__file__).resolve().parents[1]
CONTRACT='p2-cd-production-v1'
CASES=(None,'omit-exec-poll','omit-cache-poll')

def overlays(root,case):
 check(case in CASES,'unknown C/D mutation')
 result=workload.overlays(root,None)
 if case:
  path='kernel/user/services.dg';text=(Path(root)/path).read_text(encoding='utf-8')
  needle='return runtime_exec.poll(RUNTIME_EXEC,d,cpu);' if case=='omit-exec-poll' else 'return runtime_cache.poll(RUNTIME_CACHE,d,cpu);'
  check(text.count(needle)==1,'C/D mutation anchor differs')
  marker=1 if case=='omit-exec-poll' else 2
  text=text.replace(needle,f'P2CD_NEGATIVE={marker};return 0;')
  text=text.replace('module user.services;','module user.services;\npub var P2CD_NEGATIVE:u64=0;',1)
  result[path]=text.encode()
 return result

def prepare(output,*,source_root=ROOT,case=None):
 output,source_root=Path(output).resolve(),Path(source_root).resolve();check(not output.exists(),'fresh C/D build required')
 before=base.inputs(source_root);check(before,'empty C/D source graph');stage=output/'source';stage.mkdir(parents=True)
 for name in before:
  dest=stage/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((source_root/name).read_bytes())
 check(base.inputs(stage)==base.inputs(source_root)==before,'C/D source copy changed')
 changes=overlays(source_root,case)
 for name,raw in changes.items():(stage/name).write_bytes(raw)
 record=dict(schema=1,contract=CONTRACT,source_root=str(source_root),output=str(output),case=case,
  source_sha256=before,staged_sha256=base.inputs(stage),overlay_paths=sorted(changes),built=False,actual_guest_executed=False)
 write(output/'p2-cd-source.json',record);return record

def verify_prepared(output,*,source_root=ROOT):
 output,source_root=Path(output).resolve(),Path(source_root).resolve();r=json.loads((output/'p2-cd-source.json').read_text())
 check(r['contract']==CONTRACT and r['source_root']==str(source_root) and r['output']==str(output),'C/D build redirection')
 check(base.inputs(source_root)==r['source_sha256'],'C/D current source graph changed')
 expected=dict(r['source_sha256']);changes=overlays(source_root,r['case']);expected.update({n:hashlib.sha256(v).hexdigest() for n,v in changes.items()})
 check(r['overlay_paths']==sorted(changes) and r['staged_sha256']==expected==base.inputs(output/'source'),'unbound C/D overlay')
 return r

def build(output,*,source_root=ROOT,case=None):
 r=prepare(output,source_root=source_root,case=case);output=Path(output).resolve();env=os.environ.copy()
 try:
  roles=base.resolve_tools();spec=base.command_spec(output,roles);r['build_tool_roles']=roles;r['build_tools_sha256']={v['path']:v['sha256']for v in roles.values()}
  for name in spec['environment_removed']:env.pop(name,None)
  env.update(spec['environment_overrides']);write(output/'build-command.json',spec);r['build_command_sha256']=sha(output/'build-command.json')
  with (output/'build.log').open('wb')as log:v=subprocess.run(spec['argv'],cwd=spec['cwd'],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=1800)
  r['build_returncode']=v.returncode;r['build_log_sha256']=sha(output/'build.log');check(v.returncode==0,'C/D production build failed')
  verify_prepared(output,source_root=source_root)
  r.update(built=True,os_link_executed=True,source_unchanged=True,esp=str(output/'image/esp'),artifacts_sha256=base.artifacts(output/'image'),production_manifest_sha256=sha(output/'image/build-inputs.json'))
  base.verify_completed(output,r)
 finally:write(output/'p2-cd-source.json',r)
 return r

def identity(esp):
 out=Path(esp).resolve().parent.parent;r=verify_prepared(out);base.verify_completed(out,r);return r

def types_for(esp):return {t['full_name']:t for t in json.loads((Path(esp).parent/'dong_layout.json').read_text())['types']}
def offset(types,name,field):return next(f['offset']for f in types[name]['fields']if f['name']==field)
def scalars(types,name,data):
 check(len(data)>=types[name]['size'],'short C/D native object')
 return {f['name']:struct.unpack_from('<Q',data,f['offset'])[0]for f in types[name]['fields']if f['size']==8}

class CDGuest(pcid.PcidGuest):
 def running_shell(self,command,*,exact=None):
  check(not self.stopped,'continuous UART requires an already running guest')
  start=len(self.raw);self.uart.sendall(pcid.life.fat.command_bytes(command)+b'\r');deadline=time.monotonic()+90
  while True:
   end=len(self.raw);segment=bytes(self.raw[start:end]);reply=pcid.life.fat.fresh_response(segment,command,exact=exact)
   if reply is not None:break
   check(self.process.poll() is None and time.monotonic()<deadline,'continuous UART response timeout')
   time.sleep(.01)
  return dict(command=command,serial_offset=start,serial_end=end,serial_sha256=bulk.digest(segment),**reply)
 def initial_snapshot(self):
  audit=self.evidence['bootstrap_audit']
  image=pcid.CapturedImage(self._capture_registry,audit['epoch'],copy.deepcopy(self._boot_info_ref),esp=self.esp,symbols=self.symbols,contract=self.contract,label='before')
  return self.cd_image(image,'before')
 def cd_snapshot(self,label):
  image=self.capture_image(label);self.resume();return self.cd_image(image,label)
 def cd_image(self,image,label):
  image.initialize();cap=pcid.Capture(image);types=types_for(image.esp);parts={}
  def get(name,address,size):
   raw,parts[name]=cap.part(address,size,'C/D '+name);return raw
  def pointer(module,name):return struct.unpack('<Q',get(module+'.'+name,image.symbols[pcid.storage.symbol(module,name)],8))[0]
  info=pointer('sched.user_boot','INFO');boot=struct.unpack('<10Q',get('boot',info,80));get('domain',boot[5],120)
  catalog=pointer('user.services','CATALOG');get('catalog',catalog,pcid.life.CATALOG_BYTES)
  get('failures',image.symbols[pcid.storage.symbol('sched.user_bridge','FAILURES')],16*224)
  for short,module,ptr,storage,typ in [('C','mm.runtime_exec','RUNTIME_EXEC','EXEC_STORAGE','user.services.ExecStorage'),('D','mm.runtime_cache','RUNTIME_CACHE','CACHE_STORAGE','user.services.CacheStorage')]:
   addr=pointer('user.services',ptr);held=pointer('user.services',storage)
   if held:
    get(short+'.storage',held,types[typ]['size']);get(short+'.context',held+offset(types,typ,'context'),types[module+'.Context']['size'])
  trace=pointer('sched.runtime_exec_entry','TRACE_RECORDS')
  if trace:get('trace',trace,32*types['sched.runtime_exec_entry.RawTrace']['size'])
  marker=pcid.storage.symbol('user.services','P2CD_NEGATIVE')
  if marker in image.symbols:get('negative_marker',image.symbols[marker],8)
  _,poolref=cap.physical(cap.pool[0],cap.pool[1]*4096,'complete kernel pool C/D')
  record=dict(label=label,epoch=image.epoch,serial_offset=image.serial_offset,parts=parts,kernel_pool=cap.pool,kernel_pool_ref=poolref,boot_info_ref=image.boot_info_ref)
  decoded=decode(record,image.archive(),types,image.symbols);image.flush();return record,decoded

def decode(record,archive,types,symbols):
 archive.begin_snapshot(record['epoch']);check(record['serial_offset']==archive.snapshot_serial_offset,'mixed C/D epoch UART')
 pool=record['kernel_pool'];check(pool[1]==128 and record['kernel_pool_ref']['physical']==pool[0],'C/D kernel pool differs');archive.read(record['kernel_pool_ref'])
 parts=record['parts']
 for module,name in [('sched.user_boot','INFO'),('user.services','RUNTIME_EXEC'),('user.services','EXEC_STORAGE'),('user.services','RUNTIME_CACHE'),('user.services','CACHE_STORAGE'),('user.services','CATALOG'),('sched.runtime_exec_entry','TRACE_RECORDS')]:
  check(parts[module+'.'+name]['virtual']==symbols[pcid.storage.symbol(module,name)],'unbound C/D global address')
 get=lambda n:pcid.oracle.part_bytes(parts[n],archive,pool)
 boot_pointer=struct.unpack('<Q',get('sched.user_boot.INFO'))[0];check(parts['boot']['virtual']==boot_pointer,'unbound actual boot report')
 boot=struct.unpack('<10Q',get('boot'));check(parts['domain']['virtual']==boot[5],'unbound C/D Domain address')
 trace_pointer=struct.unpack('<Q',get('sched.runtime_exec_entry.TRACE_RECORDS'))[0]
 if 'trace'in parts:check(parts['trace']['virtual']==trace_pointer,'unbound C/D raw trace pointer')
 if 'negative_marker'in parts:check(parts['negative_marker']['virtual']==symbols[pcid.storage.symbol('user.services','P2CD_NEGATIVE')],'unbound negative marker')
 catalog_pointer=struct.unpack('<Q',get('user.services.CATALOG'))[0];check(parts['catalog']['virtual']==catalog_pointer,'unbound actual Catalog')
 result=dict(catalog=pcid.life.decode_catalog(get('catalog')),domain=scalars(types,'sched.user_domain.Domain',get('domain')),owners={},marker=struct.unpack('<Q',get('negative_marker'))[0]if 'negative_marker'in parts else 0)
 for short,module,ptr,store,typ in [('C','mm.runtime_exec','RUNTIME_EXEC','EXEC_STORAGE','user.services.ExecStorage'),('D','mm.runtime_cache','RUNTIME_CACHE','CACHE_STORAGE','user.services.CacheStorage')]:
  published=struct.unpack('<Q',get('user.services.'+ptr))[0];held=struct.unpack('<Q',get('user.services.'+store))[0];owner=dict(pointer=published,storage=held)
  if held:
   check(parts[short+'.storage']['virtual']==held and parts[short+'.context']['virtual']==held+offset(types,typ,'context'),'C/D storage pointer differs')
   context=get(short+'.context');owner.update(context=scalars(types,module+'.Context',context),report=scalars(types,module+'.Report',context[offset(types,module+'.Context','report'):]),raw=context.hex())
   if short=='D':owner['admission']=scalars(types,typ,get('D.storage'))
  result['owners'][short]=owner
 failure_address=symbols[pcid.storage.symbol('sched.user_bridge','FAILURES')];check(parts['failures']['virtual']==failure_address,'unbound Bridge failure address')
 failures=get('failures');stride=types['sched.user_bridge.Failure']['size']
 result['failures']=[scalars(types,'sched.user_bridge.Failure',failures[i*stride:(i+1)*stride])for i in range(16)]
 check(all(f['published']==0 or f['domain']==boot[5]for f in result['failures']),'Bridge failure belongs to another Domain')
 result['trace']=get('trace').hex()if 'trace'in parts else ''
 return result

def validate(decoded,types,case=None):
 domain=decoded['domain'];owners=decoded['owners'];c=owners['C'].get('report',{});d=owners['D'].get('report',{})
 if case:
  short='C'if case=='omit-exec-poll'else'D';r=owners[short].get('report',{})
  check(decoded['marker']==(1 if short=='C'else 2),'actual C/D negative site never executed')
  check(domain['failed']==1 and r.get('poison')==1 and r.get('complete')==0 and r.get('held')==1,'C/D negative did not retain failed owner')
  code=r.get('error_code');local=0x06140005 if short=='C'else 0x06150006;propagated=0x06140004 if short=='C'else 0x06090004
  check(code in (local,propagated),'negative lacks exact local/propagated failure')
  check(domain['owner']==0 and domain['lock']==1 and r.get('phase')==2,'negative did not fail inside first reader action')
  if short=='C':check(r.get('barriers')==2 and r.get('state')==1 and r.get('command')==6 and r.get('action_sequence')==1 and r.get('ack_mask')==0,'C negative failed outside initial STORE')
  else:check(r.get('barriers')==1 and r.get('request')==1 and r.get('action')==1 and r.get('round')==0 and r.get('committed')==0,'D negative failed outside initial READ')
  module='mm.runtime_exec'if short=='C'else'mm.runtime_cache';reader=module+('.ReaderReport'if short=='C'else'.Reader');raw=bytes.fromhex(owners[short]['raw']);at=offset(types,module+'.Context','readers');stride=types[reader]['size']
  for cpu in range(4):
   fields=scalars(types,reader,raw[at+cpu*stride:at+(cpu+1)*stride]);check(fields['request']==(1 if short=='D' or cpu==0 else 0) and fields['acknowledged']==0,'omitted poll request mask/ACK differs')
  failures=decoded['failures'];bsp=failures[0]
  check(bsp['published']==1 and bsp['cpu']==0 and bsp['stage']==8 and bsp['error_code']==0x060b0011 and bsp['detail_code']==code,'negative lacks exact BSP projection failure chain')
  if code==propagated:
   check(any(f['published']==1 and f['cpu']==cpu and f['argument_cpu']==cpu and f['stage']==5 and f['error_code']==0x06090005 and f['detail_code']==0 and f['owner']==0 and f['lock']==1 and f['acquired']==0 and 0<f['wait_started']<f['deadline']<=f['clock']for cpu,f in enumerate(failures[:4])if cpu>0),'propagated negative lacks actual expired AP lock deadline')
  return
 check(domain['failed']==0 and domain['ready']==1 and domain['barrier']==0,'C/D Domain unhealthy')
 for short in ['C','D']:
  o=owners[short];r=o.get('report',{});check(o['pointer']>0 and r.get('complete')==1 and r.get('poison')==0 and r.get('error_code')==0 and r.get('held')==1,'C/D owner not complete')
 check(c['phase']==10 and c['state']==0 and c['unmapped']==1 and c['receipts_consumed']==2 and c['barriers']==13 and c['tables_before']==c['tables_after'],'C lifecycle incomplete')
 check(d['phase']==10 and d['committed']==1 and d['round']==2 and d['barriers']==5 and d['linear']>0 and d['revoked']==d['reclaimed']==d['remapped']==2*d['linear'],'D lifecycle incomplete')
 for short,module,reader in [('C','mm.runtime_exec','ReaderReport'),('D','mm.runtime_cache','Reader')]:
  raw=bytes.fromhex(owners[short]['raw']);at=offset(types,module+'.Context','readers');stride=types[module+'.'+reader]['size']
  for cpu in range(4):
   body=raw[at+cpu*stride:at+(cpu+1)*stride];r=scalars(types,module+'.'+reader,body);check(r['request']==r['acknowledged'] and r['request']>0,'C/D reader omitted ACK')
   if short=='C':
    for field,value,fault in [('called42',42,0),('called43',43,0),('denied42',0x0000c30000002ab8,1),('denied43',0x0000c30000002bb8,1)]:
     sample=scalars(types,module+'.Sample',body[offset(types,module+'.'+reader,field):]);check(sample['cpu']==cpu and sample['value']==value and sample['fault']==fault,'C per-reader actual code/fault differs')
   else:check(r['reads']==5 and r['maintenances']==2,'D reader lacked real maintenance')
 trace=bytes.fromhex(decoded['trace']);stride=types['sched.runtime_exec_entry.RawTrace']['size'];seen=set()
 for at in range(0,len(trace),stride):
  raw=trace[at:at+stride];t=scalars(types,'sched.runtime_exec_entry.RawTrace',raw)
  if not t['commit']:continue
  check(t['version']==1 and t['commit']==1 and t['cpu']<4 and t['generation']==1,'C trace binding differs')
  pre=scalars(types,'mm.runtime_exec.FaultTicket',raw[offset(types,'sched.runtime_exec_entry.RawTrace','ticket_before'):]);post=scalars(types,'mm.runtime_exec.FaultTicket',raw[offset(types,'sched.runtime_exec_entry.RawTrace','ticket_after'):]);frame=scalars(types,'sched.runtime_exec_entry.Raw',raw[offset(types,'sched.runtime_exec_entry.RawTrace','raw'):])
  check(pre['armed']==1 and pre['consumed']==0 and post['armed']==0 and post['consumed']==1 and frame['vector']==14 and frame['error_code']==3 and frame['cs']==8,'C raw PF/ticket consumption differs')
  seen.add((t['cpu'],t['payload']))
 check(seen=={(cpu,word)for cpu in range(4)for word in [0x0000c30000002ab8,0x0000c30000002bb8]},'C raw PF receipts missing')

def receipt_body(receipt,serial,*,command,exact=None):
 check(receipt['command']==command,'UART command receipt redirected')
 start,end=receipt['serial_offset'],receipt['serial_end']
 check(type(start)is int and type(end)is int and 0<=start<end<=len(serial),'UART receipt bounds differ')
 segment=serial[start:end];check(bulk.digest(segment)==receipt['serial_sha256'],'UART receipt hash differs')
 reply=pcid.life.fat.fresh_response(segment,command,exact=exact)
 check(reply is not None and all(receipt[k]==v for k,v in reply.items()),'UART receipt lacks fresh complete reply')
 return bytes.fromhex(reply['response_hex'])

def ps_rows(body):
 rows=pcid.life.parse_ps(body)
 canonical=b''.join(('PROCESS '+r['name']+' id='+str(r['id'])+' token='+str(r['token'])+' generation='+str(r['generation'])+' state='+str(r['state'])+' status='+str(r['status'])+'\r\n').encode()for r in rows)
 check(body==canonical,'noncanonical actual ps body');return rows

def continuous_gui(g):
 receipts=[g.running_shell('ps')];rows=ps_rows(bytes.fromhex(receipts[0]['response_hex']))
 for cfg in pcid.prior.GUI_CONFIGS:
  row=rows[cfg];check(row['token']>0 and row['state']==2 and row['status']==0,'initial GUI identity not READY')
  command='kill '+str(row['token']);exact=('KILL OK token='+str(row['token'])+' generation=0 state=5 status=0\r\n').encode()
  receipts.append(g.running_shell(command,exact=exact))
 receipts.append(g.running_shell('ps'));return receipts

def verify_controls(result,serial,before,after):
 receipts=result['gui_control'];check(len(receipts)==6,'incomplete continuous GUI command sequence')
 initial=ps_rows(receipt_body(receipts[0],serial,command='ps'));final=ps_rows(receipt_body(receipts[-1],serial,command='ps'))
 for cfg,row in enumerate(initial):
  source=before['snapshots'][cfg]
  check(all(row[k]==source[f]for k,f in [('token','process'),('generation','generation'),('state','state'),('status','status')]),'initial ps differs from source-bound Catalog')
 for index,cfg in enumerate(pcid.prior.GUI_CONFIGS):
  row=initial[cfg];check(row['token']>0 and row['state']==2 and row['status']==0,'initial GUI not ready')
  receipt_body(receipts[index+1],serial,command='kill '+str(row['token']),exact=('KILL OK token='+str(row['token'])+' generation=0 state=5 status=0\r\n').encode())
  stopped=final[cfg];actual=after['snapshots'][cfg]
  check(stopped==dict(row,token=0,state=5,status=0),'GUI did not retain killed generation')
  check(actual['process']==0 and actual['generation']==row['generation'] and actual['state']==5 and actual['status']==0,'final raw Catalog differs from GUI kill')
 for cfg in list(range(7))+[13]:
  check(initial[cfg]==final[cfg],'GUI control changed essential identity')
  row=final[cfg];actual=after['snapshots'][cfg]
  check(all(row[k]==actual[f]for k,f in [('token','process'),('generation','generation'),('state','state'),('status','status')]),'final essential Catalog differs')
 for cfg,receipt in zip([7,8,9,10,11],result['launches']):receipt_body(receipt,serial,command=large.launch_command(cfg))
 ordered=receipts+result['launches'];check(all(a['serial_end']<=b['serial_offset']for a,b in zip(ordered,ordered[1:])),'UART receipt order/overlap differs')

def execute(esp,out,*,case=None,accel="tcg",cpu="max,+smep,+smap,+umip",kernel_irqchip=None):
 check(accel in ("tcg","whpx","kvm") and (kernel_irqchip is None or accel=="whpx" and kernel_irqchip=="off"),"invalid explicit C/D backend")
 esp,out=Path(esp).resolve(),Path(out).resolve();r=identity(esp);check(r['case']==case and not out.exists(),'guest case/output differs');out.mkdir(parents=True)
 result=dict(schema=1,contract=CONTRACT,passed=False,synthetic=False,actual_guest_executed=False,case=case,source_identity=r,snapshots=[],guest_memory_or_register_writes=False,accel=accel,cpu=cpu,kernel_irqchip=kernel_irqchip)
 g=None
 try:
  disk=out/'data.img';large.create(disk,64);g=CDGuest(esp,disk,out/'boot',accel=accel,cpu=cpu,kernel_irqchip=kernel_irqchip);result['actual_guest_executed']=True
  snap,before=g.initial_snapshot();result['snapshots'].append(snap)
  check(all(not v['storage']for v in before['owners'].values()),'C/D armed before actual launch')
  result['gui_control']=continuous_gui(g)
  result['launches']=[g.running_shell(large.launch_command(cfg))for cfg in [7,8,9,10,11]]
  # No inspection stop between GUI control and all five real launches.
  check(not g.stopped,'progress wait requires running guest');time.sleep(3)
  until=time.monotonic()+120
  while True:
   snap,v=g.cd_snapshot('after');result['snapshots'].append(snap)
   try:validate(v,types_for(esp),case);break
   except ValueError:
    if v['domain']['failed'] or time.monotonic()>=until:raise
    time.sleep(2)
 except BaseException as exc:
  result['error']=type(exc).__name__+': '+str(exc)
  if g and 'observer-disturbed' not in str(exc):
   try:
    snap,failed=g.cd_snapshot('failure');result['failure_snapshot']=snap;result['failure_domain']=failed['domain'];result['failure_owners']={k:{f:v for f,v in o.items()if f!='raw'}for k,o in failed['owners'].items()}
   except BaseException as diagnostic:result['failure_capture_error']=type(diagnostic).__name__+': '+str(diagnostic)
  raise
 finally:
  if g:g.close();result['guest']=copy.deepcopy(g.evidence)
  write(out/'result.json',result)
 result['seal']=replay(out/'result.json');result['passed']=True;write(out/'result.json',result);return result

def replay(path):
 path=Path(path);r=json.loads(path.read_text());check(r['contract']==CONTRACT and r['synthetic']is False and r['actual_guest_executed']is True and r['guest_memory_or_register_writes']is False,'not actual C/D receipt')
 esp=Path(r['source_identity']['esp']);check(identity(esp)==r['source_identity'],'C/D build changed')
 state=path.parent/'boot';manifest=json.loads((state/'physical-manifest.json').read_text());registry=bulk.EpochRegistry.from_disk(state,manifest,pcid.capture_metadata(esp),profile=bulk.SCHEMA)
 archive=pcid.oracle.Archive(state,manifest,registry=registry);registry.verify_all();last=r['snapshots'][-1]
 symbols=pcid.read_elf_symbols(esp.parent/'kernel.elf');image=pcid.CapturedImage(registry,last['epoch'],last['boot_info_ref'],esp=esp,symbols=symbols,contract=pcid.elf_contract(esp),label='offline-C/D');image.initialize();pool=pcid.Capture(image).pool
 check(pool==last['kernel_pool'],'C/D replay kernel pool lacks BootInfo provenance')
 v=decode(last,archive,types_for(esp),symbols);validate(v,types_for(esp),r['case'])
 before=decode(r['snapshots'][0],archive,types_for(esp),symbols)
 check(all(not o['storage']for o in before['owners'].values()),'C/D before-state already armed')
 serial=(state/'serial.log').read_bytes()[:last['serial_offset']]
 check(all(serial.count((large.launch_command(cfg)+'\r\n').encode())==1 for cfg in [7,8,9,10,11]),'C/D actual launch UART evidence differs')
 verify_controls(r,serial,before['catalog'],v['catalog'])
 pcid.verify_launch_command(r['guest']['command'],accel=r['accel'],cpu=r['cpu'],kernel_irqchip=r['kernel_irqchip'])
 check(r['guest'].get('cleanup_completed')is True and r['guest'].get('process_alive')is False,'owned C/D QEMU still alive')
 check(len(r['launches'])==5 and not r['guest'].get('cleanup_failures'),'incomplete C/D launches/cleanup')
 return dict(passed=True,raw_files=len(manifest),raw_manifest_sha256=sha(state/'physical-manifest.json'),case=r['case'])

def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--build',type=Path);a.add_argument('--execute',type=Path);a.add_argument('--reuse-esp',type=Path);a.add_argument('--case',choices=CASES[1:]);a.add_argument('--replay',type=Path);a.add_argument('--accel',choices=['tcg','whpx','kvm'],default='tcg');a.add_argument('--cpu',default='max,+smep,+smap,+umip');a.add_argument('--kernel-irqchip',choices=['off']);v=a.parse_args()
 if v.build:result=build(v.build,case=v.case)
 elif v.execute:result=execute(v.reuse_esp,v.execute,case=v.case,accel=v.accel,cpu=v.cpu,kernel_irqchip=v.kernel_irqchip)
 elif v.replay:result=replay(v.replay)
 else:a.error('explicit build, execute or replay required')
 print(json.dumps(result))
if __name__=='__main__':main()
