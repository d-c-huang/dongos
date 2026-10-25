/* Independent byte fixtures and output sentinels for the actual Dong module. */
#ifndef _WIN32
#define _GNU_SOURCE
#endif
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#include <windows.h>
#else
#include <sys/mman.h>
#include <unistd.h>
#endif
#define SYSV __attribute__((sysv_abi))
typedef uint64_t U;
typedef struct {U base,capacity,disk_capacity;} View;
_Static_assert(sizeof(View)==24,"independent three-word partition view");
extern U SYSV up_inspect(const uint8_t*,U,U,View*);
extern U SYSV up_translate(const View*,U,U,U*);
void SYSV __dong_panic(U code,const char *text,U length) {
    (void)text;(void)length;fprintf(stderr,"unexpected Dong panic %llu\n",(unsigned long long)code);exit(9);
}
enum {INVALID=0x081f0001,UNSUPPORTED=0x081f0002,BOUNDS=0x081f0003};
static unsigned checks;
static const char *where="startup";
#define CHECK(x) do {++checks;if(!(x)){fprintf(stderr,"USB_PARTITION_ASSERT case=%s line=%d; returned normally\n",where,__LINE__);return 1;}}while(0)
static uint8_t sector[512],saved[512];
static void p16(size_t at,U v) {sector[at]=(uint8_t)v;sector[at+1]=(uint8_t)(v>>8);}
static void p32(size_t at,U v) {p16(at,v);p16(at+2,v>>16);}
static void signature(void) {sector[510]=0x55;sector[511]=0xaa;}
static void entry(unsigned index,unsigned kind,unsigned boot,U base,U count) {
    size_t at=446+(size_t)index*16;sector[at]=(uint8_t)boot;sector[at+4]=(uint8_t)kind;
    p32(at+8,base);p32(at+12,count);
}
static void mbr(unsigned index,unsigned kind,unsigned boot,U base,U count) {
    memset(sector,0,sizeof(sector));signature();entry(index,kind,boot,base,count);
}
static void bpb(U total,unsigned spc,U fat) {
    memset(sector,0,sizeof(sector));signature();sector[0]=0xeb;sector[1]=0x58;sector[2]=0x90;
    memcpy(sector+3,"MSDOS5.0",8);p16(11,512);sector[13]=(uint8_t)spc;p16(14,32);
    sector[16]=2;sector[21]=0xf8;p32(32,total);p32(36,fat);p32(44,2);p16(48,1);p16(50,6);
    memcpy(sector+82,"FAT32   ",8);
}
static int inspect_ok(U disk,U base,U capacity) {
    struct {U before[2];View view;U after[2];} out;
    memset(&out,0xa5,sizeof(out));memcpy(saved,sector,512);
    CHECK(up_inspect(sector,512,disk,&out.view)==0);
    CHECK(out.view.base==base&&out.view.capacity==capacity&&out.view.disk_capacity==disk);
    CHECK(out.before[0]==UINT64_C(0xa5a5a5a5a5a5a5a5)&&out.before[1]==out.before[0]);
    CHECK(out.after[0]==out.before[0]&&out.after[1]==out.before[0]);CHECK(memcmp(saved,sector,512)==0);
    return 0;
}
static int inspect_bad(U disk,U expected) {
    struct {U before[2];View view;U after[2];} out,previous;
    memset(&out,0xa5,sizeof(out));previous=out;memcpy(saved,sector,512);
    CHECK(up_inspect(sector,512,disk,&out.view)==expected);
    CHECK(memcmp(&out,&previous,sizeof(out))==0);CHECK(memcmp(saved,sector,512)==0);
    return 0;
}
static int bad_translation(const View *view,U lba,U count,U error) {
    U result=UINT64_C(0x123456789abcdef0);
    View previous={0};if(view)previous=*view;
    CHECK(up_translate(view,lba,count,&result)==error);CHECK(result==UINT64_C(0x123456789abcdef0));
    if(view)CHECK(memcmp(view,&previous,sizeof(previous))==0);
    return 0;
}
static int guard_sector(void) {
    uint8_t *allocation;size_t page;
#ifdef _WIN32
    SYSTEM_INFO info;GetSystemInfo(&info);page=info.dwPageSize;
    allocation=VirtualAlloc(NULL,page*2,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);CHECK(allocation!=NULL);
    DWORD old_protection;CHECK(VirtualProtect(allocation+page,page,PAGE_NOACCESS,&old_protection));
#else
    page=(size_t)sysconf(_SC_PAGESIZE);
    allocation=mmap(NULL,page*2,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);CHECK(allocation!=MAP_FAILED);
    CHECK(mprotect(allocation+page,page,PROT_NONE)==0);
#endif
    bpb(131072,1,1024);uint8_t *edge=allocation+page-512;memcpy(edge,sector,512);
    View out={7,8,9},old=out;
    CHECK(up_inspect(edge,511,131072,&out)==INVALID);CHECK(memcmp(&out,&old,sizeof(out))==0);
    CHECK(up_inspect(edge,512,131072,&out)==0&&out.base==0&&out.capacity==131072);
    CHECK(up_inspect(edge,4096,131072,&out)==0); /* Reads only the first sector. */
#ifdef _WIN32
    CHECK(VirtualFree(allocation,0,MEM_RELEASE));
#else
    CHECK(munmap(allocation,page*2)==0);
#endif
    return 0;
}
int main(void) {
    where="valid superfloppy";bpb(131072,1,1024);CHECK(inspect_ok(131072,0,131072)==0);
    CHECK(inspect_ok(262144,0,131072)==0);sector[0]=0xe9;sector[2]=0;CHECK(inspect_ok(131072,0,131072)==0);
    bpb(1048576,8,1024);CHECK(inspect_ok(1048576,0,1048576)==0);
    bpb(15231744,8,14900);CHECK(inspect_ok(15232000,0,15231744)==0);
    where="valid MBR entries";
    for(unsigned slot=0;slot<4;slot++)for(unsigned type=0;type<3;type++)for(unsigned active=0;active<2;active++) {
        const unsigned kinds[]={0x0b,0x0c,0xef};mbr(slot,kinds[type],active?0x80:0,2048,131072);
        CHECK(inspect_ok(133120,2048,131072)==0);
        mbr(slot,kinds[type],active?0x80:0,2048,131072);CHECK(inspect_ok(262144,2048,131072)==0);
    }
    where="actual SanDisk-sized MBR";mbr(0,0x0c,0x80,256,15231744);CHECK(inspect_ok(15232000,256,15231744)==0);
    where="top READ10 sector boundary";mbr(0,0x0c,0,256,UINT32_MAX-256);CHECK(inspect_ok(UINT32_MAX,256,UINT32_MAX-256)==0);
    where="empty malformed and ambiguous tables";
    memset(sector,0,512);signature();CHECK(inspect_bad(262144,INVALID)==0);
    mbr(0,0x0c,0,2048,131072);entry(1,0x0c,0,135168,65536);CHECK(inspect_bad(262144,INVALID)==0);
    mbr(0,0x0c,0,2048,131072);entry(1,0x0b,0,2049,65536);CHECK(inspect_bad(262144,INVALID)==0);
    mbr(0,0x0c,0,2048,131072);sector[446+16+1]=1;CHECK(inspect_bad(262144,INVALID)==0);
    mbr(0,0x0c,0x7f,2048,131072);CHECK(inspect_bad(262144,INVALID)==0);
    mbr(0,0x0c,0,2048,131072);p16(444,1);CHECK(inspect_bad(262144,INVALID)==0);
    mbr(0,0x0c,0,2048,131072);sector[511]=0;CHECK(inspect_bad(262144,INVALID)==0);
    for(unsigned i=0;i<6;i++) {
        const unsigned kinds[]={0xee,0x05,0x0f,0x85,0x07,0};mbr(0,kinds[i],0,2048,131072);
        CHECK(inspect_bad(262144,UNSUPPORTED)==0);
    }
    where="partition bounds";
    mbr(0,0x0c,0,0,131072);CHECK(inspect_bad(262144,BOUNDS)==0);
    mbr(0,0x0c,0,262144,65536);CHECK(inspect_bad(262144,BOUNDS)==0);
    mbr(0,0x0c,0,2048,0);CHECK(inspect_bad(262144,BOUNDS)==0);
    mbr(0,0x0c,0,2048,65535);CHECK(inspect_bad(262144,BOUNDS)==0);
    mbr(0,0x0c,0,2048,131073);CHECK(inspect_bad(133120,BOUNDS)==0);
    mbr(0,0x0c,0,UINT32_MAX,UINT32_MAX);CHECK(inspect_bad(UINT32_MAX,BOUNDS)==0);
    where="malformed BPBs";
    bpb(131072,1,1024);sector[0]=0;CHECK(inspect_bad(131072,INVALID)==0);
    bpb(131072,0,1024);CHECK(inspect_bad(131072,INVALID)==0);
    bpb(131072,3,1024);CHECK(inspect_bad(131072,INVALID)==0);
    bpb(131072,128,1024);CHECK(inspect_bad(131072,INVALID)==0);
    bpb(131072,1,0);CHECK(inspect_bad(131072,INVALID)==0);
    bpb(131072,1,1024);p16(14,7);CHECK(inspect_bad(131072,INVALID)==0);
    bpb(131072,1,1024);sector[21]=0xf0;CHECK(inspect_bad(131072,INVALID)==0);
    bpb(131072,1,1024);p16(40,0x80);CHECK(inspect_bad(131072,INVALID)==0);
    bpb(131072,1,1024);p16(42,1);CHECK(inspect_bad(131072,INVALID)==0);
    bpb(131072,1,1024);p32(28,2048);CHECK(inspect_bad(131072,INVALID)==0);
    bpb(131072,1,1024);sector[82]='X';CHECK(inspect_bad(131072,INVALID)==0);
    bpb(65535,1,1024);CHECK(inspect_bad(131072,BOUNDS)==0);
    bpb(131073,1,1024);CHECK(inspect_bad(131072,BOUNDS)==0);
    bpb(131072,1,65536);CHECK(inspect_bad(131072,INVALID)==0);
    bpb(131072,1,32);CHECK(inspect_bad(131072,INVALID)==0);
    bpb(131072,1,1024);p32(44,128994);CHECK(inspect_bad(131072,INVALID)==0);
    for(unsigned i=0;i<4;i++) {
        bpb(131072,1,1024);if(i==0)p16(48,0);if(i==1)p16(48,32);if(i==2)p16(50,0);if(i==3)p16(50,31);
        CHECK(inspect_bad(131072,INVALID)==0);
    }
    where="disguised MBR must not become BPB";bpb(131072,1,1024);entry(0,0x0c,0,2048,65536);CHECK(inspect_bad(131072,INVALID)==0);
    where="null inputs and output preservation";bpb(131072,1,1024);
    View view={5,6,7},previous=view;
    CHECK(up_inspect(NULL,512,131072,&view)==INVALID&&memcmp(&view,&previous,sizeof(view))==0);
    CHECK(up_inspect(sector,0,131072,&view)==INVALID&&memcmp(&view,&previous,sizeof(view))==0);
    CHECK(up_inspect(sector,512,131072,NULL)==INVALID);
    CHECK(inspect_bad(0,BOUNDS)==0);CHECK(inspect_bad(UINT64_MAX,BOUNDS)==0);
    where="translations and exact endpoints";view=(View){2048,131072,262144};U lba=0;
    CHECK(up_translate(&view,0,1,&lba)==0&&lba==2048);
    CHECK(up_translate(&view,131071,1,&lba)==0&&lba==133119);
    CHECK(up_translate(&view,0,131072,&lba)==0&&lba==2048);
    CHECK(bad_translation(&view,131071,2,BOUNDS)==0);
    CHECK(bad_translation(&view,131072,1,BOUNDS)==0);CHECK(bad_translation(&view,0,0,BOUNDS)==0);
    CHECK(bad_translation(&view,UINT64_MAX,1,BOUNDS)==0);CHECK(bad_translation(&view,0,UINT64_MAX,BOUNDS)==0);
    CHECK(bad_translation(NULL,0,1,INVALID)==0);CHECK(up_translate(&view,0,1,NULL)==INVALID);
    const View invalid_views[]={{0,0,262144},{262144,1,262144},{2048,131073,133120},
        {UINT64_MAX,1,UINT64_MAX},{UINT64_MAX-1,2,UINT64_MAX},{0,1,0},{0,1,UINT64_MAX}};
    for(unsigned i=0;i<sizeof(invalid_views)/sizeof(invalid_views[0]);i++)CHECK(bad_translation(&invalid_views[i],0,1,BOUNDS)==0);
    view=(View){0,131072,131072};CHECK(up_translate(&view,131071,1,&lba)==0&&lba==131071);
    view=(View){256,UINT32_MAX-256,UINT32_MAX};
    CHECK(up_translate(&view,view.capacity-1,1,&lba)==0&&lba==UINT32_MAX-1);
    CHECK(bad_translation(&view,view.capacity-1,2,BOUNDS)==0);
    where="bounded sector read at guard page";CHECK(guard_sector()==0);
    printf("USB partition native checks passed: %u; returned normally\n",checks);return 0;
}
