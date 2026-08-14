import { getDailyPuzzle, todayDateString } from "./scheduler.js";
import { computeFeedback, mergeKeyStatus } from "./feedback.js";
import { loadDayState, saveDayState } from "./storage.js";
import {
  showRevealPanel,
  hideRevealPanel,
  primeAudioOnce,
  isSoundEnabled,
  setSoundEnabled,
} from "./reveal.js";
import { recordResult } from "./stats.js";

const MAX_TRIES = 6;
const KEYBOARD_ROWS = [
  ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
  ["A", "S", "D", "F", "G", "H", "J", "K", "L"],
  ["ENTER", "Z", "X", "C", "V", "B", "N", "M", "BACK"],
];

const boardEl = document.getElementById("board");
const keyboardEl = document.getElementById("keyboard");
const statusEl = document.getElementById("status-message");
const categoryBadgeEl = document.getElementById("category-badge");
const revealPanelEl = document.getElementById("reveal-panel");
const revealReopenEl = document.getElementById("reveal-reopen");
const soundToggleEl = document.getElementById("sound-toggle");

// ?date=YYYY-MM-DD lets QA/testing preview a specific day's puzzle without
// waiting for the calendar. Not linked from the UI; harmless if unused.
const dateOverride = new URLSearchParams(location.search).get("date");

const state = {
  dateStr: dateOverride || todayDateString(),
  puzzle: null,
  guessSet: null,
  guesses: [], // array of {word, feedback}
  current: "",
  status: "playing", // "playing" | "won" | "lost"
  keyStatus: {},
  statsRecorded: false,
};

window.__birdleDebug = state;

async function init() {
  const [wordbank] = await Promise.all([
    fetch("../data/wordbank.json").then((r) => r.json()),
  ]);

  state.puzzle = getDailyPuzzle(state.dateStr, wordbank);

  const guessList = await fetch(
    `../data/guesses/${state.puzzle.length}.json`
  ).then((r) => r.json());
  state.guessSet = new Set(guessList.map((w) => w.toUpperCase()));

  restoreDayState();
  renderCategoryBadge();
  renderBoard();
  renderKeyboard();
  attachInput();
  initSoundToggle();
  announce(
    `${state.puzzle.length}-letter word. ${
      state.puzzle.word.category === "character"
        ? "This is a character round."
        : ""
    }`
  );
}

function restoreDayState() {
  const saved = loadDayState(state.dateStr);
  if (!saved) return;
  // Only trust saved state if it matches today's puzzle length (defensive
  // against a mid-day code change or a clock skew edge case).
  if (saved.length !== state.puzzle.length) return;
  state.guesses = saved.guesses || [];
  state.status = saved.status || "playing";
  state.statsRecorded = saved.statsRecorded || false;
  for (const g of state.guesses) {
    mergeKeyStatus(state.keyStatus, g.word, g.feedback);
  }
}

function persist() {
  saveDayState(state.dateStr, {
    length: state.puzzle.length,
    guesses: state.guesses,
    status: state.status,
    statsRecorded: state.statsRecorded,
  });
}

// Guards against double-counting: called once per finished day, even across
// reloads (state.statsRecorded persists in the same per-day storage record).
function recordStatsIfNeeded() {
  if (state.statsRecorded) return;
  if (state.status !== "won" && state.status !== "lost") return;
  recordResult(state.dateStr, state.status === "won", state.guesses.length);
  state.statsRecorded = true;
  persist();
}

function renderCategoryBadge() {
  if (state.puzzle.word.category === "character") {
    categoryBadgeEl.textContent = "★ CHARACTER ROUND";
    categoryBadgeEl.hidden = false;
    boardEl.classList.add("character-round");
  } else {
    categoryBadgeEl.hidden = true;
    boardEl.classList.remove("character-round");
  }
}

// justCompletedRow: only the row that was JUST submitted plays the flip-in
// animation. Every renderBoard() call rebuilds the whole board (simplest
// correct approach for a 6-row grid), but without this, recreating the DOM
// would re-trigger the entrance animation for every already-completed row
// on every keystroke.
function renderBoard(justCompletedRow = -1) {
  boardEl.innerHTML = "";
  boardEl.style.setProperty("--word-length", state.puzzle.length);

  for (let row = 0; row < MAX_TRIES; row++) {
    const rowEl = document.createElement("div");
    rowEl.className = "board-row";
    rowEl.setAttribute("role", "row");

    const guess = state.guesses[row];
    const isCurrentRow = row === state.guesses.length && state.status === "playing";
    const rowLetters = guess
      ? guess.word.split("")
      : isCurrentRow
      ? state.current.padEnd(state.puzzle.length, " ").split("")
      : new Array(state.puzzle.length).fill(" ");

    for (let col = 0; col < state.puzzle.length; col++) {
      const tile = document.createElement("div");
      tile.className = "tile";
      tile.setAttribute("role", "gridcell");
      const letter = rowLetters[col].trim();
      tile.textContent = letter;
      if (guess) {
        tile.classList.add(guess.feedback[col]);
        tile.classList.add("revealed");
        if (row === justCompletedRow) {
          tile.classList.add("flip-in");
          tile.style.setProperty("--flip-delay", `${col * 120}ms`);
        }
      } else if (letter) {
        tile.classList.add("filled");
      }
      rowEl.appendChild(tile);
    }
    boardEl.appendChild(rowEl);
  }
}

