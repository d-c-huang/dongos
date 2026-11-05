#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#include <malloc.h>
#endif
#define ABI __attribute__((sysv_abi))
typedef uint64_t U;
typedef struct {U state,root,generation,incarnation,pages,unmapped,online,before,after,error;} View;
extern ABI U dr_prepare(void),dr_other_pool(void),dr_kernel(void),dr_kernel_tables(void),dr_memory_setup(void),dr_pool(void),dr_meta(void),dr_frames(void),dr_recycled(void),dr_pin(void),dr_run(void),dr_memory_bad(U),dr_view(View*);
extern ABI void dr_sync_lease(void),dr_host_setup(void),dr_domain_setup(void),dr_host_bad(U),dr_domain_bad(U),dr_finish_barrier(U),dr_fail_at(U),dr_lease(U*);
static unsigned checks,barriers;static U barrier_kind,used,allocation_failure;static void *arena;
#define CK(x) do{++checks;if(!(x)){fprintf(stderr,"retire check failed line %d: %s\n",__LINE__,#x);exit(1);}}while(0)
ABI void __dong_panic(void){fprintf(stderr,"unexpected Dong panic\n");exit(99);}
ABI U user_current_root(void){return 0x1000000;}
ABI U user_smp_arch_if0(void){return 1;}
ABI U user_smp_arch_cpu(void){return 0;}
ABI U dr_allocate(U pages,U alignment,U *out){CK(pages&&alignment==1&&used+pages<=256);out[0]=0x5000000+used*4096;out[1]=(U)(uintptr_t)arena+used*4096;out[2]=pages;memset((void*)(uintptr_t)out[1],0,(size_t)pages*4096);used+=pages;return allocation_failure?0x04060001:0;}
/* Raw page-table walk independent of Dong query and retirement observations. */
static U leaf(U root,U va){U pa=root;for(unsigned level=0;level<4;level++){
 U *pool;U base,limit;if(pa>=0x1000000&&pa<0x1080000){pool=(U*)(uintptr_t)dr_kernel_tables();base=0x1000000;limit=128;}
 else{pool=(U*)(uintptr_t)dr_pool();base=0x2000000;limit=32;}
 CK(pa>=base&&(pa-base)/4096<limit);U e=pool[(pa-base)/8+((va>>(39-9*level))&511)];if(!(e&1))return 0;
 if(level==3)return e;
 CK(!(e&128));pa=e&UINT64_C(0x000ffffffffff000);
 }return 0;}
