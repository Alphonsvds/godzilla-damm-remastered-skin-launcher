# Godzilla DAMM Remastered Skin Launcher (WIP)

New monster skins for **Godzilla: Destroy All Monsters Melee Remastered**, with a one-click skin switcher.

| Character | Skins |
| --- | --- |
| Gigan | Final Wars, Chainsaw |
| Godzilla | 2004 (Final Wars) |
| Godzilla 2000 | 2004 (Final Wars), including its Burning Millennium version |

## Final Wars Gigan

Play as Final Wars Gigan in **Godzilla: Destroy All Monsters Melee Remastered**, with or without chainsaw arms.
Comes with a one-click skin switcher.

![Final Wars Gigan firing his visor beam](docs/screenshots/beam-canyon-2.webp)

<p align="center">
  <a href="../../releases/latest"><img alt="Download the latest release" src="https://img.shields.io/badge/DOWNLOAD-Latest%20release-e12626?style=for-the-badge&logo=github&logoColor=white" height="44"></a>
</p>

| | |
| --- | --- |
| ![Visor beam over the river](docs/screenshots/beam-river.webp) | ![Final Wars Gigan in the rain](docs/screenshots/city-rain.webp) |
| ![Chainsaw Gigan against Rodan](docs/screenshots/chainsaw-harbor.webp) | ![Downtown fight with Rodan](docs/screenshots/city-rodan.webp) |
| ![Beam across the canyon](docs/screenshots/beam-canyon.webp) | ![Gigan on the city skyline](docs/screenshots/city-skyline.webp) |

### Skins

- **Final Wars:** the Final Wars Gigan model from Godzilla Unleashed (Wii), with upscaled textures.
- **Chainsaw:** the same model with the chainsaw arms from Godzilla (PS3).

## 2004 Godzilla (Final Wars)

The 2004 Final Wars Godzilla, as a skin for both Godzilla and Godzilla 2000. He keeps his own proportions (shorter neck, upright stance), and on Godzilla 2000 the Burning Millennium skin becomes a burning 2004 Godzilla.

| | |
| --- | --- |
| ![2004 Godzilla over Godzilla](docs/screenshots/godzilla-2004.webp) | ![2004 Godzilla over Godzilla 2000](docs/screenshots/godzilla2000-2004.webp) |
| ![Burning 2004 Godzilla over Godzilla 2000](docs/screenshots/godzilla2000-2004-burning.webp) | ![2004 Godzilla's beam across the canyon](docs/screenshots/godzilla2004-beam-canyon.webp) |
| ![2004 Godzilla's beam by the river](docs/screenshots/godzilla2004-beam-river.webp) | ![Burning 2004 Godzilla's beam over the city](docs/screenshots/burning2004-beam-city.webp) |
| ![Burning 2004 Godzilla firing at sunset](docs/screenshots/burning2004-beam-sunset.webp) | ![Burning 2004 Godzilla against King Ghidorah](docs/screenshots/burning2004-vs-ghidorah.webp) |
| ![Burning 2004 Godzilla grappling King Ghidorah](docs/screenshots/burning2004-grapple-ghidorah.webp) | ![Burning 2004 Godzilla behind King Ghidorah](docs/screenshots/burning2004-vs-ghidorah-tail.webp) |
| ![Burning 2004 Godzilla throwing a building](docs/screenshots/burning2004-building-throw.webp) | |

### Skins

- **Godzilla, 2004:** the [2004 Godzilla MMD model by JJJ and MMDCharizard](https://www.deviantart.com/mmdcharizard/art/MMD-Godzilla---Godzilla-2004-%2BDL%2B-831163150), rebuilt for the game's Godzilla skeleton.
- **Godzilla 2000, 2004:** the same model over Godzilla 2000. Picking the game's Burning Millennium skin gives a burning 2004 Godzilla.

## Good to know

- This is a work in progress. The model was rebuilt to fit the Remastered skeleton, so expect some clipping and stretching in places.
- It uses the game's own animations, moves and hitboxes. Only the look changes.
- Offline use only. Use online at your own risk, or switch back to Showa before playing online.
- The Godzilla skins ship their own copy of that Godzilla's skeleton (so he keeps the 2004 proportions), so they can't be combined with other mods that change the same Godzilla.
- Each character keeps its own skin, so Gigan and both Godzillas can wear new skins at the same time.

## Install

<img alt="Godzilla DAMMR Skin Launcher" src="docs/screenshots/launcher.png" width="520">

1. Download **Godzilla_DAMMR_Skin_Launcher_v0.4.zip** from the [latest release](../../releases/latest).
2. Extract it anywhere, for example your Desktop. Keep everything in the folder together.
3. Close the game.
4. Open the **Godzilla DAMMR Skin Launcher** folder and run **Godzilla DAMMR Skin Launcher.exe**.
5. Pick a character, pick a skin and click **Apply & Play**.

The launcher finds the game through Steam on its own. If it can't, click **Browse for game folder** and pick the game's folder (the one that has GZPro in it).

Windows may show a SmartScreen warning because the launcher isn't signed. Click **More info**, then **Run anyway**.

### Install by hand

You can do it this way, but the launcher is a million times easier.

1. Download **Godzilla_DAMMR_Skins_v0.4_Files.zip** from the [latest release](../../releases/latest).
2. In Steam, right-click the game, then **Manage > Browse local files**.
3. Open `GZPro\Content\Paks` and create a folder named `~mods` if it isn't there.
4. Pick ONE Gigan skin folder, `Gigan\Final Wars` or `Gigan\Chainsaw`, and copy all three files inside it (`zGiganFW_P.pak`, `.ucas` and `.utoc`) into `~mods`.

To switch skins, delete those three files from `~mods` and copy in the three from the other folder.

The 2004 Godzilla skins work the same way, each with its own three files: `Godzilla\2004` (`zHeisei2004_P`) and `Godzilla 2000\2004` (`zGodzilla2004_P`).

## Uninstall

Pick Showa in the launcher and click Apply, or delete the three `zGiganFW_P` files from `GZPro\Content\Paks\~mods`.
For the Godzillas, pick Heisei (Godzilla) or Millennium (Godzilla 2000), or delete their `zHeisei2004_P` / `zGodzilla2004_P` files.

## What's in this repo

- `launcher/` is the Godzilla DAMMR Skin Launcher (C#, .NET 10, Windows Forms). It copies the chosen skin's three files into `~mods`, removes only files it installed itself, and starts the game.
- `scripts/` and `build_all.ps1` are the pipeline that fits the Wii and PS3 models onto the game's skeleton (Blender) and packages them (Unreal Engine 5.8).
- `exporter/` is a small CUE4Parse tool used to read the game's skeleton, animations and textures.

The models and textures themselves aren't in the repo, only in the release downloads.

## Credits

Models from Godzilla Unleashed (Wii) and Godzilla (PS3). 2004 Godzilla model by JJJ and MMDCharizard ([MMD Godzilla - Godzilla 2004 on DeviantArt](https://www.deviantart.com/mmdcharizard/art/MMD-Godzilla---Godzilla-2004-%2BDL%2B-831163150)). Built with CUE4Parse, UE4SS, Blender, Unreal Engine 5 and Real-ESRGAN.
