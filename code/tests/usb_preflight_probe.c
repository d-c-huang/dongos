/* Independent PCI inventory oracle. Only configuration-read/view boundaries
 * are host callbacks. The actual Dong scanner, BAR and map code execute. */
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define ABI __attribute__((sysv_abi))
typedef uint64_t U;
typedef struct { U framebuffer_base,framebuffer_size,width,height,stride,pixel_format; } Display;
typedef struct { Display display;U boot_info,raw_map,raw_size,descriptor_size,rsdp,rsdp_size,pool,pool_physical,pool_pages,stack_bottom,stack_top,stack_probe_bottom,stack_probe_top,root_physical; } View;
typedef struct { U version,done,error_code,flags,xhci_count,ehci_count,ohci_count,uhci_count,other_count,pci_count,usb_counts,ecam,identity,class_code,header,bar0,bar1,bar_physical,descriptor_found,descriptor_index,descriptor_type,descriptor_base,descriptor_pages,descriptor_attributes,framebuffer_base,framebuffer_bytes,mcfg_base,mcfg_first,mcfg_last; } Report;
typedef struct { U low[4];View view;U high[4]; } ViewGuard;
typedef struct { U low[4];unsigned char bytes[16*256];U high[4]; } RawGuard;
typedef struct { U ecam;uint32_t identity,code,header,bar0,bar1; } Function;
typedef struct { U low[4];Function functions[128];U high[4]; } ConfigGuard;
_Static_assert(sizeof(Report)==232&&sizeof(View)==160&&sizeof(Display)==48,"actual ABI sizes");
_Static_assert(offsetof(View,raw_map)==56&&offsetof(View,descriptor_size)==72&&offsetof(View,root_physical)==152,"actual RuntimeView offsets");
extern ABI const Report *dong_usb_preflight_run(void);
extern ABI const Report *dong_usb_preflight_pointer(void);
extern ABI void usb_preflight_reset(void);
extern U usb_preflight_report_canary_low[4],usb_preflight_report_canary_high[4];
static ViewGuard vg;static RawGuard raw;static ConfigGuard cfg;
static U base,first,last,fail_address,read_count,region_count,view_count,write_count;
static unsigned used,null_view,misaligned_view,bad_view_span,dense,forbid_reads,cases,checks;
static const U HHDM=UINT64_C(0xffff800000000000),RUNTIME=UINT64_C(0x8000000000000000),INVALID=UINT64_C(0x0b010001),INJECTED=UINT64_C(0x050a0002);
enum { SELECTED=1,MEMORY=2,COVERED=4,RT=8,NON_MMIO=16,FB_OVERLAP=32,BAD_BAR=64,NONE=128,COMPLETE=256,MULTIPLE=512,OTHER=1024,CLAMPED=2048,BAR64=4096,PREFLIGHT_UNALIGNED=8192 };
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"USB_PREFLIGHT_ASSERT case=%u line=%u: %s\n",cases,__LINE__,#x);exit(1);}}while(0)
ABI void __dong_panic(U code,U line,const char *file,U bytes){(void)file;(void)bytes;fprintf(stderr,"unexpected panic %llx line=%llu\n",(unsigned long long)code,(unsigned long long)line);exit(99);}
ABI U usb_info_region_base(void){CHECK(!forbid_reads);region_count++;return base;}
ABI U usb_info_region_first(void){CHECK(!forbid_reads);region_count++;return first;}
ABI U usb_info_region_last(void){CHECK(!forbid_reads);region_count++;return last;}
ABI const View *usb_info_runtime_view(void){CHECK(!forbid_reads);view_count++;if(null_view)return NULL;if(bad_view_span)return (const View *)(uintptr_t)UINT64_C(0x00007ffffffffff0);return (const View *)((const unsigned char *)&vg.view+misaligned_view);}
ABI U usb_info_configuration_read(U address,uint32_t *out){
 CHECK(!forbid_reads);read_count++;if(address==fail_address)return 1;
 CHECK(address>=base+(first<<20)&&address<base+((last+1)<<20)&&!(address&3));
 U ecam=address&~UINT64_C(4095),offset=address&4095;Function *f=NULL;
 if(dense){static Function all;all=(Function){ecam,UINT32_C(0x12348086),UINT32_C(0x0c033001),((address>>12)&7)?0:0x80,UINT32_C(0xfee01000),0};f=&all;}
 else for(unsigned i=0;i<used;i++)if(cfg.functions[i].ecam==ecam){f=&cfg.functions[i];break;}
 if(!f){CHECK(offset==0);*out=UINT32_MAX;return 0;}
 if(offset==0)*out=f->identity;
 else if(offset==8)*out=f->code;
 else if(offset==12)*out=f->header<<16;
 else if(offset==16)*out=f->bar0;
 else if(offset==20)*out=f->bar1;
 else{CHECK(0);}
 return 0;
}
/* Any accidental future reference to a write boundary is counted, never sent
 * to hardware. Current allowed DG stub exports no write operation at all. */
