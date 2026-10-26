/* Independent read-only xHCI capability and private-map oracles. */
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define ABI __attribute__((sysv_abi))
typedef uint64_t U;
static unsigned cases,checks;
#define CHECK(c) do{checks++;if(!(c)){fprintf(stderr,"XHCI_CAPS_ASSERT case=%u line=%u: %s\n",cases,__LINE__,#c);exit(1);}}while(0)
ABI void __dong_panic(U code,U line,const char *file,U bytes){(void)file;(void)bytes;fprintf(stderr,"unexpected panic %llx line=%llu\n",(unsigned long long)code,(unsigned long long)line);exit(99);}
static const U RUNTIME=UINT64_C(0x8000000000000000);
typedef struct {U framebuffer_base,framebuffer_size,width,height,stride,pixel_format;} Display;
typedef struct {Display display;U boot_info,raw_map,raw_size,descriptor_size,rsdp,rsdp_size,pool,pool_physical,pool_pages,stack_bottom,stack_top,stack_probe_bottom,stack_probe_top,root_physical;} View;
_Static_assert(sizeof(View)==160&&sizeof(Display)==48,"real immutable View ABI");

#ifdef XHCI_MAP_ORACLE
extern ABI void xhci_map_reset(U,U,U);
extern ABI U xhci_map_read(U,U,uint32_t *);
extern ABI U xhci_map_current(void);
extern ABI U xhci_map_cache(void);
extern ABI const U *xhci_map_conflict(void);
static View view;
static struct {U low[4];unsigned char bytes[4*48];U high[4];} map;
static U space[8],physical,mapped,flags,write_callbacks,loads,maps,replaces,invalidates;
static unsigned null_view,events;static char sequence[32];
static const U WINDOW=UINT64_C(0xffffc00000080000),HHDM=UINT64_C(0xffff800000000000);
ABI const View *xhci_map_host_view(void){return null_view?NULL:&view;}
ABI void *xhci_map_host_space(void){return space;}
static void event(char c){CHECK(events<sizeof sequence);sequence[events++]=c;}
ABI U xhci_map_host_map(void *s,U va,U pa,U f,U replace){CHECK(s==space&&va==WINDOW&&pa&&!(pa&4095)&&f==8&&replace<=1);mapped=pa;flags=f;if(replace)replaces++;else maps++;event(replace?'R':'M');return 0;}
ABI void xhci_map_host_invalidate(U va){CHECK(va==WINDOW&&flags==8);invalidates++;event('I');}
ABI uint32_t xhci_map_host_load(U va){CHECK(flags==8&&va>=WINDOW&&va<=WINDOW+4092&&!(va&3));loads++;event('L');return UINT32_C(0x10203040)^(uint32_t)(mapped+va-WINDOW);}
ABI U xhci_map_host_write(U address,U value){(void)address;(void)value;write_callbacks++;return 1;}
static void put64(void *p,U n){memcpy(p,&n,8);}
static void effects(void){loads=maps=replaces=invalidates=events=0;memset(sequence,0,sizeof sequence);}
static void descriptor(unsigned kind,U attributes){memset(map.bytes,0x5e,48);memcpy(map.bytes,&kind,4);put64(map.bytes+8,physical);put64(map.bytes+24,1);put64(map.bytes+32,attributes);}
static void setup(void){cases++;memset(&view,0,sizeof view);memset(&map,0xa7,sizeof map);memset(space,0x5c,sizeof space);physical=UINT64_C(0x1200001000);view.display=(Display){HHDM+0xd0000000,0x200000,640,480,672,0};view.raw_map=(U)(uintptr_t)map.bytes;view.raw_size=view.descriptor_size=48;descriptor(11,1);null_view=0;write_callbacks=0;mapped=flags=0;effects();xhci_map_reset(UINT64_C(1)<<48,0,0);}
static void read_result(U pa,U offset,U expected,const char *wanted){
 unsigned char oldmap[sizeof map];View oldview=view;U oldspace[8];memcpy(oldmap,&map,sizeof map);memcpy(oldspace,space,sizeof space);U current=xhci_map_current(),cache=xhci_map_cache();uint32_t out=0xa5a5a5a5;
 CHECK(xhci_map_read(pa,offset,&out)==expected);CHECK(!write_callbacks);CHECK(!memcmp(oldmap,&map,sizeof map)&&!memcmp(&oldview,&view,sizeof view)&&!memcmp(oldspace,space,sizeof space));
 const U *context=xhci_map_conflict();for(unsigned i=0;i<16;i++)CHECK(context[i]==0);
 if(expected){CHECK(out==0xa5a5a5a5&&!events&&!loads&&!maps&&!replaces&&!invalidates);CHECK(xhci_map_current()==current&&xhci_map_cache()==cache);}
 else{CHECK(out==(UINT32_C(0x10203040)^(uint32_t)(pa+offset)));CHECK(events==strlen(wanted)&&!memcmp(sequence,wanted,events));CHECK(xhci_map_current()==pa&&xhci_map_cache()==pa);}
}
int main(void){
 const U caps[]={0,1,2,4,8,0x1000,UINT64_C(0x123456789abcdef)};
 for(unsigned i=0;i<sizeof caps/sizeof caps[0];i++){
  setup();descriptor(11,caps[i]);read_result(physical,0,0,"MIL");CHECK(maps==1&&invalidates==1&&loads==1);effects();read_result(physical,4092,0,"L");
  setup();descriptor(11,caps[i]);xhci_map_reset(UINT64_C(1)<<48,physical,0);mapped=physical;flags=9;read_result(physical,16,0,"RIL");CHECK(replaces==1&&invalidates==1&&loads==1);
  setup();descriptor(11,RUNTIME|caps[i]);read_result(physical,0,0x050a0002,"");
 }
 for(unsigned kind=0;kind<17;kind++){
  setup();descriptor(kind,0);read_result(physical,0,(kind==0||kind==11)?0:0x050a0002,(kind==0||kind==11)?"MIL":"");
  setup();descriptor(kind,RUNTIME|1);read_result(physical,0,0x050a0002,"");
 }
 setup();read_result(physical+1,0,0x050a0001,"");setup();read_result(0,0,0x050a0001,"");setup();read_result(UINT64_C(1)<<48,0,0x050a0001,"");
 setup();read_result(physical,4096,0x050a0001,"");setup();read_result(physical,4093,0x050a0001,"");setup();null_view=1;read_result(physical,0,0x050a0001,"");
 setup();view.display.framebuffer_base=HHDM+physical;read_result(physical,0,0x050a0002,"");
 setup();xhci_map_reset(UINT64_C(1)<<48,physical,0);mapped=physical;flags=9;descriptor(11,RUNTIME|1);read_result(physical,0,0x050a0002,"");
 printf("XHCI_MAP_NATIVE_OK cases=%u checks=%u guard_before_effects; UC_supervisor_RO_flags8; forced_first_RO; no_writes\n",cases,checks);return 0;
}
#else
typedef struct {U version,done,error_code,flags,xhci_count,ehci_count,ohci_count,uhci_count,other_count,pci_count,usb_counts,ecam,identity,class_code,header,bar0,bar1,bar_physical,descriptor_found,descriptor_index,descriptor_type,descriptor_base,descriptor_pages,descriptor_attributes,framebuffer_base,framebuffer_bytes,mcfg_base,mcfg_first,mcfg_last;} Inventory;
typedef struct {U version,done,error_code,flags,bar_physical,pci_command,cap0,hcs1,hcs2,hcc1,db_off,rt_off,hcc2,operational,pagesize,usbcmd,usbsts,extended_first,extended_count,legacy_offset,legacy_support,legacy_control,protocols2,protocols3,unsupported_first,scratchpads,context_bytes,ac64,reject_mask,inventory_error,read_count,reserved;} Report;
_Static_assert(sizeof(Inventory)==232&&sizeof(Report)==256,"fixed report ABIs");
extern ABI const Report *dong_xhci_caps_run(void);
extern ABI const Report *dong_xhci_caps_pointer(void);
extern ABI void xhci_caps_reset(void);
extern U xhci_caps_canary_low[4],xhci_caps_canary_high[4];
static struct {U low[4];Inventory value;U high[4];} inventory;
static struct {U low[4];uint32_t words[1024];U high[4];} mmio;
static U command,fail_offset,mmio_attempts,mmio_success,pci_reads,inventory_reads,writes;
static unsigned read_offsets[1024],no_inventory,misaligned_inventory,pci_error,forbid_reads;
static const U BAR=UINT64_C(0x1200001000),ECAM=UINT64_C(0xe0008000),ERR=UINT64_C(0x050a0002),INVALID=UINT64_C(0x0b020001);
enum {INV=1,MEM=2,MAPPED=4,HEADER=8,COMPLETE=16,LEGACY=32,PROTO2=64,PROTO3=128,OUTSIDE=256,NONE=512,MEM_OFF=1024,MMIO_ERROR=2048,DUP_LEGACY=4096,LIMIT=8192,UNKNOWN=16384,DUP_PROTO=32768,BAD_BAR=65536};
ABI const Inventory *xhci_caps_host_inventory(void){CHECK(!forbid_reads);inventory_reads++;if(no_inventory)return NULL;return (const Inventory *)((const unsigned char *)&inventory.value+misaligned_inventory);}
ABI U xhci_caps_host_pci(U address,uint32_t *out){CHECK(!forbid_reads&&address==ECAM+4);pci_reads++;if(pci_error)return 1;*out=(uint32_t)command;return 0;}
ABI U xhci_caps_host_mmio(U physical,U offset,uint32_t *out){CHECK(!forbid_reads&&physical==BAR&&offset<=4092&&!(offset&3));mmio_attempts++;read_offsets[offset/4]++;if(offset==fail_offset)return 1;*out=mmio.words[offset/4];mmio_success++;return 0;}
ABI U xhci_caps_host_write(U address,U value){(void)address;(void)value;writes++;return 1;}
static void reg(unsigned offset,uint32_t value){CHECK(offset<=4092&&!(offset&3));mmio.words[offset/4]=value;}
static void protocol(unsigned offset,unsigned major,unsigned next,unsigned start,unsigned count){reg(offset,(major<<24)|(next<<8)|2);reg(offset+4,0x20425355);reg(offset+8,start|(count<<8));reg(offset+12,0);}
static void setup(void){
 cases++;memset(&inventory,0xa6,sizeof inventory);memset(&inventory.value,0,sizeof inventory.value);memset(&mmio,0xb7,sizeof mmio);memset(mmio.words,0,sizeof mmio.words);memset(read_offsets,0,sizeof read_offsets);
 inventory.value.version=inventory.value.done=1;inventory.value.flags=1|2|256;inventory.value.ecam=ECAM;inventory.value.bar_physical=BAR;inventory.value.descriptor_attributes=RUNTIME|1;
 command=0xabcd0406;fail_offset=UINT64_MAX;mmio_attempts=mmio_success=pci_reads=inventory_reads=writes=0;no_inventory=misaligned_inventory=pci_error=forbid_reads=0;
 reg(0,0x01100040);reg(4,0x04000108);reg(8,0);reg(16,0x00400005);reg(20,0x800);reg(24,0x600);reg(28,0x11223344);
 reg(0x40,0);reg(0x44,1);reg(0x48,1);reg(0x100,0x01000401);reg(0x104,0);protocol(0x110,2,4,1,2);protocol(0x120,3,0,3,2);
 for(unsigned i=0;i<4;i++){xhci_caps_canary_low[i]=UINT64_C(0x1122334455667700)+i;xhci_caps_canary_high[i]=UINT64_C(0x8877665544332200)+i;}
 xhci_caps_reset();Report zero={0};const Report *p=dong_xhci_caps_pointer();CHECK(!memcmp(p,&zero,sizeof zero));CHECK((uintptr_t)p==(uintptr_t)xhci_caps_canary_low+32&&(uintptr_t)xhci_caps_canary_high==(uintptr_t)p+256);CHECK(!inventory_reads&&!pci_reads&&!mmio_attempts);
}
static Report run(U reject,U required,U absent,U error){
 unsigned char oldinv[sizeof inventory],oldmmio[sizeof mmio];U low[4],high[4];memcpy(oldinv,&inventory,sizeof inventory);memcpy(oldmmio,&mmio,sizeof mmio);memcpy(low,xhci_caps_canary_low,sizeof low);memcpy(high,xhci_caps_canary_high,sizeof high);
 const Report *p=dong_xhci_caps_run();CHECK(p==dong_xhci_caps_pointer()&&p->version==1&&p->done==1&&p->error_code==error);CHECK(p->reject_mask==reject&&(p->flags&required)==required&&!(p->flags&absent));CHECK(p->read_count==mmio_success&&p->reserved==0&&!writes);
 CHECK(!memcmp(oldinv,&inventory,sizeof inventory)&&!memcmp(oldmmio,&mmio,sizeof mmio));CHECK(!memcmp(low,xhci_caps_canary_low,sizeof low)&&!memcmp(high,xhci_caps_canary_high,sizeof high));
 Report saved=*p;U reads=mmio_attempts,pci=pci_reads,inv=inventory_reads;forbid_reads=1;CHECK(dong_xhci_caps_run()==p&&!memcmp(p,&saved,sizeof saved));CHECK(mmio_attempts==reads&&pci_reads==pci&&inventory_reads==inv&&!writes);return saved;
}
static void supported_and_features(void){
 setup();Report r=run(0,255,OUTSIDE|UNKNOWN|DUP_PROTO|DUP_LEGACY|MMIO_ERROR,0);CHECK(r.bar_physical==BAR&&r.pci_command==0x406&&r.cap0==0x01100040&&r.hcs1==0x04000108&&r.hcs2==0&&r.hcc1==0x00400005&&r.db_off==0x800&&r.rt_off==0x600&&r.hcc2==0x11223344&&r.operational==0x40&&r.pagesize==1&&r.usbcmd==0&&r.usbsts==1&&r.extended_first==0x100&&r.extended_count==3&&r.legacy_offset==0x100&&r.legacy_support==0x01000401&&r.legacy_control==0&&r.protocols2==1&&r.protocols3==1&&r.unsupported_first==0&&r.scratchpads==0&&r.context_bytes==64&&r.ac64==1&&r.inventory_error==0&&r.read_count==20);
 for(unsigned version=0x100;version<=0x120;version+=0x10){setup();reg(0,(version<<16)|0x40);r=run(0,255,OUTSIDE,0);CHECK(r.hcc2==(version==0x100?0:0x11223344)&&r.read_count==(version==0x100?19:20));}
 for(unsigned i=0;i<4;i++){setup();U value=i==0?UINT64_C(1)<<27:i==1?UINT64_C(1)<<21:i==2?(UINT64_C(31)<<27)|(UINT64_C(31)<<21):UINT64_C(1)<<26;reg(8,(uint32_t)value);r=run(i==3?8:4,255,OUTSIDE,0);CHECK(r.scratchpads==(i==0?1:i==1?32:i==2?1023:0));}
 setup();reg(0x48,2);run(16,255,0,0);setup();reg(16,0x00400000);r=run(0,255,0,0);CHECK(r.context_bytes==32&&r.ac64==0);
 const uint32_t bad_hcs[]={0x04000100,0x00000108,0x21000108,0x04000008,0x04040108,0x04080108};
 for(unsigned i=0;i<sizeof bad_hcs/sizeof bad_hcs[0];i++){setup();reg(4,bad_hcs[i]);U rejection=2;if((bad_hcs[i]>>24)<=32&&(bad_hcs[i]>>24)!=4)rejection|=256;run(rejection,INV|MEM|MAPPED|HEADER,0,0);}
 const uint32_t cap0[]={0x01210040,0x01100140,0x01100010,0x01100043};
 for(unsigned i=0;i<4;i++){setup();reg(0,cap0[i]);run(1,INV|MEM|MAPPED,HEADER,i>=2?INVALID:0);}
 setup();reg(20,0x801);run(2,255,0,0);setup();reg(24,0x610);run(2,255,0,0);setup();reg(24,0x400);run(2,255,0,0);
}
static void ownership_unknown_and_protocol(void){
 const uint32_t legacy[]={0x01010401,0x00000401,0x81000401};
 for(unsigned i=0;i<3;i++){setup();reg(0x100,legacy[i]);Report r=run(32,255,0,0);CHECK(r.legacy_support==legacy[i]);}
 setup();reg(0x104,0x00010001);Report r=run(64,255,0,0);CHECK(r.legacy_control==0x00010001);
 for(unsigned id=0;id<2;id++){setup();uint32_t header=0x00000400|(id?10:192);reg(0x100,header);r=run(128,INV|MEM|MAPPED|HEADER|COMPLETE|PROTO2|PROTO3|UNKNOWN,LEGACY,0);CHECK(r.unsupported_first==header&&r.legacy_offset==0&&read_offsets[0x104/4]==0&&r.extended_count==3);}
 setup();reg(0x100,0x01000401);reg(0x110,0x01000401);reg(0x114,0);protocol(0x120,2,4,1,2);protocol(0x130,3,0,3,2);r=run(32,255|DUP_LEGACY,0,0);CHECK(r.extended_count==4&&r.legacy_offset==0x100&&r.legacy_support==0x01000401&&r.legacy_control==0);
 setup();protocol(0x120,3,0,2,2);run(256,255|DUP_PROTO,0,0);
 setup();protocol(0x110,2,4,1,1);protocol(0x120,2,4,2,1);protocol(0x130,3,0,3,2);r=run(0,255,DUP_PROTO,0);CHECK(r.protocols2==2&&r.protocols3==1);
 for(unsigned i=0;i<6;i++){setup();switch(i){case 0:reg(0x114,0);break;case 1:reg(0x118,0x200);break;case 2:reg(0x118,0x10000201);break;case 3:reg(0x11c,1);break;case 4:reg(0x110,0x04000402);break;default:reg(0x118,0x501);break;}run(256,INV|MEM|MAPPED|HEADER|COMPLETE,0,0);}
 setup();protocol(0x120,3,0,3,1);run(256,255,0,0);
}
static void bounds_errors_and_skips(void){
 setup();reg(16,0x04000005);Report r=run(0,INV|MEM|MAPPED|HEADER|OUTSIDE,COMPLETE,0);CHECK(r.extended_count==0);
 setup();reg(16,0x03ff0005);reg(4092,0x01000001);r=run(0,INV|MEM|MAPPED|HEADER|LEGACY|OUTSIDE,COMPLETE,0);CHECK(r.extended_count==1&&r.legacy_control==0&&mmio_attempts==11);
 setup();reg(16,0x03fd0005);reg(4084,0x02000002);r=run(0,INV|MEM|MAPPED|HEADER|PROTO2|OUTSIDE,COMPLETE,0);CHECK(r.extended_count==1&&read_offsets[4088/4]==0&&read_offsets[4092/4]==0);
 setup();reg(16,0x03fc0005);reg(4080,0x000008c0);r=run(128,INV|MEM|MAPPED|HEADER|OUTSIDE|UNKNOWN,COMPLETE,0);CHECK(r.extended_count==1);
 setup();for(unsigned i=0;i<64;i++)reg(0x100+i*4,0x000001c0);r=run(128,INV|MEM|MAPPED|HEADER|UNKNOWN|LIMIT,COMPLETE,0);CHECK(r.extended_count==64&&r.unsupported_first==0x000001c0);
 setup();reg(16,0x00070005);run(1,INV|MEM|MAPPED|HEADER,COMPLETE,INVALID);
 setup();reg(0x100,0x01000101);run(32,INV|MEM|MAPPED|HEADER|LEGACY,COMPLETE,INVALID);
 setup();reg(0x110,0x02000102);run(256,INV|MEM|MAPPED|HEADER|LEGACY|PROTO2,COMPLETE,INVALID);
 setup();no_inventory=1;run(0,0,INV,INVALID);CHECK(!pci_reads&&!mmio_attempts);
 setup();inventory.value.error_code=ERR;r=run(0,INV,0,ERR);CHECK(r.inventory_error==ERR&&!pci_reads&&!mmio_attempts);
 setup();inventory.value.flags=256;r=run(0,INV|NONE,0,0);CHECK(!pci_reads&&!mmio_attempts);
 setup();inventory.value.flags|=64;r=run(0,INV|BAD_BAR,0,0);CHECK(!pci_reads&&!mmio_attempts);
 setup();command=0xabcd0404;r=run(0,INV|MEM_OFF,MEM|MAPPED,0);CHECK(r.pci_command==0x404&&!mmio_attempts);
 setup();pci_error=1;run(0,INV,0,ERR);CHECK(!mmio_attempts);
 for(unsigned i=0;i<3;i++){setup();fail_offset=i==0?0:i==1?16:0x104;r=run(0,INV|MEM|MMIO_ERROR,i==0?MAPPED:0,ERR);CHECK(r.read_count==mmio_success&&mmio_attempts==mmio_success+1);}
}
int main(void){supported_and_features();ownership_unknown_and_protocol();bounds_errors_and_skips();printf("XHCI_CAPS_NATIVE_OK cases=%u checks=%u report256; first_page_only; readonly; sticky; successful_read_count\n",cases,checks);return 0;}
#endif
