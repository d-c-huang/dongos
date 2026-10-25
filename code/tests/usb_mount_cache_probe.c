/* Independent sparse sector model for the original DG mount-only adapter. */
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define ABI __attribute__((sysv_abi))
typedef uint64_t U;
typedef struct {U context,capacity,max_transfer;U(ABI*read)(U,U,size_t,uint8_t*);U(ABI*write)(U,U,size_t,const uint8_t*);U(ABI*flush)(U);} Device;
typedef struct {U valid,first,sectors;uint8_t bytes[16384];} Line;
typedef struct {const Device *source;U enabled,phase;size_t recent;U first,fat_sectors,total,backup,fsinfo;Line lines[2];} State;
_Static_assert(sizeof(Device)==48,"independent Device ABI");
_Static_assert(sizeof(State)==32888,"two bounded 32-sector lines");
_Static_assert(sizeof(State)==MOUNT_CACHE_BYTES,"actual DG State ABI");
extern ABI U mc_begin(State *,const Device *,Device *);
extern ABI void mc_finish(State *);
extern ABI U mc_profile(void);
extern ABI U mc_audit_bytes(void);
static const U IO_ERROR=UINT64_C(0x00420001),RANGE_ERROR=UINT64_C(0x00420002),INVALID=UINT64_C(0x05080010);
static struct {U low[4];State value;U high[4];} state_guard;
static Device source,adapter;
static State before_state;
static Device before_source,before_adapter;
static U clusters,reserved,fat_sectors,total,root;
static U calls,read_sectors,last_lba,last_count,writes,flushes,fail_lba;
static unsigned checks;
static const char *scenario="setup";
#define REQUIRE(x) do{++checks;if(!(x)){fprintf(stderr,"USB_CACHE_ASSERT case=%s line=%d check=%s; returned normally\n",scenario,__LINE__,#x);return 1;}}while(0)
ABI void __dong_panic(U code){fprintf(stderr,"unexpected panic=%llu\n",(unsigned long long)code);exit(99);}
static void put16(uint8_t *p,unsigned n,U v){p[n]=(uint8_t)v;p[n+1]=(uint8_t)(v>>8);}
static void put32(uint8_t *p,unsigned n,U v){for(unsigned i=0;i<4;i++)p[n+i]=(uint8_t)(v>>(8*i));}
static int all(const uint8_t *p,size_t n,uint8_t v){for(size_t i=0;i<n;i++)if(p[i]!=v)return 0;return 1;}
static uint8_t byte_at(U lba,unsigned offset){return (uint8_t)(lba*17+offset*3+11);}
static void sector(U lba,uint8_t *out){
 if(lba==0||lba==6){
  memset(out,0,512);out[0]=0xeb;out[1]=0x58;out[2]=0x90;memcpy(out+3,"CACHE   ",8);
  put16(out,11,512);out[13]=8;put16(out,14,reserved);out[16]=2;out[21]=0xf8;
  put32(out,32,total);put32(out,36,fat_sectors);put32(out,44,root);put16(out,48,1);put16(out,50,6);put16(out,510,0xaa55);return;
 }
 if(lba==1||lba==7){memset(out,0,512);put32(out,0,0x41615252);put32(out,484,0x61417272);put32(out,488,0xffffffff);put32(out,492,0xffffffff);put32(out,508,0xaa550000);return;}
 for(unsigned i=0;i<512;i++)out[i]=byte_at(lba,i);
}
static ABI U disk_read(U context,U lba,size_t count,uint8_t *out){
 ++calls;last_lba=lba;last_count=count;
 if(context!=0x42ca||!out||count==0||count>source.max_transfer||lba>=source.capacity||count>source.capacity-lba)return RANGE_ERROR;
 read_sectors+=count;
 if(fail_lba>=lba&&fail_lba-lba<count){memset(out,0xcc,count*512);return IO_ERROR;}
 for(size_t i=0;i<count;i++){sector(lba+i,out+i*512);}
 return 0;
}
static ABI U disk_write(U context,U lba,size_t count,const uint8_t *input){
 ++writes;return context==0x42ca&&lba<source.capacity&&count==1&&input?0:RANGE_ERROR;
}
static ABI U disk_flush(U context){++flushes;return context==0x42ca?0:RANGE_ERROR;}
static int guards(void){
 REQUIRE(all((const uint8_t *)state_guard.low,sizeof state_guard.low,0xa5));
 REQUIRE(all((const uint8_t *)state_guard.high,sizeof state_guard.high,0xa5));return 0;
}
static int cleared(void){
 State *s=&state_guard.value;
 REQUIRE(s->source==&source&&s->enabled==0&&s->phase==0&&s->recent==0);
 REQUIRE(s->first==0&&s->fat_sectors==0&&s->total==0&&s->backup==0&&s->fsinfo==0);
 REQUIRE(all((const uint8_t *)s->lines,sizeof s->lines,0));return guards();
}
static int fixture(U count,unsigned actual_h_geometry,U max_transfer){
 clusters=count;reserved=actual_h_geometry?3082:32;fat_sectors=actual_h_geometry?14843:(clusters+2+127)/128;
 total=actual_h_geometry?15231744:reserved+2*fat_sectors+clusters*8;root=2;
 calls=read_sectors=writes=flushes=last_lba=last_count=0;fail_lba=UINT64_MAX;
 source=(Device){0x42ca,total,max_transfer,disk_read,disk_write,disk_flush};
 memset(&state_guard,0xa5,sizeof state_guard);memset(&adapter,0xa5,sizeof adapter);
 REQUIRE(mc_begin(&state_guard.value,&source,&adapter)==0);
 REQUIRE(adapter.context==(U)(uintptr_t)&state_guard.value&&adapter.capacity==total&&adapter.max_transfer==max_transfer);
 REQUIRE(state_guard.value.enabled==1&&state_guard.value.phase==0&&state_guard.value.source==&source);
 REQUIRE(all((const uint8_t *)state_guard.value.lines,sizeof state_guard.value.lines,0));return guards();
}
static int read_sector(U lba){
 uint8_t out[578];memset(out,0xa5,sizeof out);uint8_t *payload=out+32;
 if(((uintptr_t)payload&7)==0)payload++;
 size_t prefix=(size_t)(payload-out);
 REQUIRE(((uintptr_t)payload&7)!=0);
 REQUIRE(adapter.read(adapter.context,lba,1,payload)==0);
 REQUIRE(all(out,prefix,0xa5)&&all(payload+512,sizeof out-prefix-512,0xa5));
 if(lba!=0&&lba!=6&&lba!=1&&lba!=7)for(unsigned i=0;i<512;i++)REQUIRE(payload[i]==byte_at(lba,i));
 return guards();
}
static int metadata(unsigned qualifies){
 if(read_sector(0)||read_sector(6)||read_sector(1)||read_sector(7))return 1;
 REQUIRE(calls==4&&read_sectors==4&&last_count==1);
 REQUIRE(state_guard.value.phase==(qualifies?4:255));return 0;
}
static int high_geometry(unsigned usb){
 scenario="actual 1899872-cluster H geometry eligibility without a physical disk";
 if(fixture(1899872,1,128)||metadata(usb))return 1;
 REQUIRE((total-reserved-2*fat_sectors)/8==clusters);
 if(read_sector(reserved))return 1;
 REQUIRE(calls==5&&last_lba==reserved&&last_count==(usb?32:1));
 if(read_sector(reserved+1))return 1;
 REQUIRE(calls==(usb?5:6));
 if(read_sector(reserved+fat_sectors))return 1;
 REQUIRE(calls==(usb?6:7)&&last_count==(usb?32:1));
 if(read_sector(reserved+fat_sectors+1))return 1;
 REQUIRE(calls==(usb?6:8));
 REQUIRE(writes==0&&flushes==0);
 mc_finish(&state_guard.value);return cleared();
}
static int small_cache(void){
 scenario="two independent FAT lines, hits, eviction, tail clipping and finish";
 if(fixture(70000,0,128)||metadata(1))return 1;
 U first=reserved,second=reserved+fat_sectors;
 if(read_sector(first)||read_sector(first+1)||read_sector(first+31))return 1;
 REQUIRE(calls==5&&last_lba==first&&last_count==32);
 if(read_sector(second)||read_sector(second+1)||read_sector(first))return 1;
 REQUIRE(calls==6&&state_guard.value.lines[0].valid==1&&state_guard.value.lines[1].valid==1);
 if(read_sector(first+64))return 1;REQUIRE(calls==7&&last_count==32);
 if(read_sector(second))return 1;REQUIRE(calls==8&&last_lba==second&&last_count==32);
 U tail=first+fat_sectors-1,expected_first=first+((fat_sectors-1)/32)*32;
 if(read_sector(tail))return 1;
 REQUIRE(calls==9&&last_lba==expected_first&&last_count==first+fat_sectors-expected_first);
 REQUIRE(last_lba+last_count==second);
 if(read_sector(tail))return 1;REQUIRE(calls==9);
 if(read_sector(second+fat_sectors))return 1;REQUIRE(calls==10&&last_count==1);
 mc_finish(&state_guard.value);if(cleared())return 1;
 if(read_sector(first))return 1;REQUIRE(calls==11&&last_count==1);
 REQUIRE(writes==0&&flushes==0);return cleared();
}
static int failure_and_bypass(void){
 uint8_t out[1088];State *s=&state_guard.value;U before;
 scenario="direct metadata I/O error is returned once and clears mount state";
 if(fixture(70000,0,128)||read_sector(0))return 1;
 fail_lba=6;memset(out,0xa5,sizeof out);
 REQUIRE(adapter.read(adapter.context,6,1,out+32)==IO_ERROR);
 REQUIRE(calls==2&&last_count==1&&all(out,32,0xa5)&&all(out+544,sizeof out-544,0xa5));
 if(cleared())return 1;
 scenario="failed prefetch preserves error, never retries or publishes partial bytes";
 if(fixture(70000,0,128)||metadata(1)||read_sector(reserved))return 1;
 fail_lba=reserved+fat_sectors+1;before=calls;memset(out,0xa5,sizeof out);
 REQUIRE(adapter.read(adapter.context,fail_lba,1,out+32)==IO_ERROR);
 REQUIRE(calls==before+1&&last_count==32&&all(out,sizeof out,0xa5));if(cleared())return 1;
 fail_lba=UINT64_MAX;if(read_sector(reserved))return 1;REQUIRE(calls==before+2&&last_count==1);
 scenario="out of capacity error stays direct and clears every cache byte";
 if(fixture(70000,0,128)||metadata(1)||read_sector(reserved))return 1;
 before=calls;memset(out,0xa5,sizeof out);
 REQUIRE(adapter.read(adapter.context,total,1,out+32)==RANGE_ERROR);
 REQUIRE(calls==before+1&&last_lba==total&&last_count==1&&all(out,sizeof out,0xa5));if(cleared())return 1;
 scenario="malformed read is passed through once and clears cache on error";
 if(fixture(70000,0,128)||metadata(1)||read_sector(reserved))return 1;
 before=calls;REQUIRE(adapter.read(adapter.context,reserved,1,NULL)==RANGE_ERROR);
 REQUIRE(calls==before+1);if(cleared())return 1;
 scenario="metadata order mismatch disables prefetch";
 if(fixture(70000,0,128)||read_sector(0)||read_sector(1)||read_sector(reserved))return 1;
 REQUIRE(s->phase==255&&calls==3&&last_count==1);
 scenario="source transfer bound prevents prefetch";
 if(fixture(70000,0,1)||metadata(1)||read_sector(reserved)||read_sector(reserved+1))return 1;
 REQUIRE(calls==6&&last_count==1&&s->lines[0].valid==0&&s->lines[1].valid==0);
 scenario="multi-sector caller request bypasses mount cache";
 if(fixture(70000,0,128)||metadata(1))return 1;
 memset(out,0xa5,sizeof out);REQUIRE(adapter.read(adapter.context,reserved,2,out+32)==0);
 REQUIRE(calls==5&&last_count==2&&s->phase==255&&all(out,32,0xa5)&&all(out+1056,32,0xa5));
 for(unsigned i=0;i<1024;i++)REQUIRE(out[32+i]==byte_at(reserved+i/512,i%512));
 scenario="write and flush finish mount-only caching before forwarding";
 if(fixture(70000,0,128)||metadata(1)||read_sector(reserved))return 1;
 REQUIRE(adapter.write(adapter.context,reserved,1,out)==0&&writes==1&&flushes==0);if(cleared())return 1;
 if(fixture(70000,0,128)||metadata(1)||read_sector(reserved))return 1;
 REQUIRE(adapter.flush(adapter.context)==0&&flushes==1&&writes==0);return cleared();
}
static int invalid_begin(State *s,const Device *d,Device *out){
 before_state=state_guard.value;before_source=source;before_adapter=adapter;
 REQUIRE(mc_begin(s,d,out)==INVALID);
 REQUIRE(!memcmp(&state_guard.value,&before_state,sizeof before_state));
 REQUIRE(!memcmp(&source,&before_source,sizeof before_source));
 REQUIRE(!memcmp(&adapter,&before_adapter,sizeof before_adapter));return guards();
}
static int cap_and_arguments(unsigned usb){
 U bytes=usb?2097152:32768;
 scenario="exact audit bitmap boundary still allows prefetch";
 if(fixture(bytes*8-2,0,128)||metadata(1)||read_sector(reserved))return 1;
 REQUIRE(calls==5&&last_lba==reserved&&last_count==32);
 if(read_sector(reserved+1))return 1;REQUIRE(calls==5);
 scenario="same audit bitmap cap rejects prefetch eligibility";
 if(fixture(bytes*8-1,0,128)||metadata(0)||read_sector(reserved))return 1;
 REQUIRE(calls==5&&last_count==1&&state_guard.value.lines[0].valid==0&&state_guard.value.lines[1].valid==0);
 scenario="invalid begin never installs an adapter";
 if(invalid_begin(NULL,&source,&adapter)||invalid_begin(&state_guard.value,NULL,&adapter)
  ||invalid_begin(&state_guard.value,&source,NULL)||invalid_begin(&state_guard.value,&source,&source))return 1;
 mc_finish(NULL);mc_finish(&state_guard.value);return cleared();
}
int main(int argc,char **argv){
 unsigned usb=argc==2&&!strcmp(argv[1],"usb");
 REQUIRE(mc_profile()==usb&&mc_audit_bytes()==(usb?2097152:32768));
 if(high_geometry(usb)||small_cache()||failure_and_bypass()||cap_and_arguments(usb))return 1;
 printf("USB_CACHE_NATIVE passed profile=%u checks=%u; actual H geometry sparse callbacks, no disk/VM; returned normally\n",usb,checks);return 0;
}
