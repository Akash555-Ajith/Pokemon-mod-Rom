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

run(600)
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
    for _ in range(3600 if name in ('TrySavingData',) else 120):
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

variant=int(sys.argv[3])
valid=set(range(1,252)) | set(range(277,412))
check('No Nuzlocke code linked',not any(name.startswith('Nuzlocke') for name in symbols))
create(0,15)
check('Original level limits: Rare Candy works above first gym cap',call('ExecuteTableBasedItemEffect',party,items['ITEM_RARE_CANDY'],0,0)==0 and getmon(0,'LEVEL')==16)
setmon(0,'HP',0)
check('Normal revival remains available',call('ExecuteTableBasedItemEffect',party,items['ITEM_REVIVE'],0,0)==0 and getmon(0,'HP')>0)
check('Battle style can still be changed',call('BattleStyle_ProcessInput',0)==0)
enemy=symbols['gEnemyParty']
noop=stub_base+stub_symbols['noop']+1

def enemydata(slot,field): return call('GetMonData3',enemy+slot*100,mon_data['MON_DATA_'+field],0)
def field_ready():
    call('ScriptContext_Init'); call('UnlockPlayerFieldControls'); call('ResetPaletteFade')
    write(main+0x439,bytes([read(main+0x439,1)[0]&~2]))

if variant==1:
    for i in range(6): call('CreateMon',enemy+100*i,1,5,0,0,0,0,0)
    before=read(enemy,600)
    w32(symbols['gBattleTypeFlags'],0)
    call('RandomizerEnemyParty')
    check('Wild encounters keep original enemy party',read(enemy,600)==before)
    w32(symbols['gBattleTypeFlags'],8|2)
    call('RandomizerEnemyParty')
    check('Link parties are excluded',read(enemy,600)==before)
    w32(symbols['gBattleTypeFlags'],8)
    levels=[]; species=[]
    player_before=read(party,600)
    for trial in range(35):
        call('RandomizerEnemyParty')
        for i in range(6):
            levels.append(enemydata(i,'LEVEL')); species.append(enemydata(i,'SPECIES'))
            assert enemydata(i,'MOVE1')!=0
    check('All randomized species are real Generation I-III Pokemon',set(species)<=valid)
    check('Levels stay between 1 and 100',min(levels)>=1 and max(levels)<=100)
    check('Trainer levels cover low and high ranges',min(levels)<8 and max(levels)>92)
    check('Trainer species vary broadly',len(set(species))>80)
    check('Player party is unchanged',read(party,600)==player_before)
    call('ZeroMonData',enemy+500)
    call('RandomizerEnemyParty')
    check('Randomization preserves party size',enemydata(5,'SPECIES')==0)
elif variant==2:
    field_ready()
    for i in range(3): create(i,20+i)
    call('CalculatePlayerPartyCount')
    setmon(0,'MOVE1',15) # Cut
    setmon(0,'PP1',30)
    setmon(0,'HELD_ITEM',items['ITEM_ORAN_BERRY'])
    setmon(1,'HP',0)
    setmon(2,'IS_EGG',1)
    before=read(party,600)
    w32(symbols['gBattleTypeFlags'],0)
    call('RandomizerBattleEnd'); call('RandomizerFieldUpdate')
    check('Wild battles do not shuffle the party',read(party,600)==before)
    w32(symbols['gBattleTypeFlags'],8)
    call('RandomizerBattleEnd'); call('RandomizerFieldUpdate')
    check('Trainer battle changes each occupied non-Egg slot',getmon(0,'SPECIES')!=1 and getmon(1,'SPECIES')!=1)
    check('Party levels are preserved',getmon(0,'LEVEL')==20 and getmon(1,'LEVEL')==21)
    check('Fainted Pokemon remain fainted',getmon(1,'HP')==0)
    check('Held item survives reroll',getmon(0,'HELD_ITEM')==items['ITEM_ORAN_BERRY'])
    check('HM move survives reroll',15 in [getmon(0,'MOVE'+str(i+1)) for i in range(4)])
    check('Eggs remain unchanged',getmon(2,'SPECIES')==1 and getmon(2,'IS_EGG')==1)
    check('Empty party slots remain empty',getmon(3,'SPECIES')==0)
    once=read(party,600)
    call('RandomizerFieldUpdate')
    check('Only one shuffle per completed trainer battle',read(party,600)==once)
    for target in (150,292,385,1,411):
        call('RandomizerChangeSpecies',party,target,1)
        assert getmon(0,'LEVEL')==20
    check('Cross-growth-group species changes preserve levels',getmon(0,'LEVEL')==20)
