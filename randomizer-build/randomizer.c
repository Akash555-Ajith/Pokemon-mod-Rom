#include "global.h"
#include "single_randomizer.h"
#include "battle.h"
#include "event_data.h"
#include "field_screen_effect.h"
#include "main.h"
#include "new_game.h"
#include "overworld.h"
#include "palette.h"
#include "pokedex.h"
#include "random.h"
#include "script.h"
#include "string_util.h"
#include "constants/flags.h"
#include "constants/maps.h"

// National IDs exclude the unused internal Unown slots and the Egg placeholder.
u16 RandomizerSpecies(u16 exclude)
{
    u16 species;
    do
    {
        species = NationalPokedexNumToSpecies(1 + Random() % 386);
    } while (species == exclude);
    return species;
}

// Preserve level and progress within that level when changing growth groups.
// Retain the individual, nickname, held item, status and fainted state.
void RandomizerChangeSpecies(struct Pokemon *mon, u16 species, bool8 newMoves)
{
    u16 oldSpecies = GetMonData(mon, MON_DATA_SPECIES);
    u8 level = GetMonData(mon, MON_DATA_LEVEL);
    u32 exp = GetMonData(mon, MON_DATA_EXP);
    u32 oldBase = gExperienceTables[gSpeciesInfo[oldSpecies].growthRate][level];
    u32 newBase = gExperienceTables[gSpeciesInfo[species].growthRate][level];
    u16 hp = GetMonData(mon, MON_DATA_HP);
    u16 maxHp = GetMonData(mon, MON_DATA_MAX_HP);
    u16 newMax, hms[MAX_MON_MOVES];
    u8 nickname[POKEMON_NAME_BUFFER_SIZE];
    u32 i, numHms = 0, zero = 0;

    if (level < MAX_LEVEL && exp > oldBase)
    {
        u32 oldSpan = gExperienceTables[gSpeciesInfo[oldSpecies].growthRate][level + 1] - oldBase;
        u32 newSpan = gExperienceTables[gSpeciesInfo[species].growthRate][level + 1] - newBase;
        u32 progress = exp - oldBase;
        if (progress >= oldSpan)
            progress = oldSpan - 1;
        newBase += progress * newSpan / oldSpan;
    }
    GetMonData(mon, MON_DATA_NICKNAME, nickname);
    if (StringCompare(nickname, gSpeciesNames[oldSpecies]) == 0)
        SetMonData(mon, MON_DATA_NICKNAME, gSpeciesNames[species]);
    SetMonData(mon, MON_DATA_SPECIES, &species);
    SetMonData(mon, MON_DATA_EXP, &newBase);
    if (!gSpeciesInfo[species].abilities[1])
        SetMonData(mon, MON_DATA_ABILITY_NUM, &zero);
    if (newMoves)
    {
        for (i = 0; i < MAX_MON_MOVES; i++)
        {
            u16 move = GetMonData(mon, MON_DATA_MOVE1 + i);
            if (IsHMMove2(move))
                hms[numHms++] = move;
            SetMonData(mon, MON_DATA_MOVE1 + i, &zero);
            SetMonData(mon, MON_DATA_PP1 + i, &zero);
        }
        SetMonData(mon, MON_DATA_PP_BONUSES, &zero);
        GiveMonInitialMoveset(mon);
        if (!GetMonData(mon, MON_DATA_MOVE1))
            SetMonMoveSlot(mon, gLevelUpLearnsets[species][0] & LEVEL_UP_MOVE_ID, 0);
        for (i = 0; i < numHms; i++)
        {
            SetMonData(mon, MON_DATA_MOVE1 + i, &hms[i]);
            SetMonData(mon, MON_DATA_PP1 + i, &gBattleMoves[hms[i]].pp);
        }
    }
    CalculateMonStats(mon);
    newMax = GetMonData(mon, MON_DATA_MAX_HP);
    if (hp && maxHp)
    {
        hp = (u32)hp * newMax / maxHp;
        if (!hp)
            hp = 1;
        if (hp > newMax)
            hp = newMax;
    }
    SetMonData(mon, MON_DATA_HP, &hp);
    GetSetPokedexFlag(SpeciesToNationalPokedexNum(species), FLAG_SET_SEEN);
    GetSetPokedexFlag(SpeciesToNationalPokedexNum(species), FLAG_SET_CAUGHT);
}

#if RANDOMIZER_VARIANT == 1
void RandomizerEnemyParty(void)
{
    u32 i;
    if (!(gBattleTypeFlags & BATTLE_TYPE_TRAINER)
        || (gBattleTypeFlags & (BATTLE_TYPE_LINK | BATTLE_TYPE_RECORDED | BATTLE_TYPE_WALLY_TUTORIAL)))
        return;
    for (i = 0; i < PARTY_SIZE; i++)
    {
        u16 item;
        if (!GetMonData(&gEnemyParty[i], MON_DATA_SPECIES))
            continue;
        item = GetMonData(&gEnemyParty[i], MON_DATA_HELD_ITEM);
        CreateMon(&gEnemyParty[i], RandomizerSpecies(SPECIES_NONE), 1 + Random() % 100,
                  USE_RANDOM_IVS, FALSE, 0, OT_ID_RANDOM_NO_SHINY, 0);
        if (!GetMonData(&gEnemyParty[i], MON_DATA_MOVE1))
        {
            u16 species = GetMonData(&gEnemyParty[i], MON_DATA_SPECIES);
            SetMonMoveSlot(&gEnemyParty[i], gLevelUpLearnsets[species][0] & LEVEL_UP_MOVE_ID, 0);
        }
        SetMonData(&gEnemyParty[i], MON_DATA_HELD_ITEM, &item);
    }
}
#elif RANDOMIZER_VARIANT == 2
EWRAM_DATA static u16 sPartyRerolls = 0;
void RandomizerBattleEnd(void)
{
    if ((gBattleTypeFlags & BATTLE_TYPE_TRAINER)
        && !(gBattleTypeFlags & (BATTLE_TYPE_LINK | BATTLE_TYPE_RECORDED | BATTLE_TYPE_WALLY_TUTORIAL)))
        sPartyRerolls++;
}

