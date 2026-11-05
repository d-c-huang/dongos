#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#if defined(_WIN32)
#define ABI __attribute__((sysv_abi))
#else
#define ABI
#endif
typedef uint64_t U;
typedef struct {U version,token,next_cursor,kind,ecam,segment,bus,device,function,vendor,device_id,class_code,header,flags,generation,reserved;} Device;
typedef struct {U physical,virtual,pages,root,generation,attempted,mapped,state;} Lease;
typedef struct {
 U present,slot,configuration,owner,incarnation,device_token,device_generation;
 Device identity;
 U root,memory_generation,request_bytes,request_alignment,snapshot_status,snapshot_error;
 Lease lease;
 U acquire_done,acquire_error,context_error,stop_state,stop_error,smp_retire,route_state,route_error;
 U isolation,isolation_error,reset,reset_error,generation_after,revoke_error,held,drain;
} Context;
_Static_assert(sizeof(Context)==424,"independent context ABI");
_Static_assert(sizeof(Lease)==64,"independent lease ABI");
extern ABI void p5_reset(U),p5_host_reset(U),p5_set(U,U),p5_host_change(U,U),p5_lease(const Lease*,U);
extern ABI U p5_query(U,Context*),p5_call(U,U),p5_retire(void),p5_revoke(U),p5_manager_revoke(void);
extern ABI U p5_begin(U,U,U,U,U,U);
extern ABI void p5_finish(U,U,U,U,U),p5_stop(U,U,U,U,U,U,U,U);
#define FAIL UINT64_C(0x052b0001)
#define BUSY UINT64_C(0x05120003)
#define DENIED UINT64_C(0x05120002)
#define STALE UINT64_C(0x05120004)
#define ABSENT UINT64_C(0x05120006)
#define NOLEASE UINT64_C(0x04060001)
typedef struct {U state,incarnation,stage,error;} Continuation;
extern ABI U pc_view(U,Continuation*),pc_cascade(void),pc_preload(void);
extern ABI void pc_again(U,U),pc_context_bad(U),pc_pin(U);
static U checks,count[64],terminated[16],failed=UINT64_MAX,poisoned,cascading;static Lease receipt;
#define CK(x) do{checks++;if(!(x)){fprintf(stderr,"P5 call check failed line %d: %s\n",__LINE__,#x);exit(1);}}while(0)
ABI U p5_event(U stage,U a,U b,U c){
 CK(stage<64);count[stage]++;
 if(poisoned&&(stage==12||stage==32))return FAIL;
 if(stage==33&&failed==33)poisoned=1;
 if(stage==10){if(a==0x80008000)return 0x10421af4;if(a==0x80008008)return 0x01000000;if(a==0x8000800c)return 0;return 0xffffffff;}
 if(stage==2){p5_lease(&receipt,0);}
 if(stage==7)return failed==stage?FAIL:1;
 if(stage==13&&failed!=stage){CK(a<16);terminated[a]++;}
 if(stage==32||stage==33){
  CK(a==2&&b==5&&c==2&&terminated[2]==1);CK(count[12]>=1&&count[24]>=1&&count[11]>=1&&count[6]>=2);
  if(stage==33)CK(count[32]==1);
  if(cascading)CK(terminated[6]==1&&count[28]==1);
 }
 return failed==stage?FAIL:0;
}
ABI void __dong_panic(void){fputs("unexpected native panic\n",stderr);exit(99);}
int main(int argc,char **argv){CK(argc==2);const char *name=argv[1];
 p5_reset(2);p5_host_reset(2);receipt=(Lease){0x200000,0x68000000,32,0x9000,11,32,32,2};
 CK(p5_call(131072,4096)==0);memset(count,0,sizeof count);
 int up=!strcmp(name,"up"),manager=!strcmp(name,"manager"),preload=!strcmp(name,"preload"),plain=!strcmp(name,"not-pinned"),cascade=!strcmp(name,"cascade")||!strcmp(name,"cascade-barrier");
 if(up){p5_set(6,0);}
 if(plain){pc_pin(0);}
 if(!strncmp(name,"failure",7))failed=strtoull(name+7,0,10);
 U bad=0;if(!strncmp(name,"context",7)){bad=strtoull(name+7,0,10);pc_context_bad(bad);}
 if(cascade){failed=!strcmp(name,"cascade")?32:33;cascading=1;}
 Context before;CK(p5_query(2,&before)==0);
 U result=manager?p5_manager_revoke():(preload?pc_preload():(cascade?pc_cascade():p5_retire()));
 Continuation v={0};CK(pc_view(2,&v)==0);
 if(manager||preload||up||plain){CK(result==(manager?2:0));CK(v.state==0&&count[32]==0&&count[33]==0);}
 else if(failed<32){CK(result==FAIL&&v.state==0&&count[32]==0&&count[33]==0);}
 else{
  CK(result==0&&v.incarnation==5);CK(count[24]>=1);
  if(bad){CK(v.state==3&&v.stage==1&&v.error!=0&&count[32]==0&&count[33]==0);}
  else if(failed==32||failed==33){CK(v.state==3&&v.error==FAIL&&v.stage==(failed==32?2:3));CK(count[32]==1&&count[33]==(failed==33?1:0));}
  else{CK(v.state==2&&v.stage==3&&v.error==0&&count[32]==1&&count[33]==1);}
  Continuation old=v;U p=count[32],r=count[33];pc_again(2,5);pc_again(2,6);CK(pc_view(2,&v)==0&&!memcmp(&old,&v,sizeof v));CK(count[32]==p&&count[33]==r);
 }
 if(cascade){CK(terminated[2]==1&&terminated[6]==1&&count[28]==1);}
 Context c;CK(p5_query(2,&c)==0&&c.held==1&&c.drain==0);CK(!memcmp(&c.lease,&before.lease,sizeof c.lease));
 printf("P5 call %s passed %llu checks\n",name,(unsigned long long)checks);return 0;
}
