"""
make_crop_sprites.py -- build the Garden Crops plant sheets from the game's own crop art.

Vanilla paints the tilled furrow into every crop sprite, as a bed of several plants. For each crop this keeps one
plant and drops the soil, so the plant can stand in a Dazed Dank grow bag, bucket or flood table:

  1. The crop's first (just sown) sprite marks where its soil is; only soil-coloured pixels inside that area go.
  2. Of what is left, the plant standing at the middle of the bed is kept, and the plants around it are dropped.
  3. The unhealthy, dying and dead versions are cut with the healthy plant's outline, since their browns look like soil.

Writes dazeddank_gardencrops_NN sheets (.pack and .tiles), the vanilla-to-ours sprite map Dazed Dank reads, and a
preview sheet. Needs the game installed (or copies of its Tiles2x.pack and media/lua/server/Farming). Run from the
repo root:

    python tools/make_crop_sprites.py "C:/Program Files (x86)/Steam/steamapps/common/ProjectZomboid/media"
"""
import colorsys, math, os, re, sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(__file__))
import pzpack, tdef

MOD = Path("Contents/mods/DazedDankGardenCrops/42/media")
SHEET = "dazeddank_gardencrops_"
WIDTH, ROWS = 8, 64                       # 512 tiles a sheet, the game's limit
CONDITIONS = ["sprite", "unhealthySprite", "dyingSprite", "deadSprite"]
FARMING_FILES = ["farming_vegetableconf_vegetables_sprites.lua", "farming_vegetableconf_herbs_sprites.lua"]
TILE_W, TILE_H = 128, 256
BED_X, BED_Y = 64, 224                    # middle of the floor diamond, where the middle plant stands
KEEP_HALF_WIDTH = 30                      # nothing further than this from the middle survives the cut
MIN_PART = 12                             # loose bits smaller than this (pixels) are dropped


def lua_lists(text):
    """Every farming_vegetableconf.<set>[<crop>] = { "sprite", ... } in a file, as {(set, crop): [names]}."""
    out = {}
    pat = r'farming_vegetableconf\.(\w+)(?:\["(\w+)"\]|\.(\w+))\s*=\s*\{(.*?)\}'
    for m in re.finditer(pat, text, re.S):
        out[(m.group(1), m.group(2) or m.group(3))] = re.findall(r'"(\w+)"', m.group(4))
    return out


def read_vanilla(media):
    """The game's crop sprite lists and every crop sprite in its 2x tile pack, as full-tile images."""
    lists = {}
    for f in FARMING_FILES:
        lists.update(lua_lists((Path(media) / "lua/server/Farming" / f).read_text(encoding="latin1")))
    want = {n for names in lists.values() for n in names}
    _, pages = pzpack.rd((Path(media) / "texturepacks/Tiles2x.pack").read_bytes())
    sprites = {}
    for pg in pages:
        hits = [e for e in pg["ents"] if e[0] in want]
        if not hits:
            continue
        sprites.update({n: f for n, f in pzpack.frames([dict(pg, ents=hits)]).items()})
    return lists, sprites


def soil_area(seed):
    """Where a crop's furrow is: the just-sown sprite's pixels, grown a little."""
    a = seed.getchannel("A").point(lambda v: 255 if v else 0)
    return np.array(a.filter(ImageFilter.MaxFilter(5))) > 0


def soil_pixels(img, area):
    """Pixels inside the furrow area that look like soil or its shadow."""
    rgba = np.asarray(img, dtype=np.float32) / 255
    hsv = np.array(img.convert("RGB").convert("HSV"), dtype=np.float32) / 255
    h, s, v, a = hsv[..., 0] * 360, hsv[..., 1], hsv[..., 2], rgba[..., 3]
    brown = ((h < 50) | (h > 330)) & (v < 0.62) & (s > 0.25)
    shadow = (v < 0.18) | ((a < 1) & (v < 0.35))
    return area & (a > 0) & (brown | shadow)


def components(mask):
    """Label 8-connected regions of a boolean mask. Returns (labels, count)."""
    H, W = mask.shape
    labels = np.zeros((H, W), dtype=np.int32)
    n = 0
    for y0, x0 in zip(*np.nonzero(mask)):
        if labels[y0, x0]:
            continue
        n += 1
        stack = [(y0, x0)]
        labels[y0, x0] = n
        while stack:
            y, x = stack.pop()
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < H and 0 <= xx < W and mask[yy, xx] and not labels[yy, xx]:
                        labels[yy, xx] = n
                        stack.append((yy, xx))
    return labels, n


def middle_plant(mask):
    """Of a soil-free bed, the plant at the middle: a band one plant wide down the middle, without the specks of its
    neighbours that the band clips."""
    H, W = mask.shape
    xx = np.mgrid[0:H, 0:W][1]
    band = mask & (np.abs(xx - BED_X) <= KEEP_HALF_WIDTH)
    labels, n = components(band)
    sizes = np.bincount(labels.ravel(), minlength=n + 1)
    small = sizes < MIN_PART
    small[0] = True
    return band & ~small[labels] if (sizes[1:] >= MIN_PART).any() else band


