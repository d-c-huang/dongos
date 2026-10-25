/* Sparse independent FAT32 disk model: high cluster IDs, no multi-GB image. */
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define ABI __attribute__((sysv_abi))
typedef uint64_t U;
typedef struct {U context,capacity,max_transfer;U(ABI*read)(U,U,size_t,uint8_t*);U(ABI*write)(U,U,size_t,const uint8_t*);U(ABI*flush)(U);} Device;
typedef struct {const Device *device;U ready,busy,failed,read_only,dirty,total,spc,reserved,fat_sectors,data_start,clusters,root,fsinfo,backup;} Volume;
typedef struct {uint8_t name[11],attributes;U cluster,size,sector,offset;} DirEntry;
_Static_assert(sizeof(Device)==48,"independent Device ABI");
_Static_assert(sizeof(Volume)==120,"independent Volume ABI");
_Static_assert(sizeof(DirEntry)==48,"independent DirEntry ABI");
extern ABI void fp_reset(Volume *);
extern ABI U fp_mount(Volume *,const Device *,void *);
extern ABI U fp_list(Volume *,void *,U,DirEntry *,U *);
extern ABI U fp_read(Volume *,void *,const uint8_t *,size_t,U,uint8_t *,size_t,U *);
static const U UNSUPPORTED=UINT64_C(0x05040003),CORRUPT=UINT64_C(0x05040005);
static struct {U low[4];Volume value;U high[4];} guarded_volume;
static uint8_t *scratch_allocation,*scratch;
static U clusters,root_cluster,fat_sectors,total,data_start;
static U reads,writes,flushes,bad_io;
static unsigned checks;
static const char *scenario="setup";
enum {VALID,CROSS,MIRROR,ORPHAN,CYCLE,STALE_HINTS,BACKUP_FREE_OOB,
 BACKUP_NEXT_LOW,BACKUP_NEXT_HIGH,PRIMARY_FREE_OOB,PRIMARY_NEXT_LOW,
 PRIMARY_NEXT_HIGH,BACKUP_OTHER_BYTE,SHARED_RESERVED_BYTE,INVALID_START_BOUNDARY,
 INVALID_START_MAX,MULTI_CYCLE,TAIL_CROSS,SIZE_TOO_BIG};
