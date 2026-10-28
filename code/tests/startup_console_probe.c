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
typedef struct {U version,done,error_code,kind,returns,captures,logs,slot,operation,event,syscalls,entries,bridge_stage,rip,stopped,accepted;unsigned char text[8][41];} Report;
_Static_assert(sizeof(Report)==456&&offsetof(Report,text)==128,"console ABI");
typedef struct {unsigned char bytes[1024];Metrics metrics;} XState;
typedef struct {U low[4];Boot boot;Domain domain;Cpu cpus[16];Process processes[16];Header headers[16];U addresses[16];_Alignas(64) XState states[16];Frame returned,captured;Bridge bridge;unsigned char ring[4096];U high[4];} Inputs;
static Inputs in,before;static U checks,getters,draws;static int absent;
extern ABI U dong_startup_console_run(U,U,U,const unsigned char*);
extern ABI const Report*dong_startup_console_pointer(void);
extern ABI void checkpoint_reset(void);
extern ABI Progress*checkpoint_progress_pointer(void);
extern U console_canary_low[4],console_canary_high[4];
extern ABI void startup_console_tick(U);
extern ABI U services_write_bytes(const void*,U);
extern unsigned char startup_console_disabled;
U test_cpu,test_root=0x400000,test_kernel_root=0x400000,test_flags;
U services_console_head,services_console_accepted,runtime_failure_view=0x12345678,boot_progress_view;
unsigned char services_console_ring[4096],boot_progress_phase=23;
#define CK(x) do{++checks;if(!(x)){fprintf(stderr,"STARTUP_CONSOLE_ASSERT %d %s\n",__LINE__,#x);exit(1);}}while(0)
static U pa(const void*p){return (U)(uintptr_t)p;}
ABI const Boot*checkpoint_boot(void){getters++;return absent?NULL:&in.boot;}
ABI Bridge*checkpoint_bridge(void){getters++;return &in.bridge;}
ABI void __dong_panic(void){fputs("unexpected panic\n",stderr);exit(2);}
ABI void boot_progress_draw(void){CK(boot_progress_phase==25&&boot_progress_view==runtime_failure_view);CK(dong_startup_console_pointer()->done==1);draws++;}
ABI U startup_console_write_bytes(const void*p,U n){CK(p==in.ring&&n==17);return 0xabcdef0123456789ULL;}
static void setup(void){
 checkpoint_reset();memset(&in,0,sizeof in);memset(checkpoint_progress_pointer(),0,16*sizeof(Progress));getters=draws=0;absent=0;
 test_cpu=test_flags=0;test_root=test_kernel_root=0x400000;boot_progress_phase=23;boot_progress_view=0;services_console_head=services_console_accepted=0;startup_console_disabled=0;
 for(unsigned n=0;n<4;n++){console_canary_low[n]=in.low[n]=0xaabb11220000ULL+n;console_canary_high[n]=in.high[n]=0xccdd33440000ULL+n;}
 in.boot=(Boot){1,0,1,8,255,pa(&in.domain),pa(in.addresses),0,0x400000,1000000000};
 in.domain.ready=1;in.domain.online=255;in.domain.kernel_root=0x400000;in.domain.cpus=pa(in.cpus);in.domain.processes=pa(in.processes);
 in.bridge.domain=pa(&in.domain);in.bridge.headers=pa(in.addresses);
 for(unsigned n=0;n<16;n++){in.addresses[n]=pa(&in.headers[n]);in.headers[n].ready=2;in.headers[n].logical_id=n;in.headers[n].domain=pa(&in.domain);in.headers[n].kernel_xstate=pa(&in.states[n]);}
 in.cpus[0].mode=6;in.cpus[0].slot=5;in.cpus[0].token=0x706;in.cpus[0].returned=pa(&in.returned);in.cpus[0].capture=pa(&in.captured);
 in.returned.rax=0x1122334455667788ULL;in.returned.rip=0x12345678;in.captured.rax=0x8877665544332211ULL;in.captured.rip=0x23456789;
 in.headers[0].syscalls=0x1234567800000099ULL;in.headers[0].event=0xf4;in.states[0].metrics.user_entries=0xabcdef1234567890ULL;checkpoint_progress_pointer()[0].stage=2;
}
static U call(U kind,U head,U count,const unsigned char*ring){
 before=in;Progress progress=*checkpoint_progress_pointer();U result=dong_startup_console_run(kind,head,count,ring);CK(!memcmp(&before,&in,sizeof in));CK(!memcmp(&progress,checkpoint_progress_pointer(),sizeof progress));
 for(unsigned i=0;i<4;i++){CK(console_canary_low[i]==0xaabb11220000ULL+i);CK(console_canary_high[i]==0xccdd33440000ULL+i);}
 return result;
}
static U record(const char*s,U start){for(U i=0;s[i];i++)in.ring[(start+i)&4095]=(unsigned char)s[i];return start+strlen(s);}
int main(void){
 setup();CK(call(1,0,0,NULL)==1);const Report*r=dong_startup_console_pointer();CK(r->done==1&&r->kind==1&&r->slot==5&&r->returns==1&&r->rip==in.returned.rip&&r->operation==in.returned.rax&&r->syscalls==in.headers[0].syscalls&&r->entries==in.states[0].metrics.user_entries&&r->event==0xf4&&r->bridge_stage==2);
 CK(call(3,0,0,NULL)==1&&r->captures==1&&r->rip==in.captured.rip&&r->operation==in.captured.rax);CK(call(1,0,0,NULL)==1&&call(1,0,0,NULL)==0&&r->returns==3);
 U n=record("init_ready\r\nxhci_error=0x08170001\n",0);CK(call(2,n,n,in.ring)==1);CK(!strcmp((char*)r->text[0],"INIT_READY")&&!strcmp((char*)r->text[1],"XHCI_ERROR=0X08170001"));CK(call(2,n,n,in.ring)==0);
 setup();n=record("abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqr\n",0);CK(call(2,n,n,in.ring)==1);r=dong_startup_console_pointer();CK(strlen((char*)r->text[0])==40&&!strcmp((char*)r->text[1],"OPQR"));
 setup();n=0;for(unsigned i=0;i<12;i++){char line[8];snprintf(line,sizeof line,"line%u\n",i);n=record(line,n);}CK(call(2,n,n,in.ring)==1);r=dong_startup_console_pointer();for(unsigned i=0;i<8;i++){char line[8];snprintf(line,sizeof line,"LINE%u",i+4);CK(!strcmp((char*)r->text[i],line));CK(r->text[i][40]==0);}
 setup();memset(in.ring,'x',4096);n=record("\nlast_line\n",5000);CK(call(2,n&4095,n,in.ring)==1);CK(!strcmp((char*)dong_startup_console_pointer()->text[0],"LAST_LINE"));
 setup();n=record("a\tb~c\001d\n",0);CK(call(2,n,n,in.ring)==1);CK(!strcmp((char*)dong_startup_console_pointer()->text[0],"A?B?C?D"));
 setup();for(unsigned i=0;i<5;i++)CK(!call(i==0?0:i==1?4:2,i==2?4096:i==3?1:0,i==4?4096:0,NULL));CK(!getters);
 for(unsigned bad=0;bad<10;bad++){setup();if(bad==0)absent=1;if(bad==1)in.boot.count=17;if(bad==2)in.boot.domain=0;if(bad==3)in.domain.cpus=0;if(bad==4)in.domain.processes=0;if(bad==5)in.bridge.domain=0;if(bad==6)in.addresses[0]=0;if(bad==7)in.headers[0].ready=1;if(bad==8)in.headers[0].logical_id=1;if(bad==9)in.headers[0].kernel_xstate=0;CK(!call(1,0,0,NULL));}
 setup();in.cpus[0].slot=3;CK(call(1,0,0,NULL)==1);r=dong_startup_console_pointer();CK(r->stopped==1&&r->kind==4);Report saved=*r;U old=getters;in.cpus[0].slot=5;in.boot.domain=0;CK(!call(2,1,1,(void*)1));CK(getters==old&&!memcmp(&saved,r,sizeof saved));
 setup();startup_console_tick(1);CK(draws==1&&boot_progress_view==0&&boot_progress_phase==23);test_cpu=1;startup_console_tick(1);test_cpu=0;test_root=1;startup_console_tick(1);test_root=test_kernel_root;test_flags=0x200;startup_console_tick(1);CK(draws==1);test_flags=0;
 CK(services_write_bytes(in.ring,17)==0xabcdef0123456789ULL);CK(boot_progress_view==0&&boot_progress_phase==23);
 setup();in.cpus[0].slot=3;startup_console_tick(1);CK(startup_console_disabled==1&&draws==1&&dong_startup_console_pointer()->stopped==1);
 setup();startup_console_disabled=1;startup_console_tick(1);CK(getters==0&&draws==0&&dong_startup_console_pointer()->version==0);
 printf("STARTUP_CONSOLE_OK checks=%u bytes=456 continued=1 bounded=1 handoff=1\n",(unsigned)checks);return 0;
}
