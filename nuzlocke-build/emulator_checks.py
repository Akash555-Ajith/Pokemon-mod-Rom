"""Run the compiled ROM's functions in mGBA, using a disposable diagnostic ROM copy.

The distributed ROM is never modified. A tiny Thumb call stub is appended only
to the in-memory test copy, so checks execute the actual compiled GBA code.
"""
import ctypes as C
import glob
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
from PIL import Image

root = Path(sys.argv[1])
output = Path(sys.argv[2])
output.mkdir(exist_ok=True)
symbols = {}
for line in subprocess.check_output(['arm-none-eabi-nm', '-n', str(root/'pokeemerald.elf')], text=True).splitlines():
    fields = line.split()
    if len(fields) == 3:
        symbols[fields[2]] = int(fields[0], 16)

control = symbols['gDecompressionBuffer'] + 0x3000
stub_source = f'''.syntax unified
.cpu arm7tdmi
.thumb
.global probe, noop
probe:
 push {{r4-r6,lr}}
 sub sp, #16
 ldr r5, control
 ldr r6, [r5, #32]
 ldr r4, [r5, #36]
 str r4, [r6]
 ldr r4, [r5, #40]
 str r4, [sp, #0]
 ldr r4, [r5, #44]
 str r4, [sp, #4]
 ldr r4, [r5, #48]
 str r4, [sp, #8]
 ldr r4, [r5, #52]
 str r4, [sp, #12]
 ldr r0, [r5, #16]
 ldr r1, [r5, #20]
 ldr r2, [r5, #24]
 ldr r3, [r5, #28]
 ldr r4, [r5, #8]
 bl call_r4
 str r0, [r5, #0]
 movs r0, #1
 str r0, [r5, #4]
 add sp, #16
 pop {{r4-r6,pc}}
call_r4:
 bx r4
noop:
 bx lr
.align 2
control:
 .word {control}
'''
(output/'probe.s').write_text(stub_source)
subprocess.run(['arm-none-eabi-as', '-mcpu=arm7tdmi', '-o', str(output/'probe.o'), str(output/'probe.s')], check=True)
subprocess.run(['arm-none-eabi-objcopy', '-O', 'binary', '-j', '.text', str(output/'probe.o'), str(output/'probe.bin')], check=True)
stub_symbols = {line.split()[2]: int(line.split()[0],16) for line in subprocess.check_output(['arm-none-eabi-nm', str(output/'probe.o')], text=True).splitlines() if len(line.split()) == 3}
rom = (root/'pokeemerald.gba').read_bytes()
stub_base = 0x08000000 + len(rom)
rom += (output/'probe.bin').read_bytes()
rom_buffer = C.create_string_buffer(rom)

class Descriptor(C.Structure):
    _fields_ = [('flags',C.c_uint64),('ptr',C.c_void_p),('offset',C.c_size_t),('start',C.c_size_t),('select',C.c_size_t),('disconnect',C.c_size_t),('length',C.c_size_t),('addrspace',C.c_char_p)]
class MemoryMap(C.Structure):
    _fields_ = [('descriptors',C.POINTER(Descriptor)),('count',C.c_uint)]
class GameInfo(C.Structure):
    _fields_ = [('path',C.c_char_p),('data',C.c_void_p),('size',C.c_size_t),('meta',C.c_char_p)]

ENV=C.CFUNCTYPE(C.c_bool,C.c_uint,C.c_void_p)
VIDEO=C.CFUNCTYPE(None,C.c_void_p,C.c_uint,C.c_uint,C.c_size_t)
AUDIO=C.CFUNCTYPE(None,C.c_int16,C.c_int16)
BATCH=C.CFUNCTYPE(C.c_size_t,C.c_void_p,C.c_size_t)
POLL=C.CFUNCTYPE(None)
INPUT=C.CFUNCTYPE(C.c_int16,C.c_uint,C.c_uint,C.c_uint,C.c_uint)
maps=[]
pixel_format=0
frame=None
keys=set()
directory=C.create_string_buffer(str(output.resolve()).encode())

