(function () {
  const config = window.READER_CONFIG || {};
  const maxInputChars = Number(config.maxInputChars || 12000);

  const textInput = document.getElementById("text-input");
  const charCounter = document.getElementById("char-counter");
  const voiceSelect = document.getElementById("voice-select");
  const speedSlider = document.getElementById("speed-slider");
  const speedLabel = document.getElementById("speed-label");
  const readBtn = document.getElementById("read-btn");
  const errorBanner = document.getElementById("error-banner");
  const tokenView = document.getElementById("token-view");
  const audio = document.getElementById("audio-player");
  const syncModeNote = document.getElementById("sync-mode-note");
  const inlinePlayBtn = document.getElementById("inline-play-btn");
  const inlinePauseBtn = document.getElementById("inline-pause-btn");

  let tokenToTime = new Map();
  let timeEntries = [];
  let maxTokenId = 0;
  let activeToken = null;
  const SEEK_EPSILON_SECONDS = 0.02;
  const HIGHLIGHT_EPSILON_SECONDS = 0.03;

  function setError(msg) {
    if (!msg) {
      errorBanner.hidden = true;
      errorBanner.textContent = "";
      return;
    }
    errorBanner.hidden = false;
    errorBanner.textContent = msg;
  }

  function updateCounter() {
    const count = textInput.value.length;
    charCounter.textContent = `${count}/${maxInputChars}`;
  }

  function setLoading(isLoading) {
    readBtn.disabled = isLoading;
    readBtn.textContent = isLoading ? "Reading..." : "Read";
  }

  function getCurrentTokenByTime(currentTime) {
    if (timeEntries.length === 0) return null;

    let found = null;
    for (const entry of timeEntries) {
      const tokenId = entry.tokenId;
      const ts = entry.seconds;
      if (ts <= currentTime) {
        found = tokenId;
      } else {
        break;
      }
    }
    return found;
  }

  function setActiveToken(tokenId) {
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

  function renderTokens(tokens, markToToken) {
    tokenView.innerHTML = "";
    tokenToTime = new Map();
    timeEntries = [];
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
      if (mark) {
        wrapper.dataset.mark = mark;
      }

      const ruby = document.createElement("span");
      ruby.className = "ruby";
      ruby.textContent = token.jyutping || "";

      const char = document.createElement("span");
      char.className = "char";
      char.textContent = token.char;

      wrapper.appendChild(ruby);
      wrapper.appendChild(char);

      wrapper.addEventListener("click", function () {
        const tokenId = Number(wrapper.dataset.tokenId);
        const seekTime = resolveSeekTime(tokenId);
        if (seekTime === null) {
          return;
        }
        audio.currentTime = Math.max(0, seekTime + SEEK_EPSILON_SECONDS);
        setActiveToken(tokenId);
        const playPromise = audio.play();
        if (playPromise && typeof playPromise.catch === "function") {
          playPromise.catch(() => {});
        }
      });

      frag.appendChild(wrapper);
    });

    tokenView.appendChild(frag);
  }

  function buildTimeIndex(timepoints, markToToken) {
    tokenToTime = new Map();
    (timepoints || []).forEach((point) => {
      const tokenId = markToToken[point.mark_name];
      if (tokenId === undefined || tokenId === null) {
        return;
      }
      tokenToTime.set(Number(tokenId), Number(point.seconds));
    });

    // Keep two indexes:
    // 1) token-id based for click seeks
    // 2) seconds-based for smooth timeupdate highlighting
    tokenToTime = new Map([...tokenToTime.entries()].sort((a, b) => a[0] - b[0]));
    timeEntries = [...tokenToTime.entries()]
      .map(([tokenId, seconds]) => ({ tokenId, seconds }))
      .sort((a, b) => a.seconds - b.seconds);
  }

  function resolveSeekTime(tokenId) {
    if (tokenToTime.size === 0) {
      return null;
    }
    if (tokenToTime.has(tokenId)) {
      return tokenToTime.get(tokenId);
    }

    // In reduced mode some tokens have no direct mark.
    // Seek to nearest available marked token (left or right).
    let left = tokenId - 1;
    let right = tokenId + 1;
    while (left >= 0 || right <= maxTokenId) {
      if (left >= 0 && tokenToTime.has(left)) {
        return tokenToTime.get(left);
      }
      if (right <= maxTokenId && tokenToTime.has(right)) {
        return tokenToTime.get(right);
      }
      left -= 1;
      right += 1;
    }

    return null;
  }

  async function synthesize() {
    setError("");

    const text = textInput.value;
    if (!text.trim()) {
      setError("Please enter text.");
      return;
    }

    if (text.length > maxInputChars) {
      setError(`Text exceeds max length (${maxInputChars}).`);
      return;
    }

    setLoading(true);

    try {
      const response = await fetch("/api/tts/synthesize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text,
          voice_name: voiceSelect.value,
          speaking_rate: Number(speedSlider.value),
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        setError(data.error || "Synthesis failed.");
        return;
      }

      renderTokens(data.tokens || [], data.mark_to_token || {});
      buildTimeIndex(data.timepoints || [], data.mark_to_token || {});

      audio.src = data.audio_url;
      audio.playbackRate = Number(speedSlider.value);
      audio.currentTime = 0;

      if (data.sync_mode === "reduced") {
        syncModeNote.hidden = false;
        syncModeNote.textContent = "Reduced sync mode enabled for reliability.";
      } else {
        syncModeNote.hidden = true;
        syncModeNote.textContent = "";
      }
      if (data.jyutping_available === false) {
        syncModeNote.hidden = false;
        syncModeNote.textContent = "Jyutping dependency unavailable on server; showing characters only.";
      }

      const playPromise = audio.play();
      if (playPromise && typeof playPromise.catch === "function") {
        playPromise.catch(() => {});
      }
    } catch (_err) {
      setError("Network or server error.");
    } finally {
      setLoading(false);
    }
  }

  textInput.addEventListener("input", updateCounter);
  speedSlider.addEventListener("input", function () {
    const speed = Number(speedSlider.value).toFixed(1);
    speedLabel.textContent = `${speed}x`;
    audio.playbackRate = Number(speedSlider.value);
  });

  readBtn.addEventListener("click", synthesize);

  audio.addEventListener("timeupdate", function () {
    const tokenId = getCurrentTokenByTime(audio.currentTime + HIGHLIGHT_EPSILON_SECONDS);
    setActiveToken(tokenId);
  });

  if (inlinePlayBtn) {
    inlinePlayBtn.addEventListener("click", function () {
      const p = audio.play();
      if (p && typeof p.catch === "function") {
        p.catch(() => {});
      }
    });
  }

  if (inlinePauseBtn) {
    inlinePauseBtn.addEventListener("click", function () {
      audio.pause();
    });
  }

  updateCounter();
})();
