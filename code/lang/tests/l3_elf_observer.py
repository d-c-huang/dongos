"""Host observation bridge: production native assembler ELF, no target NASM fallback.

COFF absolute symbols only connect existing C observers to mapped ELF addresses.
External host functions are explicit appended r11 tail-call stubs. All original
Dong-emitted instructions/data remain unmodified. This is a Windows host test
adapter, not an OS loader or an extension of the assembler's external ABI.
"""
import hashlib,json,os,re,struct,subprocess
from pathlib import Path

ASSEMBLER = r'''
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uint64_t U;typedef struct{void*p;U n;} S;
typedef struct{S labels,table,text,data;} W;
typedef struct{U status,line,detail,text,data,labels,written;} R;
typedef struct{U start,length,section,offset;} L;
extern U __attribute__((sysv_abi)) native_assemble(const void*,U,const void*,U,const W*,void*,U,R*);
extern U __attribute__((sysv_abi)) kernel_validate(const void*,U,void*);
void __attribute__((sysv_abi)) __dong_panic(uint32_t k,uint32_t l,const void*p,U n){(void)p;(void)n;fprintf(stderr,"compiler panic %u %u\n",k,l);exit(91);}
int main(int argc,char**argv){
 if(argc!=4)return 90;FILE*f=fopen(argv[1],"rb");if(!f)return 92;
 fseek(f,0,SEEK_END);long n=ftell(f);rewind(f);char*s=malloc(n+1);if(fread(s,1,n,f)!=(size_t)n)return 93;fclose(f);
 W w={{calloc(65536,32),65536},{calloc(131072,8),131072},{malloc(16777216),16777216},{malloc(16777216),16777216}};
 unsigned char*out=malloc(16777216);R r={0};memset(out,0xa5,16777216);
 U rc=native_assemble(s,n,argv[2],strlen(argv[2]),&w,out,16777216,&r);
 if(rc){fprintf(stderr,"assemble status=%llu line=%llu detail=%llu\n",(unsigned long long)rc,(unsigned long long)r.line,(unsigned long long)r.detail);return 94;}
 U plan[134]={0};if(kernel_validate(out,r.written,plan))return 95;
 for(U i=r.written;i<16777216;i++)if(out[i]!=0xa5)return 96;
 f=fopen(argv[3],"wb");if(!f||fwrite(out,1,r.written,f)!=r.written)return 97;fclose(f);
 for(U i=0;i<r.labels;i++){L*l=(L*)w.labels.p+i;U base=0x401000;
 if(l->section==2||l->section==3)base=0x400000+((4096+r.text+4095)&~4095ULL);
 printf("%.*s %llu\n",(int)l->length,s+l->start,(unsigned long long)(base+l->offset));}
 return 0;
}
'''

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def absolute_object(symbols):
    strings=bytearray(b'\0'*4);entries=bytearray()
    for name,address in symbols.items():
        encoded=name.encode()
        if len(encoded)<=8:field=encoded.ljust(8,b'\0')
        else:field=struct.pack('<II',0,len(strings));strings+=encoded+b'\0'
        entries+=field+struct.pack('<IhHBB',address,-1,0,2,0)
    struct.pack_into('<I',strings,0,len(strings))
    return struct.pack('<HHIIIHH',0x8664,0,0,20,len(symbols),0,0)+entries+strings

