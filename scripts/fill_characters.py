#!/usr/bin/env python3
"""Hand-fills the 66 character-category entries in data/entries/.

enrich.py's Wikipedia summary fetch gets a title/link for characters, but most
of them redirect to franchise or "List of X characters" pages (no dedicated
article), so the *blurb* and *appearances/creators/studio/first_appearance*
fields need a human-authored pass instead of an auto-extract. See HANDOFF.md
§3 "Character entries need different fields".

This is hand-researched content, not scraped — cross-check anything you're
about to rely on. A few dates (exact debut short/episode for less mainstream
characters) are marked LOW-CONFIDENCE below and are the ones most worth
double-checking.

Does NOT touch: image (stays null per HANDOFF §4), audio (stays null per §6),
title/link (kept from the Wikipedia fetch). Sets needs_hand_fill=False but
deliberately leaves verified=False — that flag is reserved for a human
confirming the match, per data/entries/{WORD}.json's schema note.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENTRIES_DIR = ROOT / "data" / "entries"

# word -> (blurb, appearances, creators, studio, first_appearance)
DATA = {
    "BUBO": (
        "A bronze mechanical owl built by the god Hephaestus and given to "
        "Perseus as a companion in the 1981 fantasy film Clash of the Titans.",
        ["Clash of the Titans (1981)"],
        ["Ray Harryhausen (stop-motion effects/design)"],
        "Metro-Goldwyn-Mayer",
        "Clash of the Titans (1981)",
    ),
    "HUEY": (
        "The eldest-looking of Donald Duck's identical triplet nephews, "
        "recognizable by his red cap in most modern art.",
        ["Donald Duck comic strip", "Donald's Nephews (1938 short)", "DuckTales"],
        ["Al Taliaferro"],
        "Walt Disney Productions",
        "Donald Duck newspaper comic strip (1937)",
    ),
    "IAGO": (
        "Jafar's wisecracking scarlet macaw sidekick in Disney's Aladdin, "
        "later reformed into an ally of the heroes in the sequels and series.",
        ["Aladdin (1992)", "The Return of Jafar (1994)", "Aladdin: The Series"],
        ["Walt Disney Animation Studios"],
        "Walt Disney Animation Studios",
        "Aladdin (1992)",
    ),
    "OPUS": (
        "A round, anxious penguin from Berkeley Breathed's satirical comic "
        "strip Bloom County, known for his prominent nose and gentle nature.",
        ["Bloom County (1980)", "Outland", "Opus"],
        ["Berkeley Breathed"],
        "Washington Post Writers Group (syndication)",
        "Bloom County — background character in 1980, breakout by 1982",
    ),
    "RICO": (
        "The demolitions-obsessed penguin commando who can regurgitate "
        "improbable objects on demand, from Madagascar's penguin squad.",
        ["Madagascar (2005)", "Penguins of Madagascar (2014)", "TV series"],
        ["DreamWorks Animation"],
        "DreamWorks Animation",
        "Madagascar (2005)",
    ),
    "ZAZU": (
        "The excitable red-billed hornbill who serves as majordomo to the "
        "Pride Lands' royal family in Disney's The Lion King.",
        ["The Lion King (1994)", "The Lion King II: Simba's Pride",
         "The Lion King (2019)"],
        ["Walt Disney Animation Studios"],
        "Walt Disney Animation Studios",
        "The Lion King (1994)",
    ),
    "BEAKY": (
        "A gangly, nervous buzzard who spends most of his Looney Tunes "
        "shorts being outwitted or lectured by Foghorn Leghorn.",
        ["Looney Tunes shorts opposite Foghorn Leghorn"],
        ["Robert McKimson"],
        "Warner Bros. Cartoons",
        "A Bird in a Guilty Cage (1952) — LOW-CONFIDENCE, double-check this date",
    ),
    "BECKY": (
        "A loon in Finding Dory who appears briefly to help ferry Marlin and "
        "Nemo — largely a sight gag with almost no dialogue.",
        ["Finding Dory (2016)"],
        ["Pixar Animation Studios (Andrew Stanton)"],
        "Pixar Animation Studios",
        "Finding Dory (2016)",
    ),
    "BIRDO": (
        "A pink, egg-spitting Mario-universe character who debuted as a "
        "boss and became a recurring rival/ally across the Mario spin-off games.",
        ["Yume Kōjō: Doki Doki Panic (1987) / Super Mario Bros. 2 (1988)",
         "Mario Kart, Mario Party, Mario Tennis, Mario Golf series"],
        ["Nintendo"],
        "Nintendo",
        "Yume Kōjō: Doki Doki Panic (1987, Japan)",
    ),
    "CHUCK": (
        "The impatient, super-fast yellow bird of the original Angry Birds "
        "trio, known for his triangular shape and speed-boost ability.",
        ["Angry Birds (2009 mobile game)", "The Angry Birds Movie (2016)"],
        ["Rovio Entertainment (Jaakko Iisalo, design)"],
        "Rovio Entertainment",
        "Angry Birds (2009)",
    ),
    "DAFFY": (
        "The vain, mischievous black duck of Looney Tunes, Bugs Bunny's "
        "frequent rival and one of Warner Bros.' flagship cartoon stars.",
        ["Porky's Duck Hunt (1937)", "Looney Tunes/Merrie Melodies shorts",
         "Space Jam (1996)"],
        ["Tex Avery", "Bob Clampett"],
        "Warner Bros. Cartoons",
        "Porky's Duck Hunt (1937)",
    ),
    "DAISY": (
        "Donald Duck's girlfriend, first drawn as an unnamed love interest "
        "before being formally named and designed for her own Disney short.",
        ["Don Donald (1937, unnamed)", "Mr. Duck Steps Out (1940, as Daisy)",
         "DuckTales", "comics"],
        ["Walt Disney Productions"],
        "Walt Disney Productions",
        "Mr. Duck Steps Out (1940)",
    ),
    "DELLA": (
        "Donald Duck's twin sister and, per modern canon, the mother of "
        "Huey, Dewey, and Louie — a minor comics reference for decades until "
        "DuckTales (2017) made her a lead character.",
        ["Donald Duck comic strip (1937 introduction)", "DuckTales (2017)"],
        ["Al Taliaferro"],
        "Walt Disney Productions / Disney Television Animation",
        "Donald Duck newspaper comic strip (1937)",
    ),
    "DEWEY": (
        "One of Donald Duck's triplet nephews, traditionally shown in a "
        "blue cap, given a distinct attention-seeking personality in DuckTales (2017).",
        ["Donald Duck comic strip", "Donald's Nephews (1938 short)", "DuckTales"],
        ["Al Taliaferro"],
        "Walt Disney Productions",
        "Donald Duck newspaper comic strip (1937)",
    ),
    "ERROL": (
        "The Weasley family's elderly, perpetually exhausted owl, prone to "
        "crash-landing after even short mail deliveries.",
        ["Harry Potter and the Chamber of Secrets (1998 novel) onward"],
        ["J.K. Rowling"],
        "Warner Bros. Pictures (film adaptations)",
        "Harry Potter and the Chamber of Secrets (1998)",
    ),
    "FALCO": (
        "The cocky, independent ace pilot of Star Fox's Arwing squadron, "
        "a falcon and Fox McCloud's rival-turned-ally.",
        ["Star Fox (1993)", "Star Fox 64", "Super Smash Bros. series"],
        ["Nintendo EAD"],
        "Nintendo",
        "Star Fox (1993)",
    ),
    "JEWEL": (
        "A wild Spix's macaw and one of the last of her species in the wild, "
        "who becomes the love interest of the captive-raised Blu in Rio.",
        ["Rio (2011)", "Rio 2 (2014)"],
        ["Blue Sky Studios (Carlos Saldanha)"],
        "Blue Sky Studios / 20th Century Fox Animation",
        "Rio (2011)",
    ),
    "KEVIN": (
        "A large, flightless, brightly colored bird who befriends Carl and "
        "Russell in Pixar's Up — revealed late in the film to be female.",
        ["Up (2009)"],
        ["Pixar Animation Studios (Pete Docter, Bob Peterson)"],
        "Pixar Animation Studios",
        "Up (2009)",
    ),
    "LOUIE": (
        "The most laid-back of Donald Duck's triplet nephews, usually shown "
        "in a green cap.",
        ["Donald Duck comic strip", "Donald's Nephews (1938 short)", "DuckTales"],
        ["Al Taliaferro"],
        "Walt Disney Productions",
        "Donald Duck newspaper comic strip (1937)",
    ),
    "MEDLI": (
        "A Rito — a bird-like race descended from the Zoras — who serves as "
        "one of Link's companions in The Legend of Zelda: The Wind Waker.",
        ["The Legend of Zelda: The Wind Waker (2002)"],
        ["Nintendo EAD"],
        "Nintendo",
        "The Legend of Zelda: The Wind Waker (2002)",
    ),
    "NIGEL": (
        "A brown pelican who helps Marlin and Dory navigate the dentist's "
        "office fish tank in Finding Nemo.",
        ["Finding Nemo (2003)"],
        ["Pixar Animation Studios (Andrew Stanton)"],
        "Pixar Animation Studios",
        "Finding Nemo (2003)",
    ),
    "PEDRO": (
        "A streetwise red-crested cardinal and samba enthusiast, one of Blu "
        "and Jewel's bird friends in Rio de Janeiro.",
        ["Rio (2011)", "Rio 2 (2014)"],
        ["Blue Sky Studios (Carlos Saldanha)"],
        "Blue Sky Studios / 20th Century Fox Animation",
        "Rio (2011)",
    ),
    "POLLY": (
        "Not a single owned character — \"Polly\" is the traditional "
        "generic name for a pet parrot, immortalized by the catchphrase "
        "\"Polly wants a cracker.\"",
        ["Traditional English-language phrase/trope, no single origin work"],
        [],
        None,
        "Folk/traditional usage; no documented single origin",
    ),
    "WEBBY": (
        "Mrs. Beakley's granddaughter, a young duck raised alongside Huey, "
        "Dewey, and Louie — a minor original-series character expanded into "
        "a lead, adventurous role in the 2017 DuckTales reboot.",
        ["DuckTales (1987)", "DuckTales (2017)"],
        ["Disney Television Animation"],
        "Walt Disney Television Animation",
        "DuckTales (1987)",
    ),
    "WOODY": (
        "A loud, laughing red-headed woodpecker created for Universal's "
        "cartoon shorts, known for his distinctive cackling laugh.",
        ["Knock Knock (1940)", "Walter Lantz cartoon shorts",
         "The Woody Woodpecker Show"],
        ["Walter Lantz", "Ben Hardaway"],
        "Walter Lantz Productions / Universal Pictures",
        "Knock Knock (1940)",
    ),
    "CHATOT": (
        "A small, colorful parrot-like Pokémon known for its music-note "
        "tail and its move Chatter, which mimics recorded sounds.",
        ["Pokémon Diamond and Pearl (2006)"],
        ["Game Freak"],
        "Game Freak / Nintendo / Creatures Inc.",
        "Pokémon Diamond and Pearl (2006, Japan)",
    ),
    "CHILLY": (
        "A small, resourceful penguin from Walter Lantz's cartoon shorts, "
        "usually scheming to get past a dim-witted polar bear guard to reach fish.",
        ["Chilly Willy (1953)", "Walter Lantz cartoon shorts"],
        ["Walter Lantz", "Paul J. Smith (director)"],
        "Walter Lantz Productions / Universal Pictures",
        "Chilly Willy (1953)",
    ),
    "DONALD": (
        "Disney's famously short-tempered sailor duck, one of animation's "
        "most enduring stars since his debut in the 1930s.",
        ["The Wise Little Hen (1934)", "Mickey Mouse cartoon shorts",
         "DuckTales", "comics"],
        ["Walt Disney Productions"],
        "Walt Disney Productions",
        "The Wise Little Hen (1934)",
    ),
    "FAWKES": (
        "Albus Dumbledore's phoenix, capable of healing tears and fiery "
        "rebirth from his own ashes.",
        ["Harry Potter and the Chamber of Secrets (1998 novel) onward"],
        ["J.K. Rowling"],
        "Warner Bros. Pictures (film adaptations)",
        "Harry Potter and the Chamber of Secrets (1998)",
    ),
    "FEAROW": (
        "A large, beak-first bird-of-prey Pokémon, the evolved form of Spearow.",
        ["Pokémon Red and Green (1996, Japan)"],
        ["Game Freak"],
        "Game Freak / Nintendo / Creatures Inc.",
        "Pokémon Red and Green (1996, Japan)",
    ),
    "GUNTER": (
        "The Ice King's ever-present penguin servant in Adventure Time — "
        "revealed partway through the series to secretly be an ancient, "
        "world-ending cosmic entity named Orgalorg.",
        ["Adventure Time (2010)"],
        ["Pendleton Ward"],
        "Cartoon Network Studios / Frederator Studios",
        "Adventure Time (2010)",
    ),
    "HECKLE": (
        "One half of Heckle and Jeckle, a pair of wisecracking, identical "
        "magpies with mismatched accents (Heckle's is Brooklyn) who delight "
        "in outsmarting everyone around them.",
        ["The Talking Magpies (1946)", "Terrytoons cartoon shorts"],
        ["Paul Terry"],
        "Terrytoons / 20th Century Fox",
        "The Talking Magpies (1946)",
    ),
    "HEDWIG": (
        "Harry Potter's loyal snowy owl, a gift from Hagrid that becomes one "
        "of the series' most beloved supporting characters.",
        ["Harry Potter and the Philosopher's Stone (1997 novel) onward"],
        ["J.K. Rowling"],
        "Warner Bros. Pictures (film adaptations)",
        "Harry Potter and the Philosopher's Stone (1997)",
    ),
    "HEIHEI": (
        "A none-too-bright rooster who stows away on Moana's canoe and "
        "survives the entire voyage more through luck than sense.",
        ["Moana (2016)"],
        ["Walt Disney Animation Studios"],
        "Walt Disney Animation Studios",
        "Moana (2016)",
    ),
    "HENERY": (
        "A pint-sized but relentlessly aggressive chicken hawk convinced "
        "every rooster he meets — usually Foghorn Leghorn — is a chicken to be caught.",
        ["The Squawkin' Hawk (1942)", "Looney Tunes shorts with Foghorn Leghorn"],
        ["Robert McKimson"],
        "Warner Bros. Cartoons",
        "The Squawkin' Hawk (1942)",
    ),
    "JECKLE": (
        "The other half of Heckle and Jeckle — identical to Heckle but "
        "speaking with a plummy British accent, forming one of animation's "
        "earliest mismatched double acts.",
        ["The Talking Magpies (1946)", "Terrytoons cartoon shorts"],
        ["Paul Terry"],
        "Terrytoons / 20th Century Fox",
        "The Talking Magpies (1946)",
    ),
    "KEHAAR": (
        "A brusque, foreign-accented black-headed gull who helps the rabbits "
        "of the Sandleford warren in Richard Adams' Watership Down.",
        ["Watership Down (1972 novel)", "Watership Down (1978 film)",
         "Watership Down (2018 miniseries)"],
        ["Richard Adams"],
        "Nepenthe Productions (1978 film)",
        "Watership Down (1972 novel)",
    ),
    "PIDGEY": (
        "A common, easily tamed bird Pokémon often caught early by new "
        "trainers, evolving into Pidgeotto and then Pidgeot.",
        ["Pokémon Red and Green (1996, Japan)"],
        ["Game Freak"],
        "Game Freak / Nintendo / Creatures Inc.",
        "Pokémon Red and Green (1996, Japan)",
    ),
    "PIPLUP": (
        "A small penguin Pokémon and one of three starter Pokémon offered "
        "in Pokémon Diamond and Pearl, prized for being proud and hard to train.",
        ["Pokémon Diamond and Pearl (2006)"],
        ["Game Freak"],
        "Game Freak / Nintendo / Creatures Inc.",
        "Pokémon Diamond and Pearl (2006, Japan)",
    ),
    "PLUCKY": (
        "A self-absorbed, fame-obsessed duck at Acme Looniversity, styled as "
        "the next generation's answer to Daffy Duck in Tiny Toon Adventures.",
        ["Tiny Toon Adventures (1990)"],
        ["Tom Ruegger"],
        "Warner Bros. Animation / Amblin Entertainment",
        "Tiny Toon Adventures (1990)",
    ),
    "RAFAEL": (
        "A wise, gregarious toco toucan in Rio who serves as a matchmaker "
        "and mentor to the film's macaw leads.",
        ["Rio (2011)", "Rio 2 (2014)"],
        ["Blue Sky Studios (Carlos Saldanha)"],
        "Blue Sky Studios / 20th Century Fox Animation",
        "Rio (2011)",
    ),
    "ROWLET": (
        "A small grass/flying-type owl Pokémon, one of three starters "
        "introduced in Pokémon Sun and Moon.",
        ["Pokémon Sun and Moon (2016)"],
        ["Game Freak"],
        "Game Freak / Nintendo / Creatures Inc.",
        "Pokémon Sun and Moon (2016)",
    ),
    "STELLA": (
        "A cheerful pink bird who leads her own flock in Angry Birds Stella, "
        "a spin-off franchise built around her and her friends.",
        ["Angry Birds Stella (2014 game/series)", "The Angry Birds Movie (2016, cameo)"],
        ["Rovio Entertainment"],
        "Rovio Entertainment",
        "Angry Birds Stella (2014)",
    ),
    "TWEETY": (
        "A small yellow canary whose wide-eyed innocent act routinely "
        "outmaneuvers Sylvester the cat, one of Warner Bros.' most enduring stars.",
        ["A Tale of Two Kitties (1942)", "Looney Tunes/Merrie Melodies shorts",
         "The Sylvester and Tweety Mysteries"],
        ["Bob Clampett"],
        "Warner Bros. Cartoons",
        "A Tale of Two Kitties (1942)",
    ),
    "WILBUR": (
        "Orville's high-strung younger brother, an albatross who reluctantly "
        "takes over air-taxi duties for the Rescue Aid Society in The Rescuers Down Under.",
        ["The Rescuers Down Under (1990)"],
        ["Walt Disney Feature Animation"],
        "Walt Disney Feature Animation",
        "The Rescuers Down Under (1990)",
    ),
    "WOODSY": (
        "\"Give a hoot, don't pollute\" — Woodsy Owl is a public-service "
        "mascot created by the U.S. Forest Service to promote conservation.",
        ["U.S. Forest Service public-service campaigns since 1971"],
        ["United States Forest Service"],
        "United States Forest Service",
        "1971 (campaign launch)",
    ),
    "ZAPDOS": (
        "A legendary electric/flying-type bird Pokémon said to live inside "
        "thunderclouds, one of the original three legendary birds.",
        ["Pokémon Red and Green (1996, Japan)"],
        ["Game Freak"],
        "Game Freak / Nintendo / Creatures Inc.",
        "Pokémon Red and Green (1996, Japan)",
    ),
    "CAMILLA": (
        "Gonzo the Great's on-again, off-again chicken girlfriend on The "
        "Muppet Show, usually appearing as part of his eccentric act.",
        ["The Muppet Show", "Muppet feature films"],
        ["Jim Henson"],
        "Jim Henson Productions",
        "The Muppet Show, second season (1976–77)",
    ),
    "CELESTE": (
        "An owl who runs the museum observatory in the Animal Crossing "
        "series, teaching players about constellations and trading star fragments.",
        ["Animal Crossing series, since Dōbutsu no Mori (2001, Japan)"],
        ["Nintendo EAD (Katsuya Eguchi)"],
        "Nintendo",
        "Dōbutsu no Mori (2001, Japan)",
    ),
    "FOGHORN": (
        "A blustering, oversized Southern rooster ceaselessly antagonized by "
        "a dim-witted dog and a persistent baby chicken hawk in his Looney Tunes shorts.",
        ["Walky Talky Hawky (1946)", "Looney Tunes shorts"],
        ["Robert McKimson"],
        "Warner Bros. Cartoons",
        "Walky Talky Hawky (1946)",
    ),
    "GWAIHIR": (
        "Windlord, chief of the Great Eagles of Middle-earth, who rescues "
        "Gandalf and other heroes at pivotal moments across Tolkien's legendarium.",
        ["The Hobbit (1937 novel)", "The Lord of the Rings (1954–55 novel)",
         "Peter Jackson film trilogies"],
        ["J.R.R. Tolkien"],
        "New Line Cinema / Warner Bros. Pictures (films)",
        "The Hobbit (1937)",
    ),
    "KAZOOIE": (
        "A wisecracking red-crested breegull who lives in her bear "
        "companion Banjo's backpack, providing flight, combat, and most of "
        "the duo's attitude.",
        ["Banjo-Kazooie (1998)", "Banjo-Tooie (2000)", "Banjo-Kazooie: Nuts & Bolts"],
        ["Rare Ltd. (Gregg Mayles)"],
        "Rare Ltd.",
        "Banjo-Kazooie (1998)",
    ),
    "MATILDA": (
        "A former \"angry bird\" turned zen anger-management instructor for "
        "Red and the flock, introduced for The Angry Birds Movie.",
        ["The Angry Birds Movie (2016)", "The Angry Birds Movie 2 (2019)"],
        ["Rovio Animation", "Sony Pictures Animation (film)"],
        "Columbia Pictures / Sony Pictures Animation, Rovio Animation",
        "The Angry Birds Movie (2016)",
    ),
    "MOLTRES": (
        "A legendary fire/flying-type bird Pokémon said to control fire and "
        "signal the arrival of spring, one of the original three legendary birds.",
        ["Pokémon Red and Green (1996, Japan)"],
        ["Game Freak"],
        "Game Freak / Nintendo / Creatures Inc.",
        "Pokémon Red and Green (1996, Japan)",
    ),
    "ORVILLE": (
        "An earnest, none-too-graceful albatross who serves as air transport "
        "for the Rescue Aid Society mice in The Rescuers.",
        ["The Rescuers (1977)"],
        ["Walt Disney Productions"],
        "Walt Disney Productions",
        "The Rescuers (1977)",
    ),
    "PIDGEOT": (
        "The final evolution of Pidgey, a large bird Pokémon capable of "
        "flying faster than sound.",
        ["Pokémon Red and Green (1996, Japan)"],
        ["Game Freak"],
        "Game Freak / Nintendo / Creatures Inc.",
        "Pokémon Red and Green (1996, Japan)",
    ),
    "PRIVATE": (
        "The youngest and most soft-hearted of Madagascar's penguin "
        "commando squad.",
        ["Madagascar (2005)", "Penguins of Madagascar (2014)", "TV series"],
        ["DreamWorks Animation"],
        "DreamWorks Animation",
        "Madagascar (2005)",
    ),
    "PSYDUCK": (
        "A perpetually confused water-type Pokémon prone to headaches that "
        "trigger unpredictable psychic outbursts.",
        ["Pokémon Red and Green (1996, Japan)"],
        ["Game Freak"],
        "Game Freak / Nintendo / Creatures Inc.",
        "Pokémon Red and Green (1996, Japan)",
    ),
    "SCROOGE": (
        "The famously penny-pinching, adventuring billionaire duck uncle of "
        "Huey, Dewey, and Louie, introduced by Carl Barks and later given his "
        "own DuckTales series.",
        ["\"Christmas on Bear Mountain,\" Four Color #178 (1947)",
         "DuckTales (1987)", "DuckTales (2017)"],
        ["Carl Barks"],
        "Walt Disney Productions",
        "Four Color #178, \"Christmas on Bear Mountain\" (1947)",
    ),
    "SCUTTLE": (
        "An eccentric, well-meaning seagull who mostly misidentifies human "
        "objects for Ariel in The Little Mermaid.",
        ["The Little Mermaid (1989)", "The Little Mermaid: Ariel's Beginning",
         "The Little Mermaid (2023 live-action)"],
        ["Ron Clements", "John Musker"],
        "Walt Disney Feature Animation",
        "The Little Mermaid (1989)",
    ),
    "SHIRLEY": (
        "Shirley the Loon, a New Age-y, dramatically expressive student at "
        "Acme Looniversity in Tiny Toon Adventures.",
        ["Tiny Toon Adventures (1990)"],
        ["Tom Ruegger"],
        "Warner Bros. Animation / Amblin Entertainment",
        "Tiny Toon Adventures (1990)",
    ),
    "SKIPPER": (
        "The gruff, no-nonsense leader of Madagascar's penguin commando "
        "squad, known for his tactical schemes and disdain for anything "
        "\"cute and cuddly.\"",
        ["Madagascar (2005)", "Penguins of Madagascar (2014)", "TV series"],
        ["DreamWorks Animation"],
        "DreamWorks Animation",
        "Madagascar (2005)",
    ),
    "SPEAROW": (
        "A small, easily-provoked bird Pokémon that evolves into Fearow.",
        ["Pokémon Red and Green (1996, Japan)"],
        ["Game Freak"],
        "Game Freak / Nintendo / Creatures Inc.",
        "Pokémon Red and Green (1996, Japan)",
    ),
    "TERENCE": (
        "The largest and quietest of the original Angry Birds cast — a "
        "hulking, near-silent red bird whose few grunted lines were voiced "
        "by the game's own composer.",
        ["Angry Birds (2009 mobile game)", "The Angry Birds Movie (2016)"],
        ["Rovio Entertainment (Jaakko Iisalo, design)"],
        "Rovio Entertainment",
        "Angry Birds (2009)",
    ),
    "TORCHIC": (
        "A small fire-type chick Pokémon, one of three starters offered in "
        "Pokémon Ruby and Sapphire.",
        ["Pokémon Ruby and Sapphire (2002)"],
        ["Game Freak"],
        "Game Freak / Nintendo / Creatures Inc.",
        "Pokémon Ruby and Sapphire (2002, Japan)",
    ),
    "PAULIE": (
        "A talking blue-crowned conure who narrates his own life story — "
        "and his long search for the girl who raised him — to a night "
        "janitor in the 1998 film Paulie.",
        ["Paulie (1998 film)"],
        ["Laurie Craig (writer)", "John Roberts (director)"],
        "DreamWorks Pictures",
        "Paulie (1998)",
    ),
    "PEEP": (
        "A newly hatched chick who wanders from his nest and befriends "
        "Chirp and Quack, the innocent, wide-eyed lead of the preschool "
        "science show Peep and the Big Wide World.",
        ["Peep and the Big Wide World (2004–2011)"],
        ["Kaj Pindal (creator)", "9 Story Entertainment", "WGBH Boston"],
        "9 Story Entertainment / WGBH Boston (Discovery Kids, later PBS Kids)",
        "Peep and the Big Wide World, \"Spring Thing\" (April 12, 2004 premiere)",
    ),
    "CHIRP": (
        "A young robin eager to grow up and fly, one of the trio at the "
        "center of Peep and the Big Wide World alongside Peep and Quack.",
        ["Peep and the Big Wide World (2004–2011)"],
        ["Kaj Pindal (creator)", "9 Story Entertainment", "WGBH Boston"],
        "9 Story Entertainment / WGBH Boston (Discovery Kids, later PBS Kids)",
        "Peep and the Big Wide World, \"Spring Thing\" (April 12, 2004 premiere)",
    ),
    "QUACK": (
        "A bossy, self-important duckling convinced the pond revolves "
        "around ducks, rounding out the trio in Peep and the Big Wide World.",
        ["Peep and the Big Wide World (2004–2011)"],
        ["Kaj Pindal (creator)", "9 Story Entertainment", "WGBH Boston"],
        "9 Story Entertainment / WGBH Boston (Discovery Kids, later PBS Kids)",
        "Peep and the Big Wide World, \"Spring Thing\" (April 12, 2004 premiere)",
    ),
}

missing = []
for word, (blurb, appearances, creators, studio, first_appearance) in DATA.items():
    path = ENTRIES_DIR / f"{word}.json"
    if not path.exists():
        missing.append(word)
        continue
    entry = json.loads(path.read_text())
    entry["blurb"] = blurb
    entry["appearances"] = appearances
    entry["creators"] = creators
    entry["studio"] = studio
    entry["first_appearance"] = first_appearance
    entry["needs_hand_fill"] = False
    path.write_text(json.dumps(entry, indent=2))

print(f"filled {len(DATA)} character entries")
if missing:
    print("WARNING - words in DATA but no entry file found:", missing)

# sanity: which character words exist but weren't covered by DATA?
all_chars = {f.stem for f in ENTRIES_DIR.glob("*.json")
             if json.loads(f.read_text())["category"] == "character"}
uncovered = sorted(all_chars - set(DATA))
if uncovered:
    print("NOT YET FILLED:", uncovered)
else:
    print("all character entries covered")
