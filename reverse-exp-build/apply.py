from pathlib import Path
import sys

root = Path(sys.argv[1])
here = Path(__file__).parent
assert not (root/'include/nuzlocke.h').exists()
assert not (root/'include/single_randomizer.h').exists()
assert not (root/'include/reverse_exp.h').exists()

def edit(path, old, new, count=1):
    p = root/path
    text = p.read_text()
    assert text.count(old) == count, (path, old[:70], text.count(old))
    p.write_text(text.replace(old, new))

for filename in ('reverse_exp.c', 'reverse_exp.h'):
    (root/('src' if filename.endswith('.c') else 'include')/filename).write_text((here/filename).read_text())
for path in ('src/battle_main.c', 'src/battle_controller_player.c', 'src/battle_script_commands.c'):
    edit(path, '#include "global.h"', '#include "global.h"\n#include "reverse_exp.h"')
for section in ('text', 'rodata'):
    edit('ld_script.ld', f'src/main.o(.{section});', f'src/main.o(.{section});\n        src/reverse_exp.o(.{section});')
edit('src/battle_main.c', '    gMain.inBattle = TRUE;', '    ReverseExpBeginBattle();\n    gMain.inBattle = TRUE;')
edit('src/battle_main.c', 'static void ReturnFromBattleToOverworld(void)\n{',
     'static void ReturnFromBattleToOverworld(void)\n{\n    ReverseExpFinishBattle();')

p = root/'src/battle_script_commands.c'
s = p.read_text()
start = s.index('static void Cmd_getexp(void)\n{')
end = s.index('\nstatic void ', start+1)
block = s[start:end]
assert block.count('MON_DATA_LEVEL) == MAX_LEVEL') == 1
assert block.count('MON_DATA_LEVEL) != MAX_LEVEL') == 1
block = block.replace('MON_DATA_LEVEL) == MAX_LEVEL', 'MON_DATA_LEVEL) <= 1')
block = block.replace('MON_DATA_LEVEL) != MAX_LEVEL', 'MON_DATA_LEVEL) > 1')
needle = '                    PREPARE_WORD_NUMBER_BUFFER(gBattleTextBuff3, 5, gBattleMoveDamage);'
assert needle in block
block = block.replace(needle, '                    gBattleMoveDamage = ReverseExpLossAmount(&gPlayerParty[gBattleStruct->expGetterMonId], gBattleMoveDamage);\n'+needle)
p.write_text(s[:start]+block+s[end:])
edit('src/battle_message.c', '{B_BUFF1} gained{B_BUFF2}', '{B_BUFF1} lost{B_BUFF2}')

p = root/'src/battle_controller_player.c'
s = p.read_text()
start = s.index('static void PlayerHandleExpUpdate(void)\n{')
end = s.index('\n#undef tExpTask_monId', start)
s = s[:start]+'''static void PlayerHandleExpUpdate(void)
{
    u8 monId = gBattleBufferA[gActiveBattler][1];
    u32 amount = T1_READ_16(&gBattleBufferA[gActiveBattler][2]);
    u32 i;
    ReverseExpApply(monId, amount);
    for (i = 0; i < gBattlersCount; i++)
    {
        if (GetBattlerSide(i) == B_SIDE_PLAYER && gBattlerPartyIndexes[i] == monId
            && !(gAbsentBattlerFlags & gBitTable[i]))
        {
            ReverseExpSyncBattler(i);
            UpdateHealthboxAttribute(gHealthboxSpriteIds[i], &gPlayerParty[monId], HEALTHBOX_ALL);
        }
    }
    PlayerBufferExecCompleted();
}
''' + s[end:]
p.write_text(s)
print('Applied only reverse battle EXP and de-evolution. Original level-5 starters retained.')
