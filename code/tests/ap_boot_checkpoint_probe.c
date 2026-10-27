#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#define ABI __attribute__((sysv_abi))
#else
#define ABI
#endif
typedef uint64_t U;
typedef struct{U ready,failed,published,count,online,domain,headers,contexts,root,hz;} Boot;
typedef struct{U ready,failed,lock,owner,online,sequence,barrier,expected,completed,root,engine,cpus,processes,arena,bytes;} Domain;
typedef struct{U version,done,error,checkpoint,cpus,published,lock,owner,online,ready_mask,error_mask,first_error,first_cpu,queue_count,boot_failed,domain_failed,parked_mask;} Report;
extern ABI const Report*dong_ap_boot_checkpoint_run(void);
extern ABI const Report*dong_ap_boot_checkpoint_pointer(void);
extern ABI void checkpoint_reset(void);
static Boot boot;static Domain domain;static U headers[16][32],table[16],engine[4],parked,reads,checks;static int absent;
#define CK(x) do{checks++;if(!(x)){fprintf(stderr,"CHECKPOINT_ASSERT line %d: %s\n",__LINE__,#x);exit(1);}}while(0)
ABI const Boot*checkpoint_boot(void){reads++;return absent?NULL:&boot;}
ABI U ap_checkpoint_parked_mask(void){return parked;}
ABI void __dong_panic(void){fprintf(stderr,"unexpected panic\n");exit(2);}
static void setup(U count){checkpoint_reset();reads=0;absent=0;memset(&domain,0,sizeof domain);domain.ready=domain.lock=1;domain.online=((U)1<<count)-1;engine[0]=1;engine[3]=12;domain.engine=(U)(uintptr_t)engine;parked=domain.online&~(U)1;memset(headers,0,sizeof headers);for(U n=0;n<16;n++){headers[n][25]=2;headers[n][10]=n;table[n]=(U)(uintptr_t)headers[n];}boot=(Boot){1,0,1,count,domain.online,(U)(uintptr_t)&domain,(U)(uintptr_t)table,0x20000,0x30000,1000000000};}
static void run(int valid){Boot b=boot;Domain d=domain;U h[16][32];memcpy(h,headers,sizeof h);const Report*r=dong_ap_boot_checkpoint_run();CK(r==dong_ap_boot_checkpoint_pointer()&&r->version==1&&r->done==1&&reads==1);CK(!memcmp(&b,&boot,sizeof b)&&!memcmp(&d,&domain,sizeof d)&&!memcmp(h,headers,sizeof h));if(valid){CK(r->error==0&&r->checkpoint==23&&r->cpus==boot.count&&r->lock==1&&r->owner==0&&r->published==1&&r->ready_mask==domain.online&&r->online==domain.online&&r->parked_mask==parked&&r->queue_count==12&&r->error_mask==0&&r->first_cpu==16&&r->first_error==0);}else CK(r->error==0x0b040001&&r->checkpoint==0);Report copy=*r;boot.failed=99;domain.lock=0;headers[0][25]=0;CK(dong_ap_boot_checkpoint_run()==r&&reads==1&&!memcmp(&copy,r,sizeof copy));}
int main(void){for(U n=3;n<=16;n++){setup(n);run(1);}setup(8);absent=1;run(0);setup(2);run(0);setup(17);run(0);setup(8);boot.domain=0;run(0);setup(8);boot.headers=0;run(0);setup(8);domain.engine=0;run(0);for(unsigned k=0;k<11;k++){setup(8);if(k==0)boot.ready=0;if(k==1)boot.failed=5;if(k==2)boot.published=0;if(k==3)domain.ready=0;if(k==4)domain.failed=9;if(k==5)domain.lock=0;if(k==6)domain.owner=1;if(k==7)domain.online|=(U)1<<63;if(k==8)parked^=4;if(k==9)engine[3]=0;if(k==10)engine[3]=17;run(0);}for(U n=0;n<8;n++){setup(8);headers[n][25]=1;run(0);setup(8);headers[n][26]=0xfeed0000+n;const Report*r=dong_ap_boot_checkpoint_run();CK(r->error==0x0b040001&&r->error_mask==((U)1<<n)&&r->first_cpu==n&&r->first_error==0xfeed0000+n);setup(8);table[n]=0;run(0);}setup(8);headers[2][26]=11;headers[5][26]=22;const Report*r=dong_ap_boot_checkpoint_run();CK(r->error_mask==0x24&&r->first_cpu==2&&r->first_error==11);printf("CHECKPOINT_NATIVE_OK checks=%lu\n",(unsigned long)checks);return 0;}
