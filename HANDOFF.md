# Birdle — Handoff Brief

A Wordle variant where every answer is a bird, a bird-anatomy/behavior term, or a
famous fictional bird. On solve or fail, a panel slides up from the bottom with a
photo of the answer and a short write-up.

Everything below is decided unless marked **OPEN**. Write all files into the
project working directory. Nothing gets committed until we review together.

---

## 1. Game rules (settled)

| Rule | Value |
|---|---|
| Word lengths | 4, 5, 6, 7 |
| Tries | **6 at every length** |
| Guess validation | Any valid English word of the right length |
| Answer pool | The Birdle bank only (`data/wordbank.json`) |
| Feedback | Standard Wordle green / yellow / grey |

**The guess/answer asymmetry is load-bearing.** Players must be able to burn a
turn on a probe like STARE or CLINT. If guesses were restricted to bird words,
they'd have to guess candidates directly and deduction collapses. Use a standard
open English word list (e.g. `dwyl/english-words` or the Wordle allowed list) for
guess validation, filtered to the current length.

3-letter mode was considered and dropped — only ~24 viable words, memorized in a
week.

### Character rounds need a visual signal

Proper nouns break the implicit contract of a word game. A player staring at
`_ A Z U` has no path to ZAZU if they assume real vocabulary. Before the first
guess, character rounds must be visibly distinct — different tile border color,
a small badge, or a header label. Player's choice of mechanism, but it can't be a
surprise revealed at the end.

Several words are legitimately both (LEGHORN is a chicken breed and half of
Foghorn Leghorn; PRIVATE is a common word and a Madagascar penguin). The bank
resolves each to exactly one category — no word appears twice. Verified by the
build script.

---

## 2. What's in this handoff

```
HANDOFF.md                  this file
data/wordbank.json          299 curated words, no definitions/images yet
scripts/build_bank.py       regenerates wordbank.json from compact source lists
assets/birdle-hero-DRAFT.png  hero illustration — HAS ERRORS, see §6
```

### `data/wordbank.json` shape

```json
{
  "schema_version": 1,
  "counts": { "5-bird_species": 37, "total": 299 },
  "words": [
    {
      "word": "ROBIN",
      "length": 5,
      "category": "bird_species",
      "obscurity": "common",
      "wikipedia_hint": "Robin",
      "verified": false
    }
  ]
}
```

- `category` — `bird_species` | `bird_adjacent` | `character`
- `obscurity` — `common` | `uncommon` | `obscure`. Drives puzzle scheduling (§5).
- `wikipedia_hint` — **a starting guess, not ground truth.** Hand-written, and
  some are certainly wrong. The enrichment script must verify each one and flag
  mismatches rather than trusting them.
- `verified` — flips to `true` only after a human confirms the fetched article
  and image actually match the word.
- `trademarked` — present on `character` entries only. See §4.

Counts by length: 58 / 78 / 87 / 76 (4/5/6/7 letters).

---

## 3. Enrichment pipeline — build this first

**Do not hand-write 299 definitions, links, or image URLs.** Any URL written from
memory is a coin flip, and a dead image on the reveal panel is worse than no
image. Fetch everything from the API and cache it.

Write `scripts/enrich.py` that, for each bank word:

1. Calls the Wikipedia REST summary endpoint:
   `https://en.wikipedia.org/api/rest_v1/page/summary/{title}` using
   `wikipedia_hint`. On 404, fall back to the search API and take the top hit.
2. Records `title`, `extract`, `canonical_url`, `thumbnail.source`,
   `originalimage.source`, and `type` (watch for `disambiguation`).
3. Downloads the image to `assets/birds/{WORD}.jpg`, resized to ~800px wide,
   WebP with JPEG fallback. **Do not hotlink Wikimedia at runtime** — they ask
   you not to, and it makes the reveal panel fail offline.
4. Fetches the image's license and author via the Commons `imageinfo` API
   (`extmetadata` → `LicenseShortName`, `Artist`, `LicenseUrl`) and stores it.
   Most Commons images are CC-BY-SA and **attribution is mandatory**. An
   unattributed CC-BY-SA photo is a license violation, not a nitpick.
