/* Independent read-only input oracle for the actual failure-status producer. */
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
typedef struct {U token,incarnation,root,frame,xstate,retiring,retirement;} Process;
typedef struct {U mode,token,incarnation,slot,captured_token,captured_incarnation,captured,requested,acknowledged,capture,capture_xstate,returned,return_xstate,return_root,seen;} Cpu;
typedef struct {U ready,failed,lock,owner,online,sequence,barrier,expected,completed,kernel_root,engine,cpus,processes,arena,bytes;} Domain;
typedef struct {U ready,failed,domain,pending,headers,service_cpu,calls,deferred;} Bridge;
typedef struct {U entry,vector,stage,wait_started,deadline,acquired;} Progress;
typedef struct {U published,version,cpu,argument_cpu,entry,vector,stage,error_code,detail_code,clock,domain_available,domain,sequence,owner,lock,mode,requested,acknowledged,barrier,completed,published_kernel_root,raw_root_available,raw_root,normalized_root_available,normalized_root,wait_started,deadline,acquired;} Failure;
typedef struct {U kernel_stack,user_stack,continuation,root_frame,original_cr3,syscalls,busy,result,smp,domain,logical_id,contexts,context_count,pcid_enabled,gdt,tss,idt,stack_bottom,df_top,nmi_top,exception_top,kernel_xstate,capture,returned,return_xstate,ready,last_error,event,raw_frame,deadline_ticks,tsc_hz,timer_hz;} Header;
typedef struct {U switches,retained,user_timers,user_entries,last_vector,failed,gs_base,kernel_gs_base,fs_base,efer,star,lstar,fmask,gdtr_base,gdtr_limit,idtr_base,idtr_limit,tr,cr4,xcr0,rsp0,reserved[3];} Metrics;
typedef struct {U r15,r14,r13,r12,r11,r10,r9,r8,rdi,rsi,rbp,rdx,rcx,rbx,rax,rip,rflags,rsp,cr3,fs_base,gs_base,status,syscalls,exit_code,reserved;} Frame;
typedef struct {U version,done,error_code,cpu,cpus,failure_cpu,failure_code,failure_detail,entry,event,stage,domain_failed,bridge_failed,lock,owner,online,mode,slot,token,captured,syscalls,user_entries,header_error,operation,rip,rsp,frame_root,raw_root,pcid,calls,failure_mask,frame_kind;} Report;
_Static_assert(sizeof(Boot)==80&&sizeof(Domain)==120&&sizeof(Cpu)==120&&sizeof(Process)==56,"domain ABI");
_Static_assert(sizeof(Header)==256&&offsetof(Header,kernel_xstate)==168&&offsetof(Header,ready)==200,"header ABI");
_Static_assert(sizeof(Bridge)==64&&sizeof(Progress)==48&&sizeof(Failure)==224,"bridge ABI");
_Static_assert(sizeof(Metrics)==192&&sizeof(Frame)==200&&offsetof(Frame,rax)==112&&offsetof(Frame,cr3)==144,"frame ABI");
_Static_assert(sizeof(Report)==256&&offsetof(Report,failure_mask)==240&&offsetof(Report,frame_kind)==248,"report ABI");
typedef struct {unsigned char bytes[1024];Metrics metrics;} XState;
typedef struct {U low[4];Boot boot;Domain domain;Cpu cpus[16];Process processes[16];Header headers[16];U addresses[16];_Alignas(64) XState states[16];Frame returned;Bridge bridge;U high[4];} Inputs;
static Inputs in,before;
static Progress prior_progress[16];static Failure prior_failures[16];
static U checks,cases,boot_reads,bridge_reads;static int absent_boot,absent_bridge;
extern ABI const Report*dong_user_runtime_status_run(U,U);
extern ABI const Report*dong_user_runtime_status_pointer(void);
extern ABI void checkpoint_reset(void);
extern ABI Progress*checkpoint_progress_pointer(void);
extern ABI Failure*checkpoint_failures_pointer(void);
extern U runtime_canary_low[4],runtime_canary_high[4];
#define CK(x) do{++checks;if(!(x)){fprintf(stderr,"USER_RUNTIME_ASSERT line %d: %s cases=%lu\n",__LINE__,#x,(unsigned long)cases);exit(1);}}while(0)
ABI const Boot*checkpoint_boot(void){++boot_reads;CK(dong_user_runtime_status_pointer()->done==0);return absent_boot?NULL:&in.boot;}
ABI Bridge*checkpoint_bridge(void){++bridge_reads;CK(dong_user_runtime_status_pointer()->done==0);return absent_bridge?NULL:&in.bridge;}
ABI void __dong_panic(void){fprintf(stderr,"unexpected panic\n");exit(2);}
static U pa(const void*p){return (U)(uintptr_t)p;}
static void setup(U count){
 checkpoint_reset();memset(&in,0,sizeof in);memset(checkpoint_progress_pointer(),0,16*sizeof(Progress));memset(checkpoint_failures_pointer(),0,16*sizeof(Failure));boot_reads=bridge_reads=0;absent_boot=absent_bridge=0;
 for(unsigned n=0;n<4;n++){in.low[n]=runtime_canary_low[n]=UINT64_C(0xaabbccdd11220000)+n;in.high[n]=runtime_canary_high[n]=UINT64_C(0x1122334455660000)+n;}
 in.boot=(Boot){1,0,1,count,((U)1<<count)-1,pa(&in.domain),pa(in.addresses),0,0x400000,1000000000};
 in.domain=(Domain){1,1,1,6,in.boot.online,0,0,0,0,0x400000,0,pa(in.cpus),pa(in.processes),0,0};
 in.bridge=(Bridge){1,1,pa(&in.domain),0,pa(in.addresses),0,UINT64_C(0x1234567800000015),0};
 for(unsigned n=0;n<16;n++){in.addresses[n]=pa(&in.headers[n]);in.headers[n].ready=2;in.headers[n].logical_id=n;in.headers[n].domain=pa(&in.domain);in.headers[n].kernel_xstate=pa(&in.states[n]);}
 in.returned.rax=UINT64_C(0xa123456700000002);in.returned.rip=UINT64_C(0xb123456700010102);in.returned.rsp=UINT64_C(0xc123456700020000);in.returned.cr3=UINT64_C(0x1234500000);
 in.cpus[0]=(Cpu){4,0x706,3,5,0,0,1,0,0,1,0,pa(&in.returned),0,in.returned.cr3,0};
 in.headers[0].last_error=UINT64_C(0x44556677060b0001);in.headers[0].event=UINT64_C(0x55667788000000f4);in.headers[0].pcid_enabled=1;in.headers[0].syscalls=UINT64_C(0x6677889900000012);in.headers[0].raw_frame=1;
 in.states[0].metrics.user_entries=UINT64_C(0x778899aa00000010);checkpoint_progress_pointer()[0]=(Progress){1,256,20,0,0,0};
 const Report*r=dong_user_runtime_status_pointer();for(unsigned n=0;n<32;n++)CK(((const U*)r)[n]==0);
}
static void guards(void){for(unsigned n=0;n<4;n++){CK(runtime_canary_low[n]==UINT64_C(0xaabbccdd11220000)+n);CK(runtime_canary_high[n]==UINT64_C(0x1122334455660000)+n);}}
static Report observe(U cpu,int valid){
 ++cases;before=in;memcpy(prior_progress,checkpoint_progress_pointer(),sizeof prior_progress);memcpy(prior_failures,checkpoint_failures_pointer(),sizeof prior_failures);
 const Report*r=dong_user_runtime_status_run(cpu,UINT64_C(0x9876543005));CK(r==dong_user_runtime_status_pointer()&&r->version==1&&r->done==1&&r->cpu==cpu&&r->raw_root==UINT64_C(0x9876543005));CK(r->error_code==(valid?0:0x0b060001));CK(boot_reads==1&&bridge_reads==1);
 CK(!memcmp(&before,&in,sizeof in));CK(!memcmp(prior_progress,checkpoint_progress_pointer(),sizeof prior_progress));CK(!memcmp(prior_failures,checkpoint_failures_pointer(),sizeof prior_failures));guards();
 Report saved=*r;in.domain.failed=9;in.cpus[0].returned=1;checkpoint_failures_pointer()[0].published=1;checkpoint_failures_pointer()[0].error_code=99;
 CK(dong_user_runtime_status_run(99,1)==r&&boot_reads==1&&bridge_reads==1&&!memcmp(&saved,r,sizeof saved));guards();return saved;
}
static void valid(int frame){
 Report r=observe(0,1);U selected=16,mask=0;for(U n=0;n<before.boot.count;n++)if(prior_failures[n].published==1){mask|=(U)1<<n;if(selected==16)selected=n;}
 CK(r.cpus==before.boot.count&&r.failure_mask==mask&&r.failure_cpu==selected);CK(r.domain_failed==before.domain.failed&&r.bridge_failed==before.bridge.failed&&r.lock==before.domain.lock&&r.owner==before.domain.owner&&r.online==before.domain.online);
 CK(r.mode==before.cpus[0].mode&&r.slot==before.cpus[0].slot&&r.token==before.cpus[0].token&&r.captured==before.cpus[0].captured&&r.syscalls==before.headers[0].syscalls&&r.user_entries==before.states[0].metrics.user_entries&&r.header_error==before.headers[0].last_error&&r.pcid==before.headers[0].pcid_enabled&&r.calls==before.bridge.calls);
 if(selected==16){CK(r.failure_code==before.headers[0].last_error&&r.failure_detail==0&&r.entry==prior_progress[0].entry&&r.event==before.headers[0].event&&r.stage==prior_progress[0].stage);}else{Failure f=prior_failures[selected];CK(r.failure_code==f.error_code&&r.failure_detail==f.detail_code&&r.entry==f.entry&&r.event==f.vector&&r.stage==f.stage);}
 CK(r.frame_kind==(frame?2:0));if(frame)CK(r.operation==before.returned.rax&&r.rip==before.returned.rip&&r.rsp==before.returned.rsp&&r.frame_root==before.returned.cr3);else CK(r.operation==0&&r.rip==0&&r.rsp==0&&r.frame_root==0);
}
static void publish(unsigned cpu,U publication){Failure*f=checkpoint_failures_pointer()+cpu;*f=(Failure){0};f->published=publication;f->cpu=15-cpu;f->error_code=UINT64_C(0x1234567800000000)+cpu;f->detail_code=UINT64_C(0x2345678900001000)+cpu;f->entry=UINT64_C(0x3456789a00000001)+cpu;f->vector=UINT64_C(0x456789ab00000100)+cpu;f->stage=UINT64_C(0x56789abc00000001)+cpu;f->clock=16-cpu;}
int main(void){
 for(U n=3;n<=16;n++){setup(n);valid(1);setup(n);for(unsigned id=0;id<16;id++)publish(id,1);valid(1);}
 for(unsigned cpu=0;cpu<16;cpu++){setup(16);publish(cpu,1);valid(1);}
 setup(16);publish(1,1);publish(7,1);publish(15,1);valid(1); /* Lowest logical slot, not timestamp or f.cpu. */
 setup(16);for(unsigned cpu=0;cpu<16;cpu++)publish(cpu,cpu%2?2:3);valid(1);
 setup(8);publish(0,2);publish(2,1);publish(3,1);valid(1);
 setup(8);publish(0,1);checkpoint_failures_pointer()[0].error_code=0;valid(1);
 setup(8);in.boot.published=0;in.domain.lock=0;in.domain.owner=16;in.cpus[0].mode=2;in.cpus[0].captured=0;valid(1);
 for(unsigned n=0;n<4;n++){setup(8);if(n==0)in.cpus[0].token=0;if(n==1)in.cpus[0].slot=16;if(n==2)in.cpus[0].returned=0;if(n==3)in.cpus[0].return_root=0;valid(0);}
 for(unsigned n=0;n<17;n++){setup(8);if(n==0)absent_boot=1;if(n==1)absent_bridge=1;if(n==2)in.boot.count=2;if(n==3)in.boot.count=17;if(n==4)in.boot.domain=0;if(n==5)in.boot.headers=0;if(n==6)in.domain.cpus=0;if(n==7)in.domain.processes=0;if(n==8)in.bridge.domain=0;if(n==9)in.bridge.headers=0;if(n==10)in.addresses[0]=0;if(n==11)in.headers[0].ready=1;if(n==12)in.headers[0].logical_id=1;if(n==13)in.headers[0].domain=0;if(n==14)in.headers[0].kernel_xstate=0;if(n==15)in.headers[0].kernel_xstate+=8;if(n==16)in.headers[0].kernel_xstate=UINT64_MAX-1023;(void)observe(0,0);}
 setup(8);(void)observe(1,0);
 printf("USER_RUNTIME_NATIVE_OK cases=%lu checks=%lu\n",(unsigned long)cases,(unsigned long)checks);return 0;
}
