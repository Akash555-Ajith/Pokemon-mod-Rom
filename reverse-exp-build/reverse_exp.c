#include "global.h"
#include "reverse_exp.h"
#include "battle.h"
#include "data.h"
#include "string_util.h"

extern const struct Evolution gEvolutionTable[][EVOS_PER_MON];

EWRAM_DATA static u8 sLostLevels[PARTY_SIZE] = {0};
EWRAM_DATA static u8 sChangedMask = 0;

void ReverseExpBeginBattle(void)
{
    u32 i;
    for (i = 0; i < PARTY_SIZE; i++)
        sLostLevels[i] = 0;
    sChangedMask = 0;
}

u32 ReverseExpLossAmount(struct Pokemon *mon, u32 amount)
{
    u16 species = GetMonData(mon, MON_DATA_SPECIES);
    u32 exp, floor;
    if (!species || GetMonData(mon, MON_DATA_IS_EGG))
        return 0;
    exp = GetMonData(mon, MON_DATA_EXP);
    floor = gExperienceTables[gSpeciesInfo[species].growthRate][1];
    if (exp <= floor)
        return 0;
    return amount < exp - floor ? amount : exp - floor;
}

// Vanilla's stat recalculation can underflow HP when maximum HP decreases.
// Preserve damage taken, clamping a living Pokemon to at least one HP.
static void RecalculateSafely(struct Pokemon *mon)
{
    s32 hp = GetMonData(mon, MON_DATA_HP);
    s32 oldMax = GetMonData(mon, MON_DATA_MAX_HP);
    s32 newMax;
    CalculateMonStats(mon);
    newMax = GetMonData(mon, MON_DATA_MAX_HP);
    if (hp)
    {
        hp += newMax - oldMax;
        if (hp < 1)
            hp = 1;
        if (hp > newMax)
            hp = newMax;
    }
    SetMonData(mon, MON_DATA_HP, &hp);
}

void ReverseExpApply(u8 slot, u32 amount)
{
    struct Pokemon *mon;
    u32 exp;
    u8 before, after;
    if (slot >= PARTY_SIZE)
        return;
    mon = &gPlayerParty[slot];
    amount = ReverseExpLossAmount(mon, amount);
    if (!amount)
        return;
    before = GetMonData(mon, MON_DATA_LEVEL);
    exp = GetMonData(mon, MON_DATA_EXP) - amount;
    SetMonData(mon, MON_DATA_EXP, &exp);
    RecalculateSafely(mon);
    after = GetMonData(mon, MON_DATA_LEVEL);
    if (before > after)
        sLostLevels[slot] += before - after;
    sChangedMask |= 1 << slot;
}

void ReverseExpSyncBattler(u8 battler)
{
    struct Pokemon *mon = &gPlayerParty[gBattlerPartyIndexes[battler]];
    gBattleMons[battler].level = GetMonData(mon, MON_DATA_LEVEL);
    gBattleMons[battler].hp = GetMonData(mon, MON_DATA_HP);
    gBattleMons[battler].maxHP = GetMonData(mon, MON_DATA_MAX_HP);
    gBattleMons[battler].attack = GetMonData(mon, MON_DATA_ATK);
    gBattleMons[battler].defense = GetMonData(mon, MON_DATA_DEF);
    gBattleMons[battler].speed = GetMonData(mon, MON_DATA_SPEED);
    gBattleMons[battler].spAttack = GetMonData(mon, MON_DATA_SPATK);
    gBattleMons[battler].spDefense = GetMonData(mon, MON_DATA_SPDEF);
}

u16 ReverseExpParent(u16 species, u8 level, bool8 lostLevel)
{
    u32 parent, i;
    if (!lostLevel)
        return SPECIES_NONE;
    for (parent = 1; parent < NUM_SPECIES; parent++)
    {
        for (i = 0; i < EVOS_PER_MON; i++)
        {
            const struct Evolution *evo = &gEvolutionTable[parent][i];
            if (!evo->method || evo->targetSpecies != species)
                continue;
            switch (evo->method)
            {
            case EVO_LEVEL:
            case EVO_LEVEL_ATK_GT_DEF:
            case EVO_LEVEL_ATK_EQ_DEF:
            case EVO_LEVEL_ATK_LT_DEF:
            case EVO_LEVEL_SILCOON:
            case EVO_LEVEL_CASCOON:
            case EVO_LEVEL_NINJASK:
            case EVO_LEVEL_SHEDINJA:
                return level < evo->param ? parent : SPECIES_NONE;
            default:
                return parent;
            }
        }
    }
    return SPECIES_NONE;
}

static void ChangeToParent(struct Pokemon *mon, u16 parent)
{
    u16 species = GetMonData(mon, MON_DATA_SPECIES);
    u32 zero = 0;
    u8 nickname[POKEMON_NAME_BUFFER_SIZE];
    GetMonData(mon, MON_DATA_NICKNAME, nickname);
    if (StringCompare(nickname, gSpeciesNames[species]) == 0)
        SetMonData(mon, MON_DATA_NICKNAME, gSpeciesNames[parent]);
    SetMonData(mon, MON_DATA_SPECIES, &parent);
    if (!gSpeciesInfo[parent].abilities[1])
        SetMonData(mon, MON_DATA_ABILITY_NUM, &zero);
    // All vanilla evolution families share a growth group, so EXP stays exact.
    RecalculateSafely(mon);
}

void ReverseExpFinishBattle(void)
{
    u32 slot, j;
    for (slot = 0; slot < PARTY_SIZE; slot++)
    {
        struct Pokemon *mon = &gPlayerParty[slot];
        u8 steps = sLostLevels[slot];
        while (steps)
        {
            u16 parent = ReverseExpParent(GetMonData(mon, MON_DATA_SPECIES),
                                         GetMonData(mon, MON_DATA_LEVEL), TRUE);
            if (!parent)
                break;
            ChangeToParent(mon, parent);
            steps--;
        }
        // Partner battles restore a backed-up party after returning to the field.
        if ((sChangedMask & (1 << slot)) && (gBattleTypeFlags & BATTLE_TYPE_INGAME_PARTNER))
        {
            for (j = 0; j < PARTY_SIZE; j++)
            {
                struct Pokemon *saved = &gSaveBlock1Ptr->playerParty[j];
                if (GetMonData(saved, MON_DATA_SPECIES)
                    && GetMonData(saved, MON_DATA_PERSONALITY) == GetMonData(mon, MON_DATA_PERSONALITY)
                    && GetMonData(saved, MON_DATA_OT_ID) == GetMonData(mon, MON_DATA_OT_ID))
                {
                    u32 exp = GetMonData(mon, MON_DATA_EXP);
                    u16 species = GetMonData(mon, MON_DATA_SPECIES);
                    ChangeToParent(saved, species);
                    SetMonData(saved, MON_DATA_EXP, &exp);
                    RecalculateSafely(saved);
                }
            }
        }
    }
    ReverseExpBeginBattle();
}
