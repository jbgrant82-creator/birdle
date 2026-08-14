// Running stats aggregate across all puzzles played, however many that is
// in one sitting — puzzles are on-demand now (see scheduler.js), not one
// per day, so streak is just "consecutive wins," no calendar involved.

const STATS_KEY = "birdle:stats";

const DEFAULT_STATS = {
  played: 0,
  won: 0,
  currentStreak: 0,
  maxStreak: 0,
  guessDistribution: [0, 0, 0, 0, 0, 0], // index 0 = solved in 1 try
};

export function loadStats() {
  try {
    const raw = localStorage.getItem(STATS_KEY);
    return raw ? { ...DEFAULT_STATS, ...JSON.parse(raw) } : { ...DEFAULT_STATS };
  } catch {
    return { ...DEFAULT_STATS };
  }
}

function saveStats(stats) {
  try {
    localStorage.setItem(STATS_KEY, JSON.stringify(stats));
  } catch {
    // ignore — stats just won't persist this session
  }
}

/**
 * Call exactly once per finished puzzle (game.js guards this with a
 * statsRecorded flag on the current-game record — see storage.js).
 * @param {boolean} won
 * @param {number} tries - guesses used; only meaningful when won
 */
export function recordResult(won, tries) {
  const stats = loadStats();
  stats.played += 1;

  if (won) {
    stats.won += 1;
    if (tries >= 1 && tries <= 6) stats.guessDistribution[tries - 1] += 1;
    stats.currentStreak += 1;
    stats.maxStreak = Math.max(stats.maxStreak, stats.currentStreak);
  } else {
    stats.currentStreak = 0;
  }

  saveStats(stats);
  return stats;
}
