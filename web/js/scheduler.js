// Deterministic date-seeded daily puzzle selection. See HANDOFF.md §5.
//
// Design (resolves the §5 OPEN question): there is ONE puzzle per day. Its
// word length (4/5/6/7) is picked pseudo-randomly from the date seed, not
// chosen by the player and not rotated by weekday. Obscurity is weighted
// 60% common / 30% uncommon / 10% obscure, with a same-day-computable rule
// that guarantees no two consecutive days both land on "obscure" (see the
// proof in the comment on isConsecutiveObscureSafe below).

import { seededRand } from "./prng.js";

const LENGTHS = [4, 5, 6, 7];

export function todayDateString(date = new Date()) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function addDays(dateStr, delta) {
  const [y, m, d] = dateStr.split("-").map(Number);
  const dt = new Date(y, m - 1, d);
  dt.setDate(dt.getDate() + delta);
  return todayDateString(dt);
}

function weightedTier(r) {
  if (r < 0.6) return "common";
  if (r < 0.9) return "uncommon";
  return "obscure";
}

// The raw (pre-"no consecutive obscure" adjustment) tier for a given date,
// computed independently from that date's own seed. Draws in the exact same
// order getDailyPuzzle uses (length, then tier) so "what would this date's
// own generation have rolled" is reproducible without recursing through
// history.
function rawTierForDate(dateStr) {
  const rand = seededRand(dateStr);
  rand(); // discard the length draw, keep the sequence aligned
  return weightedTier(rand());
}

// Proof sketch that adjustedTier never yields two consecutive "obscure"
// days: adjustedTier(d) == "obscure" requires raw(d) == "obscure" AND
// raw(d-1) != "obscure" (otherwise we'd have downgraded d). If raw(d-1) !=
// "obscure", then adjustedTier(d-1) == raw(d-1) != "obscure" (the downgrade
// rule only ever fires when raw itself is "obscure"). So adjustedTier(d)
// == "obscure" implies adjustedTier(d-1) != "obscure". No recursion needed.
function adjustedTier(dateStr, rawToday) {
  if (rawToday !== "obscure") return rawToday;
  const rawYesterday = rawTierForDate(addDays(dateStr, -1));
  return rawYesterday === "obscure" ? "uncommon" : "obscure";
}

/**
 * @param {string} dateStr - "YYYY-MM-DD"
 * @param {{words: Array}} wordbank - parsed data/wordbank.json
 * @returns {{date, length, obscurity, word}} word is the full wordbank entry
 */
export function getDailyPuzzle(dateStr, wordbank) {
  const rand = seededRand(dateStr);
  const length = LENGTHS[Math.floor(rand() * LENGTHS.length)];
  const rawToday = weightedTier(rand());
  const obscurity = adjustedTier(dateStr, rawToday);

  const candidates = wordbank.words.filter(
    (w) => w.length === length && w.obscurity === obscurity
  );
  if (candidates.length === 0) {
    // Shouldn't happen (every length x obscurity bucket is non-empty as of
    // the 300-word bank), but fail safe rather than crash the page.
    const fallback = wordbank.words.filter((w) => w.length === length);
    const idx = Math.floor(rand() * fallback.length);
    return { date: dateStr, length, obscurity: fallback[idx].obscurity, word: fallback[idx] };
  }
  const idx = Math.floor(rand() * candidates.length);
  return { date: dateStr, length, obscurity, word: candidates[idx] };
}