@ENV
def environment(cmd,data):
    global maps,pixel_format
    cmd &= 0xffff
    if cmd == 36:
        mmap=C.cast(data,C.POINTER(MemoryMap)).contents
        maps=[(d.start,d.length,d.ptr,d.offset) for d in mmap.descriptors[:mmap.count] if d.ptr]
        return True
    if cmd in (9,31):
        C.cast(data,C.POINTER(C.c_char_p))[0]=C.cast(directory,C.c_char_p)
        return True
    if cmd == 10:
        pixel_format=C.cast(data,C.POINTER(C.c_int))[0]
        return True
    if cmd == 17:
        C.cast(data,C.POINTER(C.c_bool))[0]=False
        return True
    return cmd in (1,6,11,18,35,37)

@VIDEO
def video(data,w,h,pitch):
    global frame
    if data and data != C.c_void_p(-1).value:
        frame=(C.string_at(data,pitch*h),w,h,pitch,pixel_format)
@AUDIO
def audio(left,right): pass
@BATCH
def batch(data,count): return count
@POLL
def poll(): pass
@INPUT
def input_state(port,device,index,key): return int(key in keys)

core=C.CDLL(glob.glob('/usr/lib/*/libretro/mgba_libretro.so')[0])
for name,cb in [('environment',environment),('video_refresh',video),('audio_sample',audio),('audio_sample_batch',batch),('input_poll',poll),('input_state',input_state)]:
    fn=getattr(core,'retro_set_'+name)
    fn.argtypes=[type(cb)]
    fn(cb)
core.retro_init()
core.retro_load_game.argtypes=[C.POINTER(GameInfo)]
core.retro_load_game.restype=C.c_bool
assert core.retro_load_game(C.byref(GameInfo(b'emerald-test.gba',C.addressof(rom_buffer),len(rom),None)))

def ptr(address,size=1):
    for start,length,base,offset in maps:
        if start <= address and address+size <= start+length:
            return base+offset+address-start
    raise AssertionError(f'Unmapped memory {address:08x}')
def read(address,size): return C.string_at(ptr(address,size),size)
def write(address,data): C.memmove(ptr(address,len(data)),data,len(data))
def u32(address): return struct.unpack('<I',read(address,4))[0]
def w32(address,value): write(address,struct.pack('<I',value & 0xffffffff))
def run(count):
    for _ in range(count): core.retro_run()
