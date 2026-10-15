"""Apply exactly one randomizer to the pinned, pristine Emerald source."""
from pathlib import Path
import hashlib
import json
import re
import sys

root = Path(sys.argv[1])
variant = int(sys.argv[2])
assert variant in (1, 2, 3, 4)
here = Path(__file__).parent
assert not (root/'include/nuzlocke.h').exists(), 'Use pristine Emerald, not an earlier mod'
assert not (root/'include/single_randomizer.h').exists(), 'Already patched'
changed = []

def edit(path, old, new, count=1):
    p = root/path
    s = p.read_text()
    assert s.count(old) == count, (path, old[:100], s.count(old))
    p.write_text(s.replace(old, new))
    if path not in changed:
        changed.append(path)

def include(path):
    edit(path, '#include "global.h"', '#include "global.h"\n#include "single_randomizer.h"')

(root/'include/single_randomizer.h').write_text(
    '#define RANDOMIZER_VARIANT %d\n' % variant + (here/'randomizer.h').read_text())
(root/'src/single_randomizer.c').write_text((here/'randomizer.c').read_text())
edit('ld_script.ld', 'src/main.o(.text);', 'src/main.o(.text);\n        src/single_randomizer.o(.text);')
edit('ld_script.ld', 'src/main.o(.rodata);', 'src/main.o(.rodata);\n        src/single_randomizer.o(.rodata);')

if variant == 1:
    include('src/battle_main.c')
    edit('src/battle_main.c', '    gMain.inBattle = TRUE;',
         '    RandomizerEnemyParty();\n    gMain.inBattle = TRUE;')
elif variant == 2:
    include('src/battle_main.c')
    edit('src/battle_main.c', 'static void ReturnFromBattleToOverworld(void)\n{',
         'static void ReturnFromBattleToOverworld(void)\n{\n    RandomizerBattleEnd();')
    include('src/overworld.c')
    edit('src/overworld.c', '    OverworldBasic();\n    if (fading)',
         '    OverworldBasic();\n    RandomizerFieldUpdate();\n    if (fading)')
elif variant == 3:
    for path in ('src/battle_main.c', 'src/battle_controller_player.c', 'src/pokemon.c', 'src/evolution_scene.c', 'src/daycare.c'):
        include(path)
    edit('src/battle_main.c', '    gMain.inBattle = TRUE;',
         '    RandomizerBeginBattle();\n    gMain.inBattle = TRUE;')
    edit('src/battle_controller_player.c',
         '            SetMonData(mon, MON_DATA_EXP, &nextLvlExp);\n            CalculateMonStats(mon);',
         '            SetMonData(mon, MON_DATA_EXP, &nextLvlExp);\n            CalculateMonStats(mon);\n            RandomizerQueueLevel(monId);')
    edit('src/battle_controller_player.c',
         '                CalculateMonStats(&gPlayerParty[monId]);\n                gainedExp',
         '                CalculateMonStats(&gPlayerParty[monId]);\n                RandomizerQueueLevel(monId);\n                gainedExp')
    # Consume one queued evolution per earned level, including multiple levels in one battle.
    edit('src/battle_main.c', '                gLeveledUpInBattle = levelUpBits;\n\n                species = GetEvolutionTargetSpecies(&gPlayerParty[i], EVO_MODE_NORMAL, levelUpBits);',
         '                species = RandomizerNextEvolution(i);\n                if (RandomizerHasEvolution(i))\n                    levelUpBits |= gBitTable[i];\n                gLeveledUpInBattle = levelUpBits;')
    edit('src/battle_main.c', 'static void ReturnFromBattleToOverworld(void)\n{',
         'static void ReturnFromBattleToOverworld(void)\n{\n    RandomizerBattleEnd();')
    edit('src/pokemon.c', '    u8 holdEffect;\n\n    if (heldItem == ITEM_ENIGMA_BERRY)',
         '    u8 holdEffect;\n\n    if (mode == EVO_MODE_NORMAL && species && !GetMonData(mon, MON_DATA_IS_EGG))\n        return RandomizerSpecies(species);\n\n    if (heldItem == ITEM_ENIGMA_BERRY)')
    # Random forms may use different experience curves; preserve levels instead of recalculating from old XP.
    edit('src/evolution_scene.c', '            SetMonData(mon, MON_DATA_SPECIES, (void *)(&gTasks[taskId].tPostEvoSpecies));',
         '            RandomizerChangeSpecies(mon, gTasks[taskId].tPostEvoSpecies, FALSE);')
    # The level-up rule is compulsory even with B held or an Everstone.
    edit('src/evolution_scene.c', '    gTasks[id].tCanStop = canStopEvo;', '    gTasks[id].tCanStop = FALSE;')
    edit('src/evolution_scene.c', '    u32 data = 0;\n    if (gEvolutionTable[preEvoSpecies][0].method',
         '    u32 data = 0;\n    return; // Random evolution never creates an extra Shedinja.\n    if (gEvolutionTable[preEvoSpecies][0].method')
    edit('src/daycare.c', 'static void ApplyDaycareExperience(struct Pokemon *mon)\n{\n    s32 i;',
         'static void ApplyDaycareExperience(struct Pokemon *mon)\n{\n    s32 i;\n    u8 oldLevel = GetMonData(mon, MON_DATA_LEVEL);')
    edit('src/daycare.c', '    // Re-calculate the mons stats at its new level.\n    CalculateMonStats(mon);',
         '    // Re-calculate the mons stats at its new level.\n    CalculateMonStats(mon);\n    RandomizerDaycare(mon, GetMonData(mon, MON_DATA_LEVEL) - oldLevel);')
