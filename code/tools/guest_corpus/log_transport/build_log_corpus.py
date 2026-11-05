"""Build the bounded ASCII transport consumer, without executing a guest."""
from pathlib import Path
import argparse,json,struct,subprocess,sys
HERE=Path(__file__).resolve().parent
ROOT=next((p/'code' if (p/'code/tools/syscall_corpus.py').is_file() else p
           for p in HERE.parents if (p/'code/tools/syscall_corpus.py').is_file() or (p/'tools/syscall_corpus.py').is_file()),None)
if ROOT is None:raise RuntimeError('source root not found')
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.guest_corpus.build_guest_corpus import selected,values,data_bytes,sha
from tools import syscall_corpus as corpus
from tools.build import find_tool
from lang.dongc import compile_file
from lang.tests.test_dongc import nasm_flags

TRANSPORT=('corpus_guest.dg','corpus_entry.asm','corpus_log.dg','corpus_log.py','build_log_corpus.py')

def build(source,out,*,generation,mode='release'):
 raw=corpus.read_bounded(Path(source),257*2049);_,rows=selected(raw)
 if type(generation) is not int or not 0<generation<2**64:raise ValueError('positive u64 generation required')
 if mode not in ('debug','release'):raise ValueError('invalid mode')
 out=Path(out).absolute()
 if out.exists() or out.is_symlink():raise ValueError('output must be a new isolated directory')
 transport={n:(HERE/n).read_bytes() for n in TRANSPORT}
 transport_sha={n:sha(v) for n,v in transport.items()}
 bundle=sha(json.dumps(transport_sha,sort_keys=True,separators=(',',':')).encode())
 # Compile this exact annotated source. The raw BEGIN binding therefore also
 # commits every transport source, including the encoder/decoder and builder.
 guest=('// P9 transport sources SHA256 '+bundle+'\n').encode()+transport['corpus_guest.dg']
 sources={'corpus_guest.dg':guest,'corpus_entry.asm':transport['corpus_entry.asm']}
 for name,path in [('build_guest_corpus.py','tools/guest_corpus/build_guest_corpus.py'),
                   ('guest_corpus_receipt.py','tools/guest_corpus/guest_corpus_receipt.py'),
                   ('syscall_corpus.py','tools/syscall_corpus.py'),('service.ld','services/lib/service.ld')]:
  sources[name]=(ROOT/path).read_bytes()
 packed=data_bytes(rows)
 identity=dict(format='dongos-guest-corpus-build',version=1,generation=str(generation),count=len(rows),mode=mode,
               corpus_sha256=sha(raw),data_sha256=sha(packed),source_sha256={n:sha(v) for n,v in sources.items()})
 binding=sha(json.dumps(identity,sort_keys=True,separators=(',',':')).encode())
 words=struct.unpack('<4Q',bytes.fromhex(binding))
 generated=('module p9.corpus_data;\npub const COUNT:usize='+str(len(rows))+';\npub const GENERATION:u64='+str(generation)+';\npub const BINDING:[4]u64=['+','.join(map(str,words))+'];\npub const CASES:['+str(len(rows))+'][8]u64=['+','.join('['+','.join(map(str,v))+']' for v in values(rows))+'];\n').encode()
 out.mkdir(parents=True,exist_ok=False);snap=out/'inputs';(snap/'transport').mkdir(parents=True)
 for n,v in sources.items():(snap/n).write_bytes(v)
 for n,v in transport.items():(snap/'transport'/n).write_bytes(v)
 (out/'corpus.jsonl').write_bytes(raw);(out/'cases.bin').write_bytes(packed)
 stage=out/'source/p9';stage.mkdir(parents=True)
 for name,data in [('corpus_guest.dg',guest),('corpus_data.dg',generated),('corpus_log.dg',transport['corpus_log.dg'])]:(stage/name).write_bytes(data)
 compiled=compile_file(stage/'corpus_guest.dg',roots=[out/'source'],mode=mode)
 (out/'program.asm').write_text(compiled.assembly,encoding='utf-8')
 nasm,linker=find_tool('nasm','NASM'),find_tool('ld.lld','LD_LLD');commands=[]
 def run(args):
  r=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=90)
  commands.append(dict(argv=list(map(str,args)),returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))
  (out/'commands.json').write_text(json.dumps(commands,indent=2))
  if r.returncode:raise RuntimeError(r.stderr)
 for label,path in [('program',out/'program.asm'),('entry',snap/'corpus_entry.asm')]:
  run([nasm,'-O0','-f','elf64',*nasm_flags(nasm),path,'-o',out/(label+'.o')])
 run([linker,'-pie','--no-dynamic-linker','-z','norelro','--build-id=none','-T',snap/'service.ld','-o',out/'program.elf',out/'program.o',out/'entry.o'])
 manifest=dict(identity,binding_sha256=binding,generated_sha256=sha(generated),elf_sha256=sha((out/'program.elf').read_bytes()),assembly_sha256=sha((out/'program.asm').read_bytes()))
 (out/'manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
 envelope=dict(format='dongos-corpus-log-build',version=1,manifest_sha256=sha((out/'manifest.json').read_bytes()),transport_source_sha256=transport_sha)
 (out/'transport-manifest.json').write_text(json.dumps(envelope,sort_keys=True,indent=2)+'\n')
 return envelope

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('corpus',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--generation',type=int,required=True);p.add_argument('--mode',choices=['debug','release'],default='release');a=p.parse_args()
 print(json.dumps(build(a.corpus,a.output,generation=a.generation,mode=a.mode),indent=2))
if __name__=='__main__':main()
