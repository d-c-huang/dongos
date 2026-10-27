#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#if defined(_WIN32)
#define ABI __attribute__((sysv_abi))
#else
#define ABI
#endif
typedef uint64_t U;
extern U ABI services_write_bytes(const void *,U);
#ifndef LEGACY
extern U services_console_head,services_console_accepted,services_console_sent;
extern U services_console_dropped,services_console_disabled,services_console_last_lsr,services_console_timeouts;
extern unsigned char services_console_ring[4096];
#endif
static U reads,writes,clock_value,clock_step,budget=100,mode,delay,limit=UINT64_MAX;
static unsigned char transmitted[16384];
static unsigned checks;
#define C(x) do{checks++;if(!(x)){fprintf(stderr,"CONSOLE_ASSERT line %d: %s\n",__LINE__,#x);exit(1);}}while(0)
U ABI dong_services_log_budget(void){return budget;}
U ABI console_in(U port){C(port==0x3fd);reads++;if(mode==1)return 0;if(mode==2)return 255;if(delay){delay--;return 0;}return writes>=limit?0:0x60;}
void ABI console_out(U port,U value){C(port==0x3f8&&value<256&&writes<sizeof transmitted);transmitted[writes++]=(unsigned char)value;}
U ABI console_clock(void){U now=clock_value;clock_value+=clock_step;return now;}
void console_scenario(U which){mode=which;reads=writes=0;clock_value=0;clock_step=10;budget=100;delay=0;limit=UINT64_MAX;}
#ifndef INTEGRATED_INIT
#ifndef LEGACY
static void reset(U which){console_scenario(which);services_console_head=services_console_accepted=services_console_sent=0;services_console_dropped=services_console_disabled=services_console_last_lsr=services_console_timeouts=0;memset(services_console_ring,0xcc,4096);}
static void ring(const unsigned char *all,size_t n){C(services_console_accepted==n&&services_console_head==(n&4095));size_t first=n>4096?n-4096:0;for(size_t i=first;i<n;i++)C(services_console_ring[i&4095]==all[i]);}
#endif
int main(void){
 unsigned char bytes[8192];for(unsigned i=0;i<sizeof bytes;i++)bytes[i]=(unsigned char)(i*37+11);
#ifdef LEGACY
 console_scenario(1);C(services_write_bytes(bytes,32)==0x050b0004);C(reads==0x100000&&writes==0);
 printf("LEGACY_UART_BLOCKS_INIT reads=%lu status=050b0004\n",(unsigned long)reads);
#else
 reset(0);C(!services_write_bytes(NULL,0));C(!reads&&!writes&&!services_console_accepted);
 C(!services_write_bytes(bytes,4096));C(writes==4096&&reads==4096&&!memcmp(transmitted,bytes,4096));ring(bytes,4096);C(!services_console_disabled&&!services_console_dropped);
 C(!services_write_bytes(bytes+4096,4096));ring(bytes,8192);C(writes==8192&&services_console_sent==8192);
 reset(1);C(!services_write_bytes(bytes,32));ring(bytes,32);C(reads==10&&!writes&&services_console_disabled==1&&services_console_timeouts==1&&services_console_dropped==32);
 C(!services_write_bytes(bytes+32,16));ring(bytes,48);C(reads==10&&services_console_dropped==48);
 reset(2);C(!services_write_bytes(bytes,32));ring(bytes,32);C(reads==1&&!writes&&services_console_disabled==1&&!services_console_timeouts&&services_console_last_lsr==255);
 reset(0);delay=3;C(!services_write_bytes(bytes,32));C(reads==35&&writes==32&&!services_console_disabled&&!memcmp(bytes,transmitted,32));
 reset(1);clock_step=0;C(!services_write_bytes(bytes,32));C(reads==65536&&services_console_timeouts==1&&services_console_dropped==32);
 reset(1);clock_value=UINT64_MAX-25;C(!services_write_bytes(bytes,32));C(reads==10&&services_console_timeouts==1);
 reset(0);limit=4;C(!services_write_bytes(bytes,32));C(writes==4&&reads==14&&services_console_sent==4&&services_console_dropped==28);ring(bytes,32);
 reset(0);budget=0;C(!services_write_bytes(bytes,32));C(!reads&&!writes&&services_console_disabled==1);ring(bytes,32);
 printf("SERVICES_CONSOLE_OK checks=%u ring=4096 optional_uart bounded_clock_and_polls\n",checks);
#endif
 return 0;
}
#endif
