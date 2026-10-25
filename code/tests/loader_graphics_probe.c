/* Independent Microsoft-x64 UEFI layout and graphics-collection oracle. */
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#define EFI __attribute__((ms_abi))
typedef uint64_t U;
typedef struct Info {uint32_t version,width,height,format,masks[4],stride;} Info;
typedef struct Mode {uint32_t max,current;Info *info;U size,base,bytes;} Mode;
typedef struct GOP {void *query,*set,*blt;Mode *mode;} GOP;
typedef struct BootServices {uint8_t prefix[320];U(EFI *locate)(const void *,void *,GOP **);} BootServices;
typedef struct BootInfo {
 U magic,version,size,flags,memory_map,memory_map_size,descriptor_size,descriptor_version;
 U framebuffer_base,framebuffer_size,width,height,stride,pixel_format;
 U rsdp,kernel_physical,kernel_size,pml4_physical,stack_physical,stack_size;
} BootInfo;
_Static_assert(sizeof(Info)==36,"independent UEFI mode information");
_Static_assert(sizeof(Mode)==40&&offsetof(Mode,info)==8&&offsetof(Mode,size)==16,"independent UEFI mode");
_Static_assert(offsetof(GOP,mode)==24,"independent GOP interface");
_Static_assert(offsetof(BootServices,locate)==320,"UEFI BootServices LocateProtocol");
_Static_assert(sizeof(BootInfo)==160&&offsetof(BootInfo,framebuffer_base)==64,"independent BootInfo v1");
_Static_assert(offsetof(BootInfo,pixel_format)==104&&offsetof(BootInfo,rsdp)==112,"BootInfo graphic field extent");
extern U EFI probe_collect(BootServices *,BootInfo *);
extern void EFI probe_diag(GOP *);
extern U EFI probe_locate_entry(const void *,void *,GOP **);
extern uint32_t graphics_reason;
extern U graphics_status,probe_nv_bad,probe_callback_rsp_mod;

static struct {U low[4];BootInfo value;U high[4];} boot_guard;
static struct {U low[4];Info value;uint8_t high[32];} info_guard;
static struct {U low[4];Mode value;U high[4];} mode_guard;
static BootServices services;
static GOP gop;
static U locate_status,desktop_status;
static unsigned null_gop,locate_calls,desktop_calls,callback_errors,checks,cases;
static const char *scenario="setup";
enum {REASON,STATUS,MAX_MODE,CURRENT_MODE,BASE,BYTES,WIDTH,HEIGHT,STRIDE,FORMAT,LABELS};
static const char *labels[LABELS]={"GOP_FAIL_REASON=0x","GOP_FIRMWARE_STATUS=0x","GOP_MAX_MODES=0x",
 "GOP_MODE=0x","GOP_FB_BASE=0x","GOP_FB_BYTES=0x","GOP_WIDTH=0x","GOP_HEIGHT=0x","GOP_STRIDE=0x","GOP_FORMAT=0x"};
