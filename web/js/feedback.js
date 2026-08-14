// Standard two-pass Wordle feedback algorithm — handles duplicate letters
// correctly (a repeated guess letter only lights up yellow as many times as
// it actually remains unmatched in the answer).

export function computeFeedback(guess, answer) {
  const len = answer.length;
  const guessChars = guess.split("");
  const answerChars = answer.split("");
  const result = new Array(len).fill("grey");
  const remaining = {};

  for (let i = 0; i < len; i++) {
    if (guessChars[i] === answerChars[i]) {
      result[i] = "green";
    } else {
      remaining[answerChars[i]] = (remaining[answerChars[i]] || 0) + 1;
    }
  }

  for (let i = 0; i < len; i++) {
    if (result[i] === "green") continue;
    const c = guessChars[i];
    if (remaining[c] > 0) {
      result[i] = "yellow";
      remaining[c]--;
    }
  }

  return result;
}

// Merge feedback into per-letter keyboard status, respecting precedence
// green > yellow > grey so a key already confirmed green never downgrades.
const RANK = { grey: 0, yellow: 1, green: 2 };

export function mergeKeyStatus(keyStatus, guess, feedback) {
  for (let i = 0; i < guess.length; i++) {
    const c = guess[i];
    const status = feedback[i];
    if (!keyStatus[c] || RANK[status] > RANK[keyStatus[c]]) {
      keyStatus[c] = status;
    }
  }
  return keyStatus;
}
