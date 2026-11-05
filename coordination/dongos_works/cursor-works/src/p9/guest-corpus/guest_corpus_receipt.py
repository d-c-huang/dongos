"""Strict raw execution receipt checks. Host evidence never attests guest execution."""
from pathlib import Path
import hashlib,json,struct
from build_guest_corpus import selected,data_bytes,sha

BEGIN=0x5039424547494e31
CASE=0x5039434153453031
END=0x5039454e44303031
IDENTITY=('format','version','generation','count','mode','corpus_sha256','data_sha256','source_sha256')
EXTRA=('binding_sha256','generated_sha256','elf_sha256','assembly_sha256')
def unique(pairs):
    out={}
    for k,v in pairs:
        if k in out:raise ValueError('duplicate manifest key')
        out[k]=v
    return out
def verify_receipt(build,raw,*,expected_manifest_sha256,generation,exit_code,timed_out,execution='host'):
    if execution!='host':raise ValueError('guest attestation is not implemented; host evidence only')
    if type(generation) is not int or not 0<generation<2**64:raise ValueError('generation required')
    if type(exit_code) is not int or exit_code!=0 or timed_out is not False:raise ValueError('execution crashed, failed or timed out')
    build=Path(build);manifest_bytes=(build/'manifest.json').read_bytes()
    if sha(manifest_bytes)!=expected_manifest_sha256:raise ValueError('trusted build manifest digest differs')
    m=json.loads(manifest_bytes,object_pairs_hook=unique)
    if set(m)!=set(IDENTITY+EXTRA) or m['format']!='dongos-guest-corpus-build' or type(m['version']) is not int or m['version']!=1:raise ValueError('manifest schema')
    if m['generation']!=str(generation):raise ValueError('stale build generation')
    if type(m['count']) is not int or not 1<=m['count']<=256:raise ValueError('invalid count')
    if set(m['source_sha256'])!={'corpus_guest.dg','corpus_entry.asm','build_guest_corpus.py','guest_corpus_receipt.py','syscall_corpus.py','service.ld'}:raise ValueError('source manifest differs')
    for n,digest in m['source_sha256'].items():
        if sha((build/'inputs'/n).read_bytes())!=digest:raise ValueError('source SHA differs: '+n)
    for path,key in [('corpus.jsonl','corpus_sha256'),('cases.bin','data_sha256'),('program.elf','elf_sha256'),('program.asm','assembly_sha256'),('source/p9/corpus_data.dg','generated_sha256')]:
        if sha((build/path).read_bytes())!=m[key]:raise ValueError('artifact SHA differs: '+path)
    if (build/'source/p9/corpus_guest.dg').read_bytes()!=(build/'inputs/corpus_guest.dg').read_bytes():raise ValueError('compiled source differs')
    _,rows=selected((build/'corpus.jsonl').read_bytes())
    if len(rows)!=m['count'] or data_bytes(rows)!=(build/'cases.bin').read_bytes():raise ValueError('generated cases differ')
    binding=sha(json.dumps({k:m[k] for k in IDENTITY},sort_keys=True,separators=(',',':')).encode())
    if binding!=m['binding_sha256']:raise ValueError('binding SHA differs')
    count=len(rows)
    if type(raw) is not bytes or len(raw)!=64+32*count+32:raise ValueError('truncated, missing or extra receipt records')
    header=struct.unpack_from('<8Q',raw)
    if header!=(BEGIN,1,generation,count,*struct.unpack('<4Q',bytes.fromhex(binding))):raise ValueError('receipt build/generation header differs')
    actual=[]
    for index,row in enumerate(rows):
        tag,gen,observed,value=struct.unpack_from('<4Q',raw,64+32*index)
        if (tag,gen,observed)!=(CASE,generation,index):raise ValueError('missing, duplicate, reordered or stale case')
        expected=int(row['oracle']['code'],16) if row['oracle']['code'] else 0
        if value!=expected:raise ValueError('raw return mismatch at case '+str(index))
        actual.append(value)
    if struct.unpack_from('<4Q',raw,64+32*count)!=(END,generation,count,0):raise ValueError('missing or failed terminal record')
    return dict(evidence='host-boundary-only',guest_verified=False,count=count,generation=str(generation),returns=actual,manifest_sha256=expected_manifest_sha256,raw_sha256=sha(raw))
