#!/usr/bin/env python3
"""Builds data/wordbank.json for Birdle from compact source lists."""
import json, os

# ---------------------------------------------------------------- source lists
BIRDS = {
4: "crow dove duck hawk ibis kiwi lark loon myna rhea rook swan tern wren coot kite skua chat sora ruff smew teal knot huia gull",
5: "robin eagle finch goose heron macaw raven stork crane egret junco quail snipe swift vireo pipit serin galah scaup eider owlet chick drake poult squab pewee booby stilt saker hobby twite brant diver prion noddy veery grebe",
6: "toucan parrot falcon condor cuckoo pigeon puffin turkey canary oriole magpie osprey avocet gannet godwit grouse linnet merlin peewit plover shrike siskin thrush tomtit wigeon martin bulbul hoopoe jacana kakapo takahe weaver dunlin curlew dipper drongo fulmar petrel peahen turaco chough towhee trogon",
7: "pelican penguin ostrich sparrow swallow vulture buzzard bunting peacock chicken rooster mallard wagtail warbler waxwing kestrel goshawk jackdaw lapwing bittern redpoll seagull skylark babbler moorhen pintail pochard quetzal tanager tinamou manakin gadwall harrier kinglet leghorn marabou ortolan peafowl widgeon catbird cowbird",
}

# Generic words (sky, eye, leg, cage, hover...) deliberately excluded: too weak
# a thematic link, invites "is that even a bird word?" disputes.
ADJACENT = {
4: "nest beak bill wing down molt flap soar worm seed suet claw crop prey call song tail hoot peck nape lore vent rump gape cere aves",
5: "plume perch roost talon brood flock avian quill crest preen hatch wader aerie covey skein alula shaft downy guano tweet trill",
6: "aviary nestle clutch fledge wattle pinion raptor syrinx cloaca covert mantle feeder birder gaggle warble twitch ratite culmen tarsus rachis anting",
7: "feather plumage nesting preened roosted fledged migrate gizzard primary twitter birding perched wingtip remiges barbule contour pecking",
}

CHARACTERS = {
4: "iago zazu huey rico opus bubo peep",
5: "woody daffy daisy dewey louie webby della jewel pedro nigel kevin becky chuck beaky errol polly birdo falco medli chirp quack",
6: "tweety donald hedwig fawkes wilbur plucky stella heihei kehaar henery heckle jeckle paulie chilly rafael gunter woodsy zapdos pidgey fearow piplup rowlet chatot",
7: "foghorn scrooge orville scuttle matilda terence kazooie skipper private camilla celeste gwaihir shirley psyduck spearow moltres pidgeot torchic",
}