ABI U user_shared_barrier(void){barriers++;for(U n=0;n<4;n++)CK(leaf(0x2000000,0x60000000+n*4096)==0);if(barrier_kind==1)return 0;dr_finish_barrier(barrier_kind);return 1;}
int main(int argc,char **argv){CK(argc==2);const char *name=argv[1];
#ifdef _WIN32
 arena=_aligned_malloc(256*4096,4096);
#else
 arena=aligned_alloc(4096,256*4096);
#endif
 CK(arena);memset(arena,0xa5,256*4096);CK(dr_kernel()==0);CK(dr_memory_setup()==0);dr_domain_setup();dr_host_setup();
 U supervisor[4];for(U n=0;n<4;n++){
  supervisor[n]=leaf(0x1000000,UINT64_C(0xffffd00000000000)+n*4096);
  CK((supervisor[n]&UINT64_C(0x000ffffffffff000))==0x4000000+n*4096);CK((supervisor[n]&7)==3);
  U user=leaf(0x2000000,0x60000000+n*4096);CK((user&UINT64_C(0x000ffffffffff000))==0x4000000+n*4096);CK((user&7)==7);
 }
 if(!strcmp(name,"prepare-failure")){
  allocation_failure=1;CK(dr_prepare()!=0);U first=used;CK(first>0);CK(dr_prepare()!=0);CK(used==first);CK(dr_run()!=0);CK(used==first&&barriers==0);
  printf("DMA retirement %s passed %u checks\n",name,checks);return 0;
 }
 if(!strncmp(name,"prepare-host",12)){dr_host_bad(strtoull(name+12,0,10));CK(dr_prepare()!=0);CK(used==0);printf("DMA retirement %s passed %u checks\n",name,checks);return 0;}
 if(!strncmp(name,"prepare-domain",14)){dr_domain_bad(strtoull(name+14,0,10));CK(dr_prepare()!=0);CK(used==0);printf("DMA retirement %s passed %u checks\n",name,checks);return 0;}
 if(!strcmp(name,"prepare-partial")||!strcmp(name,"prepare-zero")){
  CK(dr_memory_bad(!strcmp(name,"prepare-partial")?2:3)==0);dr_sync_lease();CK(dr_prepare()!=0);CK(used==0);printf("DMA retirement %s passed %u checks\n",name,checks);return 0;
 }
 int unprepared=!strcmp(name,"unprepared");
 if(!unprepared){CK(dr_prepare()==0);U first=used;CK(first>0);CK(dr_prepare()!=0);CK(used==first);}
 int pre=unprepared;U missing=0,unmapped=4;
 if(!strncmp(name,"host",4)){dr_host_bad(strtoull(name+4,0,10));pre=1;}
 if(!strncmp(name,"memory",6)){U k=strtoull(name+6,0,10);CK(dr_memory_bad(k>8?k-7:k)==0);if(k>8)dr_sync_lease();pre=1;if(k==7)missing=1;}
 if(!strncmp(name,"domain",6)){dr_domain_bad(strtoull(name+6,0,10));pre=1;}
 if(!strncmp(name,"barrier",7))barrier_kind=strtoull(name+7,0,10);
 if(!strncmp(name,"unmap",5)){U k=strtoull(name+5,0,10);dr_fail_at(k);unmapped=k-1;}
 U lease[8],frames[12];unsigned char recycled[4],tables[32*4096],metadata[128];
 dr_lease(lease);memcpy(frames,(void*)(uintptr_t)dr_frames(),sizeof frames);memcpy(recycled,(void*)(uintptr_t)dr_recycled(),sizeof recycled);
 memcpy(tables,(void*)(uintptr_t)dr_pool(),sizeof tables);memcpy(metadata,(void*)(uintptr_t)dr_meta(),sizeof metadata);
 unsigned char kernel[128*4096],other[32*4096];U allocated=used;
 memcpy(kernel,(void*)(uintptr_t)dr_kernel_tables(),sizeof kernel);memcpy(other,(void*)(uintptr_t)dr_other_pool(),sizeof other);
 U result=dr_run();CK(used==allocated);CK(!memcmp(kernel,(void*)(uintptr_t)dr_kernel_tables(),sizeof kernel));CK(!memcmp(other,(void*)(uintptr_t)dr_other_pool(),sizeof other));View view={0};U vr=dr_view(&view);
 if(pre){CK(result!=0);CK(barriers==0);CK(vr!=0||view.state==0);CK(!memcmp(tables,(void*)(uintptr_t)dr_pool(),sizeof tables));CK(!memcmp(metadata,(void*)(uintptr_t)dr_meta(),sizeof metadata));unmapped=0;}
 else{
  CK(vr==0);CK(view.root==0x2000000&&view.generation==7&&view.incarnation==5&&view.pages==4&&view.online==15&&view.before==10&&view.unmapped==unmapped);
  if(barrier_kind||unmapped!=4){CK(result!=0&&view.state==2&&view.after==0&&view.error!=0);}else{CK(result==0&&view.state==3&&view.after==11&&view.error==0);}
  CK(barriers==(unmapped==4?1u:0u));
  if(unmapped==4){unsigned pending=0;for(unsigned n=0;n<32;n++)if(((unsigned char*)(uintptr_t)dr_meta())[n]==2)pending++;CK(pending>0);}
  View previous=view;unsigned b=barriers;CK(dr_run()!=0);CK(dr_view(&view)==0&&memcmp(&previous,&view,sizeof view)==0&&barriers==b);
 }
 for(U n=0;n<4;n++){
  CK(leaf(0x1000000,UINT64_C(0xffffd00000000000)+n*4096)==supervisor[n]);
  U present=leaf(0x2000000,0x60000000+n*4096);if(n<unmapped||(missing&&n==3))CK(present==0);else CK((present&7)==7);
 }
 U after[8];dr_lease(after);CK(!memcmp(lease,after,sizeof lease));CK(dr_pin()==1);CK(!memcmp(frames,(void*)(uintptr_t)dr_frames(),sizeof frames));CK(!memcmp(recycled,(void*)(uintptr_t)dr_recycled(),sizeof recycled));
 printf("DMA retirement %s passed %u checks\n",name,checks);return 0;
}
