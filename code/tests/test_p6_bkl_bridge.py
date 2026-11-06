"""Actual complete Bridge/FIFO/Domain native integration; hardware is synthetic."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
from lang.dongc import compile_file
from lang.tests.test_dongc import tool, nasm_flags

CAND = ROOT / 'kernel/sched'
DG_EXTRA = '''
import sched.user_bkl as fifo;
export("bf_state") fn state()*const fifo.State{return fifo.pointer();}
export("bf_retire") fn retire(slot:usize)u64{unsafe{
 match bridge.retire(slot){ok=>{return 0;},err(e)=>{return e;},}
}}
'''
C_EXTRA = '''
typedef struct {U ready;Domain*domain;U next,serving,owner,wait[16];} Fifo;
extern const Fifo* ABI bf_state(void);
extern U ABI bf_retire(U),dong_user_smp_barrier(void);
static U runtime,nested,admissions,parked,returned;
static void fifo_ticket(void){const Fifo*s=bf_state();C(s->ready==1&&s->domain==d);
 C(s->owner==cpu&&s->wait[cpu]==s->serving+1&&s->next==s->serving+1);}
static void fifo_owned(void){fifo_ticket();
 C(d->lock==1&&d->owner==cpu);}
static U after_call(U value,U ticket){const Fifo*s=bf_state();if(value!=UINT64_MAX){
 C(!d->failed&&!d->lock&&d->owner==16&&s->owner==16);
 C(s->next==ticket+1&&s->serving==ticket+1);for(unsigned i=0;i<16;i++)C(!s->wait[i]);
 admissions++;if(value) returned++;else parked++;
 }runtime=0;return value;}
static U checked_idle(U who,U vector){U ticket=bf_state()->next;runtime=1;return after_call(dong_user_smp_idle(who,vector),ticket);}
static U checked_event(U who,U frame,U vector){U ticket=bf_state()->next;runtime=1;return after_call(dong_user_smp_event(who,frame,vector),ticket);}
static void nested_calls(void){if(!nested)return;nested=0;fifo_owned();
 U ticket=bf_state()->next,sequence=d->completed;
 C(!dong_user_smp_barrier()&&d->completed==sequence+1);fifo_owned();C(bf_state()->next==ticket);
 C(d->processes[1].token);C(!bf_retire(1)&&!d->processes[1].token);
 fifo_owned();C(bf_state()->next==ticket&&d->completed==sequence+2);
}
'''


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


class BridgeFifoTests(unittest.TestCase):
    def test_actual_entry_paths_and_rejected_bad_wiring(self):
        source = (CAND / 'user_bridge.dg').read_text(encoding='utf-8')
        controls = {
            'missing-bind': ('try bkl.bind(d);', '', 0),
            'capture-direct': ('try bkl.acquire(d,cpu,limit);', 'try ud.acquire(d,cpu,limit);', 0),
            'idle-direct': ('try bkl.acquire(d,cpu,limit);', 'try ud.acquire(d,cpu,limit);', 1),
            'park-direct-unlock': ('try bkl.unlock(d,cpu);', 'try ud.unlock(d,cpu);', 0),
            'return-direct-unlock': ('try bkl.unlock(d,cpu);', 'try ud.unlock(d,cpu);', 1),
            'all-direct': ('bkl.acquire(d,cpu,limit)', 'ud.acquire(d,cpu,limit)', -1),
            'nested-barrier-ticket': ('let sequence=try ud.barrier_begin(d,0);', 'try bkl.acquire(d,0,try deadline(d,0));let sequence=try ud.barrier_begin(d,0);', 0),
            'nested-retire-ticket': ('let sequence=try ud.retire_begin(d,0,slot);', 'try bkl.acquire(d,0,try deadline(d,0));let sequence=try ud.retire_begin(d,0,slot);', 0),
        }
        common = (ROOT / 'tests/user_current_entry_probe.c').read_text(encoding='utf-8')
        # Instrument hardware/caller boundaries, never rewrite the actual Dong lock.
        pos = common.index('void ABI __dong_panic')
        common = common[:pos] + C_EXTRA + common[pos:]
        common = common.replace('void ABI __dong_panic(void){fail("Dong panic",__LINE__);}',
                                'void ABI __dong_panic(void){fputs("UNEXPECTED_DONG_PANIC",stderr);exit(97);}')
        common = common.replace('void ABI user_smp_arch_unlock(U*p){C(*p==1);',
                                'void ABI user_smp_arch_unlock(U*p){if(runtime){fifo_ticket();C(d->owner==16);}C(*p==1);')
        common = common.replace('U ABI user_bridge_project(void){C(', 'U ABI user_bridge_project(void){nested_calls();C(')
        # Only fixture callers are wrapped; the real exported symbols remain intact.
        pos = common.index('static void start(')
        common = common[:pos] + common[pos:].replace('dong_user_smp_idle(', 'checked_idle(').replace('dong_user_smp_event(', 'checked_event(')
        anchor = ' /* Foreign CPU cannot use another header/capture ticket to mutate state. */'
        self.assertEqual(1, common.count(anchor))
        common = common.replace(anchor, '''
 C(admissions>=9&&parked>=3&&returned>=3);nested=1;cpu=0;
 C(!checked_idle(0,257)&&!nested&&!d->failed);C(!ue_audit());
''' + anchor)
        common += '\nU ABI user_bridge_service_policy(U a,U b,U c){(void)a;(void)b;(void)c;return 0;}\n'
        probe = (ROOT / 'tests/user_current_entry_probe.dg').read_text(encoding='utf-8') + DG_EXTRA
        watched = [Path(__file__), ROOT/'docs/p6-bkl-bridge.md', *sorted((ROOT/'kernel').rglob('*.*')),
                   *sorted((ROOT/'include').glob('*.inc')), *sorted((ROOT/'lang/dongc').glob('*.py')),
                   ROOT/'lang/tests/test_dongc.py', ROOT/'tests/user_current_entry_probe.dg', ROOT/'tests/user_current_entry_probe.c']
        hashes = lambda: {str(p): digest(p) for p in watched if p.is_file()}
        before = hashes()
        nasm, cc = tool('nasm', 'NASM'), tool('gcc', 'CC')
        self.assertTrue(nasm and cc, 'NASM and CC required; no skip')
        tools = {str(Path(p).resolve()): digest(Path(p)) for p in (sys.executable, nasm, cc)}
        out = ROOT/'build/test/p6-bkl-bridge'/('run-'+uuid.uuid4().hex[:12])
        out.mkdir(parents=True)
        evidence, commands = [], []
        passed = False
        def run(argv, directory, label):
            argv = list(map(str, argv))
            r = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=90)
            record = dict(argv=argv, returncode=r.returncode, stdout=r.stdout, stderr=r.stderr)
            (directory/(label+'.json')).write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
            commands.append(record)
            return r
        try:
            for mode in ('debug', 'release'):
                for variant in ('normal', *controls):
                    directory = out/(mode+'-'+variant)
                    shutil.copytree(ROOT/'kernel', directory/'kernel')
                    text = source
                    if variant != 'normal':
                        old, new, index = controls[variant]
                        expected = 2 if 'acquire(d,cpu,limit)' in old or 'unlock(d,cpu)' in old else 1
                        self.assertEqual(expected, text.count(old), variant)
                        if index == -1:
                            text = text.replace(old, new).replace('bkl.unlock(d,cpu)', 'ud.unlock(d,cpu)')
                        else:
                            chunks = text.split(old)
                            text = old.join(chunks[:index+1])+new+old.join(chunks[index+1:])
                    (directory/'kernel/sched/user_bridge.dg').write_text(text, encoding='utf-8')
                    entry = directory/'user_current_entry_probe.dg'; entry.write_text(probe, encoding='utf-8')
                    c = directory/'probe.c'; c.write_text(common, encoding='utf-8')
                    compiled = compile_file(entry, roots=[directory, directory/'kernel'], mode=mode)
                    layouts = {t['full_name']:t for t in compiled.layout_manifest['types']}
                    for name, size in [('sched.user_bkl.State',192),('sched.user_domain.Domain',120),
                                       ('sched.user_domain.Cpu',120),('sched.user_bridge.Bridge',64),('sched.user_bridge.Failure',224)]:
                        self.assertEqual(size, layouts[name]['size'])
                    asm = directory/'probe.asm'; asm.write_text(compiled.assembly, encoding='utf-8')
                    (directory/'layout.json').write_text(json.dumps(compiled.layout_manifest, indent=2), encoding='utf-8')
                    objects=[]
                    for name, path in [('dong',asm),('entry',ROOT/'kernel/sched/user_entry.asm'),('legacy',ROOT/'kernel/sched/user_legacy.asm')]:
                        obj=directory/(name+'.o');objects.append(obj)
                        r=run([nasm,'-f','win64' if os.name=='nt' else 'elf64',*nasm_flags(nasm),'-I',str(ROOT/'include')+os.sep,path,'-o',obj],directory,'assemble-'+name)
                        self.assertEqual(0,r.returncode,r.stderr)
                    exe=directory/('probe.exe' if os.name=='nt' else 'probe')
                    r=run([cc,'-std=c11','-O2','-Wall','-Wextra','-Werror',*([] if os.name=='nt' else ['-no-pie']),c,*objects,'-o',exe],directory,'link')
                    self.assertEqual(0,r.returncode,r.stderr)
                    r=run([exe],directory,'native')
                    self.assertNotIn('UNEXPECTED_DONG_PANIC',r.stderr)
                    self.assertEqual(0 if variant=='normal' else 1,r.returncode,r.stdout+r.stderr)
                    self.assertIn('native checks=' if variant=='normal' else 'oracle line',r.stdout+r.stderr)
                    evidence.append(dict(mode=mode,variant=variant,returncode=r.returncode,bridge_sha256=digest(directory/'kernel/sched/user_bridge.dg'),exe_sha256=digest(exe)))
            passed=True
        finally:
            after=hashes();stable=before==after and all(digest(Path(p))==h for p,h in tools.items())
            (out/'validation-summary.json').write_text(json.dumps(dict(passed=passed and stable,evidence=evidence,
                source_before=before,source_after=after,sources_unchanged=before==after,tools=tools,stable=stable,
                commands=commands,skipped=[],actual_bridge_domain_fifo=True,hardware_mocked=True,guest_executed=False),indent=2)+'\n',encoding='utf-8')
            print('P6_BKL_BRIDGE_EVIDENCE',out)
        self.assertTrue(stable)


if __name__ == '__main__':
    unittest.main(verbosity=2)
