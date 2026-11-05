"""Compile real Dong + syscall assembly; execute only the host boundary build."""
import copy,hashlib,importlib.util,json,os,struct,subprocess,sys,unittest,uuid
from pathlib import Path
from lang.dongc import compile_file
from lang.tests.test_dongc import tool,nasm_flags
from tools import syscall_corpus as corpus
ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/'tools/guest_corpus'
from tools.guest_corpus import build_guest_corpus as builder
from tools.guest_corpus import guest_corpus_receipt as receipt
C=r'''
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#define ABI __attribute__((sysv_abi))
typedef uint64_t U;
extern ABI U corpus_main(void);
static U expected[256][8],count,calls,emits,fault;
static FILE *output;
ABI U corpus_host_boundary(const U *r){
 if(calls>=count||memcmp(r,expected[calls],7*sizeof(U))){fputs("register/count mismatch\n",stderr);exit(41);}
 calls++;
 if(fault==1&&calls==1)return 0xdead;
 if(r[0]==0x70){if(r[2]>4096)return 0x050b0002;
  if(r[1]<0x10000||r[1]>=UINT64_C(0x8000000000)||r[2]>UINT64_C(0x8000000000)-r[1])return 0x04060003;
  if(r[2]==0)return 0;
  exit(45);
 }
 if(r[0]==0x10||r[0]==0x11||(r[0]>=0x22&&r[0]<=0x26)){
  U slot=r[1]&255,gen=r[1]>>8;
  if(!slot||slot>32||!gen||gen>=UINT64_C(0xffffffffffffff))return 0x04010002;
  exit(46);
 }
 return 0x050b0001;
}
ABI U corpus_host_emit(const void *p,U bytes){
 emits++;if(fault==2&&emits==2)return 1;
 if(bytes!=32&&bytes!=64)exit(47);
 if(fwrite(p,1,(size_t)bytes,output)!=bytes)exit(48);
 return 0;
}
int main(int argc,char **argv){
 if(argc!=5)return 49;
 FILE *input=fopen(argv[1],"rb");if(!input)return 50;
 count=fread(expected,sizeof expected[0],256,input);if(!count||!feof(input)){int c=fgetc(input);if(c!=EOF)return 51;}fclose(input);
 output=fopen(argv[2],"wb");if(!output)return 52;fault=strtoull(argv[3],0,10);
 U result=corpus_main();fclose(output);
 if(result==0&&calls!=count){fputs("missing execution\n",stderr);return 42;}
 printf("host cases=%llu emits=%llu result=%llu\n",(unsigned long long)calls,(unsigned long long)emits,(unsigned long long)result);
 return (int)result;
}
'''
def corpus_bytes(count=12):
    _,rows=corpus.verify_bytes(corpus.generate(42,256))
    safe=[r for r in rows if r['requires']=='none' and r['message'] is None]
    # Include distinguishable values in every register: the unknown case lets
    # us test the seventh SysV stack argument without dereferencing pointers.
    unknown=copy.deepcopy(next(r for r in safe if r['operation']=='syscall.unknown'))
    for i,k in enumerate(corpus.REGISTERS[1:]):unknown['registers'][k]=str(0x1122334455667700+i)
    safe=[unknown]+safe
    selected=[copy.deepcopy(safe[i%len(safe)]) for i in range(count)]
    for i,r in enumerate(selected):r['index']=str(i)
    header=dict(kind='header',format=corpus.FORMAT,version=1,seed='42',count=str(count),origin='generated')
    raw=('\n'.join(json.dumps(r,separators=(',',':')) for r in [header]+selected)+'\n').encode()
    corpus.verify_bytes(raw);return raw
class GuestCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/'build/test/p9-guest-corpus'/('run-'+uuid.uuid4().hex[:12]);cls.out.mkdir(parents=True)
        cls.raw=corpus_bytes();cls.input=cls.out/'corpus.jsonl';cls.input.write_bytes(cls.raw)
        cls.hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [*HERE.glob('*.py'),*HERE.glob('*.dg'),*HERE.glob('*.asm'),Path(__file__)]}
    @classmethod
    def tearDownClass(cls):
        if cls.hashes!={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in cls.hashes}:raise AssertionError('source changed during verification')
        (cls.out/'source-sha256.json').write_text(json.dumps(cls.hashes,indent=2))
        print('P9_GUEST_CORPUS_EVIDENCE',cls.out)
    def command(self,args,d,label):
        p=subprocess.run(list(map(str,args)),cwd=ROOT,capture_output=True,text=True,timeout=90)
        (d/(label+'.json')).write_text(json.dumps(dict(argv=list(map(str,args)),returncode=p.returncode,stdout=p.stdout,stderr=p.stderr),indent=2));return p
    def verify(self,d,raw,**overrides):
        args=dict(expected_manifest_sha256=builder.sha((d/'manifest.json').read_bytes()),generation=17,exit_code=0,timed_out=False)
        args.update(overrides);return receipt.verify_receipt(d,raw,**args)
    def test_real_elf_native_registers_and_mutants(self):
        nasm,cc=tool('nasm','NASM'),tool('gcc','CC');self.assertTrue(nasm and cc)
        for mode in ('debug','release'):
            d=self.out/mode;manifest=builder.build(self.input,d,generation=17,mode=mode)
            elf=(d/'program.elf').read_bytes();self.assertEqual(elf[:7],b'\x7fELF\x02\x01\x01');self.assertEqual(struct.unpack_from('<H',elf,16)[0],3)
            # Check immutable case bytes are covered by a non-writable LOAD.
            h=struct.unpack_from('<HHIQQQIHHHHHH',elf,16);packed=(d/'cases.bin').read_bytes();found=False
            for n in range(h[9]):
                typ,flags,offset,va,pa,size,mem,align=struct.unpack_from('<IIQQQQQQ',elf,h[4]+n*h[8])
                if typ==1 and packed in elf[offset:offset+size]:self.assertFalse(flags&2);found=True
            self.assertTrue(found)
            (d/'oracle.c').write_text(C)
            variants={'normal':None,'skip-last':('dong','while index<data.COUNT','while index+1<data.COUNT',42),
             'wrong-register':('asm','mov r10,r8','xor r10d,r10d',41),
             'wrong-return':('asm','%endif\n    ret\ncorpus_emit:','%endif\n    xor rax,1\n    ret\ncorpus_emit:',3),
             'missing-end':('dong','corpus_emit(&end[0],32)','0',0)}
            for variant,mutation in variants.items():
                v=d/variant;v.mkdir();stage=v/'p9';stage.mkdir()
                dong=(HERE/'corpus_guest.dg').read_text();asm=(HERE/'corpus_entry.asm').read_text()
                if mutation:
                    kind,old,new,_=mutation;self.assertEqual((dong if kind=='dong' else asm).count(old),1)
                    if kind=='dong':dong=dong.replace(old,new)
                    else:asm=asm.replace(old,new)
                (stage/'corpus_guest.dg').write_text(dong);(stage/'corpus_data.dg').write_bytes((d/'source/p9/corpus_data.dg').read_bytes())
                generated=compile_file(stage/'corpus_guest.dg',roots=[v],mode=mode)
                (v/'program.asm').write_text(generated.assembly);(v/'entry.asm').write_text(asm)
                objects=[]
                for label in ('program','entry'):
                    obj=v/(label+'.o');objects.append(obj)
                    r=self.command([nasm,'-O0','-DCORPUS_HOST=1','-f','win64' if os.name=='nt' else 'elf64',*nasm_flags(nasm),v/(label+'.asm'),'-o',obj],v,'assemble-'+label);self.assertEqual(r.returncode,0,r.stderr)
                exe=v/('probe.exe' if os.name=='nt' else 'probe')
                r=self.command([cc,'-std=c11','-O2','-Wall','-Wextra','-Werror',* ([] if os.name=='nt' else ['-no-pie']),d/'oracle.c',*objects,'-o',exe],v,'link');self.assertEqual(r.returncode,0,r.stderr)
                rawfile=v/'receipt.bin';r=self.command([exe,d/'cases.bin',rawfile,0,variant],v,'run');self.assertEqual(r.returncode,mutation[3] if mutation else 0,r.stdout+r.stderr)
                raw=rawfile.read_bytes()
                if mutation:
                    with self.assertRaises(ValueError):self.verify(d,raw)
                else:
                    result=self.verify(d,raw);self.assertEqual(result['count'],12);self.assertFalse(result['guest_verified'])
                    (d/'verified-host.json').write_text(json.dumps(result,indent=2))
                    for fault,expected in [(1,3),(2,2)]:
                        r=self.command([exe,d/'cases.bin',v/('fault'+str(fault)+'.bin'),fault,'fault'],v,'fault'+str(fault));self.assertEqual(r.returncode,expected)
                        with self.assertRaises(ValueError):self.verify(d,(v/('fault'+str(fault)+'.bin')).read_bytes())
                    defects=[raw[:-1],raw[:-32],raw+raw[-32:],raw[:64]+raw[96:128]+raw[64:96]+raw[128:],raw[:96]+raw[64:96]+raw[128:]]
                    bad=bytearray(raw);bad[64+24]^=1;defects.append(bytes(bad))
                    bad=bytearray(raw);bad[16]^=1;defects.append(bytes(bad))
                    bad=bytearray(raw);bad[-8]=1;defects.append(bytes(bad))
                    for damaged in defects:
                        with self.assertRaises(ValueError):self.verify(d,damaged)
                    for kwargs in [dict(generation=18),dict(exit_code=1),dict(exit_code=True),dict(timed_out=True),dict(execution='guest'),dict(expected_manifest_sha256='0'*64)]:
                        with self.assertRaises(ValueError):self.verify(d,raw,**kwargs)
                    for name in ['program.elf','cases.bin','inputs/corpus_guest.dg']:
                        p=d/name;original=p.read_bytes();p.write_bytes(original+b'X')
                        try:
                            with self.assertRaises(ValueError):self.verify(d,raw)
                        finally:p.write_bytes(original)
    def test_preconditions_bounds_and_no_overwrite(self):
        builder.selected(corpus_bytes(256))
        for raw in [corpus_bytes(257),corpus.generate(42,256),b'{"passed":true}\n',self.raw[:-1]]:
            p=self.out/('bad-'+uuid.uuid4().hex+'.jsonl');p.write_bytes(raw);d=self.out/('reject-'+uuid.uuid4().hex)
            with self.assertRaises(ValueError):builder.build(p,d,generation=17)
            self.assertFalse(d.exists())
        for generation in [0,-1,True,2**64]:
            with self.assertRaises(ValueError):builder.build(self.input,self.out/('gen-'+str(generation)),generation=generation)
        keep=self.out/'existing';keep.mkdir();(keep/'sentinel').write_text('keep')
        with self.assertRaises(ValueError):builder.build(self.input,keep,generation=17)
        self.assertEqual((keep/'sentinel').read_text(),'keep')
