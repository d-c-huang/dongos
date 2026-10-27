/* Independent input-state oracle. The production Dong capture module is linked
 * unchanged; only boot/bridge getters and read-only owned memory are modelled. */
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#define ABI __attribute__((sysv_abi))
#else
#define ABI
#endif
typedef uint64_t U;
typedef struct {U ready,failed,published,count,online,domain,headers,contexts,root,tsc_hz;} Boot;
typedef struct {U root,incarnation,valid;} Seen;
typedef struct {U token,incarnation,root,frame,xstate,retiring,retirement;} Process;
typedef struct {U mode,token,incarnation,slot,captured_token,captured_incarnation,captured,requested,acknowledged,capture,capture_xstate,returned,return_xstate,return_root,seen;} Cpu;
typedef struct {U ready,failed,lock,owner,online,sequence,barrier,expected,completed,kernel_root,engine,cpus,processes,arena,bytes;} Domain;
typedef struct {U ready,failed,domain,pending,headers,service_cpu,calls,deferred;} Bridge;
typedef struct {U entry,vector,stage,wait_started,deadline,acquired;} Progress;
typedef struct {U published,version,cpu,argument_cpu,entry,vector,stage,error_code,detail_code,clock,domain_available,domain,sequence,owner,lock,mode,requested,acknowledged,barrier,completed,published_kernel_root,raw_root_available,raw_root,normalized_root_available,normalized_root,wait_started,deadline,acquired;} Failure;
typedef struct {U kernel_stack,user_stack,continuation,root_frame,original_cr3,syscalls,busy,result,smp,domain,logical_id,contexts,context_count,pcid_enabled,gdt,tss,idt,stack_bottom,df_top,nmi_top,exception_top,kernel_xstate,capture,returned,return_xstate,ready,last_error,event,raw_frame,deadline_ticks,tsc_hz,timer_hz;} Header;
typedef struct {U switches,retained,user_timers,user_entries,last_vector,failed,gs_base,kernel_gs_base,fs_base,efer,star,lstar,fmask,gdtr_base,gdtr_limit,idtr_base,idtr_limit,tr,cr4,xcr0,rsp0,reserved[3];} Metrics;
typedef struct {U r15,r14,r13,r12,r11,r10,r9,r8,rdi,rsi,rbp,rdx,rcx,rbx,rax,rip,rflags,rsp,cr3,fs_base,gs_base,status,syscalls,exit_code,reserved;} Frame;
typedef struct {U version,done,error_code,reason,cpu,cpus,vector,operation,rip,rsp,frame_root,raw_root,mode,slot,token,captured,syscalls,user_entries,header_error,bridge_stage,first_error,domain_failed,bridge_failed,frame_kind;} Report;
_Static_assert(sizeof(Boot)==80 && sizeof(Domain)==120 && sizeof(Cpu)==120 && sizeof(Process)==56,"domain ABI");
_Static_assert(sizeof(Bridge)==64 && sizeof(Progress)==48 && sizeof(Failure)==224,"bridge ABI");
_Static_assert(sizeof(Header)==256 && offsetof(Header,ready)==200 && offsetof(Header,last_error)==208,"header ABI");
_Static_assert(sizeof(Metrics)==192 && sizeof(Frame)==200 && offsetof(Frame,rax)==112 && offsetof(Frame,cr3)==144,"capture ABI");
_Static_assert(sizeof(Report)==192,"report ABI");
typedef struct {unsigned char xstate[1024];Metrics metrics;} XState;
typedef struct {U low[4];Boot boot;Domain domain;Cpu cpus[16];Process processes[16];Header headers[16];U pointers[16];_Alignas(64) XState states[16];Frame raw,capture,returned;Bridge bridge;U high[4];} Inputs;
static Inputs in,prior;
static Progress progress_before[16];static Failure failures_before[16];
static U boot_reads,bridge_reads,checks,cases;static int absent_boot,absent_bridge;
extern ABI const Report*dong_first_user_checkpoint_run(U,U,U,U,U);
extern ABI const Report*dong_first_user_checkpoint_pointer(void);
extern ABI void checkpoint_reset(void);
extern ABI Progress*checkpoint_progress_pointer(void);
extern ABI Failure*checkpoint_failures_pointer(void);
extern U first_checkpoint_canary_low[4],first_checkpoint_canary_high[4];
#define CK(x) do{++checks;if(!(x)){fprintf(stderr,"FIRST_USER_ASSERT line %d: %s cases=%lu\n",__LINE__,#x,(unsigned long)cases);exit(1);}}while(0)
ABI const Boot*checkpoint_boot(void){++boot_reads;return absent_boot?NULL:&in.boot;}
ABI Bridge*checkpoint_bridge(void){++bridge_reads;return absent_bridge?NULL:&in.bridge;}
ABI void __dong_panic(void){fprintf(stderr,"unexpected panic\n");exit(2);}
static U pa(const void*p){return (U)(uintptr_t)p;}
static void setup(U count){
 checkpoint_reset();memset(&in,0,sizeof in);memset(checkpoint_progress_pointer(),0,16*sizeof(Progress));memset(checkpoint_failures_pointer(),0,16*sizeof(Failure));boot_reads=bridge_reads=0;absent_boot=absent_bridge=0;
 for(unsigned n=0;n<4;n++){in.low[n]=first_checkpoint_canary_low[n]=UINT64_C(0x12345678a55a0000)+n;in.high[n]=first_checkpoint_canary_high[n]=UINT64_C(0xfedcba985aa50000)+n;}
 in.boot=(Boot){1,0,1,count,((U)1<<count)-1,pa(&in.domain),pa(in.pointers),0x10000,0x400000,1000000000};
 in.domain=(Domain){1,0,0,16,in.boot.online,0,0,0,0,0x400000,0,pa(in.cpus),pa(in.processes),0x500000,131072};
 in.bridge=(Bridge){1,0,pa(&in.domain),0,pa(in.pointers),0,0,0};
 for(unsigned n=0;n<16;n++){in.pointers[n]=pa(&in.headers[n]);in.headers[n].ready=2;in.headers[n].logical_id=n;in.headers[n].domain=pa(&in.domain);in.headers[n].kernel_xstate=pa(&in.states[n]);}
 in.raw=(Frame){UINT64_C(0x111100000000000f),14,13,12,11,10,9,8,7,6,5,4,3,2,UINT64_C(0x1234567800000002),UINT64_C(0x1234567800010102),0x202,UINT64_C(0x2345678900020000),UINT64_C(0x0000001234500000),0,0,0,UINT64_C(0x3456789a00000001),0,0};
 in.capture=in.returned=in.raw;
 in.cpus[0]=(Cpu){4,0x706,UINT64_C(0x1234567800000007),5,0x706,UINT64_C(0x1234567800000007),1,0,0,pa(&in.capture),0,pa(&in.returned),0,in.raw.cr3,0};
 in.processes[5]=(Process){in.cpus[0].token,in.cpus[0].incarnation,in.raw.cr3,pa(&in.raw),0,0,0};
 in.headers[0].syscalls=in.raw.syscalls;in.headers[0].raw_frame=pa(&in.raw);in.states[0].metrics.user_entries=UINT64_C(0x456789ab00000001);
 checkpoint_progress_pointer()[0]=(Progress){1,256,2,0,0,0};
 const Report*r=dong_first_user_checkpoint_pointer();for(unsigned n=0;n<24;n++)CK(((const U*)r)[n]==0);
}
static void canaries(void){for(unsigned n=0;n<4;n++){CK(first_checkpoint_canary_low[n]==UINT64_C(0x12345678a55a0000)+n);CK(first_checkpoint_canary_high[n]==UINT64_C(0xfedcba985aa50000)+n);}}
static Report observe(U cpu,U frame,U vector,U reason,U rawroot,int valid){
 ++cases;prior=in;memcpy(progress_before,checkpoint_progress_pointer(),sizeof progress_before);memcpy(failures_before,checkpoint_failures_pointer(),sizeof failures_before);
 const Report*r=dong_first_user_checkpoint_run(cpu,frame,vector,reason,rawroot);
 CK(r==dong_first_user_checkpoint_pointer() && r->version==1 && r->done==1 && r->error_code==(valid?0:0x0b050001));
 CK(r->cpu==cpu&&r->reason==reason&&r->vector==vector&&r->raw_root==rawroot);CK(boot_reads==1&&bridge_reads==1);
 CK(!memcmp(&prior,&in,sizeof in));CK(!memcmp(progress_before,checkpoint_progress_pointer(),sizeof progress_before));CK(!memcmp(failures_before,checkpoint_failures_pointer(),sizeof failures_before));canaries();
 Report saved=*r;in.boot.failed=99;in.cpus[0].capture=1;in.headers[0].raw_frame=1;
 CK(dong_first_user_checkpoint_run(99,1,999,99,1)==r&&boot_reads==1&&bridge_reads==1&&!memcmp(&saved,r,sizeof saved));canaries();return saved;
}
static void success(U vector){Report r=observe(0,pa(&in.raw),vector,0,in.domain.kernel_root,1);CK(r.cpus==prior.boot.count&&r.mode==4&&r.slot==5&&r.token==prior.cpus[0].token&&r.captured==1&&r.frame_kind==1);CK(r.operation==prior.raw.rax&&r.rip==prior.raw.rip&&r.rsp==prior.raw.rsp&&r.frame_root==prior.raw.cr3);CK(r.syscalls==prior.headers[0].syscalls&&r.user_entries==prior.states[0].metrics.user_entries&&r.header_error==prior.headers[0].last_error&&r.bridge_stage==progress_before[0].stage&&r.domain_failed==prior.domain.failed&&r.bridge_failed==prior.bridge.failed);U first=failures_before[0].published==1?failures_before[0].error_code:prior.headers[0].last_error;CK(r.first_error==first);}
static void invalid(void){(void)observe(0,pa(&in.raw),256,0,UINT64_C(0x400000),0);}
static void failure(int fallback){
 Report r=observe(0,1,14,1,UINT64_C(0x812345000),1);CK(r.cpus==prior.boot.count&&r.mode==prior.cpus[0].mode&&r.slot==prior.cpus[0].slot&&r.token==prior.cpus[0].token);CK(r.frame_kind==(fallback?2:0));
 if(fallback)CK(r.operation==prior.returned.rax&&r.rip==prior.returned.rip&&r.rsp==prior.returned.rsp&&r.frame_root==prior.returned.cr3);else CK(r.operation==0&&r.rip==0&&r.rsp==0&&r.frame_root==0);
 CK(r.first_error==(failures_before[0].published==1?failures_before[0].error_code:prior.headers[0].last_error));CK(r.header_error==prior.headers[0].last_error&&r.bridge_stage==progress_before[0].stage&&r.domain_failed==prior.domain.failed&&r.bridge_failed==prior.bridge.failed);
}
int main(void){
 for(U n=3;n<=16;n++){setup(n);success(256);}for(U vector=0;vector<3;vector++){setup(8);success(vector==0?64:vector==1?14:0xf4);}
 setup(8);in.domain.lock=1;in.domain.owner=3;success(256); /* AP idle may own BKL; no atomic global-lock snapshot is promised. */
 for(unsigned n=0;n<19;n++){setup(8);if(n==0)absent_boot=1;if(n==1)absent_bridge=1;if(n==2)in.boot.count=2;if(n==3)in.boot.count=17;if(n==4)in.boot.domain=0;if(n==5)in.boot.headers=0;if(n==6)in.domain.cpus=0;if(n==7)in.domain.processes=0;if(n==8)in.bridge.domain=0;if(n==9)in.bridge.headers=0;if(n==10)in.pointers[0]=0;if(n==11)in.headers[0].ready=1;if(n==12)in.headers[0].logical_id=1;if(n==13)in.headers[0].domain=0;if(n==14)in.headers[0].kernel_xstate=0;if(n==15)in.boot.published=0;if(n==16)in.bridge.calls=1;if(n==17)in.cpus[0].mode=2;if(n==18)in.states[0].metrics.user_entries=0;invalid();}
 setup(8);in.headers[0].kernel_xstate+=8;invalid();setup(8);in.headers[0].kernel_xstate=UINT64_MAX-1023;invalid();
 setup(8);(void)observe(1,pa(&in.raw),256,0,in.domain.kernel_root,0);setup(8);(void)observe(0,pa(&in.raw),256,2,in.domain.kernel_root,0);setup(8);(void)observe(0,0,256,0,in.domain.kernel_root,0);setup(8);(void)observe(0,pa(&in.returned),256,0,in.domain.kernel_root,0);
 for(unsigned n=0;n<13;n++){setup(8);if(n==0)in.cpus[0].slot=4;if(n==1)in.cpus[0].slot=UINT64_MAX;if(n==2)in.cpus[0].token=0;if(n==3)in.cpus[0].captured=0;if(n==4)in.cpus[0].capture=0;if(n==5)in.cpus[0].captured_token^=1;if(n==6)in.cpus[0].captured_incarnation^=1;if(n==7)in.domain.kernel_root^=4096;if(n==8)in.processes[5].token^=1;if(n==9)in.processes[5].incarnation^=1;if(n==10)in.processes[5].root^=4096;if(n==11)in.cpus[0].return_root^=4096;if(n==12)in.headers[0].raw_frame=0;invalid();}
 for(unsigned n=0;n<25;n++){setup(8);((U*)&in.raw)[n]^=UINT64_C(0x8000000000000000);invalid();}
 setup(8);in.cpus[0].mode=2;in.cpus[0].captured=0;in.domain.failed=1;in.bridge.failed=1;in.headers[0].last_error=UINT64_C(0x12345678060b0001);checkpoint_progress_pointer()[0].stage=15;failure(1);
 setup(8);in.headers[0].last_error=UINT64_C(0x11111111060b0001);checkpoint_failures_pointer()[0].published=1;checkpoint_failures_pointer()[0].error_code=UINT64_C(0x2222222206090005);failure(1);
 setup(8);in.headers[0].last_error=UINT64_C(0x33333333060b0001);checkpoint_failures_pointer()[0].published=2;checkpoint_failures_pointer()[0].error_code=UINT64_C(0x4444444406090005);failure(1);
 setup(8);checkpoint_failures_pointer()[0].published=1;checkpoint_failures_pointer()[0].error_code=0;in.headers[0].last_error=99;failure(1);
 for(unsigned n=0;n<4;n++){setup(8);if(n==0)in.cpus[0].token=0;if(n==1)in.cpus[0].slot=16;if(n==2)in.cpus[0].returned=0;if(n==3)in.cpus[0].return_root=0;failure(0);}
 printf("FIRST_USER_NATIVE_OK cases=%lu checks=%lu\n",(unsigned long)cases,(unsigned long)checks);return 0;
}