elif variant==3:
    create(0,37)
    setmon(0,'HELD_ITEM',items['ITEM_EVERSTONE'])
    call('RandomizerBeginBattle')
    for _ in range(3): call('RandomizerQueueLevel',0)
    for _ in range(3):
        target=call('RandomizerNextEvolution',0)
        assert target in valid and target!=getmon(0,'SPECIES')
        call('RandomizerChangeSpecies',party,target,0)
        assert getmon(0,'LEVEL')==37
    check('Three level gains produce exactly three random evolutions',call('RandomizerNextEvolution',0)==0)
    check('Random evolution preserves level across growth groups',getmon(0,'LEVEL')==37)
    check('Everstone cannot prevent random level evolution',call('GetEvolutionTargetSpecies',party,0,0) in valid)
    call('RandomizerQueueLevel',0)
    original=getmon(0,'SPECIES')
    call('RandomizerBattleEnd')
    check('Loss or escape still applies pending evolution',getmon(0,'SPECIES')!=original)
    original=getmon(0,'SPECIES')
    call('RandomizerDaycare',party,1)
    check('Daycare level also changes species',getmon(0,'SPECIES')!=original and getmon(0,'LEVEL')==37)
    check('Moves remain usable after evolution',getmon(0,'MOVE1')!=0)
    # Run a real forced evolution animation to ensure sprites and post-evolution XP stay valid.
    call('CalculatePlayerPartyCount')
    w32(symbols['gCB2_AfterEvolution'],noop)
    call('EvolutionScene',party,3,1,0)
    for n in range(1600):
        keys.clear()
        keys.add(0) # Hold B; the mandatory evolution must not cancel.
        if n%30<3: keys.add(8) # A confirms any text.
        run(1)
        if n>120 and u32(main+4)==noop: break
    keys.clear()
    screenshot('evolution.png')
    # Stop the scene callback before using the function probe again.
    finished=u32(main+4)==noop
    check('Evolution animation completes despite B button',finished)
    check('Animated evolution reaches requested species at same level',getmon(0,'SPECIES')==3 and getmon(0,'LEVEL')==37)
elif variant==4:
    entries=json.loads((root/'randomizer-warps.json').read_text())
    check('More than 200 valid entrance tiles are available',len(entries)>200)
    source=next(e for e in entries if e['name']=='LittlerootTown' and e['warp']==1)
    write(save1+4,bytes([source['group'],source['map']]))
    check('Intro entrances remain normal before receiving starter',call('RandomizerWarp',source['warp'])==0)
    call('FlagSet',0x860)
    first=call('RandomizerWarpIndex',source['group'],source['map'],source['warp'])
    check('Warp destination remains stable across repeated visits',all(call('RandomizerWarpIndex',source['group'],source['map'],source['warp'])==first for _ in range(5)))
    indices=[call('RandomizerWarpIndex',e['group'],e['map'],e['warp']) for e in entries[::max(1,len(entries)//40)]]
    check('Every sampled destination is in the validated table',all(0<=i<len(entries) for i in indices))
    check('Different entrances lead to varied locations',len(set(indices))>20)
    id_before=read(save2+10,4)
    write(save2+10,b'\x12\x34\x56\x78')
    other=call('RandomizerWarpIndex',source['group'],source['map'],source['warp'])
    check('A different trainer ID changes the layout',other!=first)
    write(save2+10,id_before)
    check('Restored save identity restores same layout',call('RandomizerWarpIndex',source['group'],source['map'],source['warp'])==first)
    check('Actual warp hook accepts a normal house entrance',call('RandomizerWarp',source['warp'])==1)
    target=entries[first]
    call('CB2_LoadMap')
    run(600)
    screenshot('random-map.png')
    active_save=u32(symbols['gSaveBlock1Ptr'])
    check('Random destination map loads',read(active_save+4,2)==bytes([target['group'],target['map']]))
    check('Random destination renders',len(set(frame[0]))>8)
    field_ready()
    # GBA key bits: L=0x200, R=0x100, Select=4.
    # Rescue function is tested through real held/new-key input in CB1_Overworld below.
    w32(main,symbols['CB1_Overworld']|1)
    w32(main+4,symbols['CB2_Overworld']|1)
    keys.update((10,11)); run(2); keys.add(2); run(2); keys.clear(); run(600)
    screenshot('rescue.png')
    active_save=u32(symbols['gSaveBlock1Ptr'])
    check('L+R+Select rescue returns to Littleroot',read(active_save+4,2)==b'\x00\x00')

(output/'emulator-checks.json').write_text(json.dumps({'variant':variant,'passed':len(checks),'checks':checks},indent=2))
print('All',len(checks),'checks passed for variant',variant,flush=True)
core.retro_unload_game(); core.retro_deinit()