5. Writes `data/entries/{WORD}.json`.
6. Appends anything suspicious to `data/review-queue.json`: 404s, disambiguation
   pages, a returned title that doesn't obviously correspond to the word, missing
   image, or an unclear license.

Be polite to the API: descriptive `User-Agent` with a contact URL, ~1 req/sec,
and cache aggressively so re-runs are cheap. The whole bank is ~300 lookups.

### `data/entries/{WORD}.json` target shape

```json
{
  "word": "PUFFIN",
  "category": "bird_species",
  "title": "Puffin",
  "blurb": "Puffins are stocky seabirds that spend most of the year far out at sea...",
  "facts": [
    "Can hold a dozen or more fish crosswise in its bill at once",
    "Nests in burrows dug into clifftop turf",
    "Beak turns bright orange only for the breeding season"
  ],
  "link": { "label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Puffin" },
  "image": {
    "file": "assets/birds/PUFFIN.webp",
    "alt": "An Atlantic puffin standing on a grassy cliff edge",
    "credit": "Photo by <author> — CC BY-SA 4.0, via Wikimedia Commons",
    "credit_url": "https://commons.wikimedia.org/wiki/File:..."
  },
  "audio": {
    "file": "assets/audio/PUFFIN.webm",
    "fallback": "assets/audio/PUFFIN.mp3",
    "label": "Growling call, recorded at a clifftop colony",
    "duration_sec": 4.2,
    "credit": "Recording by <recordist> — CC BY-NC-SA 4.0, via Xeno-canto",
    "credit_url": "https://xeno-canto.org/..."
  },
  "verified": true
}
```

`blurb` should be the first 1–2 sentences of the Wikipedia extract, trimmed to
~250 characters. `facts` is 2–3 bullets — pull candidates from the extract, but
expect to hand-edit these; the auto-extracted version will be dry. That's fine as
a v1, we can improve them later.

For `bird_adjacent` words the Wikipedia extract is often too technical (SYRINX,
CULMEN, RACHIS). Same pipeline, but plan on a hand-editing pass so these read
like a definition rather than an anatomy paper.

### Character entries need different fields

For `category: "character"`, the reveal should answer: what is it, what was it
in, and who made it.

```json
{
  "word": "TWEETY",
  "category": "character",
  "title": "Tweety",
  "blurb": "A yellow canary who debuted in 1942 and spent the next fifty years...",
  "appearances": ["Looney Tunes", "Merrie Melodies", "Space Jam (1996)"],
  "creators": ["Bob Clampett (creator)", "Mel Blanc (voice)"],
  "studio": "Warner Bros.",
  "first_appearance": "A Tale of Two Kitties (1942)",
  "link": { "label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Tweety" },
  "image": null,
  "image_note": "trademarked — no image, see HANDOFF §4",
  "verified": true
}
```

Wikipedia infoboxes carry most of this, but the REST summary endpoint doesn't
return infobox data. Either parse it from the `parse` API or hand-fill the
character set — there are only 66 of them, and hand-filling is probably faster
and definitely more accurate.

---

## 4. Images: the character problem

**Bird species photos are fine.** Wikimedia Commons is overwhelmingly free-license
for wildlife photography. Attribute per §3 and you're clear.

**Character images are not.** Tweety, Donald, Hedwig, the Pokémon, the Angry
Birds, the Muppets — those images are copyrighted, and the Wikipedia versions are
non-free fair-use files licensed for use *on Wikipedia*, not for reuse. Scraping
them into a game is straightforward infringement. Fandom wiki images are the same
story with worse provenance.

So: **`character` entries ship with `image: null` in v1.** The enrichment script
must skip image fetching entirely when `trademarked: true`. Don't let it quietly
grab a non-free file.

Options for filling that space, in order of my preference:

1. **Commission or generate original stylized art** in the game's own visual
   language. A generic yellow cartoon canary for Tweety infringes nothing.
2. **Silhouette or icon** — clean, cheap, reads as a deliberate style choice.
3. **Text-only reveal** with a nice typographic treatment. Perfectly acceptable.

