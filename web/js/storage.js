// localStorage persistence for the current day's in-progress/finished game.
// Stats/streak aggregation across days is HANDOFF.md step 8, not built yet —
// this only keeps today's board state intact across a reload.

const PREFIX = "birdle:day:";

export function loadDayState(dateStr) {
  try {
    const raw = localStorage.getItem(PREFIX + dateStr);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function saveDayState(dateStr, state) {
  try {
    localStorage.setItem(PREFIX + dateStr, JSON.stringify(state));
  } catch {
    // localStorage unavailable (private browsing, quota, etc) — the game
    // still works, it just won't survive a reload. Not fatal.
  }
}

const SOUND_PREF_KEY = "birdle:soundEnabled";

export function loadSoundPref() {
  try {
    return localStorage.getItem(SOUND_PREF_KEY) === "true";
  } catch {
    return false;
  }
}

export function saveSoundPref(enabled) {
  try {
    localStorage.setItem(SOUND_PREF_KEY, enabled ? "true" : "false");
  } catch {
    // ignore
  }
}
