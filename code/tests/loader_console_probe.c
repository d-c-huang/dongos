/* Independent native Microsoft x64 ABI oracle. No firmware or port I/O. */
#ifndef _WIN32
#define _GNU_SOURCE
#endif
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#include <windows.h>
#else
#include <sys/mman.h>
#include <unistd.h>
#endif

#define EFI __attribute__((ms_abi))
typedef uint64_t U;
typedef struct Console Console;
typedef U EFI Output(Console *, const uint16_t *);
struct Console { void *reset; Output *output; };
typedef struct { unsigned char before_console[64]; Console *console; } Table;
_Static_assert(offsetof(Table,console)==64,"independent EFI_SYSTEM_TABLE.ConOut");
_Static_assert(offsetof(Console,output)==8,"independent EFI OutputString");

extern void EFI loader_console_initialize(const Table *);
extern void EFI loader_console_write(const char *);
extern void EFI loader_console_seal(void);
extern void EFI probe_diagnostic_write(const char *);
extern U EFI probe_invoke(void *,const void *);
extern U EFI probe_output_string(Console *,const uint16_t *);
U probe_callback_rsp_mod,probe_serial_calls,probe_serial_pointer;

static Console console={NULL,probe_output_string};
static Table table={{0},&console};
static unsigned expected_calls,actual_calls;
static uint16_t expected[128];
static size_t expected_length;
static U callback_result;
static int callback_bad;
static unsigned checks;
static const char *where="setup";
#define REQUIRE(x) do { ++checks; if(!(x)){fprintf(stderr,"loader console oracle case=%s check=%s line=%d; returned normally\n",where,#x,__LINE__);return 1;} } while(0)

U EFI loader_console_probe_output(Console *self,const uint16_t *message) {
    ++actual_calls;
    if(self!=&console||!message||probe_callback_rsp_mod!=8){callback_bad=1;return callback_result;}
    for(size_t i=0;i<expected_length;i++) {
        if(message[i]!=expected[i]){callback_bad=1;}
    }
    if(message[expected_length]!=0){callback_bad=1;}
    return callback_result;
}

static void expect(const char *bytes,size_t length) {
    expected_length=length>127?127:length;
    memset(expected,0,sizeof(expected));
    for(size_t i=0;i<expected_length;i++){expected[i]=(unsigned char)bytes[i];}
    expected_calls=actual_calls+1;
}
static void expect_screen(const char *bytes,size_t length) {
    char prefixed[128];
    size_t copied=length>119?119:length;
    memcpy(prefixed,"SCREEN: ",8);
    memcpy(prefixed+8,bytes,copied);
    prefixed[8+copied]=0;
    expect(prefixed,8+copied);
}
static int invoke(void *function,const void *argument) {
    REQUIRE(probe_invoke(function,argument)==0);
    return 0;
}
static int delivered(void) {
    REQUIRE(actual_calls==expected_calls);
    REQUIRE(callback_bad==0);
    REQUIRE(probe_callback_rsp_mod==8);
    return 0;
}
static int no_call(const char *message) {
    unsigned before=actual_calls;
    REQUIRE(invoke((void *)loader_console_write,message)==0);
    REQUIRE(actual_calls==before);
    return 0;
}

