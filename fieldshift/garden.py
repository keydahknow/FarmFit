"""Home and small-space gardening: crops, containers and beginner guides.

Container sizes and spacing follow common extension guidance (University of
Florida IFAS container vegetable guide, Caribbean extension leaflets) and are
starting points, not rules. Crops that are also in the FarmFit crop table get
this garden's own climate-based planting window.
"""

# name, in crop table?, space types it suits, container guide, days to first harvest, sun, beginner tip
CROPS = [
    ("Callaloo", True, ["Containers or pots", "Raised bed", "Backyard plot"], "10 L pot or larger", "35-50", "Full sun",
     "Pick the top leaves often and it keeps producing for months."),
    ("Pak Choi", True, ["Containers or pots", "Raised bed", "Balcony or wall (vertical)"], "5-10 L pot", "40-50", "Sun or part shade",
     "Grows fast; best in the cooler, drier months."),
    ("Chive / scallion", False, ["Containers or pots", "Balcony or wall (vertical)", "Raised bed"], "3-5 L pot", "60-80", "Sun or part shade",
     "Cut leaves 3 cm above the base and they regrow."),
    ("Culantro (shado beni / chadon beni)", False, ["Containers or pots", "Raised bed"], "5 L pot", "70-90", "Part shade",
     "Likes shade and moist soil; remove flower stalks to keep leaves coming."),
    ("Thyme", False, ["Containers or pots", "Balcony or wall (vertical)"], "3-5 L pot", "70-90", "Full sun",
     "Do not overwater; let the top of the soil dry between waterings."),
    ("Hot Pepper", True, ["Containers or pots", "Raised bed", "Backyard plot"], "15-20 L pot", "90-120", "Full sun",
     "One plant can feed a household for months; stake it before storm season."),
    ("Sweet Pepper", True, ["Containers or pots", "Raised bed", "Backyard plot"], "15-20 L pot", "75-90", "Full sun",
     "Needs steady watering; uneven watering causes blossom-end rot."),
    ("Tomato", True, ["Containers or pots", "Raised bed", "Backyard plot"], "20 L pot (cherry types do best)", "60-80", "Full sun",
     "Stake or cage it; water the soil, not the leaves, to avoid blight."),
    ("Bodi", True, ["Balcony or wall (vertical)", "Raised bed", "Backyard plot"], "15 L pot with a trellis", "50-60", "Full sun",
     "Grows up a fence or trellis; pick pods young and often."),
    ("Cucumber", True, ["Balcony or wall (vertical)", "Raised bed", "Backyard plot"], "20 L pot with a trellis", "50-60", "Full sun",
     "Train it up a trellis to save space and keep fruit clean."),
    ("Okra", True, ["Raised bed", "Backyard plot", "Containers or pots"], "20 L pot", "50-60", "Full sun",
     "Loves heat; harvest pods every 2 days while small."),
    ("Sweet Potato", True, ["Backyard plot", "Raised bed"], "Large bag or 40 L tub", "100-120", "Full sun",
     "Vines cover bare soil; the leaves are edible too."),
]

GUIDES = [
    ("Start with good soil", [
        "Fill containers with potting mix plus compost, not soil dug from the yard (it packs down and drains badly).",
        "Make sure every pot has drainage holes.",
        "In the ground, mix in compost and raise the bed 15-20 cm if water sits after rain."]),
    ("Watering, simply", [
        "Push a finger into the soil: water only when the top 2-3 cm is dry.",
        "Water early in the morning, at the base of the plant.",
        "Containers dry out fast in the dry season: check them every day.",
        "Mulch with dried grass or leaves to keep the soil moist and cool."]),
    ("Feeding plants", [
        "Compost from kitchen scraps (no meat or oil) and yard waste is the cheapest fertiliser.",
        "Leafy greens like a little nitrogen (well-rotted manure or compost); fruiting plants need steady feeding once they flower."]),
    ("Keeping pests away", [
        "Look under leaves twice a week; squash caterpillars and egg clusters by hand.",
        "Grow herbs and flowers nearby; they bring in insects that eat pests.",
        "A soap-and-water spray (a teaspoon of mild dish soap in a litre of water) knocks back aphids; test on one leaf first.",
        "Report anything spreading fast on the Pest & disease watch map."]),
    ("Before a storm", [
        "Bring pots indoors or into a sheltered corner; lay tall plants down.",
        "Harvest anything close to ripe.",
        "Clear drains so the yard does not flood; tie down shade cloth and trellises."]),
]