def loader_source(raw,slots,receipt):
    # The production validator has already checked the exact ELF. Validate bounds
    # again in this independent host adapter before copying; enforce RX/RW pages.
    declarations='\n'.join('extern void host_%d(void) __asm__(%s);'%(i,json.dumps(name)) for i,(_,name) in enumerate(slots))
    patches='\n'.join('*(uintptr_t*)(uintptr_t)%d=(uintptr_t)&host_%d;'%(address,i) for i,(address,_) in enumerate(slots))
    return r'''
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h>
'''+declarations+'\nstatic const unsigned char raw[]={'+','.join(str(x) for x in raw)+r'''};
static uint64_t u64(size_t n){uint64_t v;memcpy(&v,raw+n,8);return v;}
static unsigned u16(size_t n){unsigned short v;memcpy(&v,raw+n,2);return v;}
static void load_native_elf(void){
 if((uintptr_t)GetModuleHandleA(NULL)!=0x10000000)exit(110);
 size_t n=sizeof raw;if(n<64||memcmp(raw,"\177ELF",4))exit(101);
 uint64_t ph=u64(32);unsigned count=u16(56),stride=u16(54);uint64_t end=0x400000;
 if(count<1||count>2||stride!=56||ph+(uint64_t)count*stride>n)exit(102);
 for(unsigned i=0;i<count;i++){size_t h=ph+i*stride;uint64_t va=u64(h+16),sz=u64(h+40);
 if(va<0x400000||va+sz<va||va+sz>0x1400000){exit(103);}
 if(va+sz>end){end=va+sz;}}
 size_t size=(end-0x400000+4095)&~4095ULL;
 void*p=VirtualAlloc((void*)0x400000,size,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);if(p!=(void*)0x400000)exit(104);
 for(unsigned i=0;i<count;i++){size_t h=ph+i*stride;uint64_t off=u64(h+8),va=u64(h+16),len=u64(h+32),mem=u64(h+40);
 if(off>n||len>n-off||len>mem){exit(105);}
 memcpy((void*)(uintptr_t)va,raw+off,len);
 if(memcmp((void*)(uintptr_t)va,raw+off,len))exit(106);}
'''+patches+r'''
 for(unsigned i=0;i<count;i++){size_t h=ph+i*stride;unsigned flags;memcpy(&flags,raw+h+4,4);DWORD old;
 if(flags!=5&&flags!=6)exit(107);
 if(!VirtualProtect((void*)(uintptr_t)u64(h+16),(size_t)u64(h+40),flags==5?PAGE_EXECUTE_READ:PAGE_READWRITE,&old))exit(108);}
 FlushInstructionCache(GetCurrentProcess(),p,size);
 FILE*f=fopen('''+json.dumps(str(receipt))+r''',"wb");if(!f)exit(109);
 fputs("mapped exact ELF; runtime slots patched; RX/RW enforced\n",f);fclose(f);
}
#undef main
extern int elf_observer_main(int,char**);
static int saved_argc;static char**saved_argv;
static DWORD WINAPI observer_worker(void*parent){
 WaitForSingleObject((HANDLE)parent,INFINITE);CloseHandle((HANDLE)parent);
 load_native_elf();ExitProcess((UINT)elf_observer_main(saved_argc,saved_argv));return 0;
}
int main(int argc,char**argv){
 saved_argc=argc;saved_argv=argv;HANDLE parent;
 if(!DuplicateHandle(GetCurrentProcess(),GetCurrentThread(),GetCurrentProcess(),&parent,SYNCHRONIZE,FALSE,0))return 111;
 HANDLE worker=CreateThread(NULL,0,observer_worker,parent,0,NULL);if(!worker)return 112;
 CloseHandle(worker);ExitThread(0);return 113;
}
'''


# The original NASM negative control uses a symbolic RIP displacement outside
# the production dialect. Preserve its wrong address (+8), not that spelling:
# two LEAs have the same value and flags and assemble through the real backend.
MUTANT_NASM = r'symbol(s,(*x).value);if (*g).symbols[(*x).value].kind==names.GLOBAL{put(s,"+8");}put(s,"]\n");'
MUTANT_ELF = r'symbol(s,(*x).value);put(s,"]\n");if (*g).symbols[(*x).value].kind==names.GLOBAL{put(s,"lea rax, [rax+8]\n");}'