static unsigned kind;
static unsigned backup_changed_byte;
static FILE *readonly_file;
#define REQUIRE(x) do {++checks;if(!(x)){fprintf(stderr,"USB_FAT_ASSERT case=%s line=%d check=%s; returned normally\n",scenario,__LINE__,#x);return 1;}} while(0)
ABI void __dong_panic(U code){fprintf(stderr,"unexpected panic=%llu\n",(unsigned long long)code);exit(99);}
static void put16(uint8_t *p,unsigned at,U value){p[at]=(uint8_t)value;p[at+1]=(uint8_t)(value>>8);}
static void put32(uint8_t *p,unsigned at,U value){for(unsigned i=0;i<4;i++)p[at+i]=(uint8_t)(value>>(8*i));}
static U get16(const uint8_t *p,unsigned at){return (U)p[at]|((U)p[at+1]<<8);}
static U get32(const uint8_t *p,unsigned at){return get16(p,at)|(get16(p,at+2)<<16);}
static U fat(U c){
 if(c==0)return 0x0ffffff8;
 if(c==1)return 0x0fffffff;
 if(c==root_cluster)return 0x0fffffff;
 if(c==root_cluster+1){
  if(kind==INVALID_START_BOUNDARY||kind==INVALID_START_MAX)return 0;
  if(kind==MULTI_CYCLE||kind==TAIL_CROSS)return root_cluster+3;
  return kind==CYCLE?c:0x0fffffff;
 }
 if(c==root_cluster+2)return kind==CROSS?0:kind==TAIL_CROSS?root_cluster+3:0x0fffffff;
 if(c==root_cluster+3){if(kind==MULTI_CYCLE)return root_cluster+1;if(kind==TAIL_CROSS)return 0x0fffffff;}
 if(c==root_cluster+9&&kind==ORPHAN)return 0x0fffffff;
 return 0;
}
static void boot(uint8_t *out){
 memset(out,0,512);out[0]=0xeb;out[1]=0x58;out[2]=0x90;memcpy(out+3,"USBTEST ",8);
 put16(out,11,512);out[13]=8;put16(out,14,32);out[16]=2;out[21]=0xf8;
 put32(out,32,total);put32(out,36,fat_sectors);put32(out,44,root_cluster);put16(out,48,1);put16(out,50,6);
 out[64]=0x80;out[66]=0x29;memcpy(out+82,"FAT32   ",8);put16(out,510,0xaa55);
}
static void entry(uint8_t *out,unsigned offset,const char *name,U cluster){
 memcpy(out+offset,name,11);out[offset+11]=0x20;put16(out,offset+20,cluster>>16);
 put16(out,offset+26,cluster);put32(out,offset+28,512);
}
static void sector(U lba,uint8_t *out){
 memset(out,0,512);
 if(lba==0||lba==6){boot(out);return;}
 if(lba==1||lba==7){
  put32(out,0,0x41615252);put32(out,484,0x61417272);put32(out,488,0xffffffff);put32(out,492,0xffffffff);put32(out,508,0xaa550000);
  if(kind==STALE_HINTS){put32(out,488,lba==1?clusters-3:0xffffffff);put32(out,492,lba==1?168:2);}
  if(kind==SHARED_RESERVED_BYTE)out[backup_changed_byte]^=1;
  if(lba==7){
   if(kind==BACKUP_FREE_OOB)put32(out,488,clusters+1);
   if(kind==BACKUP_NEXT_LOW)put32(out,492,1);
   if(kind==BACKUP_NEXT_HIGH)put32(out,492,clusters+2);
   if(kind==BACKUP_OTHER_BYTE)out[backup_changed_byte]^=1;
  }
  if(lba==1){
   if(kind==PRIMARY_FREE_OOB)put32(out,488,clusters+1);
   if(kind==PRIMARY_NEXT_LOW)put32(out,492,1);
   if(kind==PRIMARY_NEXT_HIGH)put32(out,492,clusters+2);
  }
  return;
 }
 if(lba>=32&&lba<32+2*fat_sectors){
  U relative=lba-32,copy=relative/fat_sectors,index=relative%fat_sectors;
  for(unsigned i=0;i<128;i++)put32(out,i*4,fat(index*128+i));
  if(kind==MIRROR&&copy==1&&index==(root_cluster+2)/128)out[((root_cluster+2)%128)*4]^=1;
  return;
 }
 U root_lba=data_start+(root_cluster-2)*8;
 if(lba==root_lba){
  U one=kind==INVALID_START_BOUNDARY?clusters+2:kind==INVALID_START_MAX?0xffffffff:root_cluster+1;
  entry(out,0,"ONE     BIN",one);entry(out,32,"TWO     BIN",root_cluster+(kind==CROSS?1:2));
  if(kind==SIZE_TOO_BIG)put32(out,28,4097);
  return;
 }
 if(lba==root_lba+8){for(unsigned i=0;i<512;i++)out[i]=(uint8_t)(i*13+7);return;}
 if(lba==root_lba+16){for(unsigned i=0;i<512;i++)out[i]=(uint8_t)(i*17+11);return;}
}
static ABI U disk_read(U context,U lba,size_t count,uint8_t *out){
 ++reads;if(context!=0x51a7||!out||count!=1||lba>=total){++bad_io;return 1;}sector(lba,out);return 0;
}
static ABI U disk_write(U context,U lba,size_t count,const uint8_t *in){
 (void)context;(void)lba;(void)count;(void)in;++writes;return 0;
}
static ABI U disk_flush(U context){(void)context;++flushes;return 0;}
static int all(const uint8_t *p,size_t n,uint8_t expected){for(size_t i=0;i<n;i++)if(p[i]!=expected)return 0;return 1;}
static int guards(void){
 REQUIRE(all((const uint8_t *)guarded_volume.low,sizeof guarded_volume.low,0xa5));
 REQUIRE(all((const uint8_t *)guarded_volume.high,sizeof guarded_volume.high,0xa5));
 REQUIRE(all(scratch_allocation,32,0xa5));REQUIRE(all(scratch+FAT32_SCRATCH_BYTES,32,0xa5));
 REQUIRE(writes==0&&flushes==0&&bad_io==0);return 0;
}
static void fixture(U cluster_count,unsigned corruption){
 kind=corruption;clusters=cluster_count;root_cluster=clusters>1500010?1500000:65536;
 fat_sectors=(clusters+2+127)/128;data_start=32+2*fat_sectors;total=data_start+clusters*8;
 reads=writes=flushes=bad_io=0;
 memset(&guarded_volume,0xa5,sizeof guarded_volume);fp_reset(&guarded_volume.value);
 memset(scratch_allocation,0xa5,FAT32_SCRATCH_BYTES+64);
}
static int rejected(U cluster_count,unsigned corruption,U expected,unsigned first_read_only){
 fixture(cluster_count,corruption);
 Device d={0x51a7,total,1,disk_read,disk_write,disk_flush};
 REQUIRE(fp_mount(&guarded_volume.value,&d,scratch)==expected);
 REQUIRE(guarded_volume.value.ready==0&&guarded_volume.value.busy==0);
 REQUIRE(all((const uint8_t *)&guarded_volume.value,sizeof guarded_volume.value,0));
 if(first_read_only)REQUIRE(reads==1);
 return guards();
}
static int clean_mount(U cluster_count,unsigned corruption){
 fixture(cluster_count,corruption);
 Device d={0x51a7,total,1,disk_read,disk_write,disk_flush};Volume *v=&guarded_volume.value;
 REQUIRE(fp_mount(v,&d,scratch)==0);
 REQUIRE(v->ready==1&&v->busy==0&&v->read_only==0&&v->dirty==0);
 REQUIRE(v->clusters==cluster_count&&v->root==root_cluster&&v->spc==8&&v->total==total);
 return guards();
}
/* This optional mode never opens a writable stream. The callbacks exposed to
   the real filesystem reject write/flush requests without touching the file. */