function renderKeyboard() {
  keyboardEl.innerHTML = "";
  for (const row of KEYBOARD_ROWS) {
    const rowEl = document.createElement("div");
    rowEl.className = "keyboard-row";
    for (const key of row) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "key";
      if (key === "ENTER" || key === "BACK") btn.classList.add("key-wide");
      btn.textContent = key === "BACK" ? "⌫" : key;
      btn.dataset.key = key;
      btn.setAttribute(
        "aria-label",
        key === "BACK" ? "Backspace" : key === "ENTER" ? "Enter" : key
      );
      const status = state.keyStatus[key];
      if (status) btn.classList.add(status);
      btn.addEventListener("click", () => handleKey(key));
      rowEl.appendChild(btn);
    }
    keyboardEl.appendChild(rowEl);
  }
}

function updateKeyboardStatuses() {
  for (const btn of keyboardEl.querySelectorAll(".key")) {
    btn.classList.remove("green", "yellow", "grey");
    const status = state.keyStatus[btn.dataset.key];
    if (status) btn.classList.add(status);
  }
}

function attachInput() {
  window.addEventListener("keydown", (e) => {
    primeAudioOnce(); // HANDOFF §6: prime on the session's first keystroke
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    const key = e.key.toUpperCase();
    if (key === "ENTER") handleKey("ENTER");
    else if (key === "BACKSPACE") handleKey("BACK");
    else if (/^[A-Z]$/.test(key)) handleKey(key);
  });
}

function initSoundToggle() {
  updateSoundToggleUI();
  soundToggleEl.addEventListener("click", () => {
    setSoundEnabled(!isSoundEnabled());
    updateSoundToggleUI();
  });
}

function updateSoundToggleUI() {
  const enabled = isSoundEnabled();
  soundToggleEl.textContent = enabled ? "🔊" : "🔇";
  soundToggleEl.setAttribute("aria-pressed", String(enabled));
  soundToggleEl.setAttribute(
    "aria-label",
    enabled ? "Sound is on for bird call recordings" : "Enable sound for bird call recordings"
  );
}

function handleKey(key) {
  if (state.status !== "playing") return;

  if (key === "BACK") {
    state.current = state.current.slice(0, -1);
    renderBoard();
    return;
  }

  if (key === "ENTER") {
    submitGuess();
    return;
  }

  if (state.current.length < state.puzzle.length) {
    state.current += key;
    renderBoard();
  }
}

function shakeCurrentRow() {
  const rows = boardEl.querySelectorAll(".board-row");
  const row = rows[state.guesses.length];
  if (!row) return;
  row.classList.remove("shake");
  // Force reflow so the animation can retrigger on repeated invalid guesses.
  void row.offsetWidth;
  row.classList.add("shake");
}

function submitGuess() {
  const guess = state.current;
  if (guess.length !== state.puzzle.length) {
    announce("Not enough letters");
    shakeCurrentRow();
    return;
  }
  if (!state.guessSet.has(guess)) {
    announce(`${guess} is not a recognized word`);
    shakeCurrentRow();
    return;
  }

  const answer = state.puzzle.word.word;
  const feedback = computeFeedback(guess, answer);
  state.guesses.push({ word: guess, feedback });
  mergeKeyStatus(state.keyStatus, guess, feedback);
  state.current = "";

  const won = guess === answer;
  if (won) {
    state.status = "won";
  } else if (state.guesses.length >= MAX_TRIES) {
    state.status = "lost";
  }

  recordStatsIfNeeded();
  persist();
  renderBoard(state.guesses.length - 1);
  updateKeyboardStatuses();

  if (state.status === "won") {
    announce(`Correct! The word was ${answer}.`);
    revealReopenEl.hidden = true;
    showRevealPanel(revealPanelEl, state, () => (revealReopenEl.hidden = false));
  } else if (state.status === "lost") {
    announce(`Out of tries. The word was ${answer}.`);
    revealReopenEl.hidden = true;
    showRevealPanel(revealPanelEl, state, () => (revealReopenEl.hidden = false));
  } else {
    announce(
      feedback
        .map((f, i) => `${guess[i]}: ${f}`)
        .join(", ")
    );
  }
}

function announce(msg) {
  statusEl.textContent = msg;
}

// Resume an already-finished day's game with its panel visible, and wire the
// "Show result" reopen button for whenever the player dismisses it.
function maybeShowEndBannerOnLoad() {
  const onClose = () => (revealReopenEl.hidden = false);
  if (state.status === "won" || state.status === "lost") {
    recordStatsIfNeeded(); // covers a day finished in a previous session
    showRevealPanel(revealPanelEl, state, onClose);
  }
  revealReopenEl.addEventListener("click", () => {
    revealReopenEl.hidden = true;
    showRevealPanel(revealPanelEl, state, onClose);
  });
}

init().then(maybeShowEndBannerOnLoad);
