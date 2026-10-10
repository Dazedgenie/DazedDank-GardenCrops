-- Dazed Dank: Garden Crops. Lets Dazed Dank's grow bags, buckets and flood tables take vanilla crops, and gives each
-- crop a plant without its furrow to stand in them. Dazed Dank does the growing, watering and harvesting; this add-on
-- says which crops may go where and supplies the plants.

require "DazedGardenCrops/GardenCropsSprites"

local GC = DazedGardenCrops

-- Crops that need soil: root and bulb crops, big sprawling ones and grains. Grow bags take them, hydro doesn't.
GC.SOIL_ONLY = {
    Potatoes = true, SweetPotato = true, Carrots = true, Radishes = true, SugarBeets = true, Turnip = true,
    Onion = true, Garlic = true, WildGarlic = true, Leek = true,
    Pumpkin = true, Watermelon = true, Corn = true, Zucchini = true,
    Wheat = true, Barley = true, Rye = true, Flax = true,
}

local cropSet = {}
for _, crop in ipairs(GC.CROPS) do cropSet[crop] = true end

--- True if this add-on has plants for a vanilla crop.
function GC.hasCrop(crop)
    return cropSet[crop] == true
end
