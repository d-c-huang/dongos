/* Independent native oracle around actual Dong device_memory + device_policy.
 * Only startup pointers and external paging/TLB effects are host fixtures.
 */
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "native_layout.h"
#define ABI __attribute__((sysv_abi))
typedef uint64_t U;
typedef struct { U cr0,cr3,cr4,efer,rflags,pat; } State;
typedef struct { U kind,base,length; } Resource;
typedef struct { U physical,flags; } Mapping;
typedef struct { U value[11]; } Views;
typedef struct { Views views; U physical[11],count; } Plan;
typedef struct { U version,valid,error,slot,address,page,descriptor_index,kind,base,pages,attributes; } Conflict;
typedef struct { U low[4]; Views value; U high[4]; } ViewGuard;
typedef struct { U low[4]; Conflict value; U high[4]; } ConflictGuard;
_Static_assert(sizeof(State)==48 && sizeof(Views)==88 && sizeof(Plan)==184,"independent prepare ABI");
_Static_assert(sizeof(Conflict)==88 && offsetof(Conflict,attributes)==80,"independent complete conflict ABI");
extern ABI U dm_prepare(const State*,Views*);
extern ABI U dm_prepare_diag(const State*,Views*,Conflict*);
extern ABI const Plan *dm_plan(void);
extern ABI const Plan *dm_storage(void);
extern ABI void dm_reset(void);
extern ABI U dm_state(void);

static const U BASE=UINT64_C(0xffffc00000000000);
enum { INVALID_INPUT=0x03030001,RAM_CONFLICT=0x03030002,RESOURCE_CONFLICT=0x03030003,
       DUPLICATE=0x03030004,UNSUPPORTED=0x03030005,INVALID_STATE=0x03030006,
       ATTEMPTED=0x03030007,OCCUPIED=0x03030008,NOT_MAPPED=0x02030002,INJECTED=0x02030999 };
static _Alignas(8) uint8_t inventory[INV_BYTES],view[160],space[64],raw[16*48];
static Resource kept[21];
static State state;
static unsigned checks,queries,maps,invalidates,touches,pointer_mask,query_at,map_at;
static U query_error;
typedef struct { char kind; U virtual,physical,flags; } Event;
static Event events[64];
static unsigned event_count;
#define REQUIRE(c) do{if(!(c)){fprintf(stderr,"DM_NATIVE_ASSERT line=%d: %s\n",__LINE__,#c);exit(1);}}while(0)
ABI void __dong_panic(U code,U line,const char *file,U size) {
    (void)file;(void)size;fprintf(stderr,"unexpected Dong panic code=%llu line=%llu\n",(unsigned long long)code,(unsigned long long)line);exit(99);
}
static void put64(void *at,U value){memcpy(at,&value,8);}
static U get64(const void *at){U value;memcpy(&value,at,8);return value;}
static U physical(unsigned slot) {
    if(slot==0)return 0xfee00000;
    if(slot<=8)return 0xfec00000+(U)(slot-1)*4096;
    return slot==9?0xfed00000:0xfed01000;
}
static U address(unsigned slot){return physical(slot)+(slot==10?16:0);}
static void descriptor(unsigned index,unsigned kind,U base,U pages,U attributes) {
    uint8_t *p=raw+index*48;memset(p,0,48);memcpy(p,&kind,4);put64(p+8,base);put64(p+24,pages);put64(p+32,attributes);
}
static void raw_length(unsigned count){put64(view+VIEW_RAW_SIZE,(U)count*48);}
static void fixture(void) {
    dm_reset();memset(inventory,0,sizeof inventory);memset(view,0,sizeof view);memset(space,0,sizeof space);memset(raw,0,sizeof raw);
    pointer_mask=queries=maps=invalidates=touches=event_count=query_at=map_at=0;query_error=0;
    put64(inventory+INV_LAPIC_ADDRESS,physical(0));put64(inventory+INV_IOAPIC_COUNT,8);
    for(unsigned i=0;i<8;i++)put64(inventory+INV_IOAPICS+i*24+8,physical(i+1));
    put64(inventory+INV_HPET,0xabc000);put64(inventory+INV_HPET_GAS+32,physical(9));
    put64(inventory+INV_PM_TIMER_GAS+32,address(10));
    put64(view+VIEW_RAW_MAP,(U)(uintptr_t)raw);put64(view+VIEW_DESCRIPTOR_SIZE,48);put64(view+VIEW_ROOT_PHYSICAL,0x400000);
    descriptor(0,7,0x100000,0x1000,0);raw_length(1);
    for(unsigned i=0;i<21;i++)kept[i]=(Resource){8,0x100000+(U)i*4096,4096};
    state=(State){0x80010001,0x400000,0x20,0xd00,2,6};
}
ABI const void *dm_host_view(void){return pointer_mask&1?NULL:view;}
ABI void *dm_host_space(void){return pointer_mask&2?NULL:space;}
ABI const void *dm_host_inventory(void){return pointer_mask&4?NULL:inventory;}
ABI const void *dm_host_manifest(void){return pointer_mask&8?NULL:kept;}
static void event(char kind,U virtual,U physical_address,U flags) {
    REQUIRE(event_count<64);events[event_count++]=(Event){kind,virtual,physical_address,flags};
}
ABI U dm_host_query(const void *s,U virtual,Mapping *out) {
    REQUIRE(s==space && out!=NULL);queries++;event('Q',virtual,0,0);
    if(query_at==queries){if(query_error==0)*out=(Mapping){0x12345000,9};return query_error;}
    return NOT_MAPPED;
}
ABI U dm_host_map(void *s,U virtual,U physical_address,U flags) {
    REQUIRE(s==space);maps++;touches++;event('M',virtual,physical_address,flags);
    return map_at==maps?INJECTED:0;
}
ABI void runtime_invalidate(U virtual){invalidates++;event('I',virtual,0,0);}

