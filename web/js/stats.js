// Cross-day stats/streak aggregate. Separate from storage.js's per-day game
// state — this is the running total shown in the reveal panel.

const STATS_KEY = "birdle:stats";

const DEFAULT_STATS = {
  played: 0,
  won: 0,
  currentStreak: 0,
  maxStreak: 0,
  guessDistribution: [0, 0, 0, 0, 0, 0], // index 0 = solved in 1 try
  lastWinDate: null, // "YYYY-MM-DD", used for streak continuity
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

function isDayAfter(prevDateStr, dateStr) {
  if (!prevDateStr) return false;
  const [py, pm, pd] = prevDateStr.split("-").map(Number);
  const prev = new Date(py, pm - 1, pd);
  prev.setDate(prev.getDate() + 1);
  const [y, m, d] = dateStr.split("-").map(Number);
  const cur = new Date(y, m - 1, d);
  return prev.getTime() === cur.getTime();
}

/**
 * Call exactly once per finished day (game.js guards this with a
 * statsRecorded flag in the per-day state — see storage.js).
 * @param {string} dateStr
 * @param {boolean} won
 * @param {number} tries - guesses used; only meaningful when won
 */
export function recordResult(dateStr, won, tries) {
  const stats = loadStats();
  stats.played += 1;

  if (won) {
    stats.won += 1;
    if (tries >= 1 && tries <= 6) stats.guessDistribution[tries - 1] += 1;
    stats.currentStreak = isDayAfter(stats.lastWinDate, dateStr)
      ? stats.currentStreak + 1
      : 1;
    stats.maxStreak = Math.max(stats.maxStreak, stats.currentStreak);
    stats.lastWinDate = dateStr;
  } else {
    stats.currentStreak = 0;
  }

  saveStats(stats);
  return stats;
}