def screenshot(name):
    data,w,h,pitch,fmt=frame
    pixels=[]
    for y in range(h):
        for x in range(w):
            if fmt==1:
                v=struct.unpack_from('<I',data,y*pitch+x*4)[0]
                pixels.append(((v>>16)&255,(v>>8)&255,v&255))
            else:
                v=struct.unpack_from('<H',data,y*pitch+x*2)[0]
                pixels.append((((v>>11)&31)*255//31,((v>>5)&63)*255//63,(v&31)*255//31) if fmt==2 else (((v>>10)&31)*255//31,((v>>5)&31)*255//31,(v&31)*255//31))
    img=Image.new('RGB',(w,h)); img.putdata(pixels); img.save(output/name)

run(900)
assert maps and u32(symbols['gSaveBlock1Ptr']) != 0
screenshot('boot.png')
main=symbols['gMain']
w32(main,0)
w32(main+4,stub_base+stub_symbols['noop']+1)

def call(name,*args):
    values=list(args)+[0]*(8-len(args))
    write(control,b'\0'*64)
    w32(control+8,symbols[name]|1)
    for i in range(4): w32(control+16+4*i,values[i])
    for i in range(4): w32(control+40+4*i,values[i+4])
    w32(control+32,main+4)
    w32(control+36,stub_base+stub_symbols['noop']+1)
    w32(main,0)
    w32(main+4,stub_base+1)
    for _ in range(3600 if name in ('TrySavingData','NuzlockeRestart') else 120):
        run(1)
        if u32(control+4)==1: return u32(control)
    screenshot('timeout-'+name+'.png')
    details={key:hex(u32(symbols[key])) for key in ('gFlashMemoryPresent','gDamagedSaveSectors','gSaveAttemptStatus','gSaveCounter') if key in symbols}
    details['callback2']=hex(u32(main+4))
    details['control']=read(control,64).hex()
    print('Timeout state:',json.dumps(details),flush=True)
    raise AssertionError('Emulator function timed out: '+name)

checks=[]
def check(label,condition):
    assert condition,label
    checks.append(label)
    print('PASS:',label,flush=True)

call('NewGameInitData')
save1=u32(symbols['gSaveBlock1Ptr'])
save2=u32(symbols['gSaveBlock2Ptr'])
party=symbols['gPlayerParty']
scratch=control+0x100

# Constants from the exact source are expanded by its preprocessor as integer macros.
def enum_values(path):
    text=(root/path).read_text()
    block=re.search(r'enum\s*\{(.*?)\};',text,re.S).group(1)
    block=re.sub(r'//[^\n]*|/\*.*?\*/','',block,flags=re.S)
    result={}; value=0
    for item in block.split(','):
        item=item.strip()
        if not item: continue
        if '=' in item:
            name,expr=item.split('=',1); value=int(expr.strip(),0)
        else: name=item
        result[name.strip()]=value; value+=1
    return result
mon_data=enum_values('include/pokemon.h')
items=enum_values('include/constants/items.h')
def getmon(index,field): return call('GetMonData3',party+100*index,mon_data['MON_DATA_'+field],0)
def setmon(index,field,value):
    w32(scratch,value)
    call('SetMonData',party+100*index,mon_data['MON_DATA_'+field],scratch)
def create(index,level=5): call('CreateMon',party+100*index,1,level,0,0,0,0,0)

# Actual gym caps, XP overflow, Rare Candy, and daycare-style boxed XP.
check('Initial cap is 15',call('NuzlockeLevelCap')==15)
badges=0x860+7
for i,expected in enumerate([19,24,29,31,33,42,46,100]):
    call('FlagSet',badges+i)
    check('Badge '+str(i+1)+' cap',call('NuzlockeLevelCap')==expected)
for i in range(8): call('FlagClear',badges+i)
create(0,14)
gain=call('NuzlockeExpGain',party,1000000)
setmon(0,'EXP',getmon(0,'EXP')+gain)
call('CalculateMonStats',party)
check('Huge EXP award stops exactly at cap',getmon(0,'LEVEL')==15)
check('No EXP accumulates at cap',call('NuzlockeExpGain',party,1000)==0)
check('Daycare boxed EXP obeys cap',call('NuzlockeBoxExpGain',party,1000)==0)
check('Rare Candy rejected at cap',call('ExecuteTableBasedItemEffect',party,items['ITEM_RARE_CANDY'],0,0)!=0 and getmon(0,'LEVEL')==15)

# Each named area consumes one opportunity, with all random encounter entry points gated.
write(save1+4,bytes([0,16])) # Route101 in the original map group order, checked below.
check('Fresh area permits encounter',call('NuzlockeEncounterUsed')==0)
call('NuzlockeUseEncounter')
check('Encounter is consumed',call('NuzlockeEncounterUsed')==1)
check('Grass encounters blocked after first',call('StandardWildEncounter',0,0)==0)
check('Sweet Scent blocked after first',call('SweetScentWildEncounter')==0)
check('Fishing blocked after first',call('DoesCurrentMapHaveFishingMons')==0)
call('RockSmashWildEncounter')
check('Rock Smash blocked after first',struct.unpack('<H',read(symbols['gSpecialVar_Result'],2))[0]==0)
write(save1+4,bytes([0,17]))
check('Different route keeps its own chance',call('NuzlockeEncounterUsed')==0)

# Removal, revival prevention, backup restoration, and wipe detection despite PC storage.
create(0); create(1); call('CalculatePlayerPartyCount'); call('SavePlayerParty')
setmon(0,'HP',0)
check('Revive cannot restore a dead Pokemon',call('ExecuteTableBasedItemEffect',party,items['ITEM_REVIVE'],0,0)!=0 and getmon(0,'HP')==0)
w32(symbols['gBattleTypeFlags'],0)
check('Survivor avoids total wipe',call('NuzlockeEndBattle')==0)
check('Fainted member removed from party',read(symbols['gPlayerPartyCount'],1)==b'\x01' and getmon(0,'HP')>0)
call('LoadPlayerParty')
check('Party backup cannot restore dead member',read(symbols['gPlayerPartyCount'],1)==b'\x01')
setmon(0,'HP',0)
check('Full party faint is a wipe',call('NuzlockeEndBattle')==1)

# Shop inventory filtering executes the compiled static shop function.
write(scratch,struct.pack('<6H',items['ITEM_POTION'],items['ITEM_POKE_BALL'],items['ITEM_REVIVE'],items['ITEM_GREAT_BALL'],items['ITEM_ANTIDOTE'],0))
write(symbols['sMartInfo']+15,b'\x00')
call('SetShopItemsForSale',scratch)
count=struct.unpack('<H',read(symbols['sMartInfo']+12,2))[0]
inventory=read(u32(symbols['sMartInfo']+8),count*2)
check('Shop retains only available ball types',inventory==struct.pack('<2H',items['ITEM_POKE_BALL'],items['ITEM_GREAT_BALL']))
check('Options lock Set style',call('BattleStyle_ProcessInput',0)==1)

# Marker sprites must be visible only for uncollected items and not add collision objects.
call('ResetSpriteData'); call('FreeAllSpritePalettes')
events=scratch+0x40
bg_event=scratch+0x80
old_events=u32(symbols['gMapHeader']+4)
write(events,struct.pack('<4B4I',0,0,0,1,0,0,0,bg_event))
write(bg_event,struct.pack('<HHBBHHH',0,0,0,7,0,items['ITEM_POTION'],0))
w32(symbols['gMapHeader']+4,events)
write(save1,struct.pack('<hh',0,0))
for name in ('gTotalCameraPixelOffsetX','gTotalCameraPixelOffsetY','gSpriteCoordOffsetX','gSpriteCoordOffsetY'):
    write(symbols[name],b'\0\0')
call('FlagClear',0x1f4)
objects_before=read(symbols['gObjectEvents'],16*36)
call('NuzlockeFieldUpdate')
markers=[symbols['gSprites']+i*68 for i in range(64) if u32(symbols['gSprites']+i*68+28)==(symbols['SpriteCB_HiddenItemMarker']|1)]
check('Uncollected hidden item gets a marker',len(markers)==1)
check('Marker adds no collision object',read(symbols['gObjectEvents'],16*36)==objects_before)
call('FlagSet',0x1f4)
call('SpriteCB_HiddenItemMarker',markers[0])
check('Collected hidden item marker disappears',read(markers[0]+62,1)[0]&1==0)
w32(symbols['gMapHeader']+4,old_events)

# Save persistence and destructive reset operate only on this emulator's disposable flash.
create(0); call('CalculatePlayerPartyCount')
check('Save succeeds in emulator',call('TrySavingData',0)==1)
core.retro_get_memory_data.argtypes=[C.c_uint]; core.retro_get_memory_data.restype=C.c_void_p
core.retro_get_memory_size.argtypes=[C.c_uint]; core.retro_get_memory_size.restype=C.c_size_t
flash=core.retro_get_memory_data(0); size=core.retro_get_memory_size(0)
check('Save flash contains the run',size>=0x20000 and C.string_at(flash,size)!=b'\xff'*size)
call('NuzlockeRestart')
check('Full wipe erases both save slots and PC data',C.string_at(flash,size)==b'\xff'*size)
run(900)
check('New run has no old party',read(symbols['gPlayerPartyCount'],1)==b'\x00')
screenshot('restart.png')
check('Restart reaches overworld',u32(main+4)==(symbols['CB2_Overworld']|1))
check('Restart renders the new map',len(set(frame[0]))>8)
(output/'emulator-checks.json').write_text(json.dumps({'passed':len(checks),'checks':checks},indent=2))
print('All',len(checks),'compiled-ROM checks passed.',flush=True)
core.retro_unload_game(); core.retro_deinit()
