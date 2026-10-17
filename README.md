# Dazed Dank: Garden Crops

An add-on for [Dazed Dank](https://github.com/Dazedgenie/DazedDank) (Project Zomboid, Build 42). With it enabled,
Dazed Dank's grow bags, DWC buckets, RDWC sites and flood tables take vanilla crops as well as cannabis.

- Every vanilla crop grows in a grow bag. Root, bulb, sprawling and grain crops (potatoes, carrots, onions, garlic,
  leeks, pumpkins, watermelons, corn, zucchini, wheat, barley, rye, flax and the like) need soil, so hydro refuses them.
- Crops grow by vanilla's rules. In a bag you water by hand. In hydro the plant drinks from the reservoir and each
  growth step takes 15% less time.
- Harvesting a crop that doesn't regrow leaves the container empty and ready to sow.
- With vanilla's Kill Crops Grown Inside on, a powered grow lamp or a grow room keeps them alive indoors.

Dazed Dank does all of the growing; this add-on supplies the crop rules and a plant for each crop. Vanilla paints the
tilled furrow into every crop sprite, so each crop is drawn here without its soil, as one plant that stands in the
container.

**Requires:** Dazed Dank 0.56 or later. Mod ID `DazedDankGardenCrops`. Multiplayer: the server and every player need it.

## The plants

`tools/make_crop_sprites.py` cuts the plants from the game's own art. It needs the game's `media` folder:

    python tools/make_crop_sprites.py "C:/Program Files (x86)/Steam/steamapps/common/ProjectZomboid/media"

For each crop it reads which part of the sprite is soil from the just-sown stage, removes soil-coloured pixels there,
keeps the plant in the middle of the bed and drops its neighbours, and cuts the unhealthy, dying and dead versions
with the healthy plant's outline. It writes the four `dazeddank_gardencrops_NN` sheets, the sprite map
(`GardenCropsSprites.lua`) and `tools/preview_crops.png` for checking the result by eye. Run it again after a game
update that changes crop art.

Each vanilla sprite maps to one plant, so any crop can later be swapped for a hand-made render without code changes.

## Licence

The code and tools are CC BY-NC-SA 4.0 (see LICENSE). The plant images are cut from Project Zomboid's own crop art,
which belongs to The Indie Stone, and are not covered by that licence.
