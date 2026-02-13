(function () {
  const config = window.READER_CONFIG || {};
  const maxInputChars = Number(config.maxInputChars || 12000);
  const maxTranslationInputChars = Number(config.maxTranslationInputChars || 12000);
  const voiceCatalog = config.voices || { standard: [], high_quality: [] };

  const textInput = document.getElementById("text-input");
  const charCounter = document.getElementById("char-counter");
  const speedSlider = document.getElementById("speed-slider");
  const speedLabel = document.getElementById("speed-label");
  const readBtn = document.getElementById("read-btn");
  const errorBanner = document.getElementById("error-banner");
  const tokenView = document.getElementById("token-view");
  const audio = document.getElementById("audio-player");
  const syncModeNote = document.getElementById("sync-mode-note");
  const voiceModeToggle = document.getElementById("voice-mode-toggle");
  const inlinePlayBtn = document.getElementById("inline-play-btn");
  const inlinePauseBtn = document.getElementById("inline-pause-btn");
  const voiceDropdownBtn = document.getElementById("voice-dropdown-btn");
  const voiceDropdownMenu = document.getElementById("voice-dropdown-menu");
  const downloadBtn = document.getElementById("download-btn");
  const translateBtn = document.getElementById("translate-btn");
  const translationStatus = document.getElementById("translation-status");
  const translationError = document.getElementById("translation-error");
  const translationOutput = document.getElementById("translation-output");

  let tokenToTime = new Map();
  let timeEntries = [];
  let timeEntrySeconds = [];
  let maxTokenId = 0;
  let activeToken = null;
  let syncEnabled = true;
  let currentVoiceMode = "standard";
  let selectedVoiceId = "";
  let voicePins = new Set();
  let animationHandle = null;

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

  function setDownloadState(audioUrl, voiceLabel) {
    if (!downloadBtn) return;
    if (!audioUrl || !voiceLabel) {
      downloadBtn.hidden = true;
      downloadBtn.href = "#";
      downloadBtn.setAttribute("aria-disabled", "true");
      downloadBtn.textContent = "Download MP3";
      downloadBtn.removeAttribute("download");
      return;
    }

    const stamp = new Date().toISOString().replace(/[:.]/g, "-");
    const safeVoice = String(voiceLabel)
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 48) || "voice";

    downloadBtn.hidden = false;
    downloadBtn.href = audioUrl;
    downloadBtn.setAttribute("aria-disabled", "false");
    downloadBtn.setAttribute("download", `speak-in-canto-${safeVoice}-${stamp}.mp3`);
    downloadBtn.textContent = `Download MP3 (${voiceLabel})`;
  }

  function setTranslationLoading(isLoading) {
    if (!translateBtn) return;
    translateBtn.disabled = isLoading;
    translateBtn.textContent = isLoading ? "Translating..." : "Translate to English";
    if (translationStatus) {
      translationStatus.hidden = !isLoading;
      translationStatus.textContent = isLoading ? "Translating..." : "";
    }
  }

  function setTranslationError(msg) {
    if (!translationError) return;
    if (!msg) {
      translationError.hidden = true;
      translationError.textContent = "";
      return;
    }
    translationError.hidden = false;
    translationError.textContent = msg;
  }

  function setTranslationOutput(text) {
    if (!translationOutput) return;
    translationOutput.textContent = text || "";
  }

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

    if (found === null) {
      return null;
    }
    return timeEntries[found].tokenId;
  }

  function setActiveToken(tokenId) {
    if (activeToken === tokenId) {
      return;
    }
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
        if (!syncEnabled) {
          return;
        }
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

    tokenToTime = new Map([...tokenToTime.entries()].sort((a, b) => a[0] - b[0]));
    timeEntries = [...tokenToTime.entries()]
      .map(([tokenId, seconds]) => ({ tokenId, seconds }))
      .sort((a, b) => a.seconds - b.seconds);
    timeEntrySeconds = timeEntries.map((entry) => entry.seconds);
  }

  function resolveSeekTime(tokenId) {
    if (tokenToTime.size === 0) {
      return null;
    }
    if (tokenToTime.has(tokenId)) {
      return tokenToTime.get(tokenId);
    }

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

  function getModeOptions(mode) {
    return mode === "high_quality" ? voiceCatalog.high_quality : voiceCatalog.standard;
  }

  function getVoiceLabelById(mode, voiceId) {
    const options = getModeOptions(mode);
    const found = (options || []).find((voice) => {
      const id = typeof voice === "string" ? voice : voice.id;
      return id === voiceId;
    });
    if (!found) return voiceId;
    return labelForVoice(found);
  }

  function sortedOptionsWithPins(options) {
    const pinned = [];
    const unpinned = [];
    (options || []).forEach((voice) => {
      const id = typeof voice === "string" ? voice : voice.id;
      if (voicePins.has(id)) {
        pinned.push(voice);
      } else {
        unpinned.push(voice);
      }
    });
    return [...pinned, ...unpinned];
  }

  function labelForVoice(voice) {
    if (typeof voice === "string") {
      return voice;
    }
    return voice.label || voice.id;
  }

  function renderVoiceMenu() {
    voiceDropdownMenu.innerHTML = "";
    const options = sortedOptionsWithPins(getModeOptions(currentVoiceMode));

    options.forEach((voice) => {
      const id = typeof voice === "string" ? voice : voice.id;
      const row = document.createElement("div");
      row.className = "voice-option-row";
      if (id === selectedVoiceId) {
        row.classList.add("selected");
      }

      const selectBtn = document.createElement("button");
      selectBtn.type = "button";
      selectBtn.className = "voice-option-select";
      selectBtn.textContent = labelForVoice(voice);
      selectBtn.addEventListener("click", function () {
        selectedVoiceId = id;
        updateVoiceButtonLabel();
        renderVoiceMenu();
        closeVoiceMenu();
      });

      const pinBtn = document.createElement("button");
      pinBtn.type = "button";
      pinBtn.className = "pin-btn";
      pinBtn.textContent = "★";
      if (voicePins.has(id)) {
        pinBtn.classList.add("pinned");
      }
      pinBtn.addEventListener("click", async function (event) {
        event.stopPropagation();
        await togglePin(id, currentVoiceMode);
      });

      row.appendChild(selectBtn);
      row.appendChild(pinBtn);
      voiceDropdownMenu.appendChild(row);
    });
  }

  function updateVoiceButtonLabel() {
    const options = getModeOptions(currentVoiceMode);
    const found = (options || []).find((voice) => {
      const id = typeof voice === "string" ? voice : voice.id;
      return id === selectedVoiceId;
    });
    if (found) {
      voiceDropdownBtn.textContent = labelForVoice(found);
      return;
    }
    voiceDropdownBtn.textContent = "Select voice";
  }

  function openVoiceMenu() {
    voiceDropdownMenu.hidden = false;
  }

  function closeVoiceMenu() {
    voiceDropdownMenu.hidden = true;
  }

  async function loadPins() {
    try {
      const response = await fetch("/api/user/voice-pins");
      if (!response.ok) return;
      const data = await response.json();
      voicePins = new Set((data.pins || []).map((pin) => pin.voice_id));
    } catch (_err) {
      // Non-fatal for reader.
    }
  }

  async function togglePin(voiceId, voiceMode) {
    try {
      const response = await fetch("/api/user/voice-pins/toggle", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ voice_id: voiceId, voice_mode: voiceMode }),
      });
      if (!response.ok) {
        return;
      }
      const data = await response.json();
      if (data.pinned) {
        voicePins.add(voiceId);
      } else {
        voicePins.delete(voiceId);
      }
      renderVoiceMenu();
    } catch (_err) {
      // Non-fatal for reader.
    }
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

    if (!selectedVoiceId) {
      setError("Please select a voice.");
      return;
    }

    const requestVoiceId = selectedVoiceId;
    const requestVoiceMode = currentVoiceMode;

    setLoading(true);

    try {
      const response = await fetch("/api/tts/synthesize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text,
          voice_name: requestVoiceId,
          voice_mode: requestVoiceMode,
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
      syncEnabled = Boolean(data.sync_supported);
      setDownloadState(data.audio_url, getVoiceLabelById(requestVoiceMode, requestVoiceId));

      audio.src = data.audio_url;
      if (requestVoiceMode === "high_quality") {
        audio.playbackRate = 1.0;
      } else {
        audio.playbackRate = Number(speedSlider.value);
      }
      audio.currentTime = 0;

      if (requestVoiceMode === "high_quality") {
        syncModeNote.hidden = false;
        syncModeNote.textContent = "High Quality mode does not support character sync.";
      } else if (data.sync_mode === "reduced") {
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

  async function translateToEnglish() {
    setTranslationError("");

    const text = textInput.value;
    if (!text.trim()) {
      setTranslationError("Please enter text.");
      return;
    }
    if (text.trim().length > maxTranslationInputChars) {
      setTranslationError(`Text exceeds max length (${maxTranslationInputChars}).`);
      return;
    }

    setTranslationLoading(true);
    try {
      const response = await fetch("/api/translate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      const data = await response.json();
      if (!response.ok) {
        setTranslationError(data.error || "Translation failed.");
        return;
      }
      setTranslationOutput(data.translation || "");
    } catch (_err) {
      setTranslationError("Network or server error.");
    } finally {
      setTranslationLoading(false);
    }
  }

  function applyVoiceMode(mode) {
    if (mode === "high_quality" && (!voiceCatalog.high_quality || voiceCatalog.high_quality.length === 0)) {
      currentVoiceMode = "standard";
      if (voiceModeToggle) {
        voiceModeToggle.checked = false;
      }
      syncModeNote.hidden = false;
      syncModeNote.textContent = "High Quality voices are unavailable in this project.";
      speedSlider.disabled = false;
      return;
    }

    currentVoiceMode = mode;

    const options = getModeOptions(mode);
    if (!options || options.length === 0) {
      selectedVoiceId = "";
    } else {
      const existing = options.some((voice) => (typeof voice === "string" ? voice : voice.id) === selectedVoiceId);
      if (!existing) {
        selectedVoiceId = typeof options[0] === "string" ? options[0] : options[0].id;
      }
    }

    renderVoiceMenu();
    updateVoiceButtonLabel();

    const isHighQuality = mode === "high_quality";
    speedSlider.disabled = isHighQuality;
    if (isHighQuality) {
      speedLabel.textContent = "1.0x";
      audio.playbackRate = 1.0;
      syncEnabled = false;
      setActiveToken(null);
      syncModeNote.hidden = false;
      syncModeNote.textContent = "High Quality mode does not support character sync.";
    } else {
      speedSlider.disabled = false;
      syncEnabled = true;
      syncModeNote.hidden = true;
      syncModeNote.textContent = "";
    }
  }

  function syncHighlightFrame() {
    if (syncEnabled && !audio.paused && !audio.ended) {
      const tokenId = getCurrentTokenByTime(audio.currentTime + HIGHLIGHT_EPSILON_SECONDS);
      setActiveToken(tokenId);
      animationHandle = window.requestAnimationFrame(syncHighlightFrame);
      return;
    }
    animationHandle = null;
  }

  function startSyncLoop() {
    if (animationHandle !== null) {
      return;
    }
    animationHandle = window.requestAnimationFrame(syncHighlightFrame);
  }

  function stopSyncLoop() {
    if (animationHandle !== null) {
      window.cancelAnimationFrame(animationHandle);
      animationHandle = null;
    }
  }

  textInput.addEventListener("input", updateCounter);
  speedSlider.addEventListener("input", function () {
    const speed = Number(speedSlider.value).toFixed(1);
    speedLabel.textContent = `${speed}x`;
    audio.playbackRate = Number(speedSlider.value);
  });

  readBtn.addEventListener("click", synthesize);
  if (translateBtn) {
    translateBtn.addEventListener("click", translateToEnglish);
  }

  audio.addEventListener("play", startSyncLoop);
  audio.addEventListener("pause", stopSyncLoop);
  audio.addEventListener("ended", stopSyncLoop);
  audio.addEventListener("seeking", function () {
    if (!syncEnabled) return;
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

  if (voiceModeToggle) {
    voiceModeToggle.addEventListener("change", function () {
      applyVoiceMode(voiceModeToggle.checked ? "high_quality" : "standard");
    });
  }

  if (voiceDropdownBtn) {
    voiceDropdownBtn.addEventListener("click", function () {
      if (voiceDropdownMenu.hidden) {
        openVoiceMenu();
      } else {
        closeVoiceMenu();
      }
    });
  }

  document.addEventListener("click", function (event) {
    if (!voiceDropdownMenu || !voiceDropdownBtn) return;
    const within = voiceDropdownMenu.contains(event.target) || voiceDropdownBtn.contains(event.target);
    if (!within) {
      closeVoiceMenu();
    }
  });

  (async function init() {
    updateCounter();
    setDownloadState("", "");
    await loadPins();
    applyVoiceMode("standard");
  })();
})();