static int guarded_limit(size_t limit,int mirror) {
    size_t page;
    unsigned char *memory;
#ifdef _WIN32
    SYSTEM_INFO info;GetSystemInfo(&info);page=info.dwPageSize;
    memory=VirtualAlloc(NULL,page*2,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
    REQUIRE(memory!=NULL);
    DWORD prior;
    REQUIRE(VirtualProtect(memory+page,page,PAGE_NOACCESS,&prior)!=0);
#else
    page=(size_t)sysconf(_SC_PAGESIZE);
    memory=mmap(NULL,page*2,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
    REQUIRE(memory!=MAP_FAILED);
    REQUIRE(mprotect(memory+page,page,PROT_NONE)==0);
#endif
    char *message=(char *)memory+page-limit;
    memset(message,'Z',limit);
    if(mirror){expect_screen(message,limit);}else{expect(message,limit);}
    U before=probe_serial_calls;
    REQUIRE(invoke(mirror?(void *)probe_diagnostic_write:(void *)loader_console_write,message)==0);
    REQUIRE(delivered()==0);
    if(mirror) {
        REQUIRE(probe_serial_calls==before+1);
        REQUIRE(probe_serial_pointer==(U)(uintptr_t)message);
    }
#ifdef _WIN32
    REQUIRE(VirtualFree(memory,0,MEM_RELEASE)!=0);
#else
    REQUIRE(munmap(memory,page*2)==0);
#endif
    return 0;
}

int main(void) {
    const char *invalid=(const char *)(uintptr_t)1;
    where="uninitialized-invalid-message";
    REQUIRE(no_call(invalid)==0);
    where="null-table";
    REQUIRE(invoke((void *)loader_console_initialize,NULL)==0);
    REQUIRE(no_call(invalid)==0);
    where="null-console";
    table.console=NULL;
    REQUIRE(invoke((void *)loader_console_initialize,&table)==0);
    REQUIRE(no_call(invalid)==0);
    where="null-method";
    table.console=&console;console.output=NULL;
    REQUIRE(invoke((void *)loader_console_initialize,&table)==0);
    REQUIRE(no_call(invalid)==0);
    console.output=probe_output_string;
    REQUIRE(invoke((void *)loader_console_initialize,&table)==0);
    where="null-message";REQUIRE(no_call(NULL)==0);
    where="empty-message";REQUIRE(no_call("")==0);

    const char *messages[]={"A","DongOS S00 EFI entry\r\n","0123456789 ABC xyz!"};
    for(size_t i=0;i<sizeof(messages)/sizeof(messages[0]);i++) {
        where="ascii-crlf";expect(messages[i],strlen(messages[i]));
        REQUIRE(invoke((void *)loader_console_write,messages[i])==0);
        REQUIRE(delivered()==0);
    }
    for(size_t length=1;length<=127;length++) {
        char message[128];
        for(size_t i=0;i<length;i++){message[i]=(char)(1+(i%126));}
        message[length]=0;where="all-bounded-lengths";expect(message,length);
        REQUIRE(invoke((void *)loader_console_write,message)==0);
        REQUIRE(delivered()==0);
    }
    char long_message[1024];memset(long_message,'L',sizeof(long_message));long_message[1023]=0;
    where="long-message-truncation";expect(long_message,1023);
    REQUIRE(invoke((void *)loader_console_write,long_message)==0);
    REQUIRE(delivered()==0);
    where="guarded-127-no-extra-read";REQUIRE(guarded_limit(127,0)==0);

    where="callback-error-is-best-effort";
    callback_result=UINT64_C(0x8000000000000007);
    expect("error callback",14);
    REQUIRE(invoke((void *)loader_console_write,"error callback")==0);
    REQUIRE(delivered()==0);
    callback_result=0;expect("after error",11);
    REQUIRE(invoke((void *)loader_console_write,"after error")==0);
    REQUIRE(delivered()==0);

    where="actual-diagnostic-mirror-preserves-message";
    const char *mirror="volatile callback clobbers RCX R8 R9\r\n";
    expect_screen(mirror,strlen(mirror));U serial_before=probe_serial_calls;
    REQUIRE(invoke((void *)probe_diagnostic_write,mirror)==0);
    REQUIRE(delivered()==0);
    REQUIRE(probe_serial_calls==serial_before+1);
    REQUIRE(probe_serial_pointer==(U)(uintptr_t)mirror);
    const size_t mirror_lengths[]={0,1,118,119,120,1023};
    for(size_t i=0;i<sizeof(mirror_lengths)/sizeof(mirror_lengths[0]);i++) {
        char message[1024];size_t length=mirror_lengths[i];
        memset(message,'M',length);message[length]=0;
        where="screen-prefix-and-source119-truncation";
        expect_screen(message,length);serial_before=probe_serial_calls;
        REQUIRE(invoke((void *)probe_diagnostic_write,message)==0);
        REQUIRE(delivered()==0);
        REQUIRE(probe_serial_calls==serial_before+1);
        REQUIRE(probe_serial_pointer==(U)(uintptr_t)message);
    }
    where="guarded-wrapper119-no-extra-read";
    REQUIRE(guarded_limit(119,1)==0);

    where="sealed-invalid-message-and-table";
    REQUIRE(invoke((void *)loader_console_seal,NULL)==0);
    /* Detect a missing seal normally before exercising invalid addresses. */
    REQUIRE(no_call("after first EBS attempt")==0);
    table.console=(Console *)(uintptr_t)1;
    REQUIRE(no_call(invalid)==0);
    REQUIRE(invoke((void *)loader_console_seal,NULL)==0);
    REQUIRE(no_call(invalid)==0);
    where="sealed-diagnostic-still-serial-only";
    serial_before=probe_serial_calls;
    REQUIRE(invoke((void *)probe_diagnostic_write,mirror)==0);
    REQUIRE(probe_serial_calls==serial_before+1);
    REQUIRE(probe_serial_pointer==(U)(uintptr_t)mirror);
    REQUIRE(actual_calls==expected_calls);

    where="new-initialization";
    table.console=&console;
    REQUIRE(invoke((void *)loader_console_initialize,&table)==0);
    expect("new boot",8);
    REQUIRE(invoke((void *)loader_console_write,"new boot")==0);
    REQUIRE(delivered()==0);
    printf("loader console oracle passed; checks=%u callbacks=%u; ABI GPR/XMM, shadow, guard, seal verified; returned normally\n",checks,actual_calls);
    return 0;
}
