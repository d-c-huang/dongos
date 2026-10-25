#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#include <malloc.h>
#endif
#define ABI __attribute__((sysv_abi))
typedef uint64_t U;
typedef struct { U root,id,generation,va,pa,bytes,flags,leaf; } Alias;
typedef struct { U epoch,pa,bytes,count; Alias aliases[64]; } Snapshot;
extern ABI U fb_kernel(U),fb_kernel_tables(void),fb_user(U,U),fb_publish(U,U),fb_map(U),fb_snapshot(void),fb_recheck(void),fb_snapshot_ptr(void),fb_tables(void),fb_epoch(void),fb_held(void),fb_retire(U),fb_hidden(void),fb_other(U);
extern ABI U fb_transition(void);
extern ABI void fb_root_change(void);
extern ABI void fb_buffers(U,U),fb_map_fail(U);
static unsigned checks,flushes,invalidates;static int fail_unbind,retiring;static void *arena;static U used;
#define CK(x) do{++checks;if(!(x)){fprintf(stderr,"ledger check failed line %d: %s\n",__LINE__,#x);exit(1);}}while(0)
static void *aligned(size_t n){
#ifdef _WIN32
 return _aligned_malloc(n,4096);
#else
 return aligned_alloc(4096,n);
#endif
}
ABI void __dong_panic(void){fprintf(stderr,"unexpected panic\n");exit(99);}
ABI U user_current_root(void){return 0;}
ABI void user_pcid_flush_all(void){flushes++;if(retiring){CK(((U*)(uintptr_t)fb_tables())[0]==0);CK(fb_held()==2);}}
ABI U user_pcid_unbind(U id,U root){CK(id==1&&root==0x2000000&&flushes&&fb_held()==2);return fail_unbind?0:1;}
ABI U user_pcid_bind(U id,U root,U generation){(void)id;(void)root;(void)generation;return 1;}
ABI void user_pcid_invalidate_root(U root){CK(root==0x2000000);invalidates++;}
ABI void runtime_invalidate(U va){(void)va;}
ABI void runtime_flush_root(void){}
ABI void runtime_copy_bytes(void *d,const void *s,U n){memcpy(d,s,(size_t)n);}
ABI U fb_allocate(U pages,U alignment,U *out){CK(pages&&alignment==1&&used+pages<=128);out[0]=0x3000000+used*4096;out[1]=(U)(uintptr_t)arena+used*4096;out[2]=pages;used+=pages;return 0;}
/* Independent raw PTE descent: no call to Dong query and no ledger-derived PA. */
static U leaf(U root,U va){U pa=root;for(unsigned level=0;level<4;level++){
 U *pool;U base,limit;if(pa>=0x1000000&&pa<0x1080000){pool=(U*)(uintptr_t)fb_kernel_tables();base=0x1000000;limit=128;}
 else{pool=(U*)(uintptr_t)fb_tables();base=0x2000000;limit=32;}
 CK(pa>=base&&(pa-base)/4096<limit);U e=pool[(pa-base)/8+((va>>(39-9*level))&511)];if(!(e&1))return 0;
 if(level==3)return e;CK(!(e&128));pa=e&UINT64_C(0x0000fffffffff000);
 }return 0;}
