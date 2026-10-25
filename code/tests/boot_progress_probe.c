/* Independent RAM/glyph oracle. Only the real safe helper/renderer executes. */
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
#define DG __attribute__((sysv_abi))
typedef uint64_t U;
typedef struct {U word,epoch,drained,opened;} Gate;
typedef struct {U framebuffer_base,framebuffer_size,width,height,stride,pixel_format;} Display;
typedef struct {U version,valid,error,slot,address,page,descriptor_index,kind,base,pages,attributes;} Conflict;
_Static_assert(sizeof(Gate)==32&&offsetof(Gate,opened)==24,"independent existing Gate ABI");
_Static_assert(sizeof(Display)==48&&offsetof(Display,pixel_format)==40,"independent RuntimeView display prefix");
_Static_assert(RUNTIME_VIEW_BYTES>=sizeof(Display),"actual compiled complete RuntimeView");
_Static_assert(sizeof(Conflict)==88&&MMIO_CONTEXT_BYTES==sizeof(Conflict),"actual compiled Conflict size");
_Static_assert(offsetof(Conflict,version)==0&&offsetof(Conflict,valid)==8&&offsetof(Conflict,error)==16,"Conflict status offsets");
_Static_assert(offsetof(Conflict,slot)==24&&offsetof(Conflict,address)==32&&offsetof(Conflict,page)==40,"Conflict device offsets");
_Static_assert(offsetof(Conflict,descriptor_index)==48&&offsetof(Conflict,kind)==56&&offsetof(Conflict,base)==64,"Conflict descriptor offsets");
_Static_assert(offsetof(Conflict,pages)==72&&offsetof(Conflict,attributes)==80,"Conflict extent offsets");
extern U DG probe_invoke(U,U,U);
extern Gate *DG probe_gate(void);
extern uint8_t boot_progress_phase,boot_progress_failed;
extern U boot_progress_error,boot_progress_view,boot_progress_cpus;
extern Conflict boot_progress_mmio;
U panic_saved_frames[16],panic_saved_frame_count;

#define CLOSED (UINT64_C(1)<<63)
#define CLOSING (UINT64_C(1)<<62)
#define SENTINEL UINT32_C(0xa5a5a5a5)
#define WHITE UINT32_C(0x00f4f4f4)
#define RAM_CONFLICT UINT64_C(0x03030002)
static const U FLAG_BITS=UINT64_C(0xcd5);
static const char *scenario="setup";
static unsigned checks,cases;
static Gate *gate;
static uint8_t *view_allocation,*view,*view_before;
static uint8_t *pixels,*pixels_before;
static void *fb_mapping;
static size_t fb_mapping_size,fb_size,guard_page;
static Display *display;
static const char *const titles[15]={"DONGOS P3 ACPI READY",
 "DONGOS S01 IRQ PREPARE","DONGOS S02 IRQ PLATFORM","DONGOS S03 THREADS TEST",
 "DONGOS S04 THREADS PASS","DONGOS S05 AVX CHECK","DONGOS S06 SMP START",
 "DONGOS S07 SMP APS READY","DONGOS S08 SMP LARGE TEST","DONGOS S09 SMP PARALLEL TEST",
 "DONGOS S10 SMP PASS","DONGOS S11 DESKTOP ENABLE","DONGOS S12 SERVICES PREPARE",
 "DONGOS S13 ELF READY","DONGOS S14 CPL3 START"};
/* Stated independently from the production font storage. */
static const uint8_t digits[16][7]={
 {14,17,19,21,25,17,14},{4,12,4,4,4,4,14},{14,17,1,2,4,8,31},{30,1,1,14,1,1,30},
 {2,6,10,18,31,2,2},{31,16,16,30,1,1,30},{14,16,16,30,17,17,14},{31,1,2,4,8,8,8},
 {14,17,17,14,17,17,14},{14,17,17,15,1,1,14},{14,17,17,31,17,17,17},{30,17,17,30,17,17,30},
 {14,17,16,16,16,17,14},{30,17,17,17,17,17,30},{31,16,16,30,16,16,31},{31,16,16,30,16,16,16}};
