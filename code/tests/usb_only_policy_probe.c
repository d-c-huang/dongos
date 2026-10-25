/* Independent role/ledger and extracted early-guard oracle. No actual I/O. */
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define ABI __attribute__((sysv_abi))
typedef uint64_t U;
typedef struct {U version,token,next_cursor,kind,ecam,segment,bus,device,function,vendor,device_id,class_code,header,flags,generation,reserved;} Device;
typedef struct {U version,device_token,role,configuration_id,generation,irq_mask,flags,reserved;} Binding;
typedef struct {U view[8],owner,device_token,live,serial;} IrqState;
typedef struct {U initialized,count;Device devices[32];Binding bindings[4];IrqState interrupts[2];} Table;
_Static_assert(sizeof(Device)==128,"independent Device ABI");
_Static_assert(sizeof(Binding)==64,"independent Binding ABI");
_Static_assert(sizeof(Table)==4560,"independent Table ABI");
extern ABI U usb_policy_mode(void),usb_policy_audit_bytes(void),usb_policy_rank(const Device *,U);
extern ABI U usb_policy_init(Table *),usb_policy_register(Table *,const Device *,Device *);
extern ABI U usb_policy_bind(Table *,U,const Device *,U,Binding *),usb_policy_binding(const Table *,U,Binding *);
extern ABI U usb_policy_claim(U,U),usb_policy_admit(U,U),usb_policy_sizes(U);
static unsigned checks,hardware_calls;
static U hardware_kind,hardware_id,hardware_ecam;
static const char *where="setup";
#define REQUIRE(x) do {++checks;if(!(x)){fprintf(stderr,"USB_ONLY_ASSERT case=%s line=%d check=%s; returned normally\n",where,__LINE__,#x);return 1;}} while(0)
ABI void __dong_panic(U code){fprintf(stderr,"unexpected panic=%llu\n",(unsigned long long)code);exit(99);}
ABI U usb_policy_hardware(U kind,U id,U ecam){++hardware_calls;hardware_kind=kind;hardware_id=id;hardware_ecam=ecam;return 0;}
static Device pci(U vendor,U device,U class_code,U number){
 Device d={0};d.version=1;d.kind=1;d.ecam=UINT64_C(0xe0000000)+number*4096;d.device=number;
 d.vendor=vendor;d.device_id=device;d.class_code=class_code;return d;
}
static int storage(unsigned usb,U vendor,U device,U class_code,U expected_rank){
 Table table={0},before;Device raw=pci(vendor,device,class_code,1),kept=raw,registered;
 Binding output,old;
 REQUIRE(usb_policy_rank(&raw,1)==(usb?0:expected_rank));
 REQUIRE(usb_policy_init(&table)==0);
 REQUIRE(usb_policy_register(&table,&raw,&registered)==0);REQUIRE(!memcmp(&raw,&kept,sizeof raw));
 REQUIRE(table.count==1&&registered.token==257&&registered.generation==1);
 REQUIRE(registered.flags==(usb?0:1));before=table;
 memset(&output,0xa7,sizeof output);old=output;
 U result=usb_policy_bind(&table,registered.token,&raw,1,&output);
 if(usb){
  REQUIRE(result==UINT64_C(0x05120002));REQUIRE(!memcmp(&before,&table,sizeof table));REQUIRE(!memcmp(&output,&old,sizeof output));
  REQUIRE(usb_policy_binding(&table,1,&output)==UINT64_C(0x05120006));REQUIRE(!memcmp(&output,&old,sizeof output));
 }else{
  REQUIRE(result==0);REQUIRE(output.role==1&&output.configuration_id==2&&output.device_token==257&&output.flags==2);
  REQUIRE(table.devices[0].flags==3);REQUIRE(usb_policy_binding(&table,1,&output)==0);
 }
 return 0;
}
int main(int argc,char **argv){
 unsigned usb=argc==2&&(strcmp(argv[1],"usb")==0);
 REQUIRE(usb_policy_mode()==usb);REQUIRE(usb_policy_audit_bytes()==(usb?2097152:32768));
 REQUIRE(usb_policy_sizes(0)==sizeof(Table)&&usb_policy_sizes(1)==sizeof(Device)&&usb_policy_sizes(2)==sizeof(Binding));
 where="VirtIO";if(storage(usb,0x1af4,0x1042,0x010000,3))return 1;
 where="NVMe";if(storage(usb,0x144d,0xa80a,0x010802,2))return 1;
 where="AHCI";if(storage(usb,0x8086,0x2922,0x010601,1))return 1;
 where="preserved XHCI input roles";
 Device devices[3]={pci(0x1b36,0x000d,0x0c0330,2),pci(0x1af4,0x1052,0x090000,3),{0}};
 devices[2].version=1;devices[2].kind=2;
 const U roles[3]={4,2,3},configs[3]={13,4,4};
 Table table={0};REQUIRE(usb_policy_init(&table)==0);
 for(unsigned i=0;i<3;i++){
  Device output;Binding binding;
  REQUIRE(usb_policy_rank(&devices[i],roles[i])==1);
  REQUIRE(usb_policy_register(&table,&devices[i],&output)==0);
  REQUIRE(usb_policy_bind(&table,output.token,&devices[i],roles[i],&binding)==0);
  REQUIRE(binding.configuration_id==configs[i]&&binding.role==roles[i]);
 }
 REQUIRE(table.bindings[0].device_token==0);
 where="kernel grant early guard";
 U ecam=UINT64_C(0xe0001000);unsigned prior=hardware_calls;
 REQUIRE(usb_policy_claim(2,ecam)==(usb?UINT64_C(0x050a0002):0));
 REQUIRE(hardware_calls==prior+(usb?0:1));
 if(!usb){REQUIRE(hardware_kind==0&&hardware_id==2&&hardware_ecam==ecam);}
 where="kernel admit early guard";prior=hardware_calls;
 REQUIRE(usb_policy_admit(1,ecam)==(usb?UINT64_C(0x050a0002):0));
 REQUIRE(hardware_calls==prior+(usb?0:1));
 if(!usb){REQUIRE(hardware_kind==1&&hardware_id==1&&hardware_ecam==ecam);}
 where="other early guards preserved";
 prior=hardware_calls;REQUIRE(usb_policy_claim(13,ecam)==0);REQUIRE(hardware_calls==prior+1&&hardware_id==13);
 prior=hardware_calls;REQUIRE(usb_policy_claim(4,ecam)==0);REQUIRE(hardware_calls==prior+1&&hardware_id==4);
 prior=hardware_calls;REQUIRE(usb_policy_admit(4,ecam)==0);REQUIRE(hardware_calls==prior+1&&hardware_id==4);
 where="invalid matching inputs";REQUIRE(usb_policy_rank(NULL,1)==0);
 Device invalid=devices[0];invalid.version=2;REQUIRE(usb_policy_rank(&invalid,4)==0);
 invalid=devices[0];invalid.header=1;REQUIRE(usb_policy_rank(&invalid,4)==0);
 printf("USB_ONLY_NATIVE passed checks=%u profile=%u hardware_callbacks=%u; returned normally\n",checks,usb,hardware_calls);
 return 0;
}