Five character entries are marked `trademarked: false` — KEHAAR, GWAIHIR, POLLY,
WOODSY, OPUS — as older, literary, generic, or government-produced. Those are
lower risk but still worth checking individually before pulling any image.

Separately from images: **the names themselves.** Character names generally aren't
copyrightable, so a word list isn't the exposure. The trademark risk is that a
public game where players guess DONALD and TWEETY can read as implying Disney or
Warner involvement. Fine for something private; if this goes public or takes
money, that's a conversation with an actual IP lawyer. I'm not one, and this
brief isn't legal advice. The `trademarked` flag exists so we can strip the whole
character mode with one filter if we decide to.

---

## 5. Reveal panel

Fires on solve **and** on fail. On fail, show the answer prominently first — the
player needs to see what they missed before they'll read anything else.

Layout, bottom of the board:

- Photo left (or top, on mobile), ~120px square, rounded
- Word in the game's display face
- Blurb, then 2–3 facts as bullets
- Play button for the bird call, if a clip exists (§6) — omit entirely if not
- Link out to Wikipedia, opens in a new tab
- Photo and recording credits in small type — required, not optional
- Share button (standard Wordle emoji grid) below the panel

Slide up with a short animation, ~250ms. Keep it dismissable and don't trap
keyboard focus inside it.

**Scheduling** (uses `obscurity`): don't serve three obscure words in a row. A
run of POCHARD → ORTOLAN → TINAMOU will lose players faster than any try count.
Suggested weighting per puzzle: 60% common, 30% uncommon, 10% obscure, with a
hard rule that no two consecutive puzzles are `obscure`. Puzzle schedule should
be deterministic from a date seed so everyone gets the same word.

**OPEN:** do the four lengths rotate by day of week, run as parallel daily
puzzles, or does the player pick? Affects the scheduler, so worth deciding before
you build it.

---

## 6. Audio on reveal

When the panel opens, offer a bird call for `bird_species` entries. Same shape as
images: free-licensed sources only, downloaded and cached locally, and the panel
must look right when there's no clip.

### Source

**Xeno-canto** is the one to use — a large archive of user-contributed bird
recordings, almost all CC-licensed, with a search API that takes a species name.
Check its current API terms and whether it now requires a registered key before
building against it; that has changed recently and I don't want you coding to a
stale assumption. Wikimedia Commons is a decent secondary source for the common
species. **Macaulay Library** has better recordings but tighter reuse terms —
read them carefully before pulling anything.

Extend `scripts/enrich.py` to query by the resolved Wikipedia title, prefer
recordings tagged as song or call over flight/alarm calls, prefer higher quality
ratings, and take one clip per word. Normalize loudness, trim to **3–6 seconds**,
encode to Opus in WebM with an MP3 fallback. Cache to `assets/audio/{WORD}.webm`.

Attribution is mandatory the same way it is for photos — Xeno-canto's CC licenses
require recordist credit. Store it alongside the file and render it in the panel.

### Coverage is going to be partial, by design

- **`bird_adjacent` words get no audio.** There is no sound of a GIZZARD. Roughly
  87 of the 299 entries are in this bucket.
- **Many species won't have a usable clip** — the obscure end especially (HUIA is
  extinct; TAKAHE, KAKAPO, HOHO-type rarities may have nothing clean).
- So audio is a bonus, never a load-bearing part of the reveal. If the clip is
  missing, the button simply isn't rendered. No broken player, no empty slot, no
  "audio unavailable" message.

Log coverage counts at the end of the enrich run so we can see what we actually got.

### Character audio: don't

Same answer as character images, and the exposure is larger. A Tweety catchphrase
clip is copyrighted twice over — the recording and the voice performance — and
voice actors and their estates are actively litigious about exactly this. Mel
Blanc's performances are not free to sample because the character is famous.

`character` entries get `audio: null` in v1. The script must not fetch audio for
anything flagged `trademarked`, and it must not fall back to YouTube rips, sound
effect sites, or fan archives, all of which are just infringement with extra
steps. If we want sound on character reveals later, the clean route is original
recordings we commission or make ourselves.

