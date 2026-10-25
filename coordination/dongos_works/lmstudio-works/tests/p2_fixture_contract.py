import re
INPUTS=[('aligned-byte',0x100000,1),('aligned-page',0x100000,4096),('edge-exact',0x100001,4095),('cross-page',0x100fff,2),('unaligned-two-pages',0x12345001,8192),('maximum-aligned',0x100000,0x1000000),('maximum-unaligned',0x100001,0x1000000),('physical-limit-exact',0xffffffffff00,256),('physical-limit-overflow',0xffffffffff00,257),('zero-size',0x100000,0),('size-too-large',0x100000,0x1000001),('below-one-mib',0xfffff,1)]
def hexvalue(value):
    assert isinstance(value,str) and re.fullmatch(r'0x[0-9a-fA-F]+',value)
    return int(value,16)
def validate_rounding(data):
    assert set(data)=={'schema','cases'} and type(data['schema']) is int and data['schema']==1
    assert len(data['cases'])==len(INPUTS)
    seen=set()
    for row,(name,base,size) in zip(data['cases'],INPUTS):
        assert set(row)=={'id','base','size','valid','physical','bytes'}
        assert row['id']==name and name not in seen;seen.add(name)
        assert hexvalue(row['base'])==base and hexvalue(row['size'])==size
        valid=0x100000<=base<2**48 and 0<size<=2**24 and base+size<=2**48
        assert type(row['valid']) is bool and row['valid']==valid
        if valid:
            first=(base//4096)*4096;last=((base+size+4095)//4096)*4096
            assert hexvalue(row['physical'])==first and hexvalue(row['bytes'])==last-first
        else:assert row['physical'] is None and row['bytes'] is None
    return True
def validate_errors(data,source):
    constants=dict((name,int(value.replace('_',''),16)) for name,value in re.findall(r'pub error (\w+)=(0x[0-9a-fA-F_]+);',source))
    assert len(constants)==8
    assert set(data)=={'schema','module','errors'} and data['schema']==1 and data['module']=='mm.runtime_cache'
    assert len(data['errors'])==8
    seen=set()
    for row in data['errors']:
        assert set(row)=={'name','code','meaning'} and row['name'] in constants and row['name'] not in seen
        seen.add(row['name']);assert hexvalue(row['code'])==constants[row['name']]
        assert isinstance(row['meaning'],str) and len(row['meaning'].strip())>=4
    assert seen==set(constants)
    return True
