# Pokemon Emerald Mod ROMs

Eight separate English Pokemon Emerald variants. Choose one ROM to play: the changes are **not combined** into a single game.

## Choose a game

All downloads are in [pokemon emerald mod](pokemon%20emerald%20mod/). Open a file on GitHub and select **Download raw file** to download the ROM.

| ROM | What changes |
| --- | --- |
| [Level 100 Trainers](pokemon%20emerald%20mod/Pokemon%20Emerald%20-%20Level%20100%20Trainers.gba) | All 1,825 Pokemon across 854 standard trainer party records are level 100. Species, held items, and explicit moves stay the same. Wild Pokemon and starters are unchanged. |
| [Legendary Trainers](pokemon%20emerald%20mod/Pokemon%20Emerald%20-%20Trainers%20legendary%20pokemon.gba) | Those standard trainer parties use legendary Pokemon, with their **original levels** preserved. Team sizes, held items, IVs, and explicit moves stay the same. Wild Pokemon and starters are unchanged. |
| [Nuzlocke Seven Rules](pokemon%20emerald%20mod/Pokemon%20Emerald%20-%20Nuzlocke%20Seven%20Rules.gba) | Enforces encounter limits, permanent death, full-wipe resets, Poke Ball-only item shops, gym level caps, Set battle style, and hidden-item sparkles. Trainer species and levels remain original. |
| [Random Trainers and Levels](pokemon%20emerald%20mod/Pokemon%20Emerald%20-%20Random%20Trainers%20and%20Levels.gba) | NPC trainer Pokemon reroll among the original 386 species, with independent levels from 1 to 100, at battle start. Rematches reroll too. Party sizes and held items stay the same. |
| [Party Shuffle After Trainers](pokemon%20emerald%20mod/Pokemon%20Emerald%20-%20Party%20Shuffle%20After%20Trainers.gba) | After an NPC trainer battle, each occupied non-Egg party slot becomes a different random species. Levels, EXP progress, items, nicknames, status, and fainted state are preserved; moves are adjusted, keeping existing HM moves. PC Pokemon are unaffected. |
| [Random Evolution Every Level](pokemon%20emerald%20mod/Pokemon%20Emerald%20-%20Random%20Evolution%20Every%20Level.gba) | Each gained level triggers a compulsory random evolution, including Rare Candies and daycare gains. Multiple levels give multiple changes. Everstones and B cannot cancel this rule. Moves, items, nicknames, and level progress are preserved. |
| [Consistent Map Randomizer](pokemon%20emerald%20mod/Pokemon%20Emerald%20-%20Consistent%20Map%20Randomizer.gba) | Doors, stairs, and cave entrances lead to shuffled destinations after you receive your starter. Each entrance keeps its destination across saves, based on the saved trainer ID. |
| [Reverse EXP](pokemon%20emerald%20mod/Pokemon%20Emerald%20-%20Reverse%20EXP.gba) | Battle EXP is subtracted instead of added, lowering levels down to level 1. Evolved Pokemon can de-evolve after battle as levels drop. Starters begin at the normal level 5; original trainer teams and levels remain unchanged. |

The two fixed trainer-table mods do not cover separately generated special teams such as Battle Frontier parties. Automatically selected moves can differ when a species or level changes.

The four randomizers each enable only their named rule. They do not include the fixed level-100, legendary-trainer, or Nuzlocke rules. They are intended for single-player gameplay; link battles and recorded replays retain their original behavior. See the [full randomizer guide](randomizer-build/README.md) for details and edge cases.

## How to play

1. Download the `.gba` variant you want.
2. Open it in a GBA emulator using its **File > Open** command. The repository also contains a Windows executable in [Visual boy advance](Visual%20boy%20advance/).
3. **Start a new game for each variant.** Keep each ROM's distinct filename so its save stays separate.
4. Save through the game's menu and keep backups of saves you care about. Avoid transferring saves or mid-battle save states between variants: they can retain old battle data or incompatible progress.
5. Check your emulator's control settings for the keyboard buttons mapped to the GBA controls.

These are ready-to-open ROM files; the build scripts are not required to play.

## Important rules before starting

### Nuzlocke

- One wild encounter chance per named area; fleeing or failing to catch consumes it. Floors sharing an area name share the chance. Tutorial exceptions apply.
- Fainted Pokemon are permanently removed, including field-poison deaths. Normal revival does not restore them.
- **A full party wipe erases this game's entire in-game save, including boxed Pokemon, and starts a new run.** Other ROMs' saves are unaffected. The game autosaves after relevant events once field scripts finish.
- Normal item shops sell only their originally available Poke Ball types. Found/gifted items still work, except revival of dead Pokemon.
- Gym caps are **15, 19, 24, 29, 31, 33, 42, 46**, then 100 after eight badges. Set battle style is enforced.
- Hidden-item sparkles mark uncollected standard hidden items. Face the tile from beside it and press A.

