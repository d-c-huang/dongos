"""Real Dong ASCII encoder and assembly, independent register and wire oracles."""
import hashlib,importlib.util,json,os,struct,subprocess,unittest,uuid
from pathlib import Path
from lang.dongc import compile_file
from lang.tests.test_dongc import tool,nasm_flags
from tests.test_guest_corpus import C,corpus_bytes
from tools.guest_corpus import guest_corpus_receipt as receipt
ROOT=Path.cwd()
HERE=ROOT/'tools/guest_corpus/log_transport'
def module(name):
 spec=importlib.util.spec_from_file_location('p9log_'+name,HERE/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
builder=module('build_log_corpus');decoder=module('corpus_log')

def wire(raw):
 records=[raw[:64]]+[raw[i:i+32] for i in range(64,len(raw),32)]
 return b''.join(('P9LOG1 %04x %02x %s\n'%(i,len(r),r.hex())).encode() for i,r in enumerate(records))

class CorpusLogTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/'build/test/p9-corpus-log'/('run-'+uuid.uuid4().hex[:12]);cls.out.mkdir(parents=True)
  cls.paths=[HERE/n for n in builder.TRANSPORT]+[Path(__file__)]
  cls.hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in cls.paths}
 @classmethod
 def tearDownClass(cls):
  if cls.hashes!={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in cls.paths}:raise AssertionError('sources changed')
  (cls.out/'source-sha256.json').write_text(json.dumps(cls.hashes,indent=2));print('P9_LOG_EVIDENCE',cls.out)
 def command(self,args,d,label):
  r=subprocess.run(list(map(str,args)),cwd=ROOT,capture_output=True,text=True,timeout=90)
  (d/(label+'.json')).write_text(json.dumps(dict(argv=list(map(str,args)),returncode=r.returncode,stdout=r.stdout,stderr=r.stderr),indent=2));return r
 def verify(self,d,raw,**kw):
  args=dict(expected_manifest_sha256=builder.sha((d/'transport-manifest.json').read_bytes()),generation=17,exit_code=0,timed_out=False);args.update(kw)
  return decoder.verify_log(d,raw,**args)
 def test_native_encoder_wire_binding_and_bad_bodies(self):
  nasm,cc=tool('nasm','NASM'),tool('gcc','CC');self.assertTrue(nasm and cc)
  for mode,count in [('debug',12),('release',12),('release',256),('debug',1)]:
   source=self.out/(mode+str(count)+'.jsonl');source.write_bytes(corpus_bytes(count))
   d=self.out/(mode+str(count));builder.build(source,d,generation=17,mode=mode)
   elf=(d/'program.elf').read_bytes();self.assertEqual(elf[:7],b'\x7fELF\x02\x01\x01');self.assertEqual(struct.unpack_from('<H',elf,16)[0],3)
   h=struct.unpack_from('<HHIQQQIHHHHHH',elf,16);packed=(d/'cases.bin').read_bytes();found=False
   for n in range(h[9]):
    typ,flags,offset,va,pa,size,mem,align=struct.unpack_from('<IIQQQQQQ',elf,h[4]+n*h[8])
    if typ==1 and packed in elf[offset:offset+size]:self.assertFalse(flags&2);found=True
   self.assertTrue(found)
   (d/'oracle.c').write_text(C.replace('bytes!=32&&bytes!=64','bytes!=80&&bytes!=144'))
   variants={'normal':None}
   if count==12:variants.update({'wrong-case':('index as u64,actual','(index as u64)+1,actual'),
    'missing-end':('log.emit(&end[0],32)','0'),
    'mixed-generation':('data.GENERATION,index as u64,actual','data.GENERATION+1,index as u64,actual')})
   for name,mutation in variants.items():
    v=d/name;stage=v/'p9';stage.mkdir(parents=True)
    dong=(d/'source/p9/corpus_guest.dg').read_text()
    if mutation:self.assertEqual(dong.count(mutation[0]),1);dong=dong.replace(*mutation)
    (stage/'corpus_guest.dg').write_text(dong)
    for n in ['corpus_data.dg','corpus_log.dg']:(stage/n).write_bytes((d/'source/p9'/n).read_bytes())
    compiled=compile_file(stage/'corpus_guest.dg',roots=[v],mode=mode)
    (v/'program.asm').write_text(compiled.assembly);(v/'entry.asm').write_bytes((HERE/'corpus_entry.asm').read_bytes())
    objects=[]
    for label in ('program','entry'):
     obj=v/(label+'.o');objects.append(obj)
     r=self.command([nasm,'-O0','-DCORPUS_HOST=1','-f','win64' if os.name=='nt' else 'elf64',*nasm_flags(nasm),v/(label+'.asm'),'-o',obj],v,'assemble-'+label);self.assertEqual(r.returncode,0,r.stderr)
    exe=v/('probe.exe' if os.name=='nt' else 'probe')
    r=self.command([cc,'-std=c11','-O2','-Wall','-Wextra','-Werror',* ([] if os.name=='nt' else ['-no-pie']),d/'oracle.c',*objects,'-o',exe],v,'link');self.assertEqual(r.returncode,0,r.stderr)
    capture=v/'capture.log';r=self.command([exe,d/'cases.bin',capture,0,name],v,'run');self.assertEqual(r.returncode,0,r.stdout+r.stderr)
    raw=capture.read_bytes()
    if mutation:
     with self.assertRaises(ValueError):self.verify(d,raw)
     continue
    m=json.loads((d/'manifest.json').read_bytes());rows=list(struct.iter_unpack('<8Q',packed))
    expected=struct.pack('<8Q',receipt.BEGIN,1,17,count,*struct.unpack('<4Q',bytes.fromhex(m['binding_sha256'])))
    expected+=b''.join(struct.pack('<4Q',receipt.CASE,17,i,row[7]) for i,row in enumerate(rows))
    expected+=struct.pack('<4Q',receipt.END,17,count,0)
    self.assertEqual(raw,wire(expected));self.assertEqual(decoder.decode(raw),expected)
    result=self.verify(d,raw);self.assertEqual(result['count'],count);self.assertFalse(result['guest_verified']);(d/'verified-host.json').write_text(json.dumps(result,indent=2))
    if count==256:self.assertEqual(len(raw),decoder.MAX_CAPTURE)
    if count!=12:continue
    for fault,code in [(1,3),(2,2)]:
     bad=v/('fault'+str(fault)+'.log');r=self.command([exe,d/'cases.bin',bad,fault,'fault'],v,'fault'+str(fault));self.assertEqual(r.returncode,code)
     with self.assertRaises(ValueError):self.verify(d,bad.read_bytes())
    for i in range(len(raw)):
     with self.assertRaises(ValueError):self.verify(d,raw[:i])
    lines=raw.splitlines(keepends=True)
    defects=[raw+b'noise\n',b'noise\n'+raw,raw.replace(b'\n',b'\r\n'),raw.upper(),raw+lines[-1],b''.join([lines[0],lines[2],lines[1],*lines[3:]]),raw.replace(b'0001 20',b'0000 20',1),raw.replace(b'0001 20',b'0001 40',1),raw.replace(b'P9LOG1',b'P9LOG2',1)]
    damaged=bytearray(expected);damaged[64+24]^=1;defects.append(wire(damaged))
    for bad in defects:
     with self.assertRaises(ValueError):self.verify(d,bad)
    for kw in [dict(generation=18),dict(exit_code=1),dict(exit_code=True),dict(timed_out=True),dict(execution='guest'),dict(expected_manifest_sha256='0'*64)]:
     with self.assertRaises(ValueError):self.verify(d,raw,**kw)
    for filename in ['program.elf','cases.bin','inputs/corpus_guest.dg','source/p9/corpus_log.dg',*('inputs/transport/'+n for n in builder.TRANSPORT)]:
     p=d/filename;original=p.read_bytes();p.write_bytes(original+b'X')
     try:
      with self.assertRaises(ValueError):self.verify(d,raw)
     finally:p.write_bytes(original)
    p=d/'transport-manifest.json';original=p.read_bytes()
    try:
     for envelope in [None,[],1,True,{'format':'dongos-corpus-log-build','version':True,'manifest_sha256':'0'*64,'transport_source_sha256':{}}]:
      p.write_text(json.dumps(envelope))
      with self.assertRaises(ValueError):self.verify(d,raw)
    finally:p.write_bytes(original)
 def test_input_bounds_and_isolation(self):
  for count in (0,257):
   source=self.out/('invalid'+str(count));source.write_bytes(corpus_bytes(count));out=self.out/('reject'+str(count))
   with self.assertRaises(ValueError):builder.build(source,out,generation=17)
   self.assertFalse(out.exists())
  source=self.out/'valid.jsonl';source.write_bytes(corpus_bytes(1))
  for generation in [0,-1,True,2**64]:
   with self.assertRaises(ValueError):builder.build(source,self.out/('gen'+str(generation)),generation=generation)
  keep=self.out/'existing';keep.mkdir();(keep/'sentinel').write_text('keep')
  with self.assertRaises(ValueError):builder.build(source,keep,generation=17)
  self.assertEqual((keep/'sentinel').read_text(),'keep')
  for bad in [None,b'',bytearray(b'x'),b'x'*(decoder.MAX_CAPTURE+1)]:
   with self.assertRaises(ValueError):decoder.decode(bad)