# ------------------------------------------------------- wikipedia title hints
# Only where the bare word is ambiguous or redirects somewhere useless.
# The enrichment script MUST still verify every result (see HANDOFF.md).
LOOKUP = {
    # birds
    "chat": "Chat (bird)", "knot": "Red knot", "kite": "Kite (bird)",
    "rook": "Rook (bird)", "crane": "Crane (bird)", "swift": "Swift (bird)",
    "diver": "Loon", "hobby": "Eurasian hobby", "saker": "Saker falcon",
    "martin": "Martin (bird)", "merlin": "Merlin (bird)", "brant": "Brant (goose)",
    "weaver": "Weaver (bird)", "dipper": "Dipper", "wigeon": "Wigeon",
    "widgeon": "Wigeon", "peewit": "Northern lapwing", "harrier": "Harrier (bird)",
    "chick": "Chicken", "drake": "Duck", "poult": "Poultry", "squab": "Squab (food)",
    "owlet": "Owl", "peahen": "Peafowl", "leghorn": "Leghorn chicken",
    "rooster": "Chicken", "seagull": "Gull", "booby": "Booby",
    "grebe": "Grebe", "stilt": "Stilt", "petrel": "Petrel",
    # "Robin" bare is a disambiguation page (American vs European); the
    # European robin is the eponymous one the name derives from.
    "robin": "European robin",
    # adjacent
    "down": "Down feather", "crop": "Crop (anatomy)", "lore": "Lore (anatomy)",
    "vent": "Cloaca", "cere": "Cere", "aves": "Bird", "gape": "Beak",
    "nape": "Nape", "rump": "Rump (animal)", "call": "Bird vocalization",
    "song": "Bird vocalization", "molt": "Moulting", "suet": "Suet",
    # "Hoot"/"Tweet" bare each 404 or disambiguate into unrelated kids'
    # media / Twitter/X — verified wrong during the first enrich.py run.
    "hoot": "Owl", "tweet": "Bird vocalization",
    # "Nestle" bare resolves to the Nestlé corporation, not the verb.
    "nestle": "Bird nest",
    # Peep, Chirp, and Quack: the trio from WGBH/9 Story Entertainment's
    # "Peep and the Big Wide World" (2003, Discovery Kids -> PBS Kids).
    # No individual character pages exist on Wikipedia; all three point at
    # the show page and get a hand-written blurb like the other characters.
    "peep": "Peep and the Big Wide World", "chirp": "Peep and the Big Wide World",
    "quack": "Peep and the Big Wide World",
    "plume": "Feather", "talon": "Claw", "quill": "Flight feather",
    "alula": "Alula", "shaft": "Feather", "covey": "Covey", "skein": "Flock (birds)",
    "aerie": "Bird nest", "wader": "Wader", "avian": "Bird", "brood": "Brood",
    "flock": "Flock (birds)", "downy": "Down feather", "guano": "Guano",
    "syrinx": "Syrinx (bird anatomy)", "cloaca": "Cloaca", "covert": "Covert feather",
    "mantle": "Mantle (mollusc)", "pinion": "Flight feather", "wattle": "Wattle (anatomy)",
    "ratite": "Ratite", "culmen": "Beak", "tarsus": "Bird anatomy",
    "rachis": "Feather", "anting": "Anting (bird activity)", "twitch": "Twitcher",
    "gaggle": "Flock (birds)", "clutch": "Clutch (eggs)", "fledge": "Fledge",
    "raptor": "Bird of prey", "remiges": "Flight feather", "barbule": "Feather",
    "contour": "Feather", "primary": "Flight feather", "gizzard": "Gizzard",
    "plumage": "Plumage", "migrate": "Bird migration", "birding": "Birdwatching",
    "birder": "Birdwatching", "twitter": "Bird vocalization",
    # characters
    "woody": "Woody Woodpecker", "daffy": "Daffy Duck", "daisy": "Daisy Duck",
    "donald": "Donald Duck", "tweety": "Tweety", "huey": "Huey, Dewey and Louie",
    "dewey": "Huey, Dewey and Louie", "louie": "Huey, Dewey and Louie",
    "webby": "Webby Vanderquack", "della": "Della Duck", "scrooge": "Scrooge McDuck",
    "iago": "Iago (Disney)", "zazu": "Zazu", "opus": "Opus the Penguin",
    "hedwig": "Hedwig (Harry Potter)", "fawkes": "Fawkes (Harry Potter)",
    "errol": "List of Harry Potter creatures", "foghorn": "Foghorn Leghorn",
    "henery": "Henery Hawk",
    "heckle": "Heckle and Jeckle", "jeckle": "Heckle and Jeckle",
    "chilly": "Chilly Willy", "orville": "The Rescuers", "wilbur": "The Rescuers Down Under",
    "scuttle": "The Little Mermaid (1989 film)", "heihei": "Moana (2016 film)",
    "kevin": "Up (2009 film)", "becky": "Finding Dory", "nigel": "Finding Nemo",
    "rafael": "Rio (2011 film)", "pedro": "Rio (2011 film)", "jewel": "Rio (2011 film)",
    "skipper": "Penguins of Madagascar", "private": "Penguins of Madagascar",
    "rico": "Penguins of Madagascar",
    # "Sing (2016 American film)" was wrong for GUNTER — Sing's Gunter is a
    # pig, not a bird. The bird-relevant Gunter is Adventure Time's penguin.
    "gunter": "Gunter (Adventure Time)",
    "kehaar": "Watership Down", "gwaihir": "Eagle (Middle-earth)",
    "bubo": "Clash of the Titans (1981 film)",
    # "The Rescuers" has no character named Matilda (that film's bird is
    # Orville/Wilbur). The Matilda that's actually a bird is the Angry Birds
    # Movie's anger-management teacher, voiced by Maya Rudolph.
    "matilda": "The Angry Birds Movie",
    "terence": "Angry Birds", "chuck": "Angry Birds", "stella": "Angry Birds",
    "plucky": "Tiny Toon Adventures", "shirley": "Tiny Toon Adventures",
    # bare "Paulie" resolves to a Sopranos mobster; the parrot is the 1998 film.
    "paulie": "Paulie (film)", "camilla": "Camilla the Chicken", "celeste": "Animal Crossing",
    "kazooie": "Banjo-Kazooie", "birdo": "Birdo", "falco": "Falco Lombardi",
    "medli": "The Legend of Zelda: The Wind Waker",
    "beaky": "Beaky Buzzard", "polly": "Pet parrot", "woodsy": "Woodsy Owl",
    "zapdos": "Zapdos", "pidgey": "List of generation I Pokemon",
    "fearow": "List of generation I Pokemon", "spearow": "List of generation I Pokemon",
    "pidgeot": "List of generation I Pokemon", "moltres": "Moltres",
    "psyduck": "Psyduck", "piplup": "Piplup", "rowlet": "Rowlet",
    "chatot": "List of generation IV Pokemon", "torchic": "Torchic",
    # NOTE: "leghorn" (the bird_species chicken breed) is intentionally NOT
    # re-mapped here to "Foghorn Leghorn" — that was a duplicate dict key
    # that silently clobbered the correct "Leghorn chicken" hint above.
    # FOGHORN is the character-category word for the cartoon rooster.
}

