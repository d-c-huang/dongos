/* Independent full-Catalog initialization oracle; no hardware callbacks. */
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define ABI __attribute__((sysv_abi))
#ifndef USB_PROFILE
#define USB_PROFILE 0
#endif
typedef uint64_t U;
typedef struct {U version,id,dependencies,restart_limit,timeout_ticks,flags,image,name_length;uint8_t name[32];U reserved[4];} Config;
typedef struct {U version,configuration,process,generation,state,status,sequence,argument;} Snapshot;
typedef struct {U version,sequence,configuration,generation,process,state,status,flags;} Event;
typedef struct {U ready;size_t count;U sequence;Config configs[32];Snapshot states[32];U slot[32],incarnation[16],configuration[16];Event events[64];} Catalog;
_Static_assert(sizeof(Config)==128,"independent Config ABI");
_Static_assert(offsetof(Config,timeout_ticks)==32&&offsetof(Config,name)==64,"independent Config offsets");
_Static_assert(sizeof(Snapshot)==64&&sizeof(Event)==64,"independent Snapshot/Event ABI");
_Static_assert(sizeof(Catalog)==10776&&offsetof(Catalog,configs)==24&&offsetof(Catalog,events)==6680,"independent Catalog ABI");
extern U ABI catalog_initialize(Catalog *,U);
static unsigned checks;
static const char *where="setup";
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"startup budget oracle failed case=%s line=%d: %s; returned normally\n",where,__LINE__,#x);exit(1);}}while(0)
void ABI __dong_panic(void){fprintf(stderr,"unexpected startup budget Dong panic\n");exit(2);}

static const char *names[18]={"shell","fs","block","compositor","input","init","devmgr","echo","fault","waiter","ipc-peer","fs-reader","file-app","xhci","terminal","files","editor","settings"};
static const U deps[18]={2,4,64,18,64,0,32,2,2,2,2,2,2,64,10,10,10,10};
static const U flags[18]={7,7,5,7,5,5,7,8,8,8,8,8,8,4,9,9,9,9};
static const U retries[18]={3,3,0,3,0,0,3,0,0,0,0,0,0,0,0,0,0,0};
typedef struct {U before[2];Catalog c;U after[2];} Guarded;
static Guarded value,prior;

static void seed(void){
 unsigned char *bytes=(unsigned char *)&value;
 for(size_t i=0;i<sizeof(value);i++)bytes[i]=(unsigned char)(0xa5u+(unsigned)i*37u);
 value.c.ready=0;
}
static void valid(U hz){
 Catalog expected;
 memset(&expected,0,sizeof(expected));
 expected.ready=1;expected.count=18;
 for(unsigned i=0;i<32;i++){
  expected.configs[i].version=1;expected.states[i].version=1;
  expected.states[i].configuration=i;expected.slot[i]=UINT64_MAX;
 }
 for(unsigned i=0;i<16;i++)expected.configuration[i]=UINT64_MAX;
 for(unsigned i=0;i<64;i++)expected.events[i].version=1;
 for(unsigned i=0;i<18;i++){
  Config *c=&expected.configs[i];
  c->id=i;c->image=i+1;c->dependencies=deps[i];c->flags=flags[i];
  c->restart_limit=retries[i];c->timeout_ticks=hz*((USB_PROFILE&&i==1)?60u:10u);
  c->name_length=strlen(names[i]);memcpy(c->name,names[i],c->name_length);
 }
 seed();prior=value;
 CHECK(catalog_initialize(&value.c,hz)==0);
 CHECK(!memcmp(value.before,prior.before,sizeof(value.before)));
 CHECK(!memcmp(value.after,prior.after,sizeof(value.after)));
 for(unsigned i=0;i<32;i++){
  CHECK(!memcmp(&value.c.configs[i],&expected.configs[i],sizeof(Config)));
  CHECK(!memcmp(&value.c.states[i],&expected.states[i],sizeof(Snapshot)));
  CHECK(value.c.slot[i]==UINT64_MAX);
 }
 for(unsigned i=0;i<16;i++)CHECK(value.c.incarnation[i]==0&&value.c.configuration[i]==UINT64_MAX);
 for(unsigned i=0;i<64;i++)CHECK(!memcmp(&value.c.events[i],&expected.events[i],sizeof(Event)));
 CHECK(!memcmp(&value.c,&expected,sizeof(expected)));
}
static void invalid(U hz,U ready){
 seed();value.c.ready=ready;prior=value;
 CHECK(catalog_initialize(&value.c,hz)==UINT64_C(0x05110001));
 CHECK(!memcmp(&value,&prior,sizeof(value)));
}
int main(void){
 const U max10=UINT64_MAX/10,max60=UINT64_MAX/60;
 where="null";CHECK(catalog_initialize(NULL,1)==UINT64_C(0x05110001));
 where="zero-hz-no-write";invalid(0,0);
 where="profile-overflow-no-write";invalid((USB_PROFILE?max60:max10)+1,0);
 where="max-hz-no-write";invalid(UINT64_MAX,0);
 where="already-ready-no-write";invalid(1,1);invalid(1,2);
 where="normal-hz-one";valid(1);
 where="normal-hz-100";valid(100);
 where="max60-boundary";valid(max60);
 if(!USB_PROFILE){where="default-above-max60";valid(max60+1);where="max10-boundary";valid(max10);}
 else{where="usb-max10-rejected-no-write";invalid(max10,0);}
 printf("USB_STARTUP_BUDGET_PASS profile=%u configs=18 capacity=32 slots=16 checks=%u; returned normally\n",(unsigned)USB_PROFILE,checks);
 return 0;
}
