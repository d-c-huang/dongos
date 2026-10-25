"""Actual Dong assembler, independent NASM bytes, and executable ELF payloads."""
import hashlib,json,os,struct,subprocess,unittest,uuid
from pathlib import Path
from lang.dongc import compile_file
from lang.tests import test_bootstrap_native_assembler as original
from lang.tests.test_dongc import tool,nasm_flags
ROOT=Path(__file__).resolve().parents[2]
LOADER=r'''
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#include <windows.h>
#else
#include <sys/mman.h>
#endif
typedef uint64_t U;
typedef U (__attribute__((sysv_abi)) *Fn)(void);
int main(int argc,char**argv){
 if(argc!=2)return 80;
 FILE*f=fopen(argv[1],"rb");if(!f)return 81;
 unsigned char raw[131072];size_t n=fread(raw,1,sizeof raw,f);fclose(f);
 if(n<64||memcmp(raw,"\177ELF",4))return 82;
#ifdef _WIN32
 unsigned char*p=VirtualAlloc(0,131072,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE);
#else
 unsigned char*p=mmap(0,131072,PROT_READ|PROT_WRITE|PROT_EXEC,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
 if(p==MAP_FAILED)return 83;
#endif
 if(!p)return 83;
 U ph,entry;memcpy(&ph,raw+32,8);memcpy(&entry,raw+24,8);
 unsigned short count,stride;memcpy(&count,raw+56,2);memcpy(&stride,raw+54,2);
 for(unsigned i=0;i<count;i++){U off,va,sz;unsigned kind;
  if(ph+(U)i*stride+56>n)return 84;
  unsigned char*h=raw+ph+(U)i*stride;memcpy(&kind,h,4);if(kind!=1)continue;
  memcpy(&off,h+8,8);memcpy(&va,h+16,8);memcpy(&sz,h+32,8);
  if(va<0x400000||va-0x400000+sz>131072||off+sz>n)return 85;
  memcpy(p+va-0x400000,raw+off,sz);
 }
 if(entry<0x400000||entry>=0x420000)return 86;
 U value=((Fn)(p+entry-0x400000))();printf("%llu\n",(unsigned long long)value);
 return value==37?0:87;
}
'''

