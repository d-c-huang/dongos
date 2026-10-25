"""The unchanged complete G5 requirement matrix executed through native ELF."""
from pathlib import Path
from lang.tests import test_g5_full_native as matrix
from lang.tests.l3_elf_observer import ElfObservationMixin,sha

tagged=matrix.tagged
MEMORY=matrix.execution.MEMORY

OriginalRunner=matrix.full.Runner
class ElfRunner(ElfObservationMixin,OriginalRunner):
    pass

class PureElfFullLanguageTests(matrix.FullLanguageNativeTests):
    @classmethod
    def setUpClass(cls):
        matrix.full.Runner=ElfRunner
        try:
            super().setUpClass()
            cls.runner.inputs[str(Path(__file__))]=sha(__file__)
        except BaseException:
            matrix.full.Runner=OriginalRunner
            raise

    @classmethod
    def tearDownClass(cls):
        try:super().tearDownClass()
        finally:matrix.full.Runner=OriginalRunner

    # Same original behavior and opcode assertions; inspect the actual native ELF,
    # since this adapter uses COFF only for absolute observation symbols.
    def test_memory_width_canaries_atomic_old_values_and_asm(self):
        decls=[('load8','int8_t','const int8_t*'),('store8','void','int8_t*,int8_t'),
               ('load64','int64_t','const int64_t*'),('store64','void','int64_t*,int64_t'),('safe_asm','U','void')]
        for n in (32,64):
            c='uint'+str(n)+'_t';p=c+'*';suffix=str(n)
            decls += [('aload'+suffix,c,'const '+p),('astore'+suffix,'void',p+','+c),
                      ('cas'+suffix,c,p+','+c+','+c),('fetch'+suffix,c,p+','+c)]
        self.differential('memory',MEMORY,tagged.observer(decls,
            'unsigned char b[16];memset(b,0xa7,sizeof b);f_store8((int8_t*)b+1,-7);'
            'CHECK(f_load8((int8_t*)b+1)==-7&&b[0]==0xa7&&b[2]==0xa7);'
            'f_store64((int64_t*)(b+3),-1234567890123LL);CHECK(f_load64((int64_t*)(b+3))==-1234567890123LL&&b[2]==0xa7&&b[11]==0xa7);'
            'uint32_t a=17;U z=0x100000005ULL;CHECK(f_cas32(&a,16,23)==17&&a==17);'
            'CHECK(f_cas32(&a,17,23)==17&&a==23&&f_fetch32(&a,0xffffffffU)==23&&a==22);'
            'f_astore32(&a,99);CHECK(f_aload32(&a)==99);'
            'CHECK(f_cas64(&z,5,33)==0x100000005ULL&&z==0x100000005ULL);'
            'CHECK(f_cas64(&z,0x100000005ULL,0xffffffffffffffffULL)==0x100000005ULL);'
            'CHECK(f_fetch64(&z,2)==0xffffffffffffffffULL&&z==1);'
            'f_astore64(&z,0x8877665544332211ULL);CHECK(f_aload64(&z)==0x8877665544332211ULL&&f_safe_asm()==7);'))
        machine=Path(self.runner.cases[-1]['native']['assembly_path']).with_suffix('.native.elf').read_bytes()
        self.assertIn(bytes.fromhex('fafbf4cc'),machine)
        for instruction in ('f390','0faee8','0faef8','0faef0'):
            self.assertIn(bytes.fromhex(instruction),machine)
