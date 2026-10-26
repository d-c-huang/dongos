/* Independent oracle around the actual configuration-window guards.
 * Hardware effects alone are counted host callbacks; no PCI/MMIO is touched. */
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define ABI __attribute__((sysv_abi))
typedef uint64_t U;
typedef struct {U framebuffer_base,framebuffer_size,width,height,stride,pixel_format;} Display;
typedef struct {Display display;U boot_info,raw_map,raw_size,descriptor_size,rsdp,rsdp_size,pool,pool_physical,pool_pages,stack_bottom,stack_top,stack_probe_bottom,stack_probe_top,root_physical;} View;
typedef struct {U version,valid,reason,error,physical,bytes,ecam,descriptor_index,kind,base,pages,attributes,mcfg_first,mcfg_end,framebuffer_base,framebuffer_bytes;} Conflict;
typedef struct {U low[4];uint8_t bytes[16*48];U high[4];} RawGuard;
_Static_assert(sizeof(View)==160&&sizeof(Display)==48&&sizeof(Conflict)==128,"independent ABI");
_Static_assert(offsetof(View,raw_map)==56&&offsetof(View,raw_size)==64&&offsetof(View,descriptor_size)==72,"real view offsets");
extern ABI void ecam_reset(U,U,U,U);
extern ABI U ecam_guard(U,U,U);
extern ABI U ecam_address(U,U);
extern ABI U ecam_read(U,uint32_t*);
extern ABI U ecam_current(void);
extern ABI Conflict *ecam_context(void);
static const U HHDM=UINT64_C(0xffff800000000000),WINDOW=UINT64_C(0xffffc00000080000),RUNTIME=UINT64_C(0x8000000000000000);
enum {INVALID=0x050a0001,DENIED=0x050a0002};
static View view;static RawGuard raw;static U space[8],first,end,base;
static U mapped_physical,mapped_flags;static unsigned maps,replaces,invalidates,loads,event_count,checks,null_view;
static char events[32];
#define CHECK(c) do{if(!(c)){fprintf(stderr,"ECAM_NATIVE_ASSERT line=%u: %s\n",__LINE__,#c);exit(1);}}while(0)
ABI void __dong_panic(U code,U line,const char*file,U bytes){(void)file;(void)bytes;fprintf(stderr,"unexpected panic code=%llu line=%llu\n",(unsigned long long)code,(unsigned long long)line);exit(99);}
ABI const View *ecam_host_view(void){return null_view?NULL:&view;}
ABI void *ecam_host_space(void){return space;}
static void event(char c){CHECK(event_count<sizeof events);events[event_count++]=c;}
ABI U ecam_host_map(void*s,U va,U pa,U flags,U replace){CHECK(s==space&&va==WINDOW&&pa&&!(pa&4095));CHECK(flags==9&&replace<=1);if(replace)replaces++;else maps++;mapped_physical=pa;mapped_flags=flags;event(replace?'R':'M');return 0;}
ABI void ecam_host_invalidate(U va){CHECK(va==WINDOW&&mapped_flags==9);invalidates++;event('I');}
ABI uint32_t ecam_host_load(U va){CHECK(va>=WINDOW&&va<WINDOW+4096&&!(va&3)&&mapped_flags==9);loads++;event('L');return UINT32_C(0x10203040)^(uint32_t)(mapped_physical+va-WINDOW);}
static void put64(void*p,U v){memcpy(p,&v,8);}
static void descriptor(unsigned index,unsigned kind,U pa,U pages,U attr){uint8_t*p=raw.bytes+index*48;CHECK(index<16);memset(p,0xcd,48);memcpy(p,&kind,4);memset(p+4,0,4);put64(p+8,pa);put64(p+16,0);put64(p+24,pages);put64(p+32,attr);}
static void count(unsigned n){view.raw_size=(U)n*48;}
static void effects_reset(void){maps=replaces=invalidates=loads=event_count=0;memset(events,0,sizeof events);}
static void fixture(U start_bus,U last_bus){
 memset(&view,0,sizeof view);memset(&raw,0xa7,sizeof raw);memset(space,0x5c,sizeof space);base=0xe0000000;first=base+(start_bus<<20);end=base+((last_bus+1)<<20);
 view.display=(Display){HHDM+0xd0000000,65536,640,480,672,0};view.raw_map=(U)(uintptr_t)raw.bytes;view.raw_size=48;view.descriptor_size=48;view.root_physical=0x400000;
 descriptor(0,11,first,(end-first)/4096,0);mapped_physical=mapped_flags=0;null_view=0;effects_reset();ecam_reset(base,start_bus,last_bus,UINT64_C(1)<<48);
 Conflict zero={0};CHECK(!memcmp(ecam_context(),&zero,sizeof zero));CHECK(ecam_current()==0);
}
static void no_effect(void){CHECK(!maps&&!replaces&&!invalidates&&!loads&&!event_count);}
static void immutable(const RawGuard*r,const View*v,const U*s){CHECK(!memcmp(&raw,r,sizeof raw)&&!memcmp(&view,v,sizeof view)&&!memcmp(space,s,sizeof space));}
static Conflict expected(U reason,U pa,U bytes,U index,U kind,U desc_base,U pages,U attr,U fb,U fb_bytes){if(reason==1){fb=view.display.framebuffer_base-HHDM;fb_bytes=view.display.framebuffer_size;}Conflict c={1,1,reason,DENIED,pa,bytes,1,index,kind,desc_base,pages,attr,first,end,fb,fb_bytes};return c;}
static void guard_result(U pa,U bytes,U ecam,U status,const Conflict*ctx){RawGuard r=raw;View v=view;U s[8];memcpy(s,space,sizeof s);Conflict before=*ecam_context();U current=ecam_current();CHECK(ecam_guard(pa,bytes,ecam)==status);no_effect();immutable(&r,&v,s);CHECK(ecam_current()==current);CHECK(!memcmp(ecam_context(),ctx?ctx:&before,sizeof before));checks++;}
static void denied_read(U pa,U status,const Conflict*ctx){RawGuard r=raw;View v=view;U s[8];memcpy(s,space,sizeof s);Conflict before=*ecam_context();U current=ecam_current();uint32_t out=0xa5a5a5a5;CHECK(ecam_read(pa,&out)==status&&out==0xa5a5a5a5);no_effect();immutable(&r,&v,s);CHECK(ecam_current()==current);CHECK(!memcmp(ecam_context(),ctx?ctx:&before,sizeof before));checks++;}
static void runtime_matrix(void){
 const U caps[]={0,1,2,4,8,0xf,0x1f,0x1000,0x1004,0x100d,0x200,0x400};
 for(unsigned i=0;i<sizeof caps/sizeof caps[0];i++)for(unsigned start=0;start<2;start++){
  fixture(start?3:0,start?5:0);descriptor(0,11,first,(end-first)/4096,RUNTIME|caps[i]);
  guard_result(first,4096,1,0,NULL);
  RawGuard r=raw;View v=view;U s[8];memcpy(s,space,sizeof s);uint32_t out=0;
  CHECK(ecam_read(first,&out)==0&&out==(UINT32_C(0x10203040)^(uint32_t)first));CHECK(maps==1&&!replaces&&invalidates==1&&loads==1&&event_count==3&&!memcmp(events,"MIL",3));CHECK(ecam_current()==first);immutable(&r,&v,s);Conflict zero={0};CHECK(!memcmp(ecam_context(),&zero,sizeof zero));checks++;
  effects_reset();CHECK(ecam_read(first+4,&out)==0&&out==(UINT32_C(0x10203040)^(uint32_t)(first+4)));CHECK(!maps&&!replaces&&!invalidates&&loads==1&&event_count==1&&events[0]=='L');immutable(&r,&v,s);checks++;
  effects_reset();CHECK(ecam_read(first+4096,&out)==0&&out==(UINT32_C(0x10203040)^(uint32_t)(first+4096)));CHECK(!maps&&replaces==1&&invalidates==1&&loads==1&&event_count==3&&!memcmp(events,"RIL",3));CHECK(ecam_current()==first+4096);immutable(&r,&v,s);checks++;
  fixture(3,5);descriptor(0,11,first,(end-first)/4096,RUNTIME|caps[i]);guard_result(first,4096,0,DENIED,NULL);
 }
}
static void types_and_bounds(void){
 for(unsigned kind=0;kind<17;kind++)for(unsigned rt=0;rt<2;rt++)for(unsigned ecam=0;ecam<2;ecam++){
  fixture(3,5);U attr=(rt?RUNTIME:0)|1;descriptor(0,kind,first,(end-first)/4096,attr);
  U ok=kind==11?(!rt||ecam):(kind==0&&!rt&&ecam);
  Conflict c=expected(1,first,4096,0,kind,first,(end-first)/4096,attr,0,0);
  guard_result(first,4096,ecam,ok?0:DENIED,!ok&&ecam?&c:NULL);
 }
 /* Full request containment is mandatory for the new Runtime exception. */
 for(unsigned which=0;which<3;which++){
  fixture(3,5);U pa=which==0?first-4096:which==1?end:end-4096,bytes=which==2?8192:4096;
  descriptor(0,11,first-4096,(end-first)/4096+2,RUNTIME|1);
  Conflict c=expected(1,pa,bytes,0,11,first-4096,(end-first)/4096+2,RUNTIME|1,0,0);guard_result(pa,bytes,1,DENIED,&c);
 }
 for(unsigned which=0;which<4;which++){
  fixture(3,5);U pa=which==0?first-4:which==1?end:which==2?end-2:first,bytes=which==2?4:which==3?0:4;
  Conflict c=expected(3,pa,bytes,0,0,0,0,0,0,0);
  /* Zero bytes remains accepted by the unchanged bounds helper. */
  CHECK(ecam_address(pa,bytes)==(which==3?0:DENIED));no_effect();if(which!=3)CHECK(!memcmp(ecam_context(),&c,sizeof c));checks++;
 }
 fixture(3,5);guard_result(0,4096,1,INVALID,NULL);fixture(3,5);guard_result(first+1,4096,1,INVALID,NULL);fixture(3,5);guard_result(first,0,1,INVALID,NULL);fixture(3,5);guard_result(first,4097,1,INVALID,NULL);
 fixture(3,5);guard_result(UINT64_C(1)<<48,4096,1,INVALID,NULL);fixture(3,5);ecam_reset(base,3,5,first+4096);guard_result(first,8192,1,INVALID,NULL);
 fixture(3,5);null_view=1;guard_result(first,4096,1,INVALID,NULL);fixture(3,5);denied_read(first+1,INVALID,NULL);
 /* Existing undescribed-hole policy is retained, not generalized to RAM. */
 fixture(3,5);descriptor(0,7,0x100000,1,0);guard_result(first,4096,1,0,NULL);
 /* The old high reserved PCI exception remains non-Runtime and non-WC/WT. */
 fixture(3,5);descriptor(0,0,UINT64_C(0x100000000),2,1);guard_result(UINT64_C(0x100000000),4096,0,0,NULL);
 fixture(3,5);descriptor(0,0,UINT64_C(0x100000000),2,RUNTIME|1);guard_result(UINT64_C(0x100000000),4096,0,DENIED,NULL);
 fixture(3,5);descriptor(0,0,UINT64_C(0x100000000),2,4);guard_result(UINT64_C(0x100000000),4096,0,DENIED,NULL);
}
static void context_and_atomicity(void){
 /* Report the actual later raw record, retain the full 64-bit attributes. */
 fixture(3,5);descriptor(0,11,0x100000,1,0);descriptor(1,7,first-4096,3,UINT64_C(0x8123456789abcdef));count(2);
 Conflict c=expected(1,first,4096,1,7,first-4096,3,UINT64_C(0x8123456789abcdef),0,0);denied_read(first,DENIED,&c);
 Conflict saved=*ecam_context();effects_reset();view.display.framebuffer_base=HHDM+first;view.display.framebuffer_size=8192;descriptor(1,11,first-4096,3,0);guard_result(first,4096,1,DENIED,&saved);
 effects_reset();view.display.framebuffer_base=HHDM+0xd0000000;guard_result(first,4096,1,0,&saved);
 /* Fresh retained-display failure is distinguishable from descriptor denial. */
 fixture(3,5);view.display.framebuffer_base=HHDM+first+128;view.display.framebuffer_size=512;descriptor(0,11,first,(end-first)/4096,RUNTIME|1);
 c=expected(2,first,4096,0,0,0,0,0,first+128,512);denied_read(first,DENIED,&c);
 /* A rejected replacement must keep the old window and all effects at zero. */
 fixture(3,5);uint32_t out;CHECK(!ecam_read(first,&out));CHECK(ecam_current()==first);effects_reset();descriptor(0,11,first,1,0);descriptor(1,7,first+4096,1,RUNTIME|8);count(2);
 c=expected(1,first+4096,4096,1,7,first+4096,1,RUNTIME|8,0,0);denied_read(first+4096,DENIED,&c);CHECK(ecam_current()==first);
 /* Bounds denial precedes map/hardware and stays the first record. */
 fixture(3,5);c=expected(3,end,4,0,0,0,0,0,0,0);denied_read(end,DENIED,&c);saved=*ecam_context();effects_reset();descriptor(0,7,first,1,0);denied_read(first,DENIED,&saved);
}
int main(void){runtime_matrix();types_and_bounds();context_and_atomicity();printf("ECAM_MMIO_NATIVE_OK checks=%u actual_guard_read_chain; Runtime_MCFG_type11_only; BAR_Runtime_denied; first_sticky_context128; zero_effects_on_deny; UC_supervisor_flags9\n",checks);return 0;}