static void contents(Snapshot *s,U count,U epoch){CK(s->count==count&&s->epoch==epoch&&s->pa==0x4000000&&s->bytes==12288);
 Alias *a=&s->aliases[0];CK(a->root==0x1000000&&a->id==UINT64_MAX&&a->generation==0&&a->va==UINT64_C(0xffff800004000000)&&a->pa==0x4000000&&a->bytes==12288&&a->flags==17&&a->leaf==4096);
 for(U off=0;off<12288;off+=4096){U e=leaf(0x1000000,a->va+off);CK((e&UINT64_C(0x0000fffffffff000))==0x4000000+off);CK((e&135)==131);}
 if(count==2){a=&s->aliases[1];CK(a->root==0x2000000&&a->id==1&&a->generation==17&&a->va==0x60000000&&a->pa==0x4000000&&a->bytes==8192&&a->flags==19&&a->leaf==4096);
 for(U off=0;off<8192;off+=4096){U e=leaf(0x2000000,a->va+off);CK((e&UINT64_C(0x0000fffffffff000))==0x4000000+off);CK((e&135)==135);}CK(leaf(0x2000000,0x60002000)==0);}
}
int main(int argc,char **argv){CK(argc==2);const char *case_name=argv[1];arena=aligned(128*4096);CK(arena);memset(arena,0xa5,128*4096);
 U raw[20]={0};raw[2]=160;raw[8]=0x4000003;raw[9]=8192;CK(fb_kernel((U)(uintptr_t)raw)==0);
 Snapshot *snap=aligned(8192);void *roots=aligned(4096);CK(snap&&roots);memset(snap,0,8192);memset(roots,0,4096);fb_buffers((U)(uintptr_t)roots,(U)(uintptr_t)snap);
 if(!strcmp(case_name,"hhdm-overflow")){raw[8]=UINT64_C(0xffffffffff00);raw[9]=256;CK(fb_publish(UINT64_C(0xfffffffff000),4096)==0x04060003);CK(fb_epoch()==0);puts("ledger HHDM overflow rejected before arithmetic");return 0;}
 if(!strcmp(case_name,"raw-mismatch")){raw[8]+=4096;CK(fb_publish(0x4000000,12288)!=0);CK(fb_epoch()==0);puts("ledger raw authority reject passed");return 0;}
 CK(fb_publish(0x4000000,12288)==0);CK(fb_publish(0x4000000,12288)!=0);
 int aborting=!strcmp(case_name,"abort");CK(fb_user(17,aborting)==0);
 for(U i=0;i<7;i++)CK(fb_other(i)==0x04060004);
 if(!strcmp(case_name,"overflow")){*(U*)(uintptr_t)fb_epoch()=UINT64_MAX;CK(fb_map(8192)!=0);CK(!leaf(0x2000000,0x60000000));puts("ledger overflow preflight passed");return 0;}
 if(!strcmp(case_name,"partial")){fb_map_fail(2);CK(fb_map(8192)!=0);CK(fb_held()==1&&fb_epoch()==0);CK(leaf(0x2000000,0x60000000)!=0&&!leaf(0x2000000,0x60001000));CK(fb_snapshot()!=0&&fb_map(8192)!=0&&fb_retire(0)!=0);puts("ledger partial failure held passed");return 0;}
 CK(fb_map(8192)==0&&invalidates==1);CK(fb_map(8192)!=0);
 if(aborting){CK(fb_snapshot()!=0);}else{CK(fb_snapshot()==0);contents(snap,2,2);CK(fb_recheck()==0);}
 if(!strcmp(case_name,"hidden")){CK(fb_hidden()==0);Snapshot before=*snap;CK(fb_snapshot()!=0);CK(!memcmp(&before,snap,sizeof before));puts("ledger hidden alias reject passed");return 0;}
 if(!strcmp(case_name,"root-change")){fb_root_change();CK(fb_recheck()!=0);puts("ledger root metadata change rejected");return 0;}
 if(!strcmp(case_name,"transition")){CK(fb_transition()==0);CK(fb_recheck()==0);CK(fb_snapshot()!=0);puts("ledger independent authority survives transition");return 0;}
 retiring=1;fail_unbind=!strcmp(case_name,"retire-failed");U retired=fb_retire(aborting);
 if(fail_unbind){CK(retired!=0&&fb_held()==2&&fb_snapshot()!=0);puts("ledger retirement failure held passed");return 0;}
 CK(retired==0&&fb_held()==0);retiring=0;CK(fb_snapshot()==0);contents(snap,1,3);CK(!leaf(0x2000000,0x60000000));
 CK(fb_user(18,0)==0&&fb_map(8192)==0&&fb_snapshot()==0);CK(snap->epoch==4&&snap->aliases[1].generation==18);CK(fb_recheck()==0);
 printf("ledger native %s passed %u checks\n",case_name,checks);return 0;
}