void RandomizerFieldUpdate(void)
{
    u32 i;
    if (!sPartyRerolls || gMain.inBattle || gPaletteFade.active
        || ScriptContext_IsEnabled() || ArePlayerFieldControlsLocked())
        return;
    // Wait until story/facility scripts have restored the player's actual party.
    while (sPartyRerolls)
    {
        for (i = 0; i < PARTY_SIZE; i++)
        {
            u16 species = GetMonData(&gPlayerParty[i], MON_DATA_SPECIES);
            if (species && !GetMonData(&gPlayerParty[i], MON_DATA_IS_EGG))
                RandomizerChangeSpecies(&gPlayerParty[i], RandomizerSpecies(species), TRUE);
        }
        sPartyRerolls--;
    }
}
#elif RANDOMIZER_VARIANT == 3
EWRAM_DATA static u8 sPendingEvolutions[PARTY_SIZE] = {0};
void RandomizerBeginBattle(void)
{
    u32 i;
    for (i = 0; i < PARTY_SIZE; i++)
        sPendingEvolutions[i] = 0;
}
void RandomizerQueueLevel(u8 slot)
{
    if (slot < PARTY_SIZE && sPendingEvolutions[slot] < MAX_LEVEL)
        sPendingEvolutions[slot]++;
}
bool8 RandomizerHasEvolution(u8 slot)
{
    return slot < PARTY_SIZE && sPendingEvolutions[slot] != 0;
}
u16 RandomizerNextEvolution(u8 slot)
{
    if (!RandomizerHasEvolution(slot))
        return SPECIES_NONE;
    sPendingEvolutions[slot]--;
    return RandomizerSpecies(GetMonData(&gPlayerParty[slot], MON_DATA_SPECIES));
}
void RandomizerBattleEnd(void)
{
    u32 i;
    // Loss/escape can bypass the normal evolution scene; still honor gained levels.
    for (i = 0; i < PARTY_SIZE; i++)
        while (RandomizerHasEvolution(i))
            RandomizerChangeSpecies(&gPlayerParty[i], RandomizerNextEvolution(i), FALSE);
}
void RandomizerDaycare(struct Pokemon *mon, u8 levels)
{
    while (levels--)
        RandomizerChangeSpecies(mon, RandomizerSpecies(GetMonData(mon, MON_DATA_SPECIES)), FALSE);
}
#elif RANDOMIZER_VARIANT == 4
struct RandomWarp { u8 group, map, warp; };
#include "randomizer_warps.h"

u32 RandomizerWarpIndex(u8 group, u8 map, u8 warp)
{
    u32 seed = GetTrainerId(gSaveBlock2Ptr->playerTrainerId);
    u32 value = seed ^ ((u32)group << 24) ^ ((u32)map << 8) ^ warp ^ 0x9E3779B9;
    value ^= value >> 16;
    value *= 0x7FEB352D;
    value ^= value >> 15;
    value *= 0x846CA68B;
    value ^= value >> 16;
    return value % ARRAY_COUNT(sRandomWarps);
}
bool8 RandomizerWarp(s8 warpId)
{
    u32 i;
    const struct RandomWarp *target;
    // Keep the opening playable until the player has obtained their starter.
    if (!FlagGet(FLAG_SYS_POKEMON_GET) || warpId < 0)
        return FALSE;
    for (i = 0; i < ARRAY_COUNT(sRandomWarps); i++)
        if (sRandomWarps[i].group == gSaveBlock1Ptr->location.mapGroup
            && sRandomWarps[i].map == gSaveBlock1Ptr->location.mapNum
            && sRandomWarps[i].warp == warpId)
            break;
    if (i == ARRAY_COUNT(sRandomWarps))
        return FALSE;
    i = RandomizerWarpIndex(gSaveBlock1Ptr->location.mapGroup, gSaveBlock1Ptr->location.mapNum, warpId);
    target = &sRandomWarps[i];
    ResetInitialPlayerAvatarState();
    SetWarpDestination(target->group, target->map, target->warp, -1, -1);
    return TRUE;
}
bool8 RandomizerRescue(void)
{
    if (!FlagGet(FLAG_SYS_POKEMON_GET) || gMain.inBattle || gPaletteFade.active
        || ScriptContext_IsEnabled() || ArePlayerFieldControlsLocked())
        return FALSE;
    if ((gMain.heldKeys & (L_BUTTON | R_BUTTON)) == (L_BUTTON | R_BUTTON)
        && (gMain.newKeys & SELECT_BUTTON))
    {
        ResetInitialPlayerAvatarState();
        SetWarpDestination(MAP_GROUP(MAP_LITTLEROOT_TOWN), MAP_NUM(MAP_LITTLEROOT_TOWN), -1, 10, 10);
        DoWarp();
        return TRUE;
    }
    return FALSE;
}
#endif
