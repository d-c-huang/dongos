"""Positive and rejection controls for actual service pool ownership checks."""
import unittest
from tests.run_services_qemu import verify_private_pools


class PoolOwnershipTests(unittest.TestCase):
    def fixture(self):
        arena=0x40000000
        root=arena+64*4096
        pointer=0xffffd40000000000+64*4096
        return dict(roots=[0x200000,0x220000,root],static_count=2,table_base=0x200000,
                    dynamic=[0,0,root]+[0]*13,pointers=[0,0,pointer]+[0]*13,
                    limits=[32]*16,arena=arena,arena_bytes=128*1024*1024,next_page=96,
                    kernel_root=0x100000,mapping=lambda va:root+va-pointer|0x8000000000000003)

    def test_dynamic_and_legacy_static_profiles(self):
        f=self.fixture();verify_private_pools(**f)
        f.update(static_count=3,roots=[0x200000,0x220000,0x240000],dynamic=[0]*16,pointers=[0]*16)
        verify_private_pools(**f)

    def test_identity_and_capacity_rejections(self):
        for key,index,value in [('roots',2,0x240000),('roots',1,0x200000),
                                ('dynamic',2,0x40041000),('pointers',2,0xffffd40000041000),
                                ('dynamic',0,0x200000),('limits',2,128)]:
            with self.subTest(key=key,index=index):
                f=self.fixture();f[key][index]=value
                with self.assertRaises(ValueError):verify_private_pools(**f)

    def test_extent_overlap_and_profile_rejections(self):
        for change in [dict(next_page=95),dict(next_page=32769),dict(arena_bytes=4096),
                       dict(arena=0),dict(kernel_root=0x40040000),dict(static_count=1),
                       dict(static_count=3)]:
            with self.subTest(change=change):
                f=self.fixture();f.update(change)
                with self.assertRaises(ValueError):verify_private_pools(**f)

    def test_every_dynamic_page_requires_exact_supervisor_mapping(self):
        for page in (0,15,31):
            for xor in (1,2,4,8,16,128,4096,1<<63):
                with self.subTest(page=page,xor=xor):
                    f=self.fixture();good=f['mapping'];bad=f['pointers'][2]+page*4096
                    f['mapping']=lambda va:good(va)^(xor if va==bad else 0)
                    with self.assertRaises(ValueError):verify_private_pools(**f)

    def test_accessed_dirty_bits_are_not_ownership_changes(self):
        f=self.fixture();good=f['mapping'];f['mapping']=lambda va:good(va)|0x60
        verify_private_pools(**f)


if __name__=='__main__':unittest.main()
