// localStorage persistence. Puzzles are on-demand now, not one-per-day (see
// scheduler.js), so there's a single "current game" record — not one per
// date — that survives a reload but gets overwritten whenever the player
// starts a new puzzle.

const CURRENT_GAME_KEY = "birdle:currentGame";

export function loadCurrentGame() {
  try {
    const raw = localStorage.getItem(CURRENT_GAME_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function saveCurrentGame(gameState) {
  try {
    localStorage.setItem(CURRENT_GAME_KEY, JSON.stringify(gameState));
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
