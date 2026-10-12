# Emerald: seven-rule Nuzlocke

This is a separate ROM based on original English Emerald. Trainer species and levels are unchanged.

1. One wild encounter per named area. Grass, surfing, fishing, Rock Smash, Sweet Scent, and scripted wild battles share the area's single chance. Running away or failing to catch still uses it. Cave floors with the same area name share a chance. Birch's opening rescue and Wally's demonstration are tutorial exceptions.
2. Fainted party members cannot be revived and are permanently removed when the battle ends. Field-poison deaths also count. The surviving party is saved automatically after scripts finish.
3. A full party wipe erases the ROM's entire in-game save, including boxed Pokemon, and starts a new run in the moving truck using the same player name and gender. Other ROMs and their save files are unaffected.
4. Normal item shops sell only their originally available Poke Ball types. Decorations are unaffected. Found and gifted items still work, except revival items cannot revive a dead Pokemon.
5. Level caps follow the next undefeated original Gym Leader: 15, 19, 24, 29, 31, 33, 42, and 46. After all eight badges, the cap is 100. Battle EXP, Exp Share, Rare Candies, and daycare gains obey the cap. Already-higher-level catches cannot gain further EXP until the cap catches up.
6. Set battle style is enforced in the engine and locked in Options.
7. Uncollected standard hidden items have repeating sparkle markers. The markers do not block movement and disappear when collected. Stand beside the marked tile, face it, and press A.

Use a new game and a new save filename. Autosaving happens after encounters/battles once field scripts finish. Emulator save states and external save editors are outside the ROM's control. Link battles and recorded replays do not apply permanent-death rules to the player's real party.

## Build and validation status

The ROM compiled successfully in GitHub Actions on Ubuntu after Windows Application Control blocked the local compiler. The unmodified source first reproduced the exact original Emerald ROM. Source checks confirmed original trainer data, all eight gym caps, and 112 standard hidden-item events.

The built ROM passed 36 automated checks executing its compiled functions in mGBA, including encounter limits, level caps, permanent removal, ball-only shops, Set mode, hidden-item markers, save creation, full save erasure, and return to the rendered starting map. These targeted checks are not a complete story playthrough or a Visual Boy Advance compatibility test.

Build: https://github.com/Akash555-Ajith/Pokemon-mod-Rom/actions/runs/38246785066

Emulator checks: https://github.com/Akash555-Ajith/Pokemon-mod-Rom/actions/runs/38249171216

ROM SHA-256: `0f3edd5b48802815bc9dc0a9f5d57dfc55979ce6b3b9c644ea2354eae33823e9`

The workflow only uploads a downloadable build artifact. It does not overwrite the repository's existing ROMs or push generated files back into the repository.

Sources are pinned to pret/pokeemerald `731ad5bfd6e6f265508d0efcca0ba42f9dcf5881` and pret/agbcc `da598c1d918402c42c0c0d7128ba14567f3175e9`.