Read the [complete Nuzlocke guide](nuzlocke-build/README.md) before playing. Emulator save states and external save editors are outside the ROM's enforcement.

### Map randomizer

**A complete story route is not guaranteed.** Entrances are not necessarily paired, and normal story flags and badge requirements still apply. Route boundaries, Fly, Dive, scripted travel, and excluded special maps retain normal behavior.

If stuck while freely moving in the overworld, **hold L + R and press Select** to return outside in Littleroot. Use the keys mapped to those GBA buttons in your emulator.

### Reverse EXP

- Each defeated enemy subtracts the EXP your eligible Pokemon would normally receive, including wild battles. Original participation, Exp. Share and EXP bonuses apply.
- EXP cannot fall below level 1. Level-100 Pokemon can also lose EXP.
- After battle, evolved Pokemon revert when their level falls below their original level-evolution threshold. Stone, trade, friendship and beauty evolutions can reverse one stage per lost level. No level loss means no de-evolution.
- De-evolution retains moves, held items, custom nicknames and remaining EXP. It happens without an evolution animation.
- Rare Candies, daycare gains, EVs, money and story rewards retain their normal behavior. There is no enemy scaling or other balancing change, and none of the earlier mods are included.

Read the [complete Reverse EXP guide](reverse-exp-build/README.md) for details. Start a new game with a separate save.

## Verification and limitations

On **2026-10-15**, the original seven repository ROMs (excluding the later Reverse EXP addition) were checked for:

- Exact size of **16,777,216 bytes (16 MiB)** each.
- Valid GBA header complement checksum and fixed header byte.
- Hash agreement with the existing build/verification records: SHA-256 for the four randomizers and Nuzlocke; SHA-1 for the two fixed trainer mods.

See [verification.json](pokemon%20emerald%20mod/verification.json) for those seven results and [SHA256SUMS.txt](pokemon%20emerald%20mod/SHA256SUMS.txt) for their download integrity checks. A valid header and matching hash confirm file consistency, not a complete gameplay test.

The Reverse EXP ROM is also **16,777,216 bytes (16 MiB)**. Its SHA-256 was verified during upload:

```text
b7d4a0273d38831a1459e1cf348ce32544dd15dad563f178d0b6c8064d76204d  Pokemon Emerald - Reverse EXP.gba
```

Previously recorded validation:

| Variants | Existing validation |
| --- | --- |
| Level 100 / Legendary Trainers | Trainer-table checks covering all 854 records and 1,825 Pokemon. Not emulator play-tested in the existing records. |
| Nuzlocke | 36 targeted automated mGBA checks, documented in the [build guide](nuzlocke-build/README.md). |
| Four randomizers | 53 targeted automated mGBA checks, including evolution animation, map loading, and the Littleroot rescue, documented in the [build guide](randomizer-build/README.md). |
| Reverse EXP | 32 targeted automated mGBA checks covering EXP loss, bonuses, Exp. Share, safe HP, level limits, de-evolution and vanilla item behavior. See the [build guide](reverse-exp-build/README.md) and [successful build](https://github.com/Akash555-Ajith/Pokemon-mod-Rom/actions/runs/39427778308). |

Those earlier emulator suites were **not rerun for this upload**. Full story playthroughs and VisualBoyAdvance-specific compatibility are not established by these checks.

To check a download in PowerShell:

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath '.\Pokemon Emerald - Random Trainers and Levels.gba'
```

Compare the result with the matching filename in `SHA256SUMS.txt` (hexadecimal letter case does not matter).

## Repository layout

- `pokemon emerald mod/`: eight playable ROM variants, plus checksums and file verification results for the original seven.
- `reverse-exp-build/`: Reverse EXP source, patch application script, emulator checks, and detailed guide.
- `randomizer-build/`: randomizer source, patch application script, emulator checks, and detailed guide.
- `nuzlocke-build/`: Nuzlocke patch, input verification, emulator checks, and detailed guide.
- `.github/workflows/`: build and test workflows.
- `Visual boy advance/`: included Windows emulator executable.

The source-based builds use pinned revisions of [pret/pokeemerald](https://github.com/pret/pokeemerald) and [pret/agbcc](https://github.com/pret/agbcc), listed in their build guides. This is an unofficial fan modification project, not an official Pokemon release.
