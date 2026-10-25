/* Independent native loader preparation oracle. Never executes copied code. */
#ifndef _WIN32
#define _GNU_SOURCE
#endif
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#include <windows.h>
#else
#include <sys/mman.h>
#include <unistd.h>
#endif
#define EFI __attribute__((ms_abi))
typedef uint64_t U;
extern U EFI loader_image_range(U,U,U);
extern U EFI loader_handoff_prepare(void *,U,U);
extern U EFI handoff_probe_invoke(void *,U,U,U);
extern const unsigned char loader_handoff_template[],loader_handoff_end[],loader_handoff_target[];
static const U kernel_base=UINT64_C(0xffffffff80000000);
static unsigned checks;
static const char *where="setup";
#define REQUIRE(x) do { ++checks; if(!(x)){fprintf(stderr,"loader handoff oracle case=%s check=%s line=%d; returned normally\n",where,#x,__LINE__);return 1;} } while(0)

static unsigned char *allocation;
static unsigned char *destination;
static size_t allocation_bytes=3*4096;
static unsigned char snapshot[3*4096];
static size_t blob_bytes,target_offset;

static int allocate_low(void) {
    for(U address=UINT64_C(0x20000000);address<UINT64_C(0xe0000000);address+=0x1000000) {
#ifdef _WIN32
        allocation=VirtualAlloc((void *)(uintptr_t)address,allocation_bytes,
                                 MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
        if(allocation){break;}
#else
        int flags=MAP_PRIVATE|MAP_ANONYMOUS;
#ifdef MAP_FIXED_NOREPLACE
        flags|=MAP_FIXED_NOREPLACE;
#endif
        void *candidate=mmap((void *)(uintptr_t)address,allocation_bytes,
                              PROT_READ|PROT_WRITE,flags,-1,0);
        if(candidate==MAP_FAILED){continue;}
        if((uintptr_t)candidate!=address){munmap(candidate,allocation_bytes);continue;}
        allocation=candidate;break;
#endif
    }
    REQUIRE(allocation!=NULL);
    REQUIRE(((uintptr_t)allocation&4095)==0);
    REQUIRE((U)(uintptr_t)allocation+allocation_bytes<=UINT64_C(0x100000000));
    destination=allocation+4096;
    return 0;
}

static int validate_copy(U entry,U capacity) {
    memset(allocation,0xa5,allocation_bytes);
    REQUIRE(handoff_probe_invoke((void *)loader_handoff_prepare,(U)(uintptr_t)destination,capacity,entry)==0);
    for(size_t i=0;i<allocation_bytes;i++) {
        unsigned char expected=0xa5;
        if(i>=4096&&i<4096+blob_bytes) {
            size_t offset=i-4096;
            expected=loader_handoff_template[offset];
            if(offset>=target_offset&&offset<target_offset+8) {
                expected=(unsigned char)(entry>>((offset-target_offset)*8));
            }
        }
        REQUIRE(allocation[i]==expected);
    }
    U patched;memcpy(&patched,destination+target_offset,8);
    REQUIRE(patched==entry);
    return 0;
}

static int invalid_copy(U address,U capacity,U entry) {
    memset(allocation,0x3c,allocation_bytes);memcpy(snapshot,allocation,allocation_bytes);
    REQUIRE(handoff_probe_invoke((void *)loader_handoff_prepare,address,capacity,entry)==1);
    REQUIRE(memcmp(snapshot,allocation,allocation_bytes)==0);
    return 0;
}

static int instruction_contract(void) {
    const unsigned char prologue[]={0xf3,0x0f,0x1e,0xfa,0xfa,0xfc};
    REQUIRE(blob_bytes>=sizeof(prologue));
    REQUIRE(memcmp(loader_handoff_template,prologue,sizeof(prologue))==0);
    const U gdt_words[]={0,UINT64_C(0x00af9b000000ffff),UINT64_C(0x00cf93000000ffff)};
    size_t gdt=blob_bytes,gdt_count=0;
    for(size_t i=0;i+sizeof(gdt_words)<=blob_bytes;i++) {
        if(memcmp(loader_handoff_template+i,gdt_words,sizeof(gdt_words))==0){gdt=i;++gdt_count;}
    }
    REQUIRE(gdt_count==1);
    REQUIRE(gdt+44==target_offset);
    REQUIRE(loader_handoff_template[gdt+24]==23&&loader_handoff_template[gdt+25]==0);
    for(size_t i=gdt+26;i<gdt+44;i++){REQUIRE(loader_handoff_template[i]==0);}
    size_t cli=blob_bytes,lgdt=blob_bytes,lidt=blob_bytes,cr3=blob_bytes;
    size_t rip_count=0,lea_count=0,store_count=0,load_count=0;
    for(size_t i=0;i<blob_bytes;i++) {
        if(loader_handoff_template[i]==0xfa&&cli==blob_bytes){cli=i;}
        if(i+2>=blob_bytes){continue;}
        const unsigned char *p=loader_handoff_template+i;
        if(p[0]==0x0f&&p[1]==0x01&&(p[2]&0xc0)!=0xc0) {
            unsigned group=(p[2]>>3)&7;
            if(group==2&&lgdt==blob_bytes){lgdt=i;}
            if(group==3&&lidt==blob_bytes){lidt=i;}
        }
        if(p[0]==0x0f&&p[1]==0x22&&(p[2]&0xf8)==0xd8&&cr3==blob_bytes){cr3=i;}
    }
    /* Decode the reviewed RIP-relative machine forms independently. Every
       target must remain valid after copying away from the PE image. */
    for(size_t i=0;i<gdt;i++) {
        const unsigned char *p=loader_handoff_template+i;
        size_t bytes=0,displacement_offset=0;unsigned kind=0;
        if(i+7<=gdt&&p[0]==0x48&&p[2]==0x05) {
            if(p[1]==0x8d){kind=1;}
            if(p[1]==0x89){kind=2;}
            if(p[1]==0x8b){kind=3;}
            if(kind){bytes=7;displacement_offset=3;}
        }
        if(i+7<=gdt&&p[0]==0x48&&p[1]==0x8d&&p[2]==0x35) {
            kind=6;bytes=7;displacement_offset=3;
        }
        if(i+7<=gdt&&p[0]==0x0f&&p[1]==0x01&&(p[2]==0x15||p[2]==0x1d)) {
            kind=p[2]==0x15?4:5;bytes=7;displacement_offset=3;
        }
        if(bytes) {
            int32_t displacement;memcpy(&displacement,p+displacement_offset,4);
            int64_t target=(int64_t)(i+bytes)+(int64_t)displacement;
            REQUIRE(target>=0&&(U)target<blob_bytes);++rip_count;
            if(kind==1) {
                if(lea_count==0){REQUIRE((size_t)target==gdt);}
                else if(lea_count==1){
                    REQUIRE(target>=2&&loader_handoff_template[target-2]==0x48&&loader_handoff_template[target-1]==0xcb);
                    REQUIRE(loader_handoff_template[target]==0x31&&loader_handoff_template[target+1]==0xed);
                }else {
                    REQUIRE(loader_handoff_template[target]==0xfa);
                }
                ++lea_count;
            }else if(kind==2){REQUIRE((size_t)target==gdt+26);++store_count;}
            else if(kind==3){REQUIRE((size_t)target==target_offset);++load_count;}
            else if(kind==4){REQUIRE((size_t)target==gdt+24);}
            else if(kind==5){REQUIRE((size_t)target==gdt+34);}
            else {
                const char error[]="DONGOS_P1_FAIL:E14_KERNEL_RETURNED\r\n";
                REQUIRE((size_t)target+sizeof(error)<=gdt);
                REQUIRE(memcmp(loader_handoff_template+target,error,sizeof(error))==0);
            }
        }
    }
    REQUIRE(rip_count==8&&lea_count==3&&store_count==1&&load_count==1);
    REQUIRE(cli<lgdt);
    REQUIRE(lgdt<cr3);
    REQUIRE(lidt<cr3);
    REQUIRE(cr3<target_offset);
    return 0;
}

int main(void) {
    where="range-boundaries";
    const U ranges[][4]={
        {0,4096,0,0},{4096,0,4096,0},{4096,4096,4096,1},
        {4096,4096,8191,1},{4096,4096,4095,0},{4096,4096,8192,0},
        {UINT64_C(0x140000000),0x12000,UINT64_C(0x140001000),1},
        {UINT64_C(0xfffff000),0x2000,UINT64_C(0x100000000),1},
        {UINT64_MAX-4095,4095,UINT64_MAX-1,1},
        {UINT64_MAX-4095,4096,UINT64_MAX-1,0},
        {UINT64_MAX,1,UINT64_MAX,0},{1,UINT64_MAX,1,0},
        {1,UINT64_MAX-1,UINT64_MAX-1,1},
        {UINT64_C(0x8000000000000000),4096,UINT64_C(0x8000000000000000),1}
    };
    for(size_t i=0;i<sizeof(ranges)/sizeof(ranges[0]);i++) {
        REQUIRE(handoff_probe_invoke((void *)loader_image_range,ranges[i][0],ranges[i][1],ranges[i][2])==ranges[i][3]);
    }
    where="template-bounds";
    blob_bytes=(size_t)((uintptr_t)loader_handoff_end-(uintptr_t)loader_handoff_template);
    target_offset=(size_t)((uintptr_t)loader_handoff_target-(uintptr_t)loader_handoff_template);
    REQUIRE(blob_bytes>0&&blob_bytes<=4096);
    REQUIRE(target_offset+8<=blob_bytes);
    unsigned char original[4096];memcpy(original,loader_handoff_template,blob_bytes);
    REQUIRE(instruction_contract()==0);
    REQUIRE(allocate_low()==0);
    where="invalid-copy-does-not-write";
    U dest=(U)(uintptr_t)destination;
    REQUIRE(invalid_copy(dest,4095,kernel_base)==0);
    REQUIRE(invalid_copy(dest,0,kernel_base)==0);
    REQUIRE(invalid_copy(dest,4096,kernel_base-1)==0);
    REQUIRE(invalid_copy(dest,4096,kernel_base+0x200000)==0);
    REQUIRE(invalid_copy(dest,4096,0)==0);
    REQUIRE(invalid_copy(dest+1,4096,kernel_base)==0);
    REQUIRE(invalid_copy(0,4096,kernel_base)==0);
    REQUIRE(invalid_copy(UINT64_C(0x100000000),4096,kernel_base)==0);
    REQUIRE(invalid_copy(UINT64_MAX&~UINT64_C(4095),UINT64_MAX,kernel_base)==0);
    where="exact-copy-and-only-target-patch";
    REQUIRE(validate_copy(kernel_base,4096)==0);
    REQUIRE(validate_copy(kernel_base+0x1000,8192)==0);
    REQUIRE(validate_copy(kernel_base+0x1fffff,UINT64_MAX)==0);
    REQUIRE(memcmp(original,loader_handoff_template,blob_bytes)==0);
#ifdef _WIN32
    REQUIRE(VirtualFree(allocation,0,MEM_RELEASE)!=0);
#else
    REQUIRE(munmap(allocation,allocation_bytes)==0);
#endif
    printf("loader handoff oracle passed; checks=%u blob=%zu target=%zu; MS ABI/range/copy/canaries/invalid guards; privileged blob not executed; returned normally\n",checks,blob_bytes,target_offset);
    return 0;
}