class ExtendedEncodingTests(unittest.TestCase):
    cases=original.NativeAssemblerTests.cases
    assemble=original.NativeAssemblerTests.assemble

    @classmethod
    def command(cls,args,label):
        p=subprocess.run(list(map(str,args)),capture_output=True,timeout=180)
        (cls.work/(label+'.stdout')).write_bytes(p.stdout)
        (cls.work/(label+'.stderr')).write_bytes(p.stderr)
        cls.records.append({'label':label,'returncode':p.returncode})
        if p.returncode:raise AssertionError((label,p.stderr.decode(errors='replace')))
        return p

    @classmethod
    def write_receipt(cls):
        (cls.work/'summary.json').write_text(json.dumps({'inputs':cls.hashes,'records':cls.records},indent=2)+'\n')

    @classmethod
    def setUpClass(cls):
        cls.nasm,cls.cc=tool('nasm','NASM'),tool('gcc','CC')
        if not cls.nasm or not cls.cc:raise RuntimeError('NASM and GCC required; no skips')
        cls.work=ROOT/'build/test/l3-extended-encoding'/('run-'+uuid.uuid4().hex[:12]);cls.work.mkdir(parents=True)
        cls.records=[];cls.hashes={};cls.executables={}
        stage=cls.work/'source';(stage/'bootstrap').mkdir(parents=True);(stage/'exec').mkdir()
        for rel in ['lang/bootstrap/native_assembler.dg','lang/bootstrap/x86_encode.dg','lang/bootstrap/elf64_image.dg','kernel/exec/elf.dg']:
            src=ROOT/rel;cls.hashes[rel]=hashlib.sha256(src.read_bytes()).hexdigest()
            (stage/Path(rel).relative_to(Path(rel).parts[0])).write_bytes(src.read_bytes())
        (stage/'entry.dg').write_text(original.WRAPPER)
        harness=original.HARNESS.replace('extern U ','extern U __attribute__((sysv_abi)) ').replace('void __dong_panic','void __attribute__((sysv_abi)) __dong_panic')
        if os.name=='nt':
            harness='#include <io.h>\n#include <fcntl.h>\n'+harness.replace('int main(void){','int main(void){\n_setmode(_fileno(stdin),_O_BINARY);_setmode(_fileno(stdout),_O_BINARY);')
        (cls.work/'probe.c').write_text(harness)
        (cls.work/'loader.c').write_text(LOADER)
        cls.loader=cls.work/'loader.exe'
        cls.command([cls.cc,'-std=c11','-D_GNU_SOURCE','-O2',cls.work/'loader.c','-o',cls.loader],'loader')
        for mode in ('debug','release'):
            asm=cls.work/(mode+'.asm');asm.write_text(compile_file(stage/'entry.dg',roots=[stage],mode=mode).assembly)
            for fmt in ('win64','elf64'):
                cls.command([cls.nasm,'-f',fmt,*nasm_flags(cls.nasm),asm,'-o',cls.work/(mode+'.'+fmt+'.o')],mode+fmt)
            obj=cls.work/(mode+('.win64.o' if os.name=='nt' else '.elf64.o'));exe=cls.work/(mode+'.exe')
            cls.command([cls.cc,'-std=c11','-O2',cls.work/'probe.c',obj,'-o',exe],mode+'-link');cls.executables[mode]=exe

    @classmethod
    def tearDownClass(cls):
        for rel,h in cls.hashes.items():
            if hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()!=h:raise AssertionError('source changed: '+rel)
        cls.write_receipt()

    def test_exact_nasm_encoding_matrix(self):
        lines=['pause','int3','lfence','sfence','mfence','cli','sti','hlt']
        for reg in range(16):
            for base in ('rax','rsp','rbp','r11','r12','r13'):
                for disp in ('','+127','-128','+128','-129'):
                    lines += [f'movdqu xmm{reg}, [{base}{disp}]',f'movdqu [{base}{disp}], xmm{reg}']
        for op in ('lock cmpxchg','lock xadd','xchg'):
            for width,reg in [('dword','eax'),('dword','r9d'),('qword','rax'),('qword','r15')]:
                for base in ('rsp','rbp','r11','r12'):
                    lines.append(f'{op} {width} [{base}+128], {reg}')
        body='\n'.join(lines)+'\nret\n';source=original.PREFIX+body
        nasm=self.work/'oracle.asm';nasm.write_text('bits 64\n'+body)
        binary=self.work/'oracle.bin';self.command([self.nasm,'-f','bin',nasm,'-o',binary],'oracle')
        expected=binary.read_bytes()
        for mode in self.executables:
            result=self.assemble(mode,'matrix',source);image=result[6]
            self.assertEqual(result[3],len(expected));self.assertEqual(image[4096:4096+len(expected)],expected)

    def test_invalid_forms_and_short_output_do_not_publish(self):
        bad=['mov rax, xmm0','movdqu rax, [rsp]','movdqu xmm16, [rsp]','movdqu xmm0, qword [rsp]',
             'movdqu xmm0, xmm1','lock mov qword [rsp], rax','lock xadd rax, rdx','lock cmpxchg byte [rsp], al',
             'lock xadd word [rsp], ax','cmpxchg qword [rsp], rax','lfence rax','pause 1','mfence rax, rbx',
             'cli rax','sti rax','hlt 1','xchg byte [rsp], al']
        for mode in self.executables:
            cases=[(original.PREFIX+x+'\n','_start',(128,257,65536,65536,131072)) for x in bad]
            for result in self.cases(mode,'invalid',cases):self.assertNotEqual(result[0],0)
            good=original.PREFIX+'pause\nret\n';image=self.assemble(mode,'capacity-good',good)[6]
            for cap in (0,len(image)-1):
                result=self.cases(mode,'short'+str(cap),[(good,'_start',(128,257,65536,65536,cap))])[0]
                self.assertEqual(result[0],2)

    def test_actual_atomic_and_xmm_execution(self):
        body='''sub rsp, 48
mov rax, 7
mov [rsp], rax
mov rax, 9
mov [rsp+8], rax
movdqu xmm0, [rsp]
movdqu [rsp+16], xmm0
mov rax, 7
mov rdx, 11
lock cmpxchg qword [rsp+16], rdx
mov rax, 5
lock xadd qword [rsp+16], rax
mov rdx, [rsp+16]
add rax, rdx
mov edx, 1
lock xadd dword [rsp+24], edx
add rax, rdx
mov rax, [rsp+24]
add rax, [rsp+16]
add rax, 11
mov rdx, 37
xchg qword [rsp], rdx
cmp rdx, 7
jne bad
mov r9, [rsp]
cmp r9, 37
jne bad
mov r10, rax
mov eax, 99
mov edx, 101
lock cmpxchg qword [rsp], rdx
cmp rax, 37
jne bad
mov r9, [rsp]
cmp r9, 37
jne bad
mov rax, r10
pause
lfence
sfence
mfence
add rsp, 48
ret
bad:
mov eax, 99
add rsp, 48
ret
'''
        for mode in self.executables:
            image=self.assemble(mode,'execution',original.PREFIX+body)[6]
            path=self.work/(mode+'-program.elf');path.write_bytes(image)
            p=self.command([self.loader,path],mode+'-execute');self.assertEqual(p.stdout.strip(),b'37')

    def test_real_frontend_backend_to_native_elf(self):
        from lang.tests import test_l3a_native_regression as bridge
        saved=bridge.CAND,bridge.BUILD
        bridge.CAND=ROOT/'lang/bootstrap';bridge.BUILD=self.work/'pipeline'
        try:
            bridge.L3ANativeRegressionTests.setUpClass()
            native=bridge.L3ANativeRegressionTests()
            source=native.work/'extended.dg'
            source.write_text('''module native;
export("__dong_panic") fn panic(k:u32,line:u32,p:*const u8,n:usize)noreturn{loop{}}
pub extern "win64" fn callback(a:u64,b:u64,c:u64,d:u64,e:u64)u64{return a+b+c+d+e;}
pub fn f()u64{unsafe{
 var x:u64=7;var y:u32=9;
 atomic_store(&x,11);atomic_store(&y,13);
 if atomic_compare_exchange(&x,11,17)!=11{return 90;}
 if atomic_compare_exchange(&x,99,100)!=17{return 91;}
 if atomic_fetch_add(&x,3)!=17{return 92;}
 if atomic_fetch_add(&y,5)!=13{return 93;}
 if atomic_load(&x)!=20||atomic_load(&y)!=18{return 94;}
 asm{pause}asm{lfence}asm{sfence}asm{mfence}
 return callback(1,2,3,4,27);
}}
fn privileged()void{unsafe{asm{cli}asm{sti}asm{hlt}asm{int3}}}
''')
            for mode in (0,1):
                asm=native.work/('extended-'+str(mode)+'.asm');elf=asm.with_suffix('.elf')
                native.command([native.driver,source,'native.dg',asm,mode,elf,bridge.label('native','f')],'extended-'+str(mode))
                for instruction in ('movdqu','lock cmpxchg','lock xadd','xchg','lfence'):
                    self.assertIn(instruction,asm.read_text())
                self.command([self.loader,elf],'pipeline-execute-'+str(mode))
            bridge.L3ANativeRegressionTests.tearDownClass()
        finally:bridge.CAND,bridge.BUILD=saved

if __name__=='__main__':unittest.main()