ABI U usb_info_configuration_write(U address,U value){(void)address;(void)value;write_count++;return 1;}
static void put64(void *p,U value){memcpy(p,&value,8);}
static void descriptor(unsigned index,U kind,U address,U pages,U attributes){
 CHECK(index<16&&vg.view.descriptor_size>=40&&vg.view.descriptor_size<=256);
 unsigned char *p=raw.bytes+index*vg.view.descriptor_size;memset(p,0xc7,(size_t)vg.view.descriptor_size);
 uint32_t k=(uint32_t)kind;memcpy(p,&k,4);memset(p+4,0,4);put64(p+8,address);put64(p+16,0);put64(p+24,pages);put64(p+32,attributes);
}
static U address(unsigned bus,unsigned device,unsigned function){return base+((U)bus<<20)+((U)device<<15)+((U)function<<12);}
static Function *add(unsigned bus,unsigned device,unsigned function,uint32_t code,uint32_t header,uint32_t bar0,uint32_t bar1){
 CHECK(used<128);Function *f=&cfg.functions[used++];*f=(Function){address(bus,device,function),UINT32_C(0x12348086),code,header,bar0,bar1};return f;
}
static void setup(void){
 cases++;memset(&vg,0xa6,sizeof vg);memset(&raw,0xb7,sizeof raw);memset(&cfg,0xc8,sizeof cfg);memset(&vg.view,0,sizeof vg.view);
 base=UINT64_C(0xe0000000);first=last=3;used=dense=forbid_reads=null_view=misaligned_view=bad_view_span=0;
 fail_address=read_count=region_count=view_count=write_count=0;
 vg.view.display=(Display){HHDM+UINT64_C(0xd0000000),UINT64_C(0x200000),640,480,672,0};
 vg.view.raw_map=(U)(uintptr_t)raw.bytes;vg.view.raw_size=48;vg.view.descriptor_size=48;
 descriptor(0,11,UINT64_C(0xfee01000),1,RUNTIME|1);
 for(unsigned i=0;i<4;i++){usb_preflight_report_canary_low[i]=UINT64_C(0x191a2b3c4d5e6f70)+i;usb_preflight_report_canary_high[i]=UINT64_C(0xf1e2d3c4b5a69788)+i;}
 usb_preflight_reset();const Report *r=dong_usb_preflight_pointer();Report zero={0};CHECK(!memcmp(r,&zero,sizeof zero));
 CHECK((uintptr_t)r==(uintptr_t)usb_preflight_report_canary_low+sizeof usb_preflight_report_canary_low);CHECK((uintptr_t)usb_preflight_report_canary_high==(uintptr_t)r+sizeof *r);
 CHECK(!read_count&&!region_count&&!view_count&&!write_count);
}
static Report basic(U flags){Report r={0};r.version=r.done=1;r.flags=flags;r.framebuffer_base=vg.view.display.framebuffer_base-HHDM;r.framebuffer_bytes=vg.view.display.framebuffer_size;r.mcfg_base=base;r.mcfg_first=first;r.mcfg_last=last;return r;}
static void counts(Report *r,U x,U e,U o,U u,U other,U pci){r->xhci_count=x;r->ehci_count=e;r->ohci_count=o;r->uhci_count=u;r->other_count=other;r->pci_count=pci;r->usb_counts=(x>65535?65535:x)|((e>65535?65535:e)<<16)|((o>65535?65535:o)<<32)|((u>65535?65535:u)<<48);}
static void selected(Report *r,const Function *f,U physical,U flags){r->ecam=f->ecam;r->identity=f->identity;r->class_code=f->code>>8;r->header=f->header;r->bar0=f->bar0;r->bar1=f->bar1;r->bar_physical=physical;r->flags|=SELECTED|flags;}
static void described(Report *r,U index,U type,U address0,U pages,U attributes){r->descriptor_found=1;r->descriptor_index=index;r->descriptor_type=type;r->descriptor_base=address0;r->descriptor_pages=pages;r->descriptor_attributes=attributes;r->flags|=COVERED;if(type!=11)r->flags|=NON_MMIO;if(attributes&RUNTIME)r->flags|=RT;}
static Report run(const Report *expected,U status,unsigned zero_reads){
 RawGuard oldraw=raw;ViewGuard oldview=vg;ConfigGuard oldcfg=cfg;U low[4],high[4];memcpy(low,usb_preflight_report_canary_low,sizeof low);memcpy(high,usb_preflight_report_canary_high,sizeof high);
 const Report *p=dong_usb_preflight_run();CHECK(p==dong_usb_preflight_pointer()&&p->version==1&&p->done==1&&p->error_code==status);
 if(expected&&memcmp(p,expected,sizeof *p)){const U *a=(const U *)p,*b=(const U *)expected;for(unsigned i=0;i<29;i++)if(a[i]!=b[i])fprintf(stderr,"field=%u actual=%llx expected=%llx\n",i,(unsigned long long)a[i],(unsigned long long)b[i]);CHECK(!memcmp(p,expected,sizeof *p));}
 if(zero_reads)CHECK(!read_count);CHECK(!write_count);
 CHECK(!memcmp(&oldraw,&raw,sizeof raw)&&!memcmp(&oldview,&vg,sizeof vg)&&!memcmp(&oldcfg,&cfg,sizeof cfg));
 CHECK(!memcmp(low,usb_preflight_report_canary_low,sizeof low)&&!memcmp(high,usb_preflight_report_canary_high,sizeof high));
 Report saved=*p;U reads=read_count,regions=region_count,views=view_count;forbid_reads=1;
 CHECK(dong_usb_preflight_run()==p&&!memcmp(p,&saved,sizeof saved));CHECK(read_count==reads&&region_count==regions&&view_count==views&&!write_count);
 CHECK(!memcmp(&oldraw,&raw,sizeof raw)&&!memcmp(&oldview,&vg,sizeof vg)&&!memcmp(&oldcfg,&cfg,sizeof cfg));return saved;
}
static void no_xhci_and_order(void){
 setup();Report r=basic(NONE|COMPLETE);run(&r,0,0);
 setup();add(3,0,0,0x0c032001,0,0,0);add(3,1,0,0x0c031002,0,0,0);add(3,2,0,0x0c030003,0,0,0);add(3,3,0,0x0c03fe04,0,0,0);add(3,4,0,0x01060100,0,0,0);
 r=basic(NONE|COMPLETE|OTHER);counts(&r,0,1,1,1,1,5);run(&r,0,0);
 setup();Function *f=add(3,0,0,0x0c033000,0x81,0,0);(void)f;
 f=add(3,0,1,0x0c03302a,0,0x00001004,0x12);add(3,0,2,0x0c032000,0,0,0);add(3,0,3,0x0c031000,0,0,0);add(3,0,4,0x0c030000,0,0,0);add(3,0,5,0x0c03ff00,0,0,0);add(3,0,6,0x01060100,0,0,0);add(3,1,0,0x0c033001,0,0xfee01000,0);
 descriptor(0,11,UINT64_C(0x1200001000),1,UINT64_C(0x8123456789abcdef));
 r=basic(COMPLETE|OTHER);counts(&r,3,1,1,1,1,8);selected(&r,f,UINT64_C(0x1200001000),MEMORY|BAR64);described(&r,0,11,UINT64_C(0x1200001000),1,UINT64_C(0x8123456789abcdef));run(&r,0,0);
 setup();f=add(3,0,0,0x0c033000,0x80,0,0);f->identity=0x12340000;add(3,0,1,0x0c033000,0,0xfee01000,0);f=add(3,1,0,0x0c033000,0,0,0);f->identity=0x1234ffff;r=basic(NONE|COMPLETE);run(&r,0,0);
 setup();last=5;add(2,0,0,0x0c033000,0,0,0);f=add(3,2,0,0x0c0330ff,0x80,0xfee01000,0xfeedface);add(5,0,0,0x0c033000,0,0xdead0000,0);
 r=basic(COMPLETE);counts(&r,2,0,0,0,0,2);selected(&r,f,0xfee01000,MEMORY);described(&r,0,11,0xfee01000,1,RUNTIME|1);run(&r,0,0);
}
static void bars_and_descriptors(void){
 const U attrs[]={0,1,8,UINT64_C(0x12345678abcdef01),UINT64_C(0x8000000000000000),UINT64_C(0x8123456789abcdef)};
 const unsigned strides[]={40,48,256};const unsigned types[]={0,7,11,12};
 for(unsigned s=0;s<3;s++)for(unsigned t=0;t<4;t++)for(unsigned a=0;a<6;a++){
  setup();vg.view.descriptor_size=vg.view.raw_size=strides[s];descriptor(0,types[t],0xfee01000,1,attrs[a]);Function *f=add(3,0,0,0x0c033001,0,0xfee01000,0x12345678);
  Report r=basic(COMPLETE);counts(&r,1,0,0,0,0,1);selected(&r,f,0xfee01000,MEMORY);described(&r,0,types[t],0xfee01000,1,attrs[a]);run(&r,0,0);
 }
 setup();Function *f=add(3,0,0,0x0c033000,0,0xfee01180,0);vg.view.raw_size=144;descriptor(0,11,0x100000,1,0);descriptor(1,7,0xfee01000,1,UINT64_C(0x8123456789abcdef));descriptor(2,11,0xfee00000,3,0);
 Report r=basic(COMPLETE|MULTIPLE);counts(&r,1,0,0,0,0,1);selected(&r,f,0xfee01180,MEMORY|PREFLIGHT_UNALIGNED);described(&r,1,7,0xfee01000,1,UINT64_C(0x8123456789abcdef));run(&r,0,0);
 setup();f=add(3,0,0,0x0c033000,0,0xfee01000,0);descriptor(0,7,0x100000,1,0);r=basic(COMPLETE);counts(&r,1,0,0,0,0,1);selected(&r,f,0xfee01000,MEMORY);run(&r,0,0);
 const uint32_t lows[]={0xd000c001,0xfee01002,0xfee01006,0,0xfffffff4};
 for(unsigned i=0;i<5;i++){
  setup();f=add(3,0,0,0x0c033000,0,lows[i],i==4?UINT32_MAX:0);r=basic(COMPLETE);counts(&r,1,0,0,0,0,1);
  U physical=i==4?UINT64_C(0xfffffffffffffff0):0;U flags=BAD_BAR|(i?MEMORY:0)|(i==4?(BAR64|PREFLIGHT_UNALIGNED):0);selected(&r,f,physical,flags);run(&r,0,0);
 }
 for(unsigned i=0;i<3;i++){
  setup();f=add(3,0,0,0x0c033000,0,0xfee01180,0);U fb=i==0?UINT64_C(0xfee01ffc):i==1?UINT64_C(0xfee00ffc):UINT64_C(0xfee02000);
  vg.view.display=(Display){HHDM+fb,4,1,1,1,0};r=basic(COMPLETE|(i==0?FB_OVERLAP:0));counts(&r,1,0,0,0,0,1);selected(&r,f,0xfee01180,MEMORY|PREFLIGHT_UNALIGNED);described(&r,0,11,0xfee01000,1,RUNTIME|1);run(&r,0,0);
 }
 setup();first=0;last=255;dense=1;Function all={base,UINT32_C(0x12348086),UINT32_C(0x0c033001),0x80,UINT32_C(0xfee01000),0};r=basic(COMPLETE|CLAMPED);counts(&r,65536,0,0,0,0,65536);selected(&r,&all,0xfee01000,MEMORY);described(&r,0,11,0xfee01000,1,RUNTIME|1);run(&r,0,0);
}
static void malformed_and_read_errors(void){
 for(unsigned i=0;i<22;i++){
  setup();switch(i){
   case 0:base=0;break;case 1:base=UINT64_C(0x100000000);break;case 2:base+=4096;break;case 3:first=5;last=4;break;case 4:last=256;break;case 5:base=0xfff00000;last=1;break;
   case 6:null_view=1;break;case 7:misaligned_view=1;break;case 8:bad_view_span=1;break;case 9:vg.view.raw_map=0;break;case 10:vg.view.raw_map++;break;case 11:vg.view.raw_size=0;break;case 12:vg.view.raw_size=65537;break;case 13:vg.view.descriptor_size=39;break;case 14:vg.view.descriptor_size=264;break;case 15:vg.view.descriptor_size=41;break;case 16:vg.view.raw_size=47;break;case 17:vg.view.raw_map=(U)(uintptr_t)dong_usb_preflight_pointer();break;case 18:vg.view.raw_map=(U)(uintptr_t)&vg.view;break;case 19:vg.view.display.pixel_format=2;break;case 20:vg.view.display.framebuffer_size=4;break;default:descriptor(0,11,0xfee01000,0,0);break;
  }
  Report actual=run(NULL,INVALID,1);CHECK(!(actual.flags&COMPLETE)&&actual.pci_count==0&&actual.xhci_count==0);
 }
 for(unsigned i=0;i<5;i++){
  setup();Function *f=add(3,0,0,0x0c033001,0,0xfee01000,0x12345678);
  fail_address=i==0?f->ecam+8:i==1?f->ecam+12:i==2?address(3,1,0):i==3?f->ecam+16:f->ecam+20;
  Report actual=run(NULL,INJECTED,0);CHECK(!(actual.flags&COMPLETE));CHECK(actual.pci_count==(i>=2?1:0));CHECK(actual.xhci_count==(i>=2?1:0));
  CHECK(actual.bar0==(i==4?f->bar0:0)&&actual.bar1==0&&actual.descriptor_found==0);
 }
}
int main(void){no_xhci_and_order();bars_and_descriptors();malformed_and_read_errors();printf("USB_PREFLIGHT_NATIVE_OK cases=%u checks=%u report232; PCI_read_only; actual_scan_BAR_map; sticky; no_writes\n",cases,checks);return 0;}