### Playback behavior — get this right or people will hate it

- **Default to muted.** People play word games in bed, in meetings, on transit.
  A bird shrieking out of a phone at 11pm is how you get uninstalled. Sound is
  opt-in, and the preference persists in `localStorage`.
- **Manual play button** on the panel — a small speaker icon. Even with sound
  enabled, I'd lean toward the player pressing it rather than autoplay on reveal.
  **OPEN:** your call, but if you do autoplay-on-enabled, make it easy to turn off
  without digging through settings.
- Browsers block audio until a user gesture. The reveal follows a guess, so a
  gesture has occurred, but initialize the audio context on the player's *first*
  keystroke of the session rather than at reveal time — otherwise the first clip
  of each session silently fails on Safari.
- Respect `prefers-reduced-motion` for the panel animation; that setting doesn't
  govern audio, but the same players often want both dialed down.
- Preload the clip for the day's answer only. Don't ship 200 audio files to
  someone playing one puzzle.

### Accessibility

Audio supplements the text, never replaces it. Every clip needs a short text
label in the panel — "Song of the European robin, recorded in Surrey" — so the
information is available to a deaf player and to anyone with sound off, which by
the default above is everyone on their first visit.

---

## 7. The hero image needs fixing before it ships

`assets/birdle-hero-DRAFT.png` is a good illustration with three rendering errors
in the text. Word-game players are precisely the audience that will notice.

1. **The fourth board row reads `ROINS`.** Meant to be ROBIN. This is the one
   that gets screenshotted.
2. **The keyboard is garbled** — H, P, U, X missing; R and D duplicated; bottom
   row out of order.
3. **The tile colors are inconsistent** — row 1 has E green in position 3 while
   row 2 has N green in the same position. Both can't be true of one answer.

Cheapest good fix: use it as **background texture only**. Fade the lower half
under a gradient and render the real HTML board on top of it. That kills both bad
regions, and a live board in the hero is the stronger design anyway. Alternatives
are cropping the bottom 40% (loses the bird), retouching the text, or
regenerating.

Deliverables when fixed: 1200×630 social card, a squarer mobile crop, WebP with
PNG fallback, target under 150KB. Alt text describes the scene — "A bluebird in a
knit hat at an easel showing the Birdle logo and a puzzle board" — and does not
transcribe the tiles.

**OPEN:** confirm the generator's terms allow commercial use before this becomes
the face of anything public.

---

## 8. Suggested build order

1. `scripts/enrich.py` + run it → `data/entries/`, `assets/birds/`,
   `assets/audio/`, `data/review-queue.json`. **Stop here and report the review
   queue and the audio coverage count** before building UI — if 40 words came
   back wrong or only a third of species have a clip, that changes the plan.
2. Hand-fix the review queue, flip `verified: true`.
3. Hand-fill the 66 character entries.
4. Core game: board, keyboard, guess validation, feedback logic, 6 tries.
5. Deterministic date-seeded scheduler with the obscurity weighting.
6. Reveal panel, including the mute-by-default sound toggle.
7. Hero image treatment.
8. Share grid, stats, streak.

Don't commit anything until we've reviewed. When we do, `assets/birds/` and
`assets/audio/` will together be a few hundred binaries — decide then whether they
belong in the repo, in Git LFS, or behind a build step.

---

## 9. Things I'd want flagged back

- Any word where the fetched Wikipedia article clearly isn't about the bird —
  the `wikipedia_hint` values are educated guesses and some are wrong.
- Words that turn out to be regional or archaic enough that a general player
  would call foul (PEEWIT, TWITE, HUIA are the ones I'd watch).
- Bank entries that aren't valid in your guess-validation word list — that'd mean
  an answer the game itself rejects as a guess. Hard bug, easy to miss.
- Audio coverage: how many `bird_species` entries ended up with a usable clip. If
  it's under half, the play button will feel arbitrary and we should rethink it.
- Any recording whose license turns out to be non-commercial or no-derivatives —
  those need a separate decision, not a silent inclusion.
- If the 4-letter bank feels thin in practice once you're playing it.
