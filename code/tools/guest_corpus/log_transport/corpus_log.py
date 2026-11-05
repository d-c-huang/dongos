"""Decode an exact bounded capture. A serial transcript is not guest attestation."""
from pathlib import Path
import json,re,sys
HERE=Path(__file__).resolve().parent
ROOT=next((p/'code' if (p/'code/tools/syscall_corpus.py').is_file() else p
           for p in HERE.parents if (p/'code/tools/syscall_corpus.py').is_file() or (p/'tools/syscall_corpus.py').is_file()),None)
if ROOT is None:raise RuntimeError('source root not found')
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.guest_corpus.build_guest_corpus import sha
from tools.guest_corpus.guest_corpus_receipt import verify_receipt,unique
TRANSPORT=('corpus_guest.dg','corpus_entry.asm','corpus_log.dg','corpus_log.py','build_log_corpus.py')
MAX_CAPTURE=144+257*80
LINE=re.compile(rb'P9LOG1 ([0-9a-f]{4}) (20|40) ([0-9a-f]+)\n')

def decode(capture):
 if type(capture) is not bytes or not 0<len(capture)<=MAX_CAPTURE:raise ValueError('capture bound/type')
 lines=capture.splitlines(keepends=True)
 if not 3<=len(lines)<=258:raise ValueError('missing or extra record count')
 raw=[]
 for index,line in enumerate(lines):
  m=LINE.fullmatch(line)
  if m is None:raise ValueError('noncanonical, truncated or foreign log line')
  size=int(m[2],16)
  if int(m[1],16)!=index or size!=(64 if index==0 else 32) or len(m[3])!=size*2:raise ValueError('sequence/length mismatch')
  raw.append(bytes.fromhex(m[3].decode('ascii')))
 return b''.join(raw)

def bounded(path,limit=1024*1024):
 with Path(path).open('rb') as f:raw=f.read(limit+1)
 if len(raw)>limit:raise ValueError('artifact bound')
 return raw

def verify_log(build,capture,*,expected_manifest_sha256,generation,exit_code,timed_out,execution='host'):
 if execution!='host':raise ValueError('guest attestation is not implemented')
 raw=decode(capture);build=Path(build)
 envelope_bytes=bounded(build/'transport-manifest.json',65536)
 if sha(envelope_bytes)!=expected_manifest_sha256:raise ValueError('trusted transport manifest differs')
 envelope=json.loads(envelope_bytes,object_pairs_hook=unique)
 if type(envelope) is not dict or set(envelope)!={'format','version','manifest_sha256','transport_source_sha256'} or envelope['format']!='dongos-corpus-log-build' or type(envelope['version']) is not int or envelope['version']!=1:raise ValueError('transport manifest schema')
 hashes=envelope['transport_source_sha256']
 if not isinstance(hashes,dict) or set(hashes)!=set(TRANSPORT):raise ValueError('transport sources schema')
 sources={n:bounded(build/'inputs/transport'/n) for n in TRANSPORT}
 if {n:sha(v) for n,v in sources.items()}!=hashes:raise ValueError('transport source SHA differs')
 bundle=sha(json.dumps(hashes,sort_keys=True,separators=(',',':')).encode())
 guest=('// P9 transport sources SHA256 '+bundle+'\n').encode()+sources['corpus_guest.dg']
 if bounded(build/'inputs/corpus_guest.dg')!=guest:raise ValueError('transport binding differs')
 if bounded(build/'inputs/corpus_entry.asm')!=sources['corpus_entry.asm'] or bounded(build/'source/p9/corpus_log.dg')!=sources['corpus_log.dg']:raise ValueError('compiled transport differs')
 # Bound files before handing the exact raw records to the existing checker.
 for name in ('manifest.json','corpus.jsonl','cases.bin','program.elf','program.asm','source/p9/corpus_data.dg','source/p9/corpus_guest.dg'):
  bounded(build/name)
 for name in ('build_guest_corpus.py','guest_corpus_receipt.py','syscall_corpus.py','service.ld'):bounded(build/'inputs'/name)
 result=verify_receipt(build,raw,expected_manifest_sha256=envelope['manifest_sha256'],generation=generation,exit_code=exit_code,timed_out=timed_out,execution=execution)
 return dict(result,transport_manifest_sha256=expected_manifest_sha256,capture_sha256=sha(capture),transport='P9LOG1')
