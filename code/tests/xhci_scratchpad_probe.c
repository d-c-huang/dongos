// Independent DMA observer over the existing hardware model and actual Dong
// controller/authority objects. No production layout helper is called by C.
#include "xhci_scratch_controller_fixture.c"
typedef struct{U owner,incarnation,binding_owner,binding_incarnation,binding_token,binding_role,lease_owner,lease_incarnation,lease_token,lease_exclusive,bar_exclusive,bar_uncached,lease_private_nx,attempted,physical_bits,bar_physical,bar_bytes,lease_physical,lease_bytes,pci_command,class_code,header_type,msi_disabled,msix_disabled,cap0,hcs1,hcs2,hcc1,dboff,rtsoff,pagesize;} SHeader;
typedef struct{U usbcmd,usbsts,dnctrl,dcbaap,crcr,config;} SRegisters;
typedef struct{U iman,imod,erstsz,erstba,erdp;} SInterrupter;
typedef struct{U offset,header,name,range,slot,control;} SExtension;
extern ABI U xa_permit(const SHeader*,const SRegisters*,const SInterrupter*,U,const SExtension*,U,const unsigned char*,U,U*);
static U n_scratch,lease_bytes,tail_checks;
static U required(U n){if(n>64)return 0;U p=32;if(n)while(p<33+n)p*=2;return p*4096;}
static uint32_t raw_count(U n){return (uint32_t)(((n&31)<<27)|((n>>5)<<21)|(1u<<26));}
static U get64(const unsigned char*p){U x;memcpy(&x,p,8);return x;}
static void put64(unsigned char*p,U x){memcpy(p,&x,8);}
static void check_tail(Hardware*h){
 CK(get64(h->dma)==(n_scratch?h->setup.physical+131072:0));
 for(U at=131072;at<lease_bytes;at+=8){
  U expected=at<131072+n_scratch*8?h->setup.physical+135168+(at-131072)/8*4096:0;
  CK(get64(h->dma+at)==expected);tail_checks++;
 }
 // Device scopes must remain clear before enumeration, and canaries beyond
 // the complete rounded lease must not be touched by the initializer.
 for(U at=16384;at<131072;at++)CK(h->dma[at]==0);
 for(U at=lease_bytes;at<lease_bytes+64;at++)CK(h->dma[at]==0xa5);
}
static ABI U scratch_fence(U context,U phase){
 Hardware*h=(Hardware*)(uintptr_t)context;
 if(phase!=4)return memory_fence(context,phase);
 h->fences[4]++;CK(h->reset_observed&&h->cnr_observed);check_tail(h);
 Trb link=load(h->dma+4096,255);CK(link.parameter==h->setup.physical+4096&&link.control==((6<<10)|2));
 return 0;
}
static ABI U scratch_enable(U context){Hardware*h=(Hardware*)(uintptr_t)context;check_tail(h);return enable_bme(context);}
static void controller_case(U n,int undersized){
 n_scratch=n;lease_bytes=required(n);U allocated=lease_bytes?lease_bytes:131072;
 Hardware*h=calloc(1,sizeof *h);CK(h);initialize_hardware(h,0);
 unsigned char*raw=malloc((size_t)allocated+4095+64);CK(raw);h->dma=(unsigned char*)(((uintptr_t)raw+4095)&~(uintptr_t)4095);
 memset(h->dma,0xa5,(size_t)allocated+64);h->setup.pointer=h->dma;h->setup.bytes=undersized?131072:allocated;
 h->registers[2]=raw_count(n);h->ops.fence=scratch_fence;h->ops.enable=scratch_enable;
 U rc=xhc_initialize(&h->state,&h->ops,(U)(uintptr_t)h,&h->setup);
 if(n>64||undersized){CK(rc==0x08110002&&!h->writes&&!h->enables&&!h->state.info.held);for(U at=0;at<allocated+64;at++)CK(h->dma[at]==0xa5);}
 else{CK(rc==0&&h->state.info.ready&&h->enables==1&&h->commands==1);for(unsigned i=0;i<8;i++)CK(xhc_noop(&h->state)==0);}
 free(raw);free(h);
}
static U permit(SHeader*h,SRegisters*r,SInterrupter*i,SExtension*e,unsigned char*d,U*o){return xa_permit(h,r,i,16,e,2,d,h->lease_bytes,o);}
static void authority_case(U n){
 U size=required(n);unsigned char*d=calloc(1,(size_t)size);CK(d);
 SHeader h={13,7,13,7,91,4,13,7,44,1,1,1,1,0,40,0xf0000000,65536,0x20000000,size,0x402,0x0c0330,0,1,1,0x01000080,(8u<<24)|(16u<<8)|64,raw_count(n),0x20000001,0x2000,0x1000,1};
 SRegisters r={0,1,0,h.lease_physical,h.lease_physical+4097,8};SInterrupter i[16]={{0}};i[0]=(SInterrupter){0,0,1,0,h.lease_physical+8192};
 SExtension e[2]={{0x8000,0x02000402,0x20425355,0x401,0,0},{0x8010,0x03000002,0x20425355,0x405,0,0}};
 put64(d+8176,h.lease_physical+4096);put64(d+8184,(U)((6<<10)|2)<<32);put64(d+12288,h.lease_physical+8192);put64(d+12296,256);
 if(n){put64(d,h.lease_physical+131072);for(U x=0;x<n;x++)put64(d+131072+x*8,h.lease_physical+135168+x*4096);}
 U out=99;CK(permit(&h,&r,i,e,d,&out)==0&&out==0x406);
 if(n){
  U saved=get64(d);put64(d,saved+4096);out=99;CK(permit(&h,&r,i,e,d,&out)==0x08180001&&out==99);put64(d,saved);
  for(U x=0;x<n;x++){U off=131072+x*8;saved=get64(d+off);put64(d+off,saved+8);out=99;CK(permit(&h,&r,i,e,d,&out)==0x08180001&&out==99);put64(d+off,saved);}
  const U corrupt[]={131072+n*8-1,135168,135168+n*4096-1,size-1};
  for(unsigned x=0;x<4;x++){d[corrupt[x]]^=1;out=99;CK(permit(&h,&r,i,e,d,&out)==0x08180001&&out==99);d[corrupt[x]]^=1;}
  saved=h.lease_bytes;h.lease_bytes=131072;out=99;CK(permit(&h,&r,i,e,d,&out)==0x08180001&&out==99);h.lease_bytes=saved;
 }
 r.usbcmd=0x100;out=99;CK(permit(&h,&r,i,e,d,&out)==0x08180001&&out==99);r.usbcmd=0;
 free(d);
}
int main(int argc,char**argv){
 CK(argc==2);if(!strcmp(argv[1],"controller")){
  const U counts[]={0,1,31,32,34,64,65,1023};for(unsigned x=0;x<8;x++)controller_case(counts[x],0);controller_case(34,1);
 }else if(!strcmp(argv[1],"authority")){
  const U counts[]={0,1,31,32,34,64};for(unsigned x=0;x<6;x++)authority_case(counts[x]);
 }else CK(0);
 printf("XHCI_SCRATCH_OK %s checks=%lu tail=%lu\n",argv[1],(unsigned long)assertions,(unsigned long)tail_checks);return 0;
}
