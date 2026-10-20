#ifndef GUARD_REVERSE_EXP_H
#define GUARD_REVERSE_EXP_H
#include "pokemon.h"
void ReverseExpBeginBattle(void);
u32 ReverseExpLossAmount(struct Pokemon *mon, u32 amount);
void ReverseExpApply(u8 slot, u32 amount);
void ReverseExpSyncBattler(u8 battler);
void ReverseExpFinishBattle(void);
u16 ReverseExpParent(u16 species, u8 level, bool8 lostLevel);
#endif
