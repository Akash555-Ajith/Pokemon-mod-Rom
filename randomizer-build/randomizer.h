#ifndef GUARD_SINGLE_RANDOMIZER_H
#define GUARD_SINGLE_RANDOMIZER_H
#include "pokemon.h"
u16 RandomizerSpecies(u16 exclude);
void RandomizerChangeSpecies(struct Pokemon *mon, u16 species, bool8 newMoves);
void RandomizerEnemyParty(void);
void RandomizerBattleEnd(void);
void RandomizerFieldUpdate(void);
void RandomizerBeginBattle(void);
void RandomizerQueueLevel(u8 slot);
u16 RandomizerNextEvolution(u8 slot);
bool8 RandomizerHasEvolution(u8 slot);
void RandomizerDaycare(struct Pokemon *mon, u8 levels);
bool8 RandomizerWarp(s8 warpId);
bool8 RandomizerRescue(void);
#endif