static const uint8_t letters[26][7]={
 {14,17,17,31,17,17,17},{30,17,17,30,17,17,30},{14,17,16,16,16,17,14},
 {30,17,17,17,17,17,30},{31,16,16,30,16,16,31},{31,16,16,30,16,16,16},
 {14,17,16,23,17,17,15},{17,17,17,31,17,17,17},{14,4,4,4,4,4,14},
 {7,2,2,2,2,18,12},{17,18,20,24,20,18,17},{16,16,16,16,16,16,31},
 {17,27,21,21,17,17,17},{17,25,21,19,17,17,17},{14,17,17,17,17,17,14},
 {30,17,17,30,16,16,16},{14,17,17,17,21,18,13},{30,17,17,30,20,18,17},
 {15,16,16,14,1,1,30},{31,4,4,4,4,4,4},{17,17,17,17,17,17,14},
 {17,17,17,17,17,10,4},{17,17,17,21,21,21,10},{17,17,10,4,10,17,17},
 {17,17,10,4,4,4,4},{31,1,2,4,8,16,31}};
#define REQUIRE(x) do{++checks;if(!(x)){fprintf(stderr,"boot progress oracle failed case=%s line=%d check=%s; returned normally\n",scenario,__LINE__,#x);return 1;}}while(0)
static int all(const uint8_t *p,size_t n,uint8_t v){for(size_t i=0;i<n;i++)if(p[i]!=v)return 0;return 1;}
static uint32_t pixel(unsigned x,unsigned y){uint32_t p;memcpy(&p,pixels+((size_t)y*672+x)*4,4);return p;}
static uint32_t background(void){return display->pixel_format?UINT32_C(0x0020141b):UINT32_C(0x001b1420);}
static int glyph(unsigned x,unsigned y,unsigned char c){
 static const uint8_t blank[7]={0};const uint8_t *rows=blank;uint32_t bg=background();
 if(c>='0'&&c<='9')rows=digits[c-'0'];
 else if(c>='A'&&c<='Z')rows=letters[c-'A'];
 else if(c!=' ')return 0;
 for(unsigned row=0;row<7;row++)for(unsigned col=0;col<7;col++){
  uint32_t wanted=col<5&&(rows[row]&(1u<<(4-col)))?WHITE:bg;
  for(unsigned dy=0;dy<2;dy++)for(unsigned dx=0;dx<2;dx++)
   if(pixel(x+2*col+dx,y+2*row+dy)!=wanted)return 0;
 }
 return 1;
}
static int text(unsigned x,unsigned y,const char *s){
 size_t n=strlen(s);for(size_t i=0;i<n;i++)if(!glyph(x+(unsigned)i*14,y,(unsigned char)s[i]))return 0;
 return glyph(x+(unsigned)n*14,y,' ');
}
static int hex(unsigned x,unsigned y,U n){
 static const char table[]="0123456789ABCDEF";
 for(unsigned i=0;i<16;i++)if(!glyph(x+14*i,y,(unsigned char)table[(n>>(60-4*i))&15]))return 0;
 return glyph(x+224,y,' ');
}
static int edges(void){
 for(unsigned y=0;y<480;y++){
  if(pixel(0,y)!=background()||pixel(639,y)!=background())return 0;
  for(unsigned x=640;x<672;x++)if(pixel(x,y)!=SENTINEL)return 0;
 }
 for(unsigned x=0;x<640;x++)if(pixel(x,0)!=background()||pixel(x,479)!=background())return 0;
 return 1;
}
static int view_guards(void){
 REQUIRE(all(view_allocation,32,0x3c)&&all(view+RUNTIME_VIEW_BYTES,32,0xc3));
 REQUIRE(!memcmp(view,view_before,RUNTIME_VIEW_BYTES));return 0;
}
static void reset(U format,U gate_word){
 memset(view_allocation,0x3c,32);memset(view,0xa5,RUNTIME_VIEW_BYTES);memset(view+RUNTIME_VIEW_BYTES,0xc3,32);
 *display=(Display){(U)(uintptr_t)pixels,(U)fb_size,640,480,672,format};
 memcpy(view_before,view,RUNTIME_VIEW_BYTES);memset(pixels,0xa5,fb_size);
 *gate=(Gate){gate_word,UINT64_C(0x1122334455667788),UINT64_C(0x2233445566778899),UINT64_C(0x33445566778899aa)};
 boot_progress_phase=0;boot_progress_failed=0;boot_progress_error=0;boot_progress_cpus=UINT64_C(0x0123456789abcdef);
 memset(&boot_progress_mmio,0,sizeof boot_progress_mmio);
 boot_progress_view=(U)(uintptr_t)view;
}
static int invoke(U action,U rax,U flags){
 Gate saved=*gate;Conflict saved_context=boot_progress_mmio;REQUIRE(probe_invoke(action,rax,flags)==0);
 REQUIRE(!memcmp(gate,&saved,sizeof saved));REQUIRE(!memcmp(&boot_progress_mmio,&saved_context,sizeof saved_context));return view_guards();
}
static int progress_pixels(unsigned phase,unsigned failed,U error,U cpus){
 const char *stage=phase<=14?titles[phase]:"DONGOS P7 BOOT STAGE";
 REQUIRE(edges());REQUIRE(text(56,48,failed?"DONGOS BOOT FAILED":stage));
 REQUIRE(text(56,84,failed?stage:"BSP BOOT PROGRESS"));
 REQUIRE(text(56,120,"STAGE")&&hex(56,156,phase));
 REQUIRE(text(56,192,"CPU COUNT")&&hex(56,228,cpus));
 REQUIRE(text(56,264,"FIRST ERROR")&&hex(56,300,error));return 0;
}
static int normal_stages(void){
 for(U format=0;format<2;format++)for(U active=0;active<2;active++){
  scenario="phase0 remains the original ACPI display";reset(format,active);
  if(invoke(0,UINT64_MAX,FLAG_BITS))return 1;
  REQUIRE(text(56,48,titles[0])&&edges());
  for(unsigned phase=1;phase<=14;phase++){
   scenario=titles[phase];memset(pixels,0xa5,fb_size);
   if(invoke(phase,UINT64_C(0xfedcba9876543210),phase&1?FLAG_BITS:0))return 1;
   REQUIRE(boot_progress_phase==phase&&boot_progress_failed==0&&boot_progress_error==0);
   if(progress_pixels(phase,0,0,boot_progress_cpus))return 1;
   ++cases;
  }
 }
 return 0;
}
static int sticky_errors(void){
 static const U errors[]={UINT64_C(0x0123456789abcdef),UINT64_C(0xfedcba9876543210),0};
 for(U format=0;format<2;format++)for(unsigned i=0;i<3;i++){
  scenario="first full-width error remains sticky";reset(format,0);
  if(invoke(12,0,FLAG_BITS)||invoke(15,errors[i],FLAG_BITS))return 1;
  REQUIRE(boot_progress_failed==1&&boot_progress_error==errors[i]&&boot_progress_phase==12);
  if(progress_pixels(12,1,errors[i],boot_progress_cpus))return 1;
  if(invoke(15,~errors[i],0)||invoke(14,0,FLAG_BITS))return 1;
  REQUIRE(boot_progress_failed==1&&boot_progress_error==errors[i]&&boot_progress_phase==14);
  if(progress_pixels(14,1,errors[i],boot_progress_cpus))return 1;
  ++cases;
 }
 return 0;
}
static int invalid_and_disabled(void){
 static const unsigned phases[]={15,255};
 for(unsigned i=0;i<2;i++){
  scenario="unknown phase uses bounded generic title";reset(i,0);boot_progress_phase=(uint8_t)phases[i];
  if(invoke(0,0,FLAG_BITS))return 1;
  REQUIRE(boot_progress_phase==phases[i]);if(progress_pixels(phases[i],0,0,boot_progress_cpus))return 1;++cases;
 }
 scenario="unarmed helper does not touch RAM or a null View";reset(0,0);boot_progress_view=0;
 memcpy(pixels_before,pixels,fb_size);if(invoke(1,0,FLAG_BITS))return 1;REQUIRE(!memcmp(pixels_before,pixels,fb_size));
 scenario="disable clears only the arm and stage cannot rearm";reset(1,0);
 if(invoke(3,0,0)||invoke(16,0,FLAG_BITS))return 1;REQUIRE(boot_progress_view==0);
 memcpy(pixels_before,pixels,fb_size);if(invoke(4,0,FLAG_BITS)||invoke(15,UINT64_MAX,0)||invoke(0,0,FLAG_BITS))return 1;
 REQUIRE(boot_progress_view==0&&!memcmp(pixels_before,pixels,fb_size));return 0;
}
static int denied_gate(void){
 static const U denied[]={CLOSED,CLOSING,CLOSED|CLOSING,UINT64_C(1)<<32,UINT64_C(1)<<61,UINT64_C(0xffffffff),CLOSED|7,CLOSING|9};
 for(unsigned i=0;i<sizeof denied/sizeof denied[0];i++){
  scenario="denied Gate rejects RAM drawing and preserves all four words";reset(i&1,denied[i]);
  memcpy(pixels_before,pixels,fb_size);if(invoke(1,0,FLAG_BITS)||invoke(15,UINT64_MAX,FLAG_BITS))return 1;
  REQUIRE(!memcmp(pixels_before,pixels,fb_size));
  scenario="denied Gate never dereferences poison RuntimeView";boot_progress_view=1;
  if(invoke(0,0,FLAG_BITS)||invoke(2,0,0)||invoke(15,UINT64_C(0x123456789abcdef0),FLAG_BITS))return 1;
  REQUIRE(boot_progress_view==1&&!memcmp(pixels_before,pixels,fb_size));++cases;
 }
 return 0;
}
static int invalid_geometry(void){
 for(unsigned i=0;i<12;i++){
  scenario="actual renderer rejects invalid geometry without touching pixels";reset(i&1,1);
  switch(i){
   case 0:display->pixel_format=2;break;case 1:display->width=639;break;
   case 2:display->width=8193;break;case 3:display->height=479;break;
   case 4:display->height=8193;break;case 5:display->stride=639;break;
   case 6:display->stride=16385;break;case 7:display->framebuffer_size--;break;
   case 8:display->framebuffer_base=0;break;case 9:display->width=UINT64_MAX;break;
   case 10:display->height=UINT64_MAX;break;default:display->stride=UINT64_MAX;break;
  }
  memcpy(view_before,view,RUNTIME_VIEW_BYTES);memcpy(pixels_before,pixels,fb_size);
  if(invoke(13,0,FLAG_BITS))return 1;
  REQUIRE(!memcmp(pixels_before,pixels,fb_size));++cases;
 }
 return 0;
}
static void mmio_context(U slot){
 boot_progress_phase=1;boot_progress_failed=1;boot_progress_error=RAM_CONFLICT;
 boot_progress_mmio=(Conflict){1,1,RAM_CONFLICT,slot,UINT64_C(0xfedcba9876543210),
  UINT64_C(0xfedcba9876543000),UINT64_C(0x66778899aabbccdd),UINT64_C(0x1020304050607080),
  UINT64_C(0x13579bdf2468a000),UINT64_C(0x12345678abcdef01),UINT64_C(0x8000000000000001)};
}
static int mmio_pixels(void){
 static const char *const labels[]={"STAGE","CPU COUNT","FIRST ERROR","DEVICE SLOT","DEV ADDRESS","UEFI TYPE","DESC BASE","DESC PAGES","EFI ATTR"};
 const U values[]={1,boot_progress_cpus,RAM_CONFLICT,boot_progress_mmio.slot,boot_progress_mmio.address,
  boot_progress_mmio.kind,boot_progress_mmio.base,boot_progress_mmio.pages,boot_progress_mmio.attributes};
 REQUIRE(edges());REQUIRE(text(56,48,"DONGOS BOOT FAILED")&&text(56,84,titles[1]));
 for(unsigned i=0;i<9;i++){unsigned y=120+i*28;REQUIRE(text(56,y,labels[i])&&hex(238,y,values[i]));}
 return 0;
}
static int valid_mmio_contexts(void){
 for(U format=0;format<2;format++)for(U active=0;active<2;active++)for(U slot=0;slot<11;slot++){
  scenario="all MMIO slots render raw full-width context under the existing Gate";reset(format,active);mmio_context(slot);
  REQUIRE(((uintptr_t)&boot_progress_mmio&7)==0);
  if(invoke(15,RAM_CONFLICT,slot&1?FLAG_BITS:0)||mmio_pixels())return 1;
  REQUIRE(boot_progress_error==RAM_CONFLICT&&boot_progress_failed==1&&boot_progress_phase==1);++cases;
 }
 return 0;
}
static int rejected_mmio_contexts(void){
 for(U format=0;format<2;format++)for(unsigned variant=0;variant<17;variant++){
  scenario="MMIO diagnostic requires exact phase first error version valid and context error";reset(format,0);mmio_context(9);
  switch(variant){
   case 0:boot_progress_mmio.version=0;break;case 1:boot_progress_mmio.version=2;break;
   case 2:boot_progress_mmio.version=UINT64_C(0x100000001);break;
   case 3:boot_progress_mmio.valid=0;break;case 4:boot_progress_mmio.valid=2;break;
   case 5:boot_progress_mmio.valid=UINT64_C(0x100000001);break;
   case 6:boot_progress_mmio.error=0;break;case 7:boot_progress_mmio.error=RAM_CONFLICT+1;break;
   case 8:boot_progress_mmio.error=UINT64_C(0x100000000)|RAM_CONFLICT;break;
   case 9:boot_progress_error=RAM_CONFLICT+1;break;
   case 10:boot_progress_error=UINT64_C(0x100000000)|RAM_CONFLICT;break;
   case 11:boot_progress_phase=0;break;case 12:boot_progress_phase=2;break;
   case 13:boot_progress_phase=14;break;case 14:boot_progress_phase=255;break;
   case 15:boot_progress_failed=0;break;default:boot_progress_failed=2;break;
  }
  if(invoke(0,UINT64_MAX,FLAG_BITS)||progress_pixels(boot_progress_phase,boot_progress_failed,boot_progress_error,boot_progress_cpus))return 1;
  ++cases;
 }
 return 0;
}
static int protected_mmio_contexts(void){
 static const U denied[]={CLOSED,CLOSING,CLOSED|CLOSING,UINT64_C(1)<<32,UINT64_C(0xffffffff),CLOSED|7,CLOSING|9};
 for(U format=0;format<2;format++)for(unsigned i=0;i<sizeof denied/sizeof denied[0];i++){
  scenario="MMIO context respects closed Gate and poison caller View";reset(format,denied[i]);mmio_context(i);
  memcpy(pixels_before,pixels,fb_size);if(invoke(0,0,FLAG_BITS))return 1;REQUIRE(!memcmp(pixels_before,pixels,fb_size));
  boot_progress_view=1;if(invoke(15,RAM_CONFLICT,0))return 1;REQUIRE(!memcmp(pixels_before,pixels,fb_size));++cases;
 }
 for(U format=0;format<2;format++){
  scenario="unarmed MMIO context stays RAM only";reset(format,0);mmio_context(10);boot_progress_view=0;
  memcpy(pixels_before,pixels,fb_size);if(invoke(0,0,FLAG_BITS)||invoke(15,RAM_CONFLICT,0))return 1;
  REQUIRE(!memcmp(pixels_before,pixels,fb_size));++cases;
  scenario="disabled MMIO diagnostic cannot repaint after CPL3 handoff";reset(format,0);mmio_context(0);
  if(invoke(0,0,FLAG_BITS)||mmio_pixels()||invoke(16,0,0))return 1;
  memcpy(pixels_before,pixels,fb_size);if(invoke(1,0,FLAG_BITS)||invoke(15,RAM_CONFLICT,0))return 1;
  REQUIRE(boot_progress_view==0&&!memcmp(pixels_before,pixels,fb_size));++cases;
  scenario="MMIO context does not bypass invalid framebuffer geometry";reset(format,0);mmio_context(1);display->width=639;
  memcpy(view_before,view,RUNTIME_VIEW_BYTES);memcpy(pixels_before,pixels,fb_size);if(invoke(0,0,FLAG_BITS))return 1;
  REQUIRE(!memcmp(pixels_before,pixels,fb_size));++cases;
 }
 return 0;
}
static int allocate(void){
#ifdef _WIN32
 SYSTEM_INFO info;GetSystemInfo(&info);guard_page=info.dwPageSize;
#else
 long page=sysconf(_SC_PAGESIZE);if(page<=0)return 0;guard_page=(size_t)page;
#endif
 fb_size=(size_t)672*480*4;if(fb_size%guard_page)return 0;fb_mapping_size=fb_size+2*guard_page;
#ifdef _WIN32
 fb_mapping=VirtualAlloc(NULL,fb_mapping_size,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);if(!fb_mapping)return 0;
 DWORD previous;
 if(!VirtualProtect(fb_mapping,guard_page,PAGE_NOACCESS,&previous)||
    !VirtualProtect((uint8_t *)fb_mapping+guard_page+fb_size,guard_page,PAGE_NOACCESS,&previous))return 0;
#else
 fb_mapping=mmap(NULL,fb_mapping_size,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
 if(fb_mapping==MAP_FAILED){fb_mapping=NULL;return 0;}
 if(mprotect(fb_mapping,guard_page,PROT_NONE)||mprotect((uint8_t *)fb_mapping+guard_page+fb_size,guard_page,PROT_NONE))return 0;
#endif
 pixels=(uint8_t *)fb_mapping+guard_page;pixels_before=malloc(fb_size);
 view_allocation=calloc(1,RUNTIME_VIEW_BYTES+64);view_before=malloc(RUNTIME_VIEW_BYTES);
 if(!pixels_before||!view_allocation||!view_before)return 0;
 view=view_allocation+32;display=(Display *)view;gate=probe_gate();return gate!=NULL;
}
int main(void){
 if(!allocate()){fprintf(stderr,"boot progress oracle allocation failed; returned normally\n");return 97;}
 /* Mutant-sensitive RAM checks precede all poison-pointer probes. */
 if(normal_stages()||sticky_errors()||invalid_and_disabled()||invalid_geometry()||denied_gate())return 1;
 REQUIRE(cases==84);
 if(valid_mmio_contexts()||rejected_mmio_contexts()||protected_mmio_contexts())return 1;
 REQUIRE(cases==182);
 free(view_before);free(view_allocation);free(pixels_before);
#ifdef _WIN32
 (void)VirtualFree(fb_mapping,0,MEM_RELEASE);
#else
 (void)munmap(fb_mapping,fb_mapping_size);
#endif
 printf("boot progress oracle passed cases=%u checks=%u; guard pages and actual RAM renderer; returned normally\n",cases,checks);return 0;
}
