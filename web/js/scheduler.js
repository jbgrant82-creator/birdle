// On-demand puzzle selection. Originally a date-seeded "one puzzle per day"
// scheme (see HANDOFF.md §5); revised so players can immediately start
// another puzzle instead of waiting for the next calendar day. Word length
// is still picked pseudo-randomly per puzzle (not player-chosen), and
// obscurity is still weighted 60% common / 30% uncommon / 10% obscure, with
// the same "never two obscure puzzles in a row" rule — just tracked across
// the session's puzzle history instead of across calendar dates.

import { seededRand } from "./prng.js";

const LENGTHS = [4, 5, 6, 7];

export function randomSeed() {
  return `${Date.now()}-${Math.floor(Math.random() * 1e9)}`;
}

function weightedTier(r) {
  if (r < 0.6) return "common";
  if (r < 0.9) return "uncommon";
  return "obscure";
}

/**
 * @param {string} seed - any string; same seed always yields the same puzzle
 * @param {{words: Array}} wordbank - parsed data/wordbank.json
 * @param {string|null} previousObscurity - the obscurity of the last puzzle
 *   played this session, or null if none yet. Prevents two obscure puzzles
 *   back to back.
 * @returns {{seed, length, obscurity, word}} word is the full wordbank entry
 */
export function pickPuzzle(seed, wordbank, previousObscurity = null) {
  const rand = seededRand(seed);
  const length = LENGTHS[Math.floor(rand() * LENGTHS.length)];
  const rawTier = weightedTier(rand());
  const obscurity =
    rawTier === "obscure" && previousObscurity === "obscure" ? "uncommon" : rawTier;

  const candidates = wordbank.words.filter(
    (w) => w.length === length && w.obscurity === obscurity
  );
  if (candidates.length === 0) {
    // Shouldn't happen (every length x obscurity bucket is non-empty as of
    // the 300-word bank), but fail safe rather than crash the page.
    const fallback = wordbank.words.filter((w) => w.length === length);
    const idx = Math.floor(rand() * fallback.length);
    return { seed, length, obscurity: fallback[idx].obscurity, word: fallback[idx] };
  }
  const idx = Math.floor(rand() * candidates.length);
  return { seed, length, obscurity, word: candidates[idx] };
}
