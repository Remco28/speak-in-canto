export function createSyncController({ tokenView, audio, seekEpsilonSeconds, highlightEpsilonSeconds, isSyncEnabled }) {
  let tokenToTime = new Map();
  let timeEntries = [];
  let timeEntrySeconds = [];
  let maxTokenId = 0;
  let activeToken = null;
  let animationHandle = null;

  function getCurrentTokenByTime(currentTime) {
    if (timeEntries.length === 0) return null;

    let low = 0;
    let high = timeEntrySeconds.length - 1;
    let found = null;

    while (low <= high) {
      const mid = Math.floor((low + high) / 2);
      const ts = timeEntrySeconds[mid];
      if (ts <= currentTime) {
        found = mid;
        low = mid + 1;
      } else {
        high = mid - 1;
      }
    }

    if (found === null) return null;
    return timeEntries[found].tokenId;
  }

  function setActiveToken(tokenId) {
    if (activeToken === tokenId) return;
    if (activeToken !== null) {
      const prev = tokenView.querySelector(`[data-token-id="${activeToken}"]`);
      if (prev) prev.classList.remove("active");
    }
    activeToken = tokenId;
    if (activeToken !== null) {
      const next = tokenView.querySelector(`[data-token-id="${activeToken}"]`);
      if (next) next.classList.add("active");
    }
  }

  function renderTokens(tokens, markToToken, onTokenClick) {
    tokenView.innerHTML = "";
    tokenToTime = new Map();
    timeEntries = [];
    timeEntrySeconds = [];
    maxTokenId = Math.max(0, (tokens || []).length - 1);
    activeToken = null;

    const markByToken = new Map();
    Object.entries(markToToken || {}).forEach(([mark, tokenId]) => {
      markByToken.set(Number(tokenId), mark);
    });

    const frag = document.createDocumentFragment();
    tokens.forEach((token) => {
      const wrapper = document.createElement("span");
      wrapper.className = "token";
      wrapper.dataset.tokenId = String(token.token_id);

      const mark = markByToken.get(Number(token.token_id));
      if (mark) wrapper.dataset.mark = mark;

      const ruby = document.createElement("span");
      ruby.className = "ruby";
      ruby.textContent = token.jyutping || "";

      const char = document.createElement("span");
      char.className = "char";
      char.textContent = token.char;

      wrapper.appendChild(ruby);
      wrapper.appendChild(char);
      wrapper.addEventListener("click", () => onTokenClick(Number(wrapper.dataset.tokenId), wrapper));
      frag.appendChild(wrapper);
    });

    tokenView.appendChild(frag);
  }

  function buildTimeIndex(timepoints, markToToken) {
    tokenToTime = new Map();
    (timepoints || []).forEach((point) => {
      const tokenId = markToToken[point.mark_name];
      if (tokenId === undefined || tokenId === null) return;
      tokenToTime.set(Number(tokenId), Number(point.seconds));
    });

    tokenToTime = new Map([...tokenToTime.entries()].sort((a, b) => a[0] - b[0]));
    timeEntries = [...tokenToTime.entries()]
      .map(([tokenId, seconds]) => ({ tokenId, seconds }))
      .sort((a, b) => a.seconds - b.seconds);
    timeEntrySeconds = timeEntries.map((entry) => entry.seconds);
  }

  function resolveSeekTime(tokenId) {
    if (tokenToTime.size === 0) return null;
    if (tokenToTime.has(tokenId)) return tokenToTime.get(tokenId);

    let left = tokenId - 1;
    let right = tokenId + 1;
    while (left >= 0 || right <= maxTokenId) {
      if (left >= 0 && tokenToTime.has(left)) return tokenToTime.get(left);
      if (right <= maxTokenId && tokenToTime.has(right)) return tokenToTime.get(right);
      left -= 1;
      right += 1;
    }
    return null;
  }

  function syncHighlightFrame() {
    if (isSyncEnabled() && !audio.paused && !audio.ended) {
      const tokenId = getCurrentTokenByTime(audio.currentTime + highlightEpsilonSeconds);
      setActiveToken(tokenId);
      animationHandle = window.requestAnimationFrame(syncHighlightFrame);
      return;
    }
    animationHandle = null;
  }

  function startSyncLoop() {
    if (animationHandle !== null) return;
    animationHandle = window.requestAnimationFrame(syncHighlightFrame);
  }

  function stopSyncLoop() {
    if (animationHandle !== null) {
      window.cancelAnimationFrame(animationHandle);
      animationHandle = null;
    }
  }

  function seekAndPlay(tokenId) {
    const seekTime = resolveSeekTime(tokenId);
    if (seekTime === null) return;
    audio.currentTime = Math.max(0, seekTime + seekEpsilonSeconds);
    setActiveToken(tokenId);
    const playPromise = audio.play();
    if (playPromise && typeof playPromise.catch === "function") playPromise.catch(() => {});
  }

  function handleSeeking() {
    if (!isSyncEnabled()) return;
    const tokenId = getCurrentTokenByTime(audio.currentTime + highlightEpsilonSeconds);
    setActiveToken(tokenId);
  }

  return {
    renderTokens,
    buildTimeIndex,
    setActiveToken,
    startSyncLoop,
    stopSyncLoop,
    seekAndPlay,
    handleSeeking,
  };
}