static Plan expected_plan(void) {
    Plan p={0};p.count=11;
    for(unsigned i=0;i<11;i++){p.views.value[i]=BASE+(U)i*4096+(i==10?16:0);p.physical[i]=physical(i);}
    return p;
}
static void no_effect(void){REQUIRE(queries==0 && maps==0 && invalidates==0 && touches==0 && event_count==0);}
static void plan_empty(void){Plan p={0};REQUIRE(dm_plan()==NULL);REQUIRE(!memcmp(dm_storage(),&p,sizeof p));}
static void guards_init(ViewGuard *v,ConflictGuard *c){memset(v,0xa5,sizeof *v);memset(c,0x3c,sizeof *c);memset(&c->value,0xee,sizeof c->value);}
static void conflict_case(unsigned slot,unsigned kind,U attributes,unsigned index) {
    fixture();descriptor(index,kind,physical(slot),1,attributes);raw_length(index+1);
    /* Fill earlier entries with disjoint legal descriptors, so index is real. */
    for(unsigned i=1;i<index;i++)descriptor(i,11,0xfd000000+(U)i*4096,1,0);
    ViewGuard output,old;ConflictGuard context,old_context;guards_init(&output,&context);old=output;old_context=context;
    State saved_state=state;uint8_t saved_inventory[sizeof inventory],saved_raw[sizeof raw],saved_view[sizeof view];Resource saved_kept[21];
    memcpy(saved_inventory,inventory,sizeof inventory);memcpy(saved_raw,raw,sizeof raw);memcpy(saved_view,view,sizeof view);memcpy(saved_kept,kept,sizeof kept);
    U status=dm_prepare_diag(&state,&output.value,&context.value);
    printf("DM_OBS conflict_status=0x%08llx slot=%u descriptor=%u query=%u map=%u invalidate=%u touches=%u\n",
        (unsigned long long)status,slot,index,queries,maps,invalidates,touches);fflush(stdout);
    REQUIRE(status==RAM_CONFLICT);
    Conflict wanted={1,1,RAM_CONFLICT,slot,address(slot),physical(slot),index,kind,physical(slot),1,attributes};
    REQUIRE(!memcmp(&context.value,&wanted,sizeof wanted));
    REQUIRE(!memcmp(output.low,old.low,sizeof old.low)&&!memcmp(output.high,old.high,sizeof old.high)&&!memcmp(&output,&old,sizeof old));
    REQUIRE(!memcmp(context.low,old_context.low,sizeof context.low)&&!memcmp(context.high,old_context.high,sizeof context.high));
    REQUIRE(!memcmp(&state,&saved_state,sizeof state)&&!memcmp(inventory,saved_inventory,sizeof inventory)&&!memcmp(raw,saved_raw,sizeof raw));
    REQUIRE(!memcmp(view,saved_view,sizeof view)&&!memcmp(kept,saved_kept,sizeof kept));no_effect();plan_empty();REQUIRE(dm_state()==1);
    /* Failed ATTEMPTED is sticky even after the real conflict is removed. */
    descriptor(index,11,physical(slot),1,0);memset(&context.value,0xee,sizeof context.value);
    U second=dm_prepare_diag(&state,&output.value,&context.value);Conflict zero={0};
    REQUIRE(second==ATTEMPTED && !memcmp(&context.value,&zero,sizeof zero));
    REQUIRE(dm_prepare(&state,&output.value)==ATTEMPTED);no_effect();plan_empty();REQUIRE(!memcmp(&output,&old,sizeof old));
    /* The compatibility API must reject identically before any page query. */
    fixture();descriptor(index,kind,physical(slot),1,attributes);raw_length(index+1);
    for(unsigned i=1;i<index;i++)descriptor(i,11,0xfd000000+(U)i*4096,1,0);
    guards_init(&output,&context);old=output;old_context=context;
    REQUIRE(dm_prepare(&state,&output.value)==RAM_CONFLICT);
    REQUIRE(!memcmp(&output,&old,sizeof old)&&!memcmp(&context,&old_context,sizeof context));
    REQUIRE(!memcmp(&state,&saved_state,sizeof state)&&!memcmp(inventory,saved_inventory,sizeof inventory)&&!memcmp(raw,saved_raw,sizeof raw));
    REQUIRE(!memcmp(view,saved_view,sizeof view)&&!memcmp(kept,saved_kept,sizeof kept));
    no_effect();plan_empty();REQUIRE(dm_state()==1);checks++;
}
static void no_conflict_failure(U expected,const State *input,Views *out,Conflict *conflict) {
    U result=dm_prepare_diag(input,out,conflict);REQUIRE(result==expected);no_effect();plan_empty();REQUIRE(dm_state()==1);checks++;
}
static void runtime_platform_success(unsigned slots,U capabilities,unsigned legacy) {
    fixture();U attributes=(UINT64_C(1)<<63)|capabilities;
    unsigned count=1;
    for(unsigned slot=0;slot<11;slot++)if(slots&(1u<<slot))descriptor(count++,11,physical(slot),1,attributes);
    raw_length(count);
    ViewGuard output,old;ConflictGuard context,old_context;guards_init(&output,&context);old=output;old_context=context;
    State saved_state=state;uint8_t saved_inventory[sizeof inventory],saved_raw[sizeof raw],saved_view[sizeof view],saved_space[sizeof space];Resource saved_kept[21];
    memcpy(saved_inventory,inventory,sizeof inventory);memcpy(saved_raw,raw,sizeof raw);memcpy(saved_view,view,sizeof view);memcpy(saved_space,space,sizeof space);memcpy(saved_kept,kept,sizeof kept);
    U status=legacy?dm_prepare(&state,&output.value):dm_prepare_diag(&state,&output.value,&context.value);
    printf("DM_RUNTIME_PLATFORM status=0x%08llx attributes=0x%016llx legacy=%u slots=0x%03x\n",(unsigned long long)status,(unsigned long long)attributes,legacy,slots);fflush(stdout);
    REQUIRE(status==0);Plan expected=expected_plan();Conflict zero={0};
    REQUIRE(dm_state()==3 && dm_plan()==dm_storage());
    REQUIRE(!memcmp(dm_storage(),&expected,sizeof expected)&&!memcmp(&output.value,&expected.views,sizeof expected.views));
    REQUIRE(!memcmp(output.low,old.low,sizeof old.low)&&!memcmp(output.high,old.high,sizeof old.high));
    if(legacy)REQUIRE(!memcmp(&context,&old_context,sizeof context));
    else REQUIRE(!memcmp(&context.value,&zero,sizeof zero)&&!memcmp(context.low,old_context.low,sizeof context.low)&&!memcmp(context.high,old_context.high,sizeof context.high));
    REQUIRE(!memcmp(&state,&saved_state,sizeof state)&&!memcmp(inventory,saved_inventory,sizeof inventory)&&!memcmp(raw,saved_raw,sizeof raw));
    REQUIRE(!memcmp(view,saved_view,sizeof view)&&!memcmp(space,saved_space,sizeof space)&&!memcmp(kept,saved_kept,sizeof kept));
    REQUIRE(queries==11 && maps==11 && invalidates==11 && touches==11 && event_count==33);
    for(unsigned i=0;i<11;i++) {
        REQUIRE(events[i].kind=='Q'&&events[i].virtual==BASE+(U)i*4096);
        /* Exactly WRITE|UNCACHED; USER and EXECUTE stay absent (supervisor NX). */
        REQUIRE(events[11+2*i].kind=='M'&&events[11+2*i].virtual==BASE+(U)i*4096&&events[11+2*i].physical==physical(i)&&events[11+2*i].flags==9);
        REQUIRE(events[12+2*i].kind=='I'&&events[12+2*i].virtual==BASE+(U)i*4096);
    }
    REQUIRE(dm_prepare(&state,&output.value)==ATTEMPTED && queries==11 && maps==11 && invalidates==11);checks++;
}
int main(void) {
    /* First case is the real bad-body discriminator: swallowing the policy
     * error returns success and the unchanged independent oracle exits 1. */
    conflict_case(0,7,0x8000000000000008ULL,1);
    for(unsigned slot=0;slot<11;slot++)for(unsigned kind=0;kind<16;kind++)
        if(kind!=11)conflict_case(slot,kind,(U)kind<<8,1+(slot%3));
    for(unsigned slot=0;slot<11;slot++)for(unsigned kind=0;kind<16;kind++)
        if(kind!=11)conflict_case(slot,kind,(UINT64_C(1)<<63)|0x100d,1+(slot%3));
    const U capabilities[]={0,1,4,8,13,0x1000,0x1004,0x100d,0x1f,0x70000,0x100000,0x3ff0};
    for(unsigned i=0;i<sizeof capabilities/sizeof capabilities[0];i++) {
        const unsigned slot_masks[]={1,2,1u<<8,1u<<9,1u<<10,0x7ff};
        for(unsigned j=0;j<sizeof slot_masks/sizeof slot_masks[0];j++) {
            runtime_platform_success(slot_masks[j],capabilities[i],0);runtime_platform_success(slot_masks[j],capabilities[i],1);
        }
    }
    ViewGuard output,old;ConflictGuard context;Conflict zero={0};Plan expected=expected_plan();
    fixture();guards_init(&output,&context);old=output;
    REQUIRE(dm_prepare_diag(&state,&output.value,NULL)==0);REQUIRE(dm_state()==3 && dm_plan()==dm_storage());
    REQUIRE(!memcmp(dm_storage(),&expected,sizeof expected)&&!memcmp(&output.value,&expected.views,sizeof expected.views));
    REQUIRE(!memcmp(output.low,old.low,sizeof old.low)&&!memcmp(output.high,old.high,sizeof old.high));
    REQUIRE(queries==11 && maps==11 && invalidates==11 && touches==11 && event_count==33);
    for(unsigned i=0;i<11;i++) {
        REQUIRE(events[i].kind=='Q'&&events[i].virtual==BASE+(U)i*4096);
        REQUIRE(events[11+2*i].kind=='M'&&events[11+2*i].virtual==BASE+(U)i*4096&&events[11+2*i].physical==physical(i)&&events[11+2*i].flags==9);
        REQUIRE(events[12+2*i].kind=='I'&&events[12+2*i].virtual==BASE+(U)i*4096);
    }
    REQUIRE(dm_prepare(&state,&output.value)==ATTEMPTED && queries==11 && maps==11 && invalidates==11);checks++;
    fixture();guards_init(&output,&context);old=output;
    for(unsigned i=0;i<11;i++)descriptor(i+1,11,physical(i),1,8);
    raw_length(12);
    REQUIRE(dm_prepare_diag(&state,&output.value,&context.value)==0 && !memcmp(&context.value,&zero,sizeof zero));checks++;
    fixture();guards_init(&output,&context);descriptor(1,7,physical(0),1,0);raw_length(2);old=output;
    REQUIRE(dm_prepare(&state,&output.value)==RAM_CONFLICT);no_effect();plan_empty();REQUIRE(!memcmp(&output,&old,sizeof old));checks++;
    fixture();guards_init(&output,&context);descriptor(1,7,physical(0),1,0);raw_length(2);old=output;
    REQUIRE(dm_prepare_diag(&state,&output.value,NULL)==RAM_CONFLICT);no_effect();plan_empty();REQUIRE(!memcmp(&output,&old,sizeof old));checks++;
    fixture();guards_init(&output,&context);state.rflags|=0x200;old=output;
    no_conflict_failure(INVALID_STATE,&state,&output.value,&context.value);REQUIRE(!memcmp(&context.value,&zero,sizeof zero)&&!memcmp(&output,&old,sizeof old));
    for(unsigned mask=1;mask<=4;mask*=2) {
        fixture();guards_init(&output,&context);pointer_mask=mask;
        no_conflict_failure(INVALID_STATE,&state,&output.value,&context.value);REQUIRE(!memcmp(&context.value,&zero,sizeof zero));
    }
    fixture();guards_init(&output,&context);no_conflict_failure(INVALID_STATE,NULL,&output.value,&context.value);REQUIRE(!memcmp(&context.value,&zero,sizeof zero));
    fixture();guards_init(&output,&context);no_conflict_failure(INVALID_STATE,&state,NULL,&context.value);REQUIRE(!memcmp(&context.value,&zero,sizeof zero));
    fixture();guards_init(&output,&context);pointer_mask=8;
    no_conflict_failure(INVALID_INPUT,&state,&output.value,&context.value);REQUIRE(!memcmp(&context.value,&zero,sizeof zero));
    fixture();guards_init(&output,&context);put64(view+VIEW_RAW_SIZE,47);
    no_conflict_failure(INVALID_INPUT,&state,&output.value,&context.value);REQUIRE(!memcmp(&context.value,&zero,sizeof zero));
    fixture();guards_init(&output,&context);put64(inventory+INV_IOAPICS+8,physical(0));
    no_conflict_failure(DUPLICATE,&state,&output.value,&context.value);REQUIRE(!memcmp(&context.value,&zero,sizeof zero));
    fixture();guards_init(&output,&context);kept[0].base=physical(0);kept[0].length=128;
    no_conflict_failure(RESOURCE_CONFLICT,&state,&output.value,&context.value);REQUIRE(!memcmp(&context.value,&zero,sizeof zero));
    fixture();guards_init(&output,&context);old=output;descriptor(1,11,physical(0),1,(UINT64_C(1)<<63)|0x100d);raw_length(2);
    kept[0].base=physical(0);kept[0].length=128;
    uint8_t retained_raw[sizeof raw];Resource retained_kept[21];memcpy(retained_raw,raw,sizeof raw);memcpy(retained_kept,kept,sizeof kept);
    no_conflict_failure(RESOURCE_CONFLICT,&state,&output.value,&context.value);
    REQUIRE(!memcmp(&context.value,&zero,sizeof zero)&&!memcmp(&output,&old,sizeof old));
    REQUIRE(!memcmp(retained_raw,raw,sizeof raw)&&!memcmp(retained_kept,kept,sizeof kept));
    for(unsigned slot=1;slot<11;slot++)for(unsigned legacy=0;legacy<2;legacy++) {
        fixture();guards_init(&output,&context);old=output;ConflictGuard saved_context=context;
        descriptor(1,11,physical(slot),1,(UINT64_C(1)<<63)|1);raw_length(2);
        kept[0].base=physical(slot);kept[0].length=128;
        memcpy(retained_raw,raw,sizeof raw);memcpy(retained_kept,kept,sizeof kept);
        U result=legacy?dm_prepare(&state,&output.value):dm_prepare_diag(&state,&output.value,&context.value);
        REQUIRE(result==RESOURCE_CONFLICT);no_effect();plan_empty();REQUIRE(dm_state()==1);
        REQUIRE(!memcmp(&output,&old,sizeof old));
        if(legacy)REQUIRE(!memcmp(&context,&saved_context,sizeof context));
        else REQUIRE(!memcmp(&context.value,&zero,sizeof zero));
        REQUIRE(!memcmp(retained_raw,raw,sizeof raw)&&!memcmp(retained_kept,kept,sizeof kept));checks++;
    }
    /* Runtime HPET/PM still cannot share a page or cross a register window. */
    fixture();guards_init(&output,&context);old=output;
    put64(inventory+INV_PM_TIMER_GAS+32,physical(9)+16);
    descriptor(1,11,physical(9),1,UINT64_C(0x8000000000000001));raw_length(2);
    no_conflict_failure(DUPLICATE,&state,&output.value,&context.value);
    REQUIRE(!memcmp(&context.value,&zero,sizeof zero)&&!memcmp(&output,&old,sizeof old));
    fixture();guards_init(&output,&context);old=output;
    put64(inventory+INV_HPET_GAS+32,physical(9)+4096-512);
    descriptor(1,11,physical(9),1,UINT64_C(0x8000000000000001));raw_length(2);
    no_conflict_failure(UNSUPPORTED,&state,&output.value,&context.value);
    REQUIRE(!memcmp(&context.value,&zero,sizeof zero)&&!memcmp(&output,&old,sizeof old));
    fixture();guards_init(&output,&context);old=output;
    REQUIRE(dm_prepare_diag(&state,&output.value,(Conflict*)(void*)&output.value)==INVALID_INPUT);
    REQUIRE(!memcmp(&output,&old,sizeof old)&&dm_state()==0);no_effect();plan_empty();checks++;
    fixture();guards_init(&output,&context);old=output;uint8_t alias_raw[sizeof raw];memcpy(alias_raw,raw,sizeof raw);
    REQUIRE(dm_prepare_diag(&state,&output.value,(Conflict*)(void*)raw)==INVALID_INPUT);
    REQUIRE(!memcmp(raw,alias_raw,sizeof raw)&&!memcmp(&output,&old,sizeof old)&&dm_state()==0);no_effect();plan_empty();checks++;
    fixture();guards_init(&output,&context);old=output;Resource alias_kept[21];memcpy(alias_kept,kept,sizeof kept);
    REQUIRE(dm_prepare_diag(&state,&output.value,(Conflict*)(void*)kept)==INVALID_INPUT);
    REQUIRE(!memcmp(kept,alias_kept,sizeof kept)&&!memcmp(&output,&old,sizeof old)&&dm_state()==0);no_effect();plan_empty();checks++;
    fixture();guards_init(&output,&context);put64(inventory+INV_HPET_GAS,1);
    no_conflict_failure(UNSUPPORTED,&state,&output.value,&context.value);REQUIRE(!memcmp(&context.value,&zero,sizeof zero));
    fixture();guards_init(&output,&context);old=output;query_at=3;
    REQUIRE(dm_prepare_diag(&state,&output.value,&context.value)==OCCUPIED && queries==3 && maps==0 && invalidates==0 && touches==0);
    REQUIRE(!memcmp(&output,&old,sizeof old)&&!memcmp(&context.value,&zero,sizeof zero)&&dm_plan()==NULL);checks++;
    fixture();guards_init(&output,&context);old=output;query_at=5;query_error=INJECTED;
    REQUIRE(dm_prepare_diag(&state,&output.value,&context.value)==INJECTED && queries==5 && maps==0 && invalidates==0 && touches==0);
    REQUIRE(!memcmp(&output,&old,sizeof old)&&!memcmp(&context.value,&zero,sizeof zero)&&dm_plan()==NULL);checks++;
    fixture();guards_init(&output,&context);old=output;map_at=3;
    REQUIRE(dm_prepare_diag(&state,&output.value,&context.value)==INJECTED && queries==11 && maps==3 && invalidates==2);
    REQUIRE(!memcmp(&output,&old,sizeof old)&&!memcmp(&context.value,&zero,sizeof zero)&&dm_plan()==NULL);
    REQUIRE(dm_prepare(&state,&output.value)==ATTEMPTED && queries==11 && maps==3 && invalidates==2);checks++;
    REQUIRE(get64(view+VIEW_ROOT_PHYSICAL)==state.cr3);
    printf("DEVICE_MEMORY_DIAG_NATIVE_OK checks=%u actual_prepare_policy; runtime_all_ACPI_slots_12caps_both_apis; HPET_PM_runtime_accept; non11_runtime_reject; platform_retained_duplicate_geometry_reject; UC_supervisor_NX_flags9; conflict=0query/0map/0invalidate/0touch; all_queries_before_maps; sticky; legacy-null; alias; atomic\n",checks);
    return 0;
}