elif variant == 4:
    groups = json.loads((root/'data/maps/map_groups.json').read_text())
    entries = []
    # Script-only/link/facility maps are not ordinary exploration entrances.
    excluded = ('BattleFrontier', 'BattlePyramid', 'TrainerHill', 'SecretBase', 'UnionRoom',
                'TradeCenter', 'Colosseum', 'RecordCorner', 'CableCar', 'Elevator',
                'InsideOfTruck', 'HallOfFame', 'SS_Tidal', 'SafariZone', 'SootopolisCity_MysteryEventsHouse')
    maps = {}
    for group, key in enumerate(groups['group_order']):
        for number, name in enumerate(groups[key]):
            p = root/'data/maps'/name/'map.json'
            data = json.loads(p.read_text())
            maps[data['id']] = (group, number, name, data)
    for group, number, name, data in maps.values():
        if any(token in name for token in excluded) or data['map_type'] not in (
                'MAP_TYPE_TOWN', 'MAP_TYPE_CITY', 'MAP_TYPE_ROUTE', 'MAP_TYPE_INDOOR', 'MAP_TYPE_UNDERGROUND'):
            continue
        for warp, event in enumerate(data.get('warp_events', [])):
            target = maps.get(event['dest_map'])
            dest = str(event['dest_warp_id'])
            if not target or not dest.isdigit() or int(dest) >= len(target[3].get('warp_events', [])):
                continue
            entries.append(dict(group=group, map=number, warp=warp, name=name, x=event['x'], y=event['y']))
    assert len(entries) > 200
    (root/'include/randomizer_warps.h').write_text('static const struct RandomWarp sRandomWarps[] = {\n' +
        ''.join('    {%d, %d, %d}, // %s\n' % (e['group'],e['map'],e['warp'],e['name']) for e in entries) + '};\n')
    (root/'randomizer-warps.json').write_text(json.dumps(entries, indent=2))
    include('src/field_control_avatar.c')
    edit('src/field_control_avatar.c', '    u8 trainerHillMapId = GetCurrentTrainerHillMapId();\n\n    if (trainerHillMapId)',
         '    u8 trainerHillMapId = GetCurrentTrainerHillMapId();\n\n    if (RandomizerWarp(warpEventId))\n        return;\n\n    if (trainerHillMapId)')
    include('src/overworld.c')
    edit('src/overworld.c', 'void CB1_Overworld(void)\n{\n    if (gMain.callback2 == CB2_Overworld)',
         'void CB1_Overworld(void)\n{\n    if (gMain.callback2 == CB2_Overworld && RandomizerRescue())\n        return;\n    if (gMain.callback2 == CB2_Overworld)')

print('Applied only randomizer variant', variant, 'to:', ', '.join(changed))
(root/'randomizer-manifest.json').write_text(json.dumps({'variant':variant,'changed':changed},indent=2))
