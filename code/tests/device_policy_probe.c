#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define ABI __attribute__((sysv_abi))
#define REQUIRE(x) do { if (!(x)) { fprintf(stderr,"device policy failure line %d: %s\n",__LINE__,#x); exit(1); } } while(0)
typedef struct { uint64_t kind,base,length; } Resource;
typedef struct { uint64_t views[11],physical[11],count; } Plan;
typedef struct { uint64_t low[4]; Plan value; uint64_t high[4]; } Guard;
typedef struct { uint64_t version,valid,error,slot,address,page,descriptor_index,kind,base,pages,attributes; } Conflict;
typedef struct { uint64_t low[4]; Conflict value; uint64_t high[4]; } ConflictGuard;
_Static_assert(sizeof(Plan)==184 && sizeof(Conflict)==88,"independent ABI");
extern ABI uint64_t device_plan(const uint64_t*,const uint8_t*,size_t,size_t,const Resource*,size_t,Plan*);
extern ABI uint64_t device_plan_diagnostic(const uint64_t*,const uint8_t*,size_t,size_t,const Resource*,size_t,Plan*,Conflict*);
extern ABI size_t device_plan_size(void);
extern ABI size_t device_conflict_size(void);
ABI void __dong_panic(uint64_t code) { fprintf(stderr,"unexpected panic %llu\n",(unsigned long long)code); exit(99); }
static uint64_t inventory[307];
static uint8_t raw[256];
static Resource resource;
static unsigned checks;
static void put64(uint8_t *p,uint64_t value) { memcpy(p,&value,8); }
static void descriptor(unsigned index,unsigned kind,uint64_t base,uint64_t pages,uint64_t attr) {
    uint8_t *p=raw+40*index; memset(p,0,40); memcpy(p,&kind,4); put64(p+8,base); put64(p+24,pages); put64(p+32,attr);
}
static void fixture(void) {
    memset(inventory,0,sizeof inventory); memset(raw,0,sizeof raw);
    inventory[8]=0xfee00000; inventory[11]=1; inventory[108]=0xfec00000;
    inventory[4]=0xabc000; inventory[42]=0xfed00000;
    resource=(Resource){8,0x100000,0x30000};
    descriptor(0,7,0x100000,16,0);
}
static uint64_t call(size_t length,size_t stride,size_t count,Guard *g) {
    return device_plan(inventory,raw,length,stride,&resource,count,&g->value);
}
static void failure(size_t length,size_t stride,size_t count,uint64_t code) {
    Guard g,before; uint64_t input[307]; uint8_t map[sizeof raw]; Resource kept=resource;
    memset(&g,0xa5,sizeof g); before=g; memcpy(input,inventory,sizeof input); memcpy(map,raw,sizeof map);
    REQUIRE(call(length,stride,count,&g)==code); REQUIRE(!memcmp(&g,&before,sizeof g));
    REQUIRE(!memcmp(input,inventory,sizeof input)); REQUIRE(!memcmp(map,raw,sizeof map)); REQUIRE(!memcmp(&kept,&resource,sizeof kept));
    checks++;
}
static unsigned diagnostic_checks;
static void descriptor_stride(unsigned index,unsigned stride,unsigned kind,uint64_t base,uint64_t pages,uint64_t attr) {
    uint8_t *p=raw+stride*index; memset(p,0xcc,stride); memset(p,0,40);
    memcpy(p,&kind,4); put64(p+8,base); put64(p+24,pages); put64(p+32,attr);
}
static void diagnostic(size_t length,size_t stride,size_t count,uint64_t code,const Conflict *expected) {
    Guard g,before,old; ConflictGuard c,cbefore; Conflict zero={0};
    uint64_t input[307]; uint8_t map[sizeof raw]; Resource kept=resource;
    memcpy(input,inventory,sizeof input); memcpy(map,raw,sizeof map);
    memset(&g,0xa5,sizeof g); before=g; old=g; memset(&c,0x9b,sizeof c); cbefore=c;
    REQUIRE(device_plan_diagnostic(inventory,raw,length,stride,&resource,count,&g.value,&c.value)==code);
    if(code) REQUIRE(!memcmp(&g,&before,sizeof g));
    else { REQUIRE(device_plan(inventory,raw,length,stride,&resource,count,&old.value)==0); REQUIRE(!memcmp(&g,&old,sizeof g)); }
    REQUIRE(!memcmp(&c.value,expected?expected:&zero,sizeof zero));
    REQUIRE(!memcmp(c.low,cbefore.low,sizeof c.low)); REQUIRE(!memcmp(c.high,cbefore.high,sizeof c.high));
    REQUIRE(!memcmp(input,inventory,sizeof input)); REQUIRE(!memcmp(map,raw,sizeof map)); REQUIRE(!memcmp(&kept,&resource,sizeof kept));
    /* The nullable new entry point is the same complete old-policy oracle. */
    old=before; REQUIRE(device_plan_diagnostic(inventory,raw,length,stride,&resource,count,&old.value,NULL)==code);
    REQUIRE(!memcmp(&old,&g,sizeof old)); diagnostic_checks++;
}
static void rejected_output(const uint64_t *inv,const uint8_t *map,size_t length,const Resource *kept,size_t count,Conflict *out) {
    Guard g,before; ConflictGuard c,cbefore; uint64_t saved[307]; uint8_t bytes[sizeof raw]; Resource r=resource;
    memset(&g,0x75,sizeof g); before=g; memset(&c,0x7a,sizeof c); cbefore=c;
    memcpy(saved,inventory,sizeof saved); memcpy(bytes,raw,sizeof bytes);
    /* A null selector intentionally aliases the actual Plan's interior. */
    Conflict *selected=out?out:(Conflict*)(void*)&g.value;
    REQUIRE(device_plan_diagnostic(inv,map,length,40,kept,count,&g.value,selected)==0x03030001);
    REQUIRE(!memcmp(&g,&before,sizeof g)); REQUIRE(!memcmp(&c,&cbefore,sizeof c));
    REQUIRE(!memcmp(saved,inventory,sizeof saved)); REQUIRE(!memcmp(bytes,raw,sizeof bytes)); REQUIRE(!memcmp(&r,&resource,sizeof r));
    diagnostic_checks++;
}
static void diagnostic_cases(void) {
    REQUIRE(device_conflict_size()==sizeof(Conflict));
    /* The actual conflict descriptor, not a guessed address/type, is published. */
    for(unsigned kind=0;kind<16;kind++) {
        fixture(); descriptor(1,kind,0xfee00000,1,0);
        Conflict expected={1,1,0x03030002,0,0xfee00000,0xfee00000,1,kind,0xfee00000,1,0};
        diagnostic(80,40,1,kind==11?0:0x03030002,kind==11?NULL:&expected);
    }
    for(unsigned slot=0;slot<11;slot++) {
        fixture(); inventory[11]=8;
        for(unsigned i=0;i<8;i++) inventory[108+3*i]=UINT64_C(0xfec00000)+i*4096;
        inventory[32]=0xfed01010;
        uint64_t address=slot==0?inventory[8]:slot==9?inventory[42]:slot==10?inventory[32]:inventory[108+3*(slot-1)];
        uint64_t page=address&~UINT64_C(4095),attr=UINT64_C(0x8123456789abcdef);
        descriptor_stride(0,48,7,0x100000,16,0); descriptor_stride(1,48,11,page,1,attr);
        Conflict expected={1,1,0x03030002,slot,address,page,1,11,page,1,attr};
        diagnostic(96,48,1,slot?0x03030002:0,slot?&expected:NULL);
    }
    /* Only MADT slot 0 gains the runtime-MMIO exception. Cache capability
       bits are retained input metadata, not an extra admission gate. */
    const uint64_t capabilities[]={0,0x1004,0x100d,1,2,4,8,0xf,0x1f,0x100,0x200,0x400};
    for(size_t i=0;i<sizeof capabilities/sizeof capabilities[0];i++) {
        fixture(); descriptor(1,11,inventory[8],1,(UINT64_C(1)<<63)|capabilities[i]);
        diagnostic(80,40,1,0,NULL);
    }
    for(unsigned kind=0;kind<16;kind++) {
        fixture(); const uint64_t attr=(UINT64_C(1)<<63)|0x100d; descriptor(1,kind,inventory[8],1,attr);
        Conflict expected={1,1,0x03030002,0,inventory[8],inventory[8],1,kind,inventory[8],1,attr};
        diagnostic(80,40,1,kind==11?0:0x03030002,kind==11?NULL:&expected);
    }
    fixture(); descriptor_stride(0,48,7,0x100000,16,0);
    descriptor_stride(1,48,11,inventory[8]-4096,3,UINT64_C(0x800000000000100d));
    diagnostic(96,48,1,0,NULL);
    fixture(); descriptor(1,11,inventory[8],1,UINT64_C(0x8000000000001004));
    resource.base=inventory[8]+128; resource.length=128; diagnostic(80,40,1,0x03030003,NULL);
    fixture(); descriptor(1,11,inventory[8],1,UINT64_C(0x8000000000000000)); inventory[108]=inventory[8];
    diagnostic(80,40,1,0x03030004,NULL);
    fixture(); descriptor(1,11,inventory[8],1,UINT64_C(0x800000000000100d)); inventory[8]++;
    diagnostic(80,40,1,0x03030005,NULL);
    /* Descriptor stride, multi-page coverage, and 64-bit page/attribute values. */
    fixture(); descriptor_stride(0,48,7,0x100000,16,0); descriptor_stride(1,48,11,0x200000,1,0);
    descriptor_stride(2,48,0,0xfee00000-4096,3,UINT64_C(0x123456789abcdef0));
    Conflict multi={1,1,0x03030002,0,0xfee00000,0xfee00000,2,0,0xfee00000-4096,3,UINT64_C(0x123456789abcdef0)};
    diagnostic(144,48,1,0x03030002,&multi);
    fixture(); descriptor(1,0,0x200000,UINT64_C(0x100000001),UINT64_C(0x13579bdf2468ace0));
    Conflict wide={1,1,0x03030002,0,0xfee00000,0xfee00000,1,0,0x200000,UINT64_C(0x100000001),UINT64_C(0x13579bdf2468ace0)};
    diagnostic(80,40,1,0x03030002,&wide);
    fixture(); descriptor(1,UINT32_MAX,0xfee00000,1,0);
    Conflict kindmax={1,1,0x03030002,0,0xfee00000,0xfee00000,1,UINT32_MAX,0xfee00000,1,0}; diagnostic(80,40,1,0x03030002,&kindmax);
    /* Half-open boundaries on both sides do not collide; exact page does. */
    fixture(); descriptor(1,7,0xfee00000-4096,1,0); descriptor(2,7,0xfee00000+4096,1,0); diagnostic(120,40,1,0,NULL);
    fixture(); inventory[8]=0xfffff000; descriptor(1,7,UINT64_C(0x100000000),1,0); diagnostic(80,40,1,0,NULL);
    /* Stale all-ones context is cleared on every success/non-conflict failure. */
    fixture(); diagnostic(40,40,1,0,NULL);
    fixture(); resource.base=0xfec00800; resource.length=128; diagnostic(40,40,1,0x03030003,NULL);
    fixture(); inventory[108]=0xfee00000; diagnostic(40,40,1,0x03030004,NULL);
    fixture(); inventory[8]++; diagnostic(40,40,1,0x03030005,NULL);
    fixture(); descriptor(1,0,0xfee00000,1,0); descriptor(2,7,0xfee00000,1,0); diagnostic(120,40,1,0x03030001,NULL);
    fixture(); diagnostic(39,40,1,0x03030001,NULL);
    fixture(); put64(raw+24,UINT64_MAX); diagnostic(40,40,1,0x03030001,NULL);
    fixture(); diagnostic(40,40,0,0x03030001,NULL);
    fixture(); inventory[11]=0; diagnostic(40,40,1,0x03030001,NULL);
    /* Raw map wins before retained-resource conflict, with no Plan publication. */
    fixture(); descriptor(1,0,0xfee00000,1,0); resource.base=0xfee00000; resource.length=4096;
    Conflict first={1,1,0x03030002,0,0xfee00000,0xfee00000,1,0,0xfee00000,1,0}; diagnostic(80,40,1,0x03030002,&first);
    /* Diagnostic ranges are validated before any write, including arithmetic overflow. */
    fixture(); rejected_output(inventory,raw,40,&resource,1,NULL);
    rejected_output(inventory,raw,40,&resource,1,(Conflict*)(void*)inventory);
    rejected_output(inventory,raw,40,&resource,1,(Conflict*)(void*)raw);
    rejected_output(inventory,raw,40,&resource,1,(Conflict*)(void*)&resource);
    uint64_t arena[32],saved[32]; memset(arena,0x81,sizeof arena); memcpy(saved,arena,sizeof saved);
    rejected_output(inventory,raw,40,&resource,1,(Conflict*)(void*)((uint8_t*)arena+1)); REQUIRE(!memcmp(arena,saved,sizeof arena));
    rejected_output(inventory,raw,40,&resource,1,(Conflict*)(uintptr_t)(UINTPTR_MAX-7));
    rejected_output(inventory,raw,40,&resource,1,(Conflict*)(uintptr_t)(UINTPTR_MAX-87));
    rejected_output((const uint64_t*)(uintptr_t)(UINTPTR_MAX-7),raw,40,&resource,1,(Conflict*)(void*)arena);
    rejected_output(inventory,(const uint8_t*)(uintptr_t)(UINTPTR_MAX-7),40,&resource,1,(Conflict*)(void*)arena);
    rejected_output(inventory,raw,40,&resource,SIZE_MAX,(Conflict*)(void*)arena); REQUIRE(!memcmp(arena,saved,sizeof arena));
    /* Exact disjoint endpoint is writable; no accidental inclusive alias rejection. */
    fixture(); memcpy(arena,raw,40); Guard g; memset(&g,0x9e,sizeof g);
    REQUIRE(device_plan_diagnostic(inventory,(const uint8_t*)arena,40,40,&resource,1,&g.value,(Conflict*)(void*)((uint8_t*)arena+40))==0);
    REQUIRE(!memcmp(arena,raw,40)); Conflict zero={0}; REQUIRE(!memcmp((uint8_t*)arena+40,&zero,sizeof zero)); diagnostic_checks++;
    printf("device diagnostic native checks=%u complete 88-byte context, zero-stale, aliases and input guards verified\n",diagnostic_checks);
}
int main(void) {
    const uint64_t base=UINT64_C(0xffffc00000000000);
    Guard g,before; fixture(); REQUIRE(device_plan_size()==sizeof(Plan));
    memset(&g,0x7c,sizeof g); before=g; REQUIRE(call(40,40,1,&g)==0);
    Plan expected={0}; expected.views[0]=base; expected.views[1]=base+4096; expected.views[9]=base+9*4096;
    expected.physical[0]=0xfee00000; expected.physical[1]=0xfec00000; expected.physical[9]=0xfed00000; expected.count=3;
    REQUIRE(!memcmp(&g.value,&expected,sizeof expected)); REQUIRE(!memcmp(g.low,before.low,sizeof g.low)); REQUIRE(!memcmp(g.high,before.high,sizeof g.high)); checks++;
    fixture(); inventory[4]=0; REQUIRE(call(40,40,1,&g)==0); REQUIRE(g.value.count==2 && !g.value.views[9]); checks++;
    fixture(); inventory[28]=0; inventory[32]=0xfed01010; REQUIRE(call(40,40,1,&g)==0); REQUIRE(g.value.count==4 && g.value.views[10]==base+10*4096+16); checks++;
    fixture(); descriptor(1,11,0xfec00000,1,0); REQUIRE(call(80,40,1,&g)==0); checks++;
    for(unsigned kind=0;kind<16;kind++) {
        fixture(); descriptor(1,kind,0xfee00000,1,0);
        if(kind==11) { REQUIRE(call(80,40,1,&g)==0); checks++; } else failure(80,40,1,0x03030002);
    }
    fixture(); descriptor(1,11,0xfee00000,1,UINT64_C(1)<<63); REQUIRE(call(80,40,1,&g)==0); REQUIRE(!memcmp(&g.value,&expected,sizeof expected)); checks++;
    fixture(); resource.base=0xfec00800; resource.length=128; failure(40,40,1,0x03030003);
    fixture(); inventory[108]=0xfee00000; failure(40,40,1,0x03030004);
    fixture(); inventory[11]=0; failure(40,40,1,0x03030001);
    fixture(); inventory[11]=9; failure(40,40,1,0x03030001);
    fixture(); inventory[8]++; failure(40,40,1,0x03030005);
    fixture(); inventory[8]=0; failure(40,40,1,0x03030005);
    fixture(); inventory[8]=UINT64_C(1)<<32; failure(40,40,1,0x03030005);
    fixture(); inventory[38]=1; failure(40,40,1,0x03030005);
    fixture(); inventory[42]=0xfed00f00; failure(40,40,1,0x03030005);
    fixture(); inventory[28]=0; inventory[32]=0xfed01ffe; failure(40,40,1,0x03030005);
    fixture(); failure(0,40,1,0x03030001);
    fixture(); failure(40,32,1,0x03030001);
    fixture(); failure(39,40,1,0x03030001);
    fixture(); failure(65537,40,1,0x03030001);
    fixture(); failure(40,40,0,0x03030001);
    fixture(); put64(raw+24,0); failure(40,40,1,0x03030001);
    fixture(); put64(raw+24,UINT64_MAX); failure(40,40,1,0x03030001);
    fixture(); put64(raw+8,0x100001); failure(40,40,1,0x03030001);
    fixture(); descriptor(1,11,0x108000,1,0); failure(80,40,1,0x03030001);
    fixture(); resource.base=UINT64_MAX-10; resource.length=20; failure(40,40,1,0x03030001);
    // Independent randomized exclusions: one page overlapping one discovered
    // register page is permitted only for actual non-runtime MMIO. Other
    // nonoverlapping pages never affect the expected original full Plan.
    uint32_t rng=0x4b1d4e39;
    for(unsigned i=0;i<1000;i++) {
        rng=rng*1664525u+1013904223u; unsigned kind=(rng>>16)&15, selected=(rng>>8)&3;
        uint64_t page=selected==0?0xfee00000:selected==1?0xfec00000:selected==2?0xfed00000:0xfd000000;
        fixture(); descriptor(1,kind,page,1,0);
        if(selected<3 && kind!=11) failure(80,40,1,0x03030002);
        else { REQUIRE(call(80,40,1,&g)==0); REQUIRE(!memcmp(&g.value,&expected,sizeof expected)); checks++; }
    }
    printf("device policy native checks=%u complete Plan and input guards verified\n",checks);
    diagnostic_cases();
    return 0;
}
