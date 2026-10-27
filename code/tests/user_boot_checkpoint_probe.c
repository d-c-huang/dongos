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
typedef struct{U version,done,error,checkpoint,cpus,boot_ready,boot_failed,published,domain_ready,domain_failed,lock,owner,online,barrier,expected,completed,enabled;} Report;
extern ABI const Report*dong_user_boot_checkpoint_run(void);
extern ABI const Report*dong_user_boot_checkpoint_pointer(void);
extern ABI void checkpoint_reset(void);
static Boot boot;static Domain domain;static U reads,checks;static int absent;
#define CK(x) do{checks++;if(!(x)){fprintf(stderr,"CHECKPOINT_ASSERT line %d: %s\n",__LINE__,#x);exit(1);}}while(0)
ABI const Boot*checkpoint_boot(void){reads++;return absent?NULL:&boot;}
ABI void __dong_panic(void){fprintf(stderr,"unexpected panic\n");exit(2);}
static void setup(U count){checkpoint_reset();reads=0;absent=0;memset(&domain,0,sizeof domain);domain.ready=domain.lock=1;domain.online=((U)1<<count)-1;domain.expected=17;domain.completed=9;domain.sequence=77;boot=(Boot){1,0,0,count,domain.online,(U)(uintptr_t)&domain,0x10000,0x20000,0x30000,1000000000};}
static void run(int valid){Boot b=boot;Domain d=domain;const Report*r=dong_user_boot_checkpoint_run();CK(r==dong_user_boot_checkpoint_pointer()&&r->version==1&&r->done==1&&reads==1);CK(!memcmp(&b,&boot,sizeof b)&&!memcmp(&d,&domain,sizeof d));if(valid){CK(r->error==0&&r->checkpoint==21&&r->enabled==1&&r->cpus==boot.count&&r->lock==1&&r->owner==0&&r->online==domain.online&&r->barrier==0&&r->expected==17&&r->completed==9);}else CK(r->error==0x0b030001&&r->enabled==0&&r->checkpoint==0);Report copy=*r;boot.failed=99;domain.lock=0;CK(dong_user_boot_checkpoint_run()==r&&reads==1&&!memcmp(&copy,r,sizeof copy));}
int main(void){for(U n=3;n<=16;n++){setup(n);run(1);}setup(8);absent=1;run(0);setup(2);run(0);setup(17);run(0);setup(8);boot.domain=0;run(0);for(unsigned k=0;k<9;k++){setup(8);if(k==0)boot.ready=0;if(k==1)boot.failed=5;if(k==2)boot.published=1;if(k==3)domain.ready=0;if(k==4)domain.failed=9;if(k==5)domain.lock=0;if(k==6)domain.owner=1;if(k==7)domain.online|=(U)1<<63;if(k==8)domain.barrier=1;run(0);}printf("CHECKPOINT_NATIVE_OK checks=%lu\n",(unsigned long)checks);return 0;}
