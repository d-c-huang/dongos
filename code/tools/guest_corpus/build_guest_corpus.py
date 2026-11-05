"""Build a private, bounded Dong CPL3 consumer. Never launch an OS or VM."""
from pathlib import Path
import argparse,hashlib,json,struct,subprocess,sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools import syscall_corpus as corpus
from lang.dongc import compile_file
from tools.build import find_tool
from lang.tests.test_dongc import nasm_flags

def sha(data):return hashlib.sha256(data).hexdigest()
def selected(raw):
    header,rows=corpus.verify_bytes(raw)
    if not 1<=len(rows)<=256:raise ValueError('batch requires 1..256 cases')
    for row in rows:
        if row['requires']!='none' or row['oracle']['class']=='accepted_shape' or row['message'] is not None:
            raise ValueError('unsupported prerequisite at case '+row['index']+'; whole batch rejected')
    return header,rows
def values(rows):
    return [[int(r['registers'][k]) for k in corpus.REGISTERS]+[int(r['oracle']['code'],16) if r['oracle']['code'] else 0] for r in rows]
def data_bytes(rows):return b''.join(struct.pack('<8Q',*r) for r in values(rows))
def build(source,out,*,generation,mode='release'):
    raw=corpus.read_bounded(Path(source),(257*2049));header,rows=selected(raw)
    if type(generation) is not int or not 0<generation<2**64:raise ValueError('positive u64 generation required')
    if mode not in ('debug','release'):raise ValueError('invalid mode')
    out=Path(out).absolute()
    if out.exists() or out.is_symlink():raise ValueError('output must be a new isolated directory')
    sources={n:(HERE/n).read_bytes() for n in ('corpus_guest.dg','corpus_entry.asm','build_guest_corpus.py','guest_corpus_receipt.py')}
    sources['syscall_corpus.py']=(ROOT/'tools/syscall_corpus.py').read_bytes()
    sources['service.ld']=(ROOT/'services/lib/service.ld').read_bytes()
    source_sha={n:sha(v) for n,v in sources.items()}
    packed=data_bytes(rows)
    identity=dict(format='dongos-guest-corpus-build',version=1,generation=str(generation),count=len(rows),mode=mode,corpus_sha256=sha(raw),data_sha256=sha(packed),source_sha256=source_sha)
    binding=sha(json.dumps(identity,sort_keys=True,separators=(',',':')).encode())
    words=struct.unpack('<4Q',bytes.fromhex(binding))
    generated=('module p9.corpus_data;\npub const COUNT:usize='+str(len(rows))+';\npub const GENERATION:u64='+str(generation)+';\npub const BINDING:[4]u64=['+','.join(map(str,words))+'];\npub const CASES:['+str(len(rows))+'][8]u64=['+','.join('['+','.join(map(str,v))+']' for v in values(rows))+'];\n').encode()
    # All validation above precedes creating any output.
    out.mkdir(parents=True,exist_ok=False);snapshot=out/'inputs';snapshot.mkdir()
    for n,v in sources.items():(snapshot/n).write_bytes(v)
    (out/'corpus.jsonl').write_bytes(raw);(out/'cases.bin').write_bytes(packed)
    stage=out/'source/p9';stage.mkdir(parents=True);(stage/'corpus_data.dg').write_bytes(generated);(stage/'corpus_guest.dg').write_bytes(sources['corpus_guest.dg'])
    result=compile_file(stage/'corpus_guest.dg',roots=[out/'source'],mode=mode)
    (out/'program.asm').write_text(result.assembly,encoding='utf-8')
    nasm=find_tool('nasm','NASM');linker=find_tool('ld.lld','LD_LLD');commands=[]
    def run(args):
        p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=90)
        commands.append(dict(argv=list(map(str,args)),returncode=p.returncode,stdout=p.stdout,stderr=p.stderr))
        (out/'commands.json').write_text(json.dumps(commands,indent=2))
        if p.returncode:raise RuntimeError(p.stderr)
    for label,file in [('program',out/'program.asm'),('entry',snapshot/'corpus_entry.asm')]:
        run([nasm,'-O0','-f','elf64',*nasm_flags(nasm),file,'-o',out/(label+'.o')])
    run([linker,'-pie','--no-dynamic-linker','-z','norelro','--build-id=none','-T',snapshot/'service.ld','-o',out/'program.elf',out/'program.o',out/'entry.o'])
    manifest=dict(identity,binding_sha256=binding,generated_sha256=sha(generated),elf_sha256=sha((out/'program.elf').read_bytes()),assembly_sha256=sha((out/'program.asm').read_bytes()))
    (out/'manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
    return manifest
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('corpus',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--generation',type=int,required=True);p.add_argument('--mode',choices=['debug','release'],default='release');a=p.parse_args()
    print(json.dumps(build(a.corpus,a.output,generation=a.generation,mode=a.mode),indent=2))
if __name__=='__main__':main()
