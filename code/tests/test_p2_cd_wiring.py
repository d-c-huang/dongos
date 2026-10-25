"""C/D wiring and independent raw verdict controls; no guest is started."""
import copy,struct,unittest
from pathlib import Path
from lang.dongc import compile_file
from tests import run_p2_cd_qemu as cd
from tests import p2_pcid_oracle as pools
ROOT=Path(__file__).resolve().parents[1]
class WiringTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  result=compile_file(ROOT/'kernel/user/services.dg',roots=[ROOT/'kernel',ROOT/'services',ROOT/'lang/std',ROOT/'lang/examples'],mode='release')
  cls.types={t['full_name']:t for t in result.layout_manifest['types']}
 def test_slot0_is_real_arena_pool_and_old_coherent_static_rejected(self):
  memory=bytearray(16*1288);space=bytearray(64);root=0x900000;pointer=0xffffd40000100000;meta=0xffffffff80180000
  struct.pack_into('<2Q',memory,0,1,root);struct.pack_into('<Q',memory,160,root)
  struct.pack_into('<6Q',space,0,1,pointer,32,root,meta,(1<<48)-4096);space[48]=1
  kw=dict(static_pools=0,static_base=0x210000,static_virtual=0xffffffff80010000,metadata_virtual=meta,limits=[32,32,32,128]+[32]*12,dynamics=[root]+[0]*15,pointers=[pointer]+[0]*15,generations=[1]+[0]*15,kernel_image=0x200000,arena=0x800000,next_page=1024)
  self.assertEqual((root,pointer),pools.pool_identity(memory,space,0,**kw))
  for kind in ['static','outside-arena','missing-receipt','wrong-count']:
   m,sp,args=bytearray(memory),bytearray(space),copy.deepcopy(kw)
   if kind=='static':
    struct.pack_into('<Q',m,8,0x210000);struct.pack_into('<Q',m,160,0x210000);struct.pack_into('<Q',sp,24,0x210000);struct.pack_into('<Q',sp,8,0xffffffff80010000);args['dynamics'][0]=0x210000;args['pointers'][0]=0xffffffff80010000
   elif kind=='outside-arena':args['next_page']=1
   elif kind=='missing-receipt':args['dynamics'][0]=0
   else:args['static_pools']=1
   with self.subTest(kind=kind),self.assertRaises(ValueError):pools.pool_identity(m,sp,0,**args)
 def fixture(self):
  t=self.types
  def put(raw,name,values,at=0):
   for key,v in values.items():struct.pack_into('<Q',raw,at+cd.offset(t,name,key),v)
  owners={}
  for short,mod in [('C','mm.runtime_exec'),('D','mm.runtime_cache')]:
   raw=bytearray(t[mod+'.Context']['size']);reader=mod+('.ReaderReport'if short=='C'else'.Reader');start=cd.offset(t,mod+'.Context','readers');stride=t[reader]['size']
   for cpu in range(4):
    at=start+cpu*stride;put(raw,reader,dict(request=7,acknowledged=7),at)
    if short=='C':
     for field,value,fault in [('called42',42,0),('called43',43,0),('denied42',0x0000c30000002ab8,1),('denied43',0x0000c30000002bb8,1)]:put(raw,mod+'.Sample',dict(cpu=cpu,value=value,fault=fault),at+cd.offset(t,reader,field))
    else:put(raw,reader,dict(reads=5,maintenances=2),at)
   owners[short]=dict(pointer=0xffffd40002000000,storage=0xffffd40002000000,raw=raw.hex(),report=dict(complete=1,poison=0,error_code=0,held=1,phase=10))
  owners['C']['report'].update(state=0,unmapped=1,receipts_consumed=2,barriers=13,tables_before=75,tables_after=75)
  owners['D']['report'].update(committed=1,round=2,barriers=5,linear=4050,revoked=8100,reclaimed=8100,remapped=8100)
  name='sched.runtime_exec_entry.RawTrace';stride=t[name]['size'];trace=bytearray(32*stride)
  for cpu in range(4):
   for j,word in enumerate([0x0000c30000002ab8,0x0000c30000002bb8]):
    at=(cpu*2+j)*stride;put(trace,name,dict(version=1,commit=1,cpu=cpu,generation=1,payload=word),at)
    put(trace,'mm.runtime_exec.FaultTicket',dict(armed=1,consumed=0),at+cd.offset(t,name,'ticket_before'));put(trace,'mm.runtime_exec.FaultTicket',dict(armed=0,consumed=1),at+cd.offset(t,name,'ticket_after'));put(trace,'sched.runtime_exec_entry.Raw',dict(vector=14,error_code=3,cs=8),at+cd.offset(t,name,'raw'))
  return dict(synthetic=True,domain=dict(failed=0,ready=1,barrier=0),owners=owners,trace=trace.hex(),marker=0)
 def test_raw_positive_and_exact_missing_proofs_rejected(self):
  v=self.fixture();cd.validate(v,self.types)
  for kind in ['unpublished','receipt','tables','maintenance','fault-trace','ACK']:
   bad=copy.deepcopy(v)
   if kind=='unpublished':bad['owners']['D']['pointer']=0
   elif kind=='receipt':bad['owners']['C']['report']['receipts_consumed']=1
   elif kind=='tables':bad['owners']['C']['report']['tables_after']=76
   elif kind=='fault-trace':bad['trace']=''
   else:
    mod='mm.runtime_cache'if kind=='maintenance'else'mm.runtime_exec';reader=mod+('.Reader'if kind=='maintenance'else'.ReaderReport');short='D'if kind=='maintenance'else'C';raw=bytearray.fromhex(bad['owners'][short]['raw']);at=cd.offset(self.types,mod+'.Context','readers');field='maintenances'if kind=='maintenance'else'acknowledged';struct.pack_into('<Q',raw,at+cd.offset(self.types,reader,field),0);bad['owners'][short]['raw']=raw.hex()
   with self.subTest(kind=kind),self.assertRaises(ValueError):cd.validate(bad,self.types)
 def test_real_negative_overlay_and_exact_causal_deadline_required(self):
  for case,short,marker,codes in [('omit-exec-poll','C',1,[0x06140005,0x06140004]),('omit-cache-poll','D',2,[0x06150006,0x06090004])]:
   changes=cd.overlays(ROOT,case);self.assertIn(('P2CD_NEGATIVE='+str(marker)).encode(),changes['kernel/user/services.dg'])
   for code in codes:
    v=self.fixture();v['domain'].update(failed=1,owner=0,lock=1);v['marker']=marker;r=v['owners'][short]['report'];r.update(poison=1,complete=0,error_code=code,phase=2)
    if short=='C':r.update(barriers=2,state=1,command=6,action_sequence=1,ack_mask=0)
    else:r.update(barriers=1,request=1,action=1,round=0,committed=0)
    module='mm.runtime_exec'if short=='C'else'mm.runtime_cache';reader=module+('.ReaderReport'if short=='C'else'.Reader');raw=bytearray.fromhex(v['owners'][short]['raw']);at=cd.offset(self.types,module+'.Context','readers');stride=self.types[reader]['size']
    for cpu in range(4):
     struct.pack_into('<Q',raw,at+cpu*stride+cd.offset(self.types,reader,'request'),1 if short=='D' or cpu==0 else 0);struct.pack_into('<Q',raw,at+cpu*stride+cd.offset(self.types,reader,'acknowledged'),0)
    v['owners'][short]['raw']=raw.hex();v['failures']=[dict(published=1,cpu=0,stage=8,error_code=0x060b0011,detail_code=code),dict(published=1,cpu=1,argument_cpu=1,stage=5,error_code=0x06090005,detail_code=0,owner=0,lock=1,acquired=0,wait_started=2,deadline=10,clock=11)]
    cd.validate(v,self.types,case)
    for kind in ['wrong-owner-code','BSP-chain','phase','missing-AP-deadline','false-expiry','ACK']:
     bad=copy.deepcopy(v)
     if kind=='wrong-owner-code':bad['owners'][short]['report']['error_code']=0x06150004
     elif kind=='BSP-chain':bad['failures'][0]['detail_code']=0
     elif kind=='phase':bad['owners'][short]['report']['phase']=1
     elif kind=='missing-AP-deadline':
      if code==codes[0]:continue
      bad['failures'][1]['published']=0
     elif kind=='false-expiry':
      if code==codes[0]:continue
      bad['failures'][1]['clock']=9
     else:
      raw=bytearray.fromhex(bad['owners'][short]['raw']);struct.pack_into('<Q',raw,at+cd.offset(self.types,reader,'acknowledged'),1);bad['owners'][short]['raw']=raw.hex()
     with self.subTest(case=case,code=code,kind=kind),self.assertRaises(ValueError):cd.validate(bad,self.types,case)

 def test_continuous_control_never_pauses_between_launches(self):
  # Explicit host adapter: orchestration proof only, never a guest receipt.
  import tempfile
  from unittest import mock
  events=[]
  class Adapter:
   instance=None
   def __init__(self,*args,**kwargs):self.stopped=False;self.evidence={};Adapter.instance=self
   def initial_snapshot(self):
    events.append('historical-before');return {'synthetic':True},{'owners':{'C':{'storage':0},'D':{'storage':0}},'domain':{'failed':0}}
   def cd_snapshot(self,label):
    events.append('final-capture');return {'synthetic':True},{'domain':{'failed':0}}
   def running_shell(self,command):
    if self.stopped:raise AssertionError('control attempted while paused')
    events.append(command);return {'synthetic':True,'command':command}
   def close(self):self.stopped=True;events.append('close')
  def wait(seconds):
   self.assertFalse(Adapter.instance.stopped,'waiting with a paused guest');events.append('wait')
  with tempfile.TemporaryDirectory()as temp:
   with mock.patch.object(cd,'identity',return_value={'case':None,'synthetic':True}),mock.patch.object(cd.large,'create'),mock.patch.object(cd,'CDGuest',Adapter),mock.patch.object(cd,'continuous_gui',side_effect=lambda g:events.append('continuous-gui')),mock.patch.object(cd.time,'sleep',side_effect=wait),mock.patch.object(cd,'types_for',return_value={}),mock.patch.object(cd,'validate')as verdict,mock.patch.object(cd,'replay',return_value={'synthetic':True}):
    cd.execute(Path(temp)/'synthetic/esp',Path(temp)/'host-adapter');verdict.assert_called_once()
  self.assertEqual(events,['historical-before','continuous-gui']+[cd.large.launch_command(cfg)for cfg in [7,8,9,10,11]]+['wait','final-capture','close'])
 def test_uart_receipts_bind_fresh_bounded_actual_bytes(self):
  serial=b'old ps\r\n> ps\r\nfresh\r\n> later ps\r\nother\r\n> '
  start=serial.index(b'ps',10);end=serial.index(b'later')
  segment=serial[start:end];reply=cd.pcid.life.fat.fresh_response(segment,'ps')
  receipt=dict(command='ps',serial_offset=start,serial_end=end,serial_sha256=cd.bulk.digest(segment),**reply)
  self.assertEqual(cd.receipt_body(receipt,serial,command='ps'),b'fresh\r\n')
  for field,value in [('serial_offset',0),('serial_end',len(serial)),('serial_sha256','0'*64),('response_hex',b'forged'.hex()),('command','kill 264')]:
   with self.subTest(field=field),self.assertRaises(ValueError):cd.receipt_body(dict(receipt,**{field:value}),serial,command='ps')

def load_tests(loader,suite,pattern):
 # These dedicated production/ASM oracles remain separate methods with their
 # real negative bodies; the coordinator records one aggregate bound suite.
 for name in ['test_runtime_exec','test_runtime_exec_entry','test_runtime_cache','test_framebuffer_gate','test_framebuffer_ledger','test_p2_bulk_capture']:
  suite.addTests(loader.loadTestsFromName('tests.'+name))
 return suite
