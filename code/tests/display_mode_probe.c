#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define EFI __attribute__((ms_abi))
typedef struct {uint32_t version,width,height,format,masks[4],stride;} Info;
typedef struct {uint32_t max,current;uint64_t info,size,base,bytes;} Mode;
typedef struct {void *query,*set,*blt;Mode *mode;} Gop;
extern uint64_t EFI probe_abi(Gop *,void *);
extern uint64_t EFI query_thunk(Gop *,uint32_t,uint64_t *,Info **);
extern uint64_t EFI set_thunk(Gop *,uint32_t);
extern uint64_t EFI free_thunk(void *);
unsigned callback_alignment_errors;
static Info advertised[256],actual[256],current_info,pool;
static Mode mode;static Gop gop;static uint64_t bs[64];
static uint64_t query_sizes[256],actual_sizes[256],bases[256],bytes[256];
static uint32_t actual_max[256],actual_index[256];
static unsigned query_kind[256],set_kind[256],set_order[256],expected_order[256];
static unsigned queries,frees,sets,held,errors,cases,expected_queries,expected_frees;
static int free_failure;
static Info image(unsigned w,unsigned h,unsigned stride,unsigned format){
 return (Info){0,w,h,format,{0},stride};
}
static void reset(unsigned count){
 memset(bs,0,sizeof bs);bs[9]=(uintptr_t)free_thunk;
 current_info=(Info){0};mode=(Mode){count,0,(uintptr_t)&current_info,sizeof current_info,0xe0000000,0x800000};
 gop=(Gop){query_thunk,set_thunk,0,&mode};queries=frees=sets=held=errors=callback_alignment_errors=0;
 expected_queries=expected_frees=count;free_failure=-1;
 for(unsigned i=0;i<256;i++){
  advertised[i]=actual[i]=image(800,600,800,1);query_sizes[i]=actual_sizes[i]=sizeof(Info);
  bases[i]=0xe0000000;bytes[i]=0x1000000;actual_max[i]=count;actual_index[i]=i;
  query_kind[i]=set_kind[i]=0;expected_order[i]=i;
 }
}
static void valid_current(void){current_info=image(1024,768,1024,1);}
uint64_t EFI query_c(Gop *p,uint32_t index,uint64_t *size,Info **out){
 if(p!=&gop||held||index>=mode.max||index!=queries){errors++;return 1;}
 queries++;
 if(query_kind[index]==1)return 1;
 if(query_kind[index]==3){*out=0;*size=sizeof(Info);return 0;}
 pool=advertised[index];*out=&pool;*size=query_sizes[index];held=1;
 return query_kind[index]==2?1:0;
}
uint64_t EFI free_c(void *p){
 if(p!=&pool||held!=1)errors++;
 frees++;held=0;memset(&pool,0xa5,sizeof pool);
 return (int)(queries-1)==free_failure?1:0;
}
uint64_t EFI set_c(Gop *p,uint32_t index){
 if(p!=&gop||held||index>=256||sets>=256){errors++;return 1;}
 set_order[sets++]=index;
 if(set_kind[index]==1)return 1;
 current_info=actual[index];mode.current=actual_index[index];mode.max=actual_max[index];
 mode.info=set_kind[index]==2?0:(uintptr_t)&current_info;mode.size=actual_sizes[index];
 mode.base=bases[index];mode.bytes=bytes[index];
 if(set_kind[index]==3)gop.mode=0;
 return 0;
}
static int run(const char *name,int success,unsigned wanted_sets){
 uint64_t result=probe_abi(&gop,bs);
 int bad=result!=(success?0u:1u)||queries!=expected_queries||frees!=expected_frees||sets!=wanted_sets||held||errors||callback_alignment_errors;
 for(unsigned i=0;i<sets;i++)if(set_order[i]!=expected_order[i])bad=1;
 if(bad){fprintf(stderr,"GOP oracle failed case=%s result=%u q=%u/%u free=%u/%u set=%u/%u held=%u ownership=%u alignment=%u first=%u expected=%u\n",
  name,(unsigned)result,queries,expected_queries,frees,expected_frees,sets,wanted_sets,held,errors,callback_alignment_errors,
  sets?set_order[0]:999,wanted_sets?expected_order[0]:999);return 0;}
 cases++;return 1;
}
#define RUN(name,success,sets) do{if(!run(name,success,sets))return 1;}while(0)
int main(void){
 reset(3);advertised[1]=actual[1]=image(1280,800,1280,1);advertised[2]=actual[2]=image(1920,1080,1920,1);expected_order[0]=2;
 RUN("rank-1080p",1,1);
 reset(3);advertised[0]=actual[0]=image(1366,768,1408,1);advertised[1]=actual[1]=image(1280,800,1280,1);
 RUN("rank-fallback-area",1,1);
 reset(1);RUN("minimum-800x600",1,1);
 reset(1);advertised[0]=actual[0]=image(1920,1080,2048,0);RUN("maximum-rgb-padded",1,1);
 reset(2);advertised[0]=actual[0]=image(1024,768,1024,1);advertised[1]=actual[1]=image(1024,768,2048,0);RUN("stable-area-tie",1,1);
 reset(3);advertised[1]=actual[1]=image(1280,800,1280,1);advertised[2]=actual[2]=image(1920,1080,1920,1);
 set_kind[2]=1;expected_order[0]=2;expected_order[1]=1;RUN("set-failure-next-best",1,2);
 reset(2);advertised[1]=actual[1]=image(1920,1080,1920,1);actual[1].width=799;expected_order[0]=1;expected_order[1]=0;
 RUN("actual-invalid-next-best",1,2);
 reset(2);advertised[1]=actual[1]=image(1920,1080,1920,1);actual_index[1]=0;expected_order[0]=1;expected_order[1]=0;
 RUN("wrong-current-next-best",1,2);
 reset(2);advertised[1]=actual[1]=image(1920,1080,1920,1);bases[1]=0x100000000;expected_order[0]=1;expected_order[1]=0;
 RUN("high-framebuffer-next-best",1,2);
 reset(2);set_kind[0]=set_kind[1]=1;RUN("all-sets-fail",0,2);
 reset(2);valid_current();set_kind[0]=set_kind[1]=1;RUN("all-sets-fail-valid-current",1,2);
 reset(2);valid_current();query_kind[0]=query_kind[1]=1;expected_frees=0;RUN("failed-query-current",1,0);
 reset(2);valid_current();query_kind[0]=query_kind[1]=2;RUN("failed-query-pools-current",1,0);
 reset(1);query_kind[0]=1;expected_frees=0;RUN("failed-query-invalid-current",0,0);
 reset(1);query_kind[0]=2;RUN("failed-query-buffer-freed",0,0);
 reset(1);query_kind[0]=3;expected_frees=0;RUN("successful-query-null-buffer",0,0);
 reset(1);query_sizes[0]=sizeof(Info)-1;RUN("short-query-info",0,0);
 reset(1);valid_current();free_failure=0;RUN("free-failure-fatal",0,0);
 reset(0);expected_queries=expected_frees=0;RUN("zero-max",0,0);
 reset(257);expected_queries=expected_frees=0;RUN("oversized-max",0,0);
 reset(1);mode.current=1;expected_queries=expected_frees=0;RUN("invalid-initial-current-index",0,0);
 reset(1);gop.mode=0;expected_queries=expected_frees=0;RUN("null-mode",0,0);
 reset(1);gop.query=0;expected_queries=expected_frees=0;RUN("null-query-callback",0,0);
 reset(1);gop.set=0;expected_queries=expected_frees=0;RUN("null-set-callback",0,0);
 reset(1);bs[9]=0;expected_queries=expected_frees=0;RUN("null-free-callback",0,0);
 /* Each malformed advertised geometry is rejected before SetMode. */
 for(unsigned variant=0;variant<10;variant++){
  reset(1);Info *v=&advertised[0];
  if(variant==0)v->width=799;if(variant==1)v->width=1921;
  if(variant==2)v->height=599;if(variant==3)v->height=1081;
  if(variant==4)v->stride=799;if(variant==5)v->stride=2049;
  if(variant==6)v->version=1;if(variant==7)v->format=2;
  if(variant==8)v->format=3;if(variant==9)v->format=UINT32_MAX;
  RUN("advertised-geometry-boundary",0,0);
 }
 /* QueryMode success is insufficient: verify every field actually installed. */
 for(unsigned variant=0;variant<25;variant++){
  reset(1);Info *v=&actual[0];
  if(variant==0)v->width=799;if(variant==1)v->width=1921;
  if(variant==2)v->height=599;if(variant==3)v->height=1081;
  if(variant==4)v->stride=799;if(variant==5)v->stride=2049;
  if(variant==6)v->version=1;if(variant==7)v->format=2;if(variant==8)v->format=3;
  if(variant==9)set_kind[0]=2;if(variant==10)actual_sizes[0]=sizeof(Info)-1;
  if(variant==11)bases[0]=0;if(variant==12)bases[0]=0xfffff;
  if(variant==13)bases[0]=0x100000000;if(variant==14)bases[0]=UINT64_MAX-1;
  if(variant==15)bytes[0]=0;if(variant==16)bytes[0]=800*600*4-1;
  if(variant==17)bytes[0]=0x1000001;if(variant==18)bases[0]=0xfff00000;
  if(variant==19){bases[0]=0xe0000001;bytes[0]=0x1000000;}
  if(variant==20)actual_max[0]=0;if(variant==21)actual_max[0]=257;
  if(variant==22)actual_index[0]=1;if(variant==23)set_kind[0]=3;
  if(variant==24){bases[0]=0x100000000+0xe0000000;bytes[0]=800*600*4;}
  RUN("actual-mode-boundary",0,1);
 }
 reset(1);bases[0]=0xffe00000;bytes[0]=0x200000;RUN("last-byte-exact-4g-boundary",1,1);
 reset(1);bases[0]=0xe0000001;bytes[0]=800*600*4;RUN("safe-unaligned-framebuffer",1,1);
 reset(1);bytes[0]=0x1000000;RUN("16m-aligned-aperture",1,1);
 reset(256);RUN("256-modes-bounded",1,1);
 reset(256);for(unsigned i=0;i<256;i++)set_kind[i]=1;RUN("256-set-failures-bounded",0,256);
 /* A shorter later invocation must not reuse scores from the previous call. */
 reset(1);query_kind[0]=2;RUN("per-call-scores-cleared",0,0);
 printf("GOP native oracle passed: %u actual mode/cleanup/ABI cases\n",cases);return 0;
}
