// The reveal panel: fires on win AND loss (HANDOFF.md §5). Fetches the
// word's data/entries/{WORD}.json lazily — only the day's answer, never the
// whole bank — and renders photo/blurb/facts/audio/link/credits/share.

import { loadSoundPref, saveSoundPref } from "./storage.js";
import { loadStats } from "./stats.js";

let soundEnabled = loadSoundPref();
let primedAudioEl = null;
let currentPlaybackEl = null;

// HANDOFF §6: initialize audio on the player's FIRST keystroke of the
// session, not at reveal time — otherwise the first clip of the session can
// silently fail on Safari. This is defense-in-depth; the real playback below
// is also always triggered synchronously inside a click handler, which is
// gesture-compliant on its own.
export function primeAudioOnce() {
  if (primedAudioEl) return;
  primedAudioEl = new Audio();
  primedAudioEl.muted = true;
  primedAudioEl.load();
}

export function isSoundEnabled() {
  return soundEnabled;
}

export function setSoundEnabled(enabled) {
  soundEnabled = enabled;
  saveSoundPref(enabled);
}

function emojiGrid(guesses) {
  const map = { green: "🟩", yellow: "🟨", grey: "⬜" };
  return guesses.map((g) => g.feedback.map((f) => map[f]).join("")).join("\n");
}

export function buildShareText({ dateStr, puzzle, guesses, status }) {
  const tries = status === "won" ? `${guesses.length}/6` : "X/6";
  const tag = puzzle.word.category === "character" ? " ★" : "";
  return `Birdle ${dateStr}${tag} ${tries}\n\n${emojiGrid(guesses)}`;
}

function renderStats() {
  const s = loadStats();
  const winPct = s.played ? Math.round((s.won / s.played) * 100) : 0;
  const stat = (value, label) =>
    `<div class="stat"><span class="stat-value">${value}</span><span class="stat-label">${label}</span></div>`;
  return `
    <div class="reveal-stats">
      ${stat(s.played, "Played")}
      ${stat(winPct, "Win %")}
      ${stat(s.currentStreak, "Streak")}
      ${stat(s.maxStreak, "Max streak")}
    </div>
  `;
}

function renderFacts(facts) {
  if (!facts || facts.length === 0) return "";
  return `<ul class="reveal-facts">${facts
    .map((f) => `<li>${escapeHtml(f)}</li>`)
    .join("")}</ul>`;
}

function escapeHtml(s) {
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}

function stopCurrentPlayback() {
  if (currentPlaybackEl) {
    currentPlaybackEl.pause();
    currentPlaybackEl = null;
  }
}

/**
 * @param {HTMLElement} panelEl - container to render into
 * @param {object} ctx - { dateStr, puzzle, guesses, status }
 * @param {() => void} [onClose] - called when the player dismisses the panel
 */
export async function showRevealPanel(panelEl, ctx, onClose) {
  const { puzzle, status } = ctx;
  const answer = puzzle.word.word;

  panelEl.hidden = false;
  panelEl.innerHTML = `<div class="reveal-loading">Loading ${answer}…</div>`;
  // Two rAFs so the browser commits the pre-transition state before we add
  // the class that triggers the slide-up (otherwise it can just snap open).
  requestAnimationFrame(() =>
    requestAnimationFrame(() => panelEl.classList.add("open"))
  );

  let entry = null;
  try {
    const res = await fetch(`../data/entries/${answer}.json`);
    if (res.ok) entry = await res.json();
  } catch {
    // fall through to the no-entry-data fallback below
  }

  const resultLabel = status === "won" ? "You got it!" : "Out of tries";

  const photoHtml = entry?.image
    ? `<picture class="reveal-photo">
         <source srcset="../${entry.image.file}" type="image/webp" />
         <img src="../${entry.image.file_jpg}" alt="${escapeHtml(entry.image.alt || answer)}" />
       </picture>`
    : "";

  const audioHtml =
    entry?.audio
      ? `<div class="reveal-audio">
           <button type="button" class="reveal-audio-btn" aria-label="Play recording">
             <span class="play-icon" aria-hidden="true">▶</span> Play call
           </button>
           <p class="reveal-audio-label">${escapeHtml(entry.audio.label)}</p>
         </div>`
      : "";

  const creditsParts = [];
  if (entry?.image?.credit) creditsParts.push(escapeHtml(entry.image.credit));
  if (entry?.audio?.credit) creditsParts.push(escapeHtml(entry.audio.credit));
  const creditsHtml = creditsParts.length
    ? `<p class="reveal-credits">${creditsParts.join("<br>")}</p>`
    : "";

  const linkHtml = entry?.link?.url
    ? `<a class="reveal-link" href="${entry.link.url}" target="_blank" rel="noopener noreferrer">
         View on ${escapeHtml(entry.link.label || "Wikipedia")} ↗
       </a>`
    : "";

  const blurbHtml = entry?.blurb
    ? `<p class="reveal-blurb">${escapeHtml(entry.blurb)}</p>`
    : "";

  panelEl.innerHTML = `
    <button type="button" class="reveal-close" aria-label="Hide details">✕</button>
    <div class="reveal-main">
      ${photoHtml}
      <div class="reveal-text">
        <p class="reveal-result">${resultLabel}</p>
        <h2 class="reveal-word">${answer}</h2>
        ${blurbHtml}
        ${renderFacts(entry?.facts)}
        ${audioHtml}
        ${linkHtml}
        ${creditsHtml}
      </div>
    </div>
    ${renderStats()}
    <button type="button" class="reveal-share-btn">Share result</button>
  `;

  panelEl.querySelector(".reveal-close").addEventListener("click", () => {
    hideRevealPanel(panelEl);
    if (onClose) onClose();
  });

  const audioBtn = panelEl.querySelector(".reveal-audio-btn");
  if (audioBtn && entry?.audio) {
    audioBtn.addEventListener("click", () => {
      setSoundEnabled(true); // clicking play is itself the opt-in gesture
      stopCurrentPlayback();
      const audio = new Audio(`../${entry.audio.file}`);
      let triedFallback = false;
      audio.onerror = () => {
        // fallback format if the primary (webm/opus) fails to decode — but
        // only once, or a fallback that ALSO 404s would retrigger onerror
        // forever (both assign a new src, which re-fires the error event).
        if (triedFallback) return;
        triedFallback = true;
        audio.src = `../${entry.audio.fallback}`;
        audio.play().catch(() => {});
      };
      currentPlaybackEl = audio;
      audio.play().catch(() => {});
    });
  }

  const shareBtn = panelEl.querySelector(".reveal-share-btn");
  shareBtn.addEventListener("click", async () => {
    const text = buildShareText(ctx);
    try {
      await navigator.clipboard.writeText(text);
      shareBtn.textContent = "Copied!";
    } catch {
      shareBtn.textContent = "Couldn't copy — see console";
      console.log(text);
    }
    setTimeout(() => {
      shareBtn.textContent = "Share result";
    }, 1800);
  });
}

export function hideRevealPanel(panelEl) {
  stopCurrentPlayback();
  panelEl.classList.remove("open");
  // Let the slide-down transition finish before removing from layout;
  // reduced-motion users get 0 duration so this resolves ~immediately.
  const duration = matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 250;
  setTimeout(() => {
    if (!panelEl.classList.contains("open")) panelEl.hidden = true;
  }, duration);
}