# Trademark-encumbered franchises. Everything in CHARACTERS is flagged unless
# listed here as clear.
TM_CLEAR = {"kehaar", "gwaihir", "polly", "woodsy", "opus"}

COMMON = set("""crow dove duck hawk kiwi lark swan wren gull robin eagle finch goose
heron raven stork crane egret quail swift toucan parrot falcon condor cuckoo pigeon
puffin turkey canary oriole osprey thrush magpie martin pelican penguin ostrich
sparrow swallow vulture buzzard peacock chicken rooster mallard seagull skylark
nest beak bill wing down claw prey call song tail feather plumage nesting perch
roost talon flock hatch crest preen quill tweet migrate aviary
woody daffy daisy donald tweety huey dewey louie hedwig scrooge iago zazu
foghorn leghorn skipper kevin nigel""".split())

OBSCURE = set("""huia smew twite serin veery prion noddy scaup galah poult squab pewee
saker sora ruff knot chat tomtit peewit linnet siskin bulbul hoopoe jacana kakapo
takahe dunlin drongo fulmar turaco chough towhee trogon babbler tinamou manakin
gadwall kinglet marabou ortolan widgeon pochard redpoll junco vireo pipit eider
brant diver avocet gannet godwit shrike wigeon quetzal tanager
lore cere aves nape rump gape culmen tarsus rachis alula skein covey syrinx cloaca
covert ratite anting remiges barbule guano
bubo medli kehaar gwaihir henery heckle jeckle beaky woodsy chatot""".split())


def obscurity(w):
    if w in COMMON:
        return "common"
    if w in OBSCURE:
        return "obscure"
    return "uncommon"


entries = []
for cat, table in (("bird_species", BIRDS), ("bird_adjacent", ADJACENT),
                   ("character", CHARACTERS)):
    for length, words in table.items():
        for w in words.split():
            assert len(w) == length, f"{w} is not {length} letters"
            e = {
                "word": w.upper(),
                "length": length,
                "category": cat,
                "obscurity": obscurity(w),
                "wikipedia_hint": LOOKUP.get(w, w.capitalize()),
                "verified": False,
            }
            if cat == "character":
                e["trademarked"] = w not in TM_CLEAR
            entries.append(e)

seen = {}
for e in entries:
    seen.setdefault(e["word"], []).append(e["category"])
dupes = {k: v for k, v in seen.items() if len(v) > 1}

entries.sort(key=lambda e: (e["length"], e["category"], e["word"]))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
out = {
    "schema_version": 1,
    "generated_note": "Hand-curated seed bank. Definitions/images are NOT in this "
                      "file - they are fetched by scripts/enrich.py into "
                      "data/entries/<WORD>.json. See HANDOFF.md.",
    "counts": {},
    "words": entries,
}
for e in entries:
    key = f"{e['length']}-{e['category']}"
    out["counts"][key] = out["counts"].get(key, 0) + 1
out["counts"]["total"] = len(entries)

with open(os.path.join(ROOT, "data", "wordbank.json"), "w") as f:
    json.dump(out, f, indent=2)

print("total:", len(entries))
for k in sorted(out["counts"]):
    print(" ", k, out["counts"][k])
print("cross-category duplicates:", dupes)