def with_alpha(img, mask):
    arr = np.array(img)
    arr[..., 3] = np.where(mask, arr[..., 3], 0)
    return Image.fromarray(arr, "RGBA")


def cut_crop(lists, sprites, crop):
    """One crop's soil-free sprites: {vanilla name: image} for every stage and condition."""
    healthy = lists.get(("sprite", crop), [])
    if not healthy or healthy[0] not in sprites:
        return {}
    area = soil_area(sprites[healthy[0]])
    out = {}
    for i, name in enumerate(healthy):
        img = sprites.get(name)
        if img is None:
            continue
        alpha = np.array(img.getchannel("A")) > 0
        plant = middle_plant(alpha & ~soil_pixels(img, area))
        out[name] = with_alpha(img, plant)
        # Sick and dead plants are the same shape recoloured: cut them with the healthy outline.
        outline = np.array(Image.fromarray(plant.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(3))) > 0
        for cond in CONDITIONS[1:]:
            names = lists.get((cond, crop), [])
            if i < len(names) and names[i] in sprites and names[i] not in out:
                out[names[i]] = with_alpha(sprites[names[i]], outline)
    return out


def write_sheets(frames):
    """Pack frames ([(vanilla name, image)]) into sheets of 512. Returns {vanilla name: our sprite name} and sheet names."""
    per = WIDTH * ROWS
    mapping, sheets = {}, []
    for s in range(math.ceil(len(frames) / per)):
        name = f"{SHEET}{s + 1:02d}"
        chunk = frames[s * per:(s + 1) * per]
        named = [(f"{name}_{n}", img) for n, (_, img) in enumerate(chunk)]
        (MOD / "texturepacks").mkdir(parents=True, exist_ok=True)
        (MOD / f"texturepacks/{name}.pack").write_bytes(pzpack.wr(1, pzpack.pack_pages(name, 0, named)))
        rows = math.ceil(len(chunk) / WIDTH)
        tiles = [[("CustomName", "Plant")] if i < len(chunk) else [] for i in range(WIDTH * rows)]
        (MOD / f"{name}.tiles").write_bytes(tdef.wr(1, [dict(name=name, img=name + ".png", w=WIDTH, h=rows, id=1, tiles=tiles)]))
        for n, (vanilla, _) in enumerate(chunk):
            mapping[vanilla] = f"{name}_{n}"
        sheets.append(name)
    return mapping, sheets


def write_map(mapping, sheets, crops):
    lines = [
        "-- Generated by tools/make_crop_sprites.py: do not edit by hand.",
        "-- Each vanilla crop sprite (soil and all) and the soil-free plant Dazed Dank draws in a container instead.",
        "",
        "DazedGardenCrops = DazedGardenCrops or {}",
        "DazedGardenCrops.SHEETS = { " + ", ".join(f'"{s}"' for s in sheets) + " }",
        "DazedGardenCrops.CROPS = { " + ", ".join(f'"{c}"' for c in crops) + " }",
        "DazedGardenCrops.SPRITES = {",
    ]
    lines += [f'    {k} = "{v}",' for k, v in sorted(mapping.items())]
    lines += ["}", ""]
    path = MOD / "lua/shared/DazedGardenCrops/GardenCropsSprites.lua"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="latin1")


def preview(per_crop, path):
    """Every crop's healthy stages in a row, on a plain background, for checking the cut by eye."""
    crops = sorted(per_crop)
    cols = max(len(v) for v in per_crop.values())
    cw, ch = TILE_W, 150
    sheet = Image.new("RGBA", (120 + cw * cols, ch * len(crops)), (70, 72, 88, 255))
    d = ImageDraw.Draw(sheet)
    for r, crop in enumerate(crops):
        d.text((4, r * ch + ch // 2), crop, fill="white")
        for c, img in enumerate(per_crop[crop]):
            sheet.alpha_composite(img.crop((0, TILE_H - ch, TILE_W, TILE_H)), (120 + c * cw, r * ch))
    sheet.save(path)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    lists, sprites = read_vanilla(sys.argv[1])
    crops = sorted({crop for (cond, crop) in lists if cond == "sprite"})
    frames, healthy = [], {}
    for crop in crops:
        cut = cut_crop(lists, sprites, crop)
        frames += list(cut.items())
        healthy[crop] = [cut[n] for n in lists[("sprite", crop)] if n in cut]
    mapping, sheets = write_sheets(frames)
    write_map(mapping, sheets, [c for c in crops if healthy[c]])
    preview(healthy, Path("tools/preview_crops.png"))
    print(f"{len(crops)} crops, {len(frames)} sprites on {len(sheets)} sheets")


if __name__ == "__main__":
    main()
