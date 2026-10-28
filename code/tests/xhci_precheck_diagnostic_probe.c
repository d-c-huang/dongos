#define __USE_MINGW_ANSI_STDIO 1
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define ABI __attribute__((sysv_abi))
typedef uint64_t U;
typedef struct{U bar,bar_bytes,token,physical;unsigned char*pointer;U bytes,bits,epoch,hz,timeout,device,exclusive,interrupts_off,pci_command;} Setup;
typedef struct{U version,op,runtime,doorbells,ports,max_slots,slots,context_bytes,ac64,protocols[32];} Caps;
typedef struct{U version,check,offset,value,aux;} Report;
typedef ABI U(*Read)(U,U,U,uint32_t*);typedef ABI U(*Write)(U,U,U,uint32_t);
typedef ABI U(*Fence)(U,U);typedef ABI U(*Now)(U,U*);typedef ABI U(*Enable)(U);
typedef struct{Read read;Write write;Fence fence;Now now;Enable enable;} Ops;
_Static_assert(sizeof(Setup)==112&&sizeof(Caps)==328&&sizeof(Report)==40,"independent ABI");
extern ABI U xhp_check(const Ops*,U,const Setup*,Caps*);
extern ABI const Report*xhp_report(void);
extern ABI U xhp_emit(U);
static uint32_t regs[16384];static unsigned char dma[524288+4096];
static U checks,reads,failing;static char log_bytes[512];static size_t log_length;
#define CK(x) do{checks++;if(!(x)){fprintf(stderr,"PRECHECK_ASSERT %d %s\n",__LINE__,#x);exit(1);}}while(0)
ABI void __dong_panic(void){fputs("unexpected panic\n",stderr);exit(2);}
static ABI U rd(U ctx,U bar,U off,uint32_t*out){CK(ctx==77&&bar==99&&out&&off%4==0&&off<sizeof(regs));reads++;if(off==failing)return 7;*out=regs[off/4];return 0;}
static ABI U wr(U a,U b,U c,uint32_t d){(void)a;(void)b;(void)c;(void)d;CK(0);return 1;}
static ABI U fence(U a,U b){(void)a;(void)b;CK(0);return 1;}
static ABI U now(U a,U*b){(void)a;(void)b;CK(0);return 1;}
static ABI U enable(U a){(void)a;CK(0);return 1;}
ABI U record_log(const unsigned char*p,U n){CK(p&&n>0&&n<64&&log_length+n<sizeof(log_bytes));memcpy(log_bytes+log_length,p,(size_t)n);log_length+=(size_t)n;return 0;}
static void one(unsigned scenario){
 memset(regs,0,sizeof regs);memset(dma,0xa5,sizeof dma);reads=0;failing=UINT64_MAX;log_length=0;memset(log_bytes,0,sizeof log_bytes);
 Setup s={99,sizeof regs,55,0x200000,(unsigned char*)(((uintptr_t)dma+4095)&~(uintptr_t)4095),131072,48,1,1000000000,1000,123,1,3,0x402};
 regs[0]=0x01000040;regs[1]=0x08000840;regs[4]=0x00080001;regs[5]=0x2000;regs[6]=0x1000;regs[0x48/4]=1;
 regs[8]=0x02000402;regs[9]=0x20425355;regs[10]=0x401;regs[12]=0x03000002;regs[13]=0x20425355;regs[14]=0x405;
 U error=0,check=0,offset=0,value=0,aux=0,expected_reads=15;
 switch(scenario){
 case 0:break;
 case 1:regs[0]=0x00960040;check=3;value=regs[0];expected_reads=1;break;
 case 2:regs[1]&=~255u;check=4;offset=4;value=regs[1];expected_reads=4;break;
 case 3:regs[2]=(2u<<21)|(1u<<27);check=4;offset=4;value=regs[1];aux=regs[2];expected_reads=4;break;
 case 4:regs[2]=1u<<27;check=5;offset=8;value=regs[2];aux=s.bytes;expected_reads=4;break;
 case 5:regs[4]&=~1u;s.physical=UINT64_C(0x100000000);check=6;offset=16;value=s.physical;aux=s.bytes;expected_reads=4;break;
 case 6:regs[0x48/4]=0x100;check=8;offset=0x48;value=0x100;expected_reads=7;break;
 case 7:case 8:regs[8]=scenario==7?0x00010001:1;check=10;offset=32;value=regs[8];expected_reads=8;break;
 case 9:regs[8]=0x01000001;regs[9]=0x2000;check=11;offset=36;value=regs[9];aux=regs[8];expected_reads=9;break;
 case 10:regs[9]^=1;check=12;offset=36;value=regs[9];aux=regs[8];expected_reads=9;break;
 case 11:regs[10]|=1u<<28;check=13;offset=40;value=regs[10];aux=regs[8];expected_reads=11;break;
 case 12:regs[11]=1;check=13;offset=40;value=regs[10];aux=((U)regs[11]<<32)|regs[8];expected_reads=11;break;
 case 13:regs[8]=192;check=16;offset=32;value=regs[8];expected_reads=8;break;
 case 14:regs[8]=0x04000402;check=13;offset=40;value=regs[10];aux=regs[8];expected_reads=11;break;
 case 15:failing=4;error=0x08110003;check=128;offset=4;value=7;expected_reads=2;break;
 case 16:s.exclusive=0;error=0x08110001;expected_reads=0;break;
 case 17:case 18:case 19:
  // Previously photographed Intel base capabilities; the extended records
  // below are explicit models, not a claimed dump of that machine.
  regs[0]=0x01000080;regs[1]=0x18000840;regs[2]=0x14200054;regs[4]=0x200077c1;s.bytes=524288;regs[0x88/4]=1;
  regs[0x8000/4]=0x01000401;regs[0x8010/4]=0x02000002;regs[0x8014/4]=0x20425355;regs[0x8018/4]=0x1801;expected_reads=13;
  if(scenario!=17){regs[0x8000/4]=scenario==18?0x00010001:192;check=scenario==18?10:16;offset=0x8000;value=regs[0x8000/4];expected_reads=8;}break;
 case 21:case 22:case 23:case 24:case 25:case 26:case 27:case 28:
  regs[4]=0x01000001;regs[0x400/4]=0x02000802;regs[0x404/4]=0x20425355;regs[0x408/4]=0x30000401;
  regs[0x410/4]=0x000c0021;regs[0x414/4]=0x05dc0012;regs[0x418/4]=0x01e00023;
  regs[0x420/4]=0x03000002;regs[0x424/4]=0x20425355;regs[0x428/4]=0x10000405;regs[0x430/4]=0x00050134;expected_reads=19;
  if(scenario==22){regs[0x414/4]=regs[0x410/4];check=17;offset=0x414;value=regs[0x414/4];aux=regs[0x400/4];expected_reads=13;}
  if(scenario==23||scenario==24){regs[0x410/4]=scenario==23?0x000c0027:0x000d0021;check=17;offset=0x410;value=regs[0x410/4];aux=regs[0x400/4];expected_reads=12;}
  if(scenario==25||scenario==26){if(scenario==25)regs[0x408/4]=0x20000401;else regs[0x400/4]=0x02000402;check=13;offset=0x408;value=regs[0x408/4];aux=regs[0x400/4];expected_reads=11;}
  if(scenario==27){regs[0x430/4]=0x00050034;check=17;offset=0x430;value=regs[0x430/4];aux=regs[0x420/4];}
  if(scenario==28){failing=0x418;error=0x08110003;check=128;offset=0x418;value=7;expected_reads=14;}
  break;
 case 20:
  regs[4]=0x01000001;for(unsigned i=0;i<64;i++){unsigned k=0x400/4+i*4;regs[k]=0x02000402;regs[k+1]=0x20425355;regs[k+2]=1;}
  check=9;offset=0x800;value=64;expected_reads=263;break;
 default:CK(0);
 }
 if(check&&error==0)error=0x08110002;
 Ops ops={rd,wr,fence,now,enable};Caps out,old;memset(&out,0x5a,sizeof out);old=out;Setup input=s;uint32_t before[16384];memcpy(before,regs,sizeof regs);
 U result=xhp_check(&ops,77,&s,&out);const Report*r=xhp_report();CK(result==error&&reads==expected_reads);CK(!memcmp(&input,&s,sizeof s)&&!memcmp(before,regs,sizeof regs));
 CK(r->version==1&&r->check==check&&r->offset==offset&&r->value==value&&r->aux==aux);
 if(error)CK(!memcmp(&out,&old,sizeof out));else CK(out.version==0x100&&out.ports==(scenario==17?24:8));
 for(unsigned i=0;i<sizeof dma;i++)CK(dma[i]==0xa5);
 // Mutate MMIO after the decision: logging must emit the stored decision
 // sample, with no read/write/fence/BME callback and no change to the code.
 memset(regs,0x77,sizeof regs);U old_reads=reads;CK(xhp_emit(result)==result&&reads==old_reads);
 char expected[512];int n;
 if(check)n=snprintf(expected,sizeof expected,"xhci_check=0x%016llx\r\nxhci_reg=0x%016llx\r\nxhci_value=0x%016llx\r\nxhci_aux=0x%016llx\r\nxhci_error=0x%016llx\r\nxhci_phase=0x0000000000000000\r\nxhci_held=0x0000000000000000\r\n",(unsigned long long)check,(unsigned long long)offset,(unsigned long long)value,(unsigned long long)aux,(unsigned long long)error);
 else n=snprintf(expected,sizeof expected,"xhci_error=0x%016llx\r\nxhci_phase=0x0000000000000000\r\nxhci_held=0x0000000000000000\r\n",(unsigned long long)error);
 CK(n>0&&log_length==(size_t)n&&!memcmp(log_bytes,expected,(size_t)n));
}
int main(void){for(unsigned i=0;i<=28;i++){one(i);one(0);}printf("PRECHECK_DIAGNOSTIC_OK checks=%llu cases=58 no_hardware_writes=1\n",(unsigned long long)checks);return 0;}