static ABI U readonly_read(U context,U lba,size_t count,uint8_t *out){
 ++reads;
 if(context!=(U)(uintptr_t)readonly_file||!out||count!=1||lba>=total){++bad_io;return 1;}
#ifdef _WIN32
 if(_fseeki64(readonly_file,(long long)(lba*512),SEEK_SET)!=0)return 1;
#else
 if(fseek(readonly_file,(long)(lba*512),SEEK_SET)!=0)return 1;
#endif
 return fread(out,1,512,readonly_file)==512?0:1;
}
static ABI U readonly_write(U context,U lba,size_t count,const uint8_t *in){
 (void)context;(void)lba;(void)count;(void)in;++writes;return 1;
}
static ABI U readonly_flush(U context){(void)context;++flushes;return 1;}
static int readonly_volume(const char *path,size_t supplied_scratch){
 uint8_t vbr[512];
 scenario="read-only volume mount";
 REQUIRE(supplied_scratch==FAT32_SCRATCH_BYTES);
 readonly_file=fopen(path,"rb");
 if(!readonly_file){perror("read-only volume open");return 2;}
 setvbuf(readonly_file,NULL,_IONBF,0);
 if(fread(vbr,1,sizeof vbr,readonly_file)!=sizeof vbr){perror("read-only VBR read");fclose(readonly_file);readonly_file=NULL;return 2;}
 if(get16(vbr,510)!=0xaa55||get16(vbr,11)!=512||get32(vbr,32)<65536){
  fprintf(stderr,"invalid read-only FAT32 VBR geometry\n");fclose(readonly_file);readonly_file=NULL;return 2;
 }
 total=get32(vbr,32);reads=1;writes=flushes=bad_io=0;
 scratch_allocation=calloc(1,FAT32_SCRATCH_BYTES+64);
 if(!scratch_allocation){fclose(readonly_file);readonly_file=NULL;return 2;}
 scratch=scratch_allocation+32;memset(scratch_allocation,0xa5,FAT32_SCRATCH_BYTES+64);
 memset(&guarded_volume,0xa5,sizeof guarded_volume);fp_reset(&guarded_volume.value);
 Device d={(U)(uintptr_t)readonly_file,total,1,readonly_read,readonly_write,readonly_flush};
 U result=fp_mount(&guarded_volume.value,&d,scratch);Volume *v=&guarded_volume.value;
 U spc=vbr[13],reserved=get16(vbr,14),fat_count=vbr[16],fat_size=get32(vbr,36);
 U first=reserved+fat_count*fat_size;
 U bpb_clusters=spc&&first<total?(total-first)/spc:0;
 printf("USB_FAT_READONLY mount_error=0x%016llx ready=%llu readonly=%llu dirty=%llu clusters=%llu bpb_clusters=%llu reads=%llu writes=%llu flushes=%llu bad_io=%llu scratch_bytes=%llu\n",
  (unsigned long long)result,(unsigned long long)v->ready,(unsigned long long)v->read_only,
  (unsigned long long)v->dirty,(unsigned long long)v->clusters,(unsigned long long)bpb_clusters,
  (unsigned long long)reads,(unsigned long long)writes,(unsigned long long)flushes,
  (unsigned long long)bad_io,(unsigned long long)supplied_scratch);
 int guarded=guards();
 fclose(readonly_file);readonly_file=NULL;free(scratch_allocation);scratch_allocation=scratch=NULL;
 if(guarded)return guarded;
 puts("USB_FAT_READONLY canaries=1 stream_mode=rb; mount result reported without repair; returned normally");
 return 0;
}
int main(int argc,char **argv){
 if(argc>=2&&!strcmp(argv[1],"--readonly-volume")){
  if(argc!=4){fprintf(stderr,"usage: --readonly-volume <path> <scratch_size>\n");return 2;}
  char *end=NULL;unsigned long long size=strtoull(argv[3],&end,10);
  if(!end||*end||size!=FAT32_SCRATCH_BYTES){fprintf(stderr,"read-only mode Scratch size does not match this actual compiled profile\n");return 2;}
  return readonly_volume(argv[2],(size_t)size);
 }
 unsigned usb=argc==2&&!strcmp(argv[1],"usb");
 size_t audit_bytes=usb?2097152u:32768u;
 REQUIRE(FAT32_SCRATCH_BYTES==audit_bytes+6888u);
 REQUIRE(FAT32_SEEN_OFFSET==1067u);
 scratch_allocation=calloc(1,FAT32_SCRATCH_BYTES+64);REQUIRE(scratch_allocation!=NULL);scratch=scratch_allocation+32;
 if(!usb){
  scenario="default keeps large-volume cap";
  if(rejected(2000000,VALID,UNSUPPORTED,1))return 1;
  scenario="default clean small-volume baseline";
  if(clean_mount(70000,VALID))return 1;
  scenario="default keeps strict FSInfo hints on an otherwise valid small volume";
  if(rejected(70000,STALE_HINTS,CORRUPT,0))return 1;
  scenario="default preserves matching reserved-byte behavior";backup_changed_byte=4;
  if(clean_mount(70000,SHARED_RESERVED_BYTE))return 1;
 }else{
  scenario="actual high-cluster clean volume";fixture(2000000,VALID);
  Device d={0x51a7,total,1,disk_read,disk_write,disk_flush};Volume *v=&guarded_volume.value;
  REQUIRE(fp_mount(v,&d,scratch)==0);REQUIRE(v->ready==1&&v->busy==0&&v->read_only==0&&v->dirty==0);
  REQUIRE(v->clusters==2000000&&v->root==1500000&&v->spc==8&&v->total==total);
  REQUIRE((scratch[FAT32_SEEN_OFFSET+root_cluster/8]&7)==7);
  for(U index=0;index<2;index++){
   DirEntry item;U present=99;REQUIRE(fp_list(v,scratch,index,&item,&present)==0&&present==1);
   REQUIRE(!memcmp(item.name,index?"TWO     BIN":"ONE     BIN",11));REQUIRE(item.cluster==root_cluster+index+1&&item.size==512);
   uint8_t buffer[576];memset(buffer,0xa5,sizeof buffer);U got=99;
   const uint8_t *name=(const uint8_t *)(index?"TWO.BIN":"ONE.BIN");
   REQUIRE(fp_read(v,scratch,name,7,0,buffer+32,512,&got)==0&&got==512);
   for(unsigned i=0;i<512;i++)REQUIRE(buffer[i+32]==(uint8_t)(i*(index?17:13)+(index?11:7)));
   REQUIRE(all(buffer,32,0xa5)&&all(buffer+544,32,0xa5));
  }
  if(guards())return 1;
  scenario="high-cluster shared chain";if(rejected(2000000,CROSS,CORRUPT,0))return 1;
  scenario="high-cluster mirror mismatch";if(rejected(2000000,MIRROR,CORRUPT,0))return 1;
  scenario="high-cluster orphan";if(rejected(2000000,ORPHAN,CORRUPT,0))return 1;
  scenario="high-cluster cycle";if(rejected(2000000,CYCLE,CORRUPT,0))return 1;
  scenario="USB first cluster equals clusters+2 is rejected before bitmap access";
  if(rejected(2000000,INVALID_START_BOUNDARY,CORRUPT,0))return 1;
  scenario="USB first cluster 0xffffffff is rejected before bitmap access";
  if(rejected(2000000,INVALID_START_MAX,CORRUPT,0))return 1;
  scenario="USB multi-node cycle is rejected by serialized seen bitmap";
  if(rejected(2000000,MULTI_CYCLE,CORRUPT,0))return 1;
  scenario="USB distinct file chains converge at a shared tail";
  if(rejected(2000000,TAIL_CROSS,CORRUPT,0))return 1;
  scenario="USB file size exceeds its actual cluster chain";
  if(rejected(2000000,SIZE_TOO_BIG,CORRUPT,0))return 1;
  scenario="high-cluster valid independent stale FSInfo hints";
  if(clean_mount(2000000,STALE_HINTS))return 1;
  scenario="backup free hint exceeds cluster count";
  if(rejected(2000000,BACKUP_FREE_OOB,CORRUPT,0))return 1;
  scenario="backup next hint below first data cluster";
  if(rejected(2000000,BACKUP_NEXT_LOW,CORRUPT,0))return 1;
  scenario="backup next hint above last data cluster";
  if(rejected(2000000,BACKUP_NEXT_HIGH,CORRUPT,0))return 1;
  scenario="primary free hint exceeds cluster count";
  if(rejected(2000000,PRIMARY_FREE_OOB,CORRUPT,0))return 1;
  scenario="primary next hint below first data cluster";
  if(rejected(2000000,PRIMARY_NEXT_LOW,CORRUPT,0))return 1;
  scenario="primary next hint above last data cluster";
  if(rejected(2000000,PRIMARY_NEXT_HIGH,CORRUPT,0))return 1;
  scenario="USB reserved FSInfo bytes must be zero even when both copies agree";
  for(backup_changed_byte=4;backup_changed_byte<508;backup_changed_byte++){
   if(backup_changed_byte>=484&&backup_changed_byte<496)continue;
   if(rejected(2000000,SHARED_RESERVED_BYTE,CORRUPT,0))return 1;
  }
 }
 scenario="every backup FSInfo byte outside the two hints remains strict";
 for(backup_changed_byte=0;backup_changed_byte<512;backup_changed_byte++){
  if(backup_changed_byte>=488&&backup_changed_byte<496)continue;
  if(rejected(usb?2000000:70000,BACKUP_OTHER_BYTE,CORRUPT,0))return 1;
 }
 scenario="bitmap cap before FAT or directory reads";
 if(rejected((U)audit_bytes*8-1,VALID,UNSUPPORTED,1))return 1;
 free(scratch_allocation);
 printf("USB_FAT_NATIVE passed profile=%u checks=%u; sparse 2000000 clusters, no host disk writes; returned normally\n",usb,checks);
 return 0;
}