static U log_value[LABELS][4];
static unsigned log_count[LABELS],before_tags,after_tags;
#define REQUIRE(x) do{++checks;if(!(x)){fprintf(stderr,"loader graphics oracle failed case=%s line=%d check=%s; returned normally\n",scenario,__LINE__,#x);return 1;}}while(0)
static int all(const void *raw,size_t n,uint8_t expected){const uint8_t *p=raw;for(size_t i=0;i<n;i++)if(p[i]!=expected)return 0;return 1;}
static void callback(void){if(probe_callback_rsp_mod!=8)++callback_errors;}
U EFI probe_locate(const void *guid,void *registration,GOP **out){
 static const uint8_t expected[16]={0xde,0xa9,0x42,0x90,0xdc,0x23,0x38,0x4a,0x96,0xfb,0x7a,0xde,0xd0,0x80,0x51,0x6a};
 callback();++locate_calls;
 if(!guid||((uintptr_t)guid&3)||memcmp(guid,expected,16)||registration||!out){++callback_errors;return UINT64_C(0x8000000000000002);}
 *out=null_gop?NULL:&gop;return locate_status;
}
U EFI probe_desktop(GOP *p,BootServices *b){
 callback();++desktop_calls;if(p!=&gop||b!=&services)++callback_errors;return desktop_status;
}
void EFI probe_write(const char *text){
 callback();
 if(text&&!strcmp(text,"GOP current before selection\r\n")){++before_tags;return;}
 if(text&&!strcmp(text,"GOP mode after selection\r\n")){++after_tags;return;}
 ++callback_errors;
}
void EFI probe_hex(const char *label,U value){
 callback();
 for(unsigned i=0;i<LABELS;i++)if(label&&!strcmp(label,labels[i])){
  if(log_count[i]>=4){++callback_errors;return;}log_value[i][log_count[i]++]=value;return;
 }
 ++callback_errors;
}
static void reset(void){
 memset(&boot_guard,0xa5,sizeof boot_guard);memset(&info_guard,0xa5,sizeof info_guard);
 memset(&mode_guard,0xa5,sizeof mode_guard);memset(&services,0,sizeof services);
 info_guard.value=(Info){0,800,600,1,{0},800};
 mode_guard.value=(Mode){7,3,&info_guard.value,sizeof(Info),UINT64_C(0xe0000000),UINT64_C(0x800000)};
 gop=(GOP){NULL,NULL,NULL,&mode_guard.value};
 /* The harness installs the LocateProtocol thunk here before entry. Its
    callback still validates the independent GUID and argument contract. */
 services.locate=probe_locate_entry;
 locate_status=desktop_status=0;null_gop=locate_calls=desktop_calls=callback_errors=0;
 memset(log_value,0,sizeof log_value);memset(log_count,0,sizeof log_count);before_tags=after_tags=0;
 graphics_reason=0xa5a5a5a5;graphics_status=UINT64_MAX;probe_nv_bad=0;probe_callback_rsp_mod=UINT64_MAX;
}
static int guards(void){
 REQUIRE(all(boot_guard.low,sizeof boot_guard.low,0xa5)&&all(boot_guard.high,sizeof boot_guard.high,0xa5));
 REQUIRE(all(info_guard.low,sizeof info_guard.low,0xa5)&&all(info_guard.high,sizeof info_guard.high,0xa5));
 REQUIRE(all(mode_guard.low,sizeof mode_guard.low,0xa5)&&all(mode_guard.high,sizeof mode_guard.high,0xa5));
 REQUIRE(callback_errors==0&&probe_nv_bad==0);return 0;
}
static int telemetry(unsigned repetitions,unsigned fields){
 Mode *m=&mode_guard.value;
 for(unsigned i=MAX_MODE;i<LABELS;i++){
  unsigned count=i>=WIDTH?fields:repetitions;REQUIRE(log_count[i]==count);
  for(unsigned j=0;j<count;j++){
   U expected=0;
   if(i==MAX_MODE)expected=m->max;
   if(i==CURRENT_MODE)expected=m->current;
   if(i==BASE)expected=m->base;
   if(i==BYTES)expected=m->bytes;
   if(i==WIDTH)expected=info_guard.value.width;
   if(i==HEIGHT)expected=info_guard.value.height;
   if(i==STRIDE)expected=info_guard.value.stride;
   if(i==FORMAT)expected=info_guard.value.format;
   REQUIRE(log_value[i][j]==expected);
  }
 }
 return 0;
}
static int collect(const char *name,unsigned reason){
 scenario=name;
 BootInfo original=boot_guard.value;Info old_info=info_guard.value;Mode old_mode=mode_guard.value;GOP old_gop=gop;
 U status=locate_status?locate_status:(EXPECT_DESKTOP&&!null_gop?desktop_status:0);
 U result=probe_collect(&services,&boot_guard.value);
 REQUIRE(result==(reason?1u:0u));REQUIRE(graphics_reason==reason&&graphics_status==status);
 REQUIRE(locate_calls==1&&desktop_calls==(unsigned)(EXPECT_DESKTOP&&locate_status==0&&!null_gop));
 REQUIRE(before_tags==(unsigned)(locate_status==0&&!null_gop));REQUIRE(after_tags==desktop_calls);
 REQUIRE(probe_callback_rsp_mod==8);
 REQUIRE(!memcmp(&old_info,&info_guard.value,sizeof old_info));REQUIRE(!memcmp(&old_mode,&mode_guard.value,sizeof old_mode));
 REQUIRE(!memcmp(&old_gop,&gop,sizeof old_gop));
 for(unsigned i=0;i<8;i++)REQUIRE(((U *)&boot_guard.value)[i]==((U *)&original)[i]);
 for(unsigned i=14;i<20;i++)REQUIRE(((U *)&boot_guard.value)[i]==((U *)&original)[i]);
 unsigned repetitions=(locate_status==0&&!null_gop&&gop.mode)?1u+EXPECT_DESKTOP:0;
 unsigned fields=repetitions&&old_mode.size>=sizeof(Info)&&old_mode.info&&old_info.version==0?repetitions:0;
 if(telemetry(repetitions,fields)||guards())return 1;
 if(reason){REQUIRE(log_count[REASON]==1&&log_value[REASON][0]==reason);REQUIRE(log_count[STATUS]==1&&log_value[STATUS][0]==status);}
 else{
  REQUIRE(log_count[REASON]==0&&log_count[STATUS]==0);
  REQUIRE(boot_guard.value.framebuffer_base==old_mode.base&&boot_guard.value.framebuffer_size==old_mode.bytes);
  REQUIRE(boot_guard.value.width==old_info.width&&boot_guard.value.height==old_info.height);
  REQUIRE(boot_guard.value.stride==old_info.stride&&boot_guard.value.pixel_format==old_info.format);
 }
 ++cases;return 0;
}
#define COLLECT(name,reason) do{if(collect(name,reason))return 1;}while(0)
static int diagnostic(const char *name,GOP *argument,unsigned mode_fields,unsigned info_fields){
 scenario=name;BootInfo b=boot_guard.value;Info i=info_guard.value;Mode m=mode_guard.value;GOP g=gop;
 probe_diag(argument);
 REQUIRE(probe_nv_bad==0&&callback_errors==0&&locate_calls==0&&desktop_calls==0);
 REQUIRE(before_tags==0&&after_tags==0&&log_count[REASON]==0&&log_count[STATUS]==0);
 REQUIRE(graphics_reason==0xa5a5a5a5&&graphics_status==UINT64_MAX);
 REQUIRE(!memcmp(&b,&boot_guard.value,sizeof b)&&!memcmp(&i,&info_guard.value,sizeof i));
 REQUIRE(!memcmp(&m,&mode_guard.value,sizeof m)&&!memcmp(&g,&gop,sizeof g));
 if(mode_fields)REQUIRE(probe_callback_rsp_mod==8);
 if(telemetry(mode_fields,info_fields)||guards())return 1;
 ++cases;return 0;
}
int main(void){
 reset();COLLECT("baseline BGR",0);
 reset();info_guard.value=(Info){0,1920,1080,0,{0},2048};mode_guard.value.bytes=UINT64_C(0x1000000);COLLECT("RGB padded desktop geometry",0);
 reset();info_guard.value=(Info){0,1,1,0,{0},1};mode_guard.value.base=UINT64_C(0xfffffffc);mode_guard.value.bytes=4;COLLECT("last byte exactly 4GiB minus one",0);
 reset();info_guard.value=(Info){0,8192,8192,1,{0},16384};mode_guard.value.base=UINT64_C(0xe0000000);mode_guard.value.bytes=UINT64_C(0x20000000);COLLECT("generic maximum geometry and low4G extent",0);
 reset();locate_status=UINT64_C(0x8000123456789abc);COLLECT("full 64-bit LocateProtocol error",1);
 reset();locate_status=UINT64_C(0x1234567800000001);COLLECT("nonzero low and high firmware status",1);
 reset();null_gop=1;COLLECT("successful LocateProtocol with null GOP",1);
#if EXPECT_DESKTOP
 reset();desktop_status=UINT64_C(0x8000fedcba987654);COLLECT("full 64-bit desktop selection error",2);
#endif
 reset();gop.mode=NULL;COLLECT("null GOP mode",3);
 reset();mode_guard.value.size=sizeof(Info)-1;mode_guard.value.info=(Info *)(uintptr_t)1;COLLECT("short Info does not dereference poison pointer",4);
 reset();mode_guard.value.info=NULL;COLLECT("null Info",5);
 reset();info_guard.value.version=1;COLLECT("invalid Info version excludes detail telemetry",6);
 reset();info_guard.value.version=UINT32_MAX;COLLECT("maximum invalid Info version",6);
 for(unsigned format=2;format<4;format++){reset();info_guard.value.format=format;COLLECT("bitmask and BLT-only formats",7);}
 reset();info_guard.value.format=UINT32_MAX;COLLECT("maximum invalid format",7);
 reset();info_guard.value.width=0;COLLECT("zero width",8);
 reset();info_guard.value.width=8193;COLLECT("width above generic limit",8);
 reset();info_guard.value.width=UINT32_MAX;COLLECT("full width is not truncated",8);
 reset();info_guard.value.stride=799;COLLECT("stride below visible width",9);
 reset();info_guard.value.stride=16385;COLLECT("stride above generic limit",9);
 reset();info_guard.value.height=0;COLLECT("zero height",10);
 reset();info_guard.value.height=8193;COLLECT("height above generic limit",10);
 reset();info_guard.value.height=UINT32_MAX;COLLECT("full height is not truncated",10);
 reset();mode_guard.value.bytes=800u*600u*4u-1u;COLLECT("framebuffer one byte too short",11);
 reset();mode_guard.value.bytes=0;COLLECT("zero framebuffer capacity",11);
 reset();mode_guard.value.base=0;COLLECT("null framebuffer base",12);
 reset();mode_guard.value.base=UINT64_MAX-15;COLLECT("base plus capacity carry",13);
 reset();mode_guard.value.base=1;mode_guard.value.bytes=UINT64_MAX;COLLECT("full capacity carry",13);
 reset();mode_guard.value.base=UINT64_C(0x100000000);COLLECT("high4G framebuffer must fail without truncation",13);
 reset();mode_guard.value.base=UINT64_C(0xfffffff0);COLLECT("low start crosses 4GiB",13);
 reset();mode_guard.value.bytes=UINT64_C(0x100000000);COLLECT("capacity exceeds low4G window",13);
 reset();if(diagnostic("diagnostic null GOP",NULL,0,0))return 1;
 reset();gop.mode=NULL;if(diagnostic("diagnostic null mode",&gop,0,0))return 1;
 reset();mode_guard.value.info=(Info *)(uintptr_t)1;mode_guard.value.size=35;
 if(diagnostic("diagnostic short poison Info",&gop,1,0))return 1;
 reset();mode_guard.value.info=NULL;if(diagnostic("diagnostic null Info",&gop,1,0))return 1;
 reset();info_guard.value.version=1;if(diagnostic("diagnostic invalid Info version",&gop,1,0))return 1;
 reset();if(diagnostic("diagnostic complete validated Info",&gop,1,1))return 1;
 printf("loader graphics oracle passed desktop=%u cases=%u checks=%u; actual loader functions; returned normally\n",EXPECT_DESKTOP,cases,checks);
 return 0;
}