class ElfObservationMixin:
    def boot(self):
        if os.name!='nt':raise RuntimeError('This observer adapter requires Windows; no skips')
        self.elf_targets={};self.elf_objects={};self.elf_executions=[]
        from lang.tests import test_l3a_globals as bridge
        self.original_source_stage=bridge.stage_compiler
        def source_stage(work,wrapper=bridge.WRAPPER,mutations=None,extra=('exec.elf',)):
            if mutations and 'nasm_program.dg' in mutations:
                old,new=mutations['nasm_program.dg']
                if MUTANT_NASM in new:
                    assert new.count(MUTANT_NASM)==1
                    mutations=dict(mutations)
                    mutations['nasm_program.dg']=(old,new.replace(MUTANT_NASM,MUTANT_ELF))
            return self.original_source_stage(work,wrapper,mutations,extra)
        bridge.stage_compiler=source_stage
        try:super().boot()
        except BaseException:
            bridge.stage_compiler=self.original_source_stage
            raise
        self.mutant_sites=[dict(old=x['old'],new=x['new'].replace(MUTANT_NASM,MUTANT_ELF)) for x in self.mutant_sites]
        self.inputs[str(Path(__file__))]=sha(__file__)
        self.elf_tool=self.work/'elf-assembler.exe';c=self.work/'elf-assembler.c';c.write_text(ASSEMBLER)
        obj=Path(self.g.drivers['good']).parent/'wrapper.obj'
        super().command([self.cc,'-std=c11','-O2',c,obj,'-o',self.elf_tool],'elf-assembler-link')

    def ensure_elf(self,asm):
        asm=Path(asm);digest=sha(asm)
        if str(asm) in self.elf_targets:
            target=self.elf_targets[str(asm)];assert target['source_sha256']==digest;return target
        binding=self.bindings[str(asm)];assert binding['native_compile_returncode']==0
        assert binding['emitted_sha256']==digest
        text=asm.read_text();labels={x.lstrip('$') for x in re.findall(r'^([\w.$]+):',text,re.M)}
        external=sorted({x.lstrip('$') for x in re.findall(r'^extern\s+(\S+)',text,re.M)}-labels)
        globals_=sorted({x.lstrip('$') for x in re.findall(r'^global\s+(\S+)',text,re.M)})
        entry='__elf_probe_entry'
        assert entry not in text and '__elf_host_slot_' not in text
        extra='\nsection .text\n__elf_probe_entry:\nret\n'
        for i,name in enumerate(external):extra+=f'{name}:\nmov r11, [rel __elf_host_slot_{i}]\njmp r11\n'
        extra+='section .data\n'
        for i,name in enumerate(external):extra+=f'__elf_host_slot_{i}:\ndq 0\n'
        source=asm.with_suffix('.elf-input.asm')
        footer='%ifidn __OUTPUT_FORMAT__,elf64'
        assert text.count(footer)==1
        source.write_text(text.replace(footer,extra+footer))
        elf=asm.with_suffix('.native.elf')
        p=super().command([self.elf_tool,source,entry,elf],'native-elf-'+asm.parent.name+'-'+asm.stem)
        symbols={}
        for row in p.stdout.splitlines():
            name,address=row.rsplit(' ',1);symbols[name.lstrip('$')]=int(address)
        obj=asm.with_suffix('.obj');exports={name:symbols[name] for name in globals_}
        obj.write_bytes(absolute_object(exports))
        load=asm.with_suffix('.elf-loader.c');receipt=asm.with_suffix('.mapped.txt')
        slots=[(symbols[f'__elf_host_slot_{i}'],name) for i,name in enumerate(external)]
        load.write_text(loader_source(elf.read_bytes(),slots,receipt))
        target=dict(source_sha256=digest,elf_path=str(elf),elf_sha256=sha(elf),input_sha256=sha(source),loader=str(load),receipt=str(receipt),external=external,exports=exports,variant=binding['variant'])
        self.elf_targets[str(asm)]=target;self.elf_objects[str(obj)]=target
        (self.work/'elf-targets.json').write_text(json.dumps(self.elf_targets,indent=2))
        return target

    def dong(self,directory,mode,tag='good'):
        asm,p=super().dong(directory,mode,tag)
        if p.returncode==0:self.ensure_elf(asm)
        return asm,p

    def command(self,args,name,expect=0):
        args=list(map(str,args))
        # Only exact target paths bound to this source-built Dong compiler qualify.
        # Compiler bootstrap, Python seed and observation assembly remain untouched.
        if hasattr(self,'elf_tool') and args[0]==str(self.nasm):
            targets=[Path(a) for a in args if a in self.bindings and self.bindings[a]['native_compile_returncode']==0]
            if targets:
                assert len(targets)==1
                asm=targets[0];target=self.ensure_elf(asm);out=Path(args[args.index('-o')+1]);fmt=args[args.index('-f')+1]
                if fmt=='win64':out.write_bytes(absolute_object(target['exports']))
                elif fmt=='elf64':out.write_bytes(Path(target['elf_path']).read_bytes())
                else:raise AssertionError('unsupported target object request')
                self.records.append(dict(name=name,command=['native_assembler',str(asm),str(out)],returncode=0,elf_sha256=target['elf_sha256']))
                return subprocess.CompletedProcess(args,0,'','')
        selected=[self.elf_objects[a] for a in args if a in getattr(self,'elf_objects',{})]
        if selected and args[0]==str(self.cc):
            assert len(selected)==1
            target=selected[0];args += [target['loader'],'-Dmain=elf_observer_main','-Wl,--image-base=0x10000000']
            exe=args[args.index('-o')+1];self.elf_objects[exe]=target
        target=getattr(self,'elf_objects',{}).get(args[0])
        if target:Path(target['receipt']).unlink(missing_ok=True)
        p=super().command(args,name,expect)
        if selected and args[0]==str(self.cc):
            host=Path(exe);data=bytearray(host.read_bytes());pe=struct.unpack_from('<I',data,60)[0]
            assert data[pe:pe+4]==b'PE\0\0'
            optional=pe+24;assert struct.unpack_from('<H',data,optional)[0]==0x20b
            assert struct.unpack_from('<Q',data,optional+24)[0]==0x10000000
            flags=struct.unpack_from('<H',data,optional+70)[0]
            struct.pack_into('<H',data,optional+70,flags & ~0x40)
            host.write_bytes(data)
        if target:
            assert Path(target['receipt']).read_text()=='mapped exact ELF; runtime slots patched; RX/RW enforced\n'
            assert sha(target['elf_path'])==target['elf_sha256']
            self.elf_executions.append(dict(name=name,exe=args[0],elf_sha256=target['elf_sha256'],variant=target['variant'],returncode=p.returncode))
        return p

    def finish(self):
        from lang.tests import test_l3a_globals as bridge
        try:result=super().finish()
        finally:bridge.stage_compiler=self.original_source_stage
        assert self.elf_targets and self.elf_executions
        result['pure_elf']=dict(targets=self.elf_targets,executions=self.elf_executions,no_target_nasm=True,host_runtime='explicit extern function slots only; native code/data unchanged',static_address_mutant=dict(original=MUTANT_NASM,actual=MUTANT_ELF,semantics='same address +8; flags unchanged'),scope='all G5 accepted target assemblies; original CPU oracles and negative controls')
        return result
