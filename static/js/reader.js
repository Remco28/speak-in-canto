import { createDictionaryController } from "./reader/dictionary.js";
import { createSyncController } from "./reader/sync.js";
import { createTranslationController } from "./reader/translation.js";
import { createVoiceController } from "./reader/voice.js";

(function () {
  const config = window.READER_CONFIG || {};
  const maxInputChars = Number(config.maxInputChars || 12000);
  const maxTranslationInputChars = Number(config.maxTranslationInputChars || 12000);
  const voiceCatalog = config.voices || { standard: [], high_quality: [] };

  const textInput = document.getElementById("text-input");
  const charCounter = document.getElementById("char-counter");
  const speedDecreaseBtn = document.getElementById("speed-decrease-btn");
  const speedIncreaseBtn = document.getElementById("speed-increase-btn");
  const speedLabel = document.getElementById("speed-label");
  const speedNote = document.getElementById("speed-note");
  const readBtn = document.getElementById("read-btn");
  const errorBanner = document.getElementById("error-banner");
  const tokenView = document.getElementById("token-view");
  const audio = document.getElementById("audio-player");
  const syncModeNote = document.getElementById("sync-mode-note");
  const readerModeToggle = document.getElementById("reader-mode-toggle");
  const voiceModeToggle = document.getElementById("voice-mode-toggle");
  const voiceDropdownBtn = document.getElementById("voice-dropdown-btn");
  const voiceDropdownMenu = document.getElementById("voice-dropdown-menu");
  const downloadBtn = document.getElementById("download-btn");

  const translationController = createTranslationController({
    translateBtn: document.getElementById("translate-btn"),
    translationStatus: document.getElementById("translation-status"),
    translationError: document.getElementById("translation-error"),
    translationOutput: document.getElementById("translation-output"),
    textInput,
    maxTranslationInputChars,
  });

  let syncEnabled = true;
  let currentReaderMode = "read";
  let currentSpeed = 1.0;
  let currentRenderedText = "";

  const SEEK_EPSILON_SECONDS = 0.02;
  const SPEED_MIN = 0.5;
  const SPEED_MAX = 2.0;
  const SPEED_STEP = 0.1;

  const voiceController = createVoiceController({
    voiceCatalog,
    voiceDropdownBtn,
    voiceDropdownMenu,
    voiceModeToggle,
    syncModeNote,
    speedNote,
  });

  const dictionaryController = createDictionaryController({
    dictionaryPopover: document.getElementById("dictionary-popover"),
    dictionaryStatus: document.getElementById("dictionary-status"),
    dictionaryTerm: document.getElementById("dictionary-term"),
    dictionaryDefinitions: document.getElementById("dictionary-definitions"),
    dictionaryAlternativesWrap: document.getElementById("dictionary-alternatives-wrap"),
    dictionaryAlternatives: document.getElementById("dictionary-alternatives"),
    tokenView,
    getRenderedText: () => currentRenderedText,
    getVoiceSettings: () => ({
      voiceName: voiceController.getSelectedVoiceId(),
      voiceMode: voiceController.getCurrentVoiceMode(),
      speed: currentSpeed,
    }),
  });

  const syncController = createSyncController({
    tokenView,
    audio,
    seekEpsilonSeconds: SEEK_EPSILON_SECONDS,
    highlightEpsilonSeconds: 0.03,
    isSyncEnabled: () => syncEnabled,
  });

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
    charCounter.textContent = `${count} / ${maxInputChars} characters`;
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

  function setSpeed(value) {
    const clamped = Math.max(SPEED_MIN, Math.min(SPEED_MAX, value));
    const rounded = Math.round(clamped / SPEED_STEP) * SPEED_STEP;
    currentSpeed = Number(rounded.toFixed(1));
    speedLabel.textContent = `${currentSpeed.toFixed(1)}x`;
    audio.playbackRate = currentSpeed;
    if (speedDecreaseBtn) speedDecreaseBtn.disabled = currentSpeed <= SPEED_MIN;
    if (speedIncreaseBtn) speedIncreaseBtn.disabled = currentSpeed >= SPEED_MAX;
  }

  function applyReaderMode(mode) {
    currentReaderMode = mode === "dictionary" ? "dictionary" : "read";
    if (readerModeToggle) readerModeToggle.checked = currentReaderMode === "dictionary";

    if (currentReaderMode === "dictionary") {
      syncController.setActiveToken(null);
      syncController.stopSyncLoop();
      dictionaryController.setStatus("Tap a word or phrase in Reader.");
      return;
    }

    dictionaryController.clearView();
  }

  function applyVoiceUi(mode) {
    const isHighQuality = mode === "high_quality";
    if (isHighQuality) {
      syncEnabled = false;
      syncController.setActiveToken(null);
      syncModeNote.hidden = false;
      syncModeNote.textContent = "High Quality mode does not support character sync.";
      if (speedNote) speedNote.hidden = false;
      return;
    }

    syncEnabled = true;
    syncModeNote.hidden = true;
    syncModeNote.textContent = "";
    if (speedNote) speedNote.hidden = true;
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

    const requestVoiceId = voiceController.getSelectedVoiceId();
    const requestVoiceMode = voiceController.getCurrentVoiceMode();
    if (!requestVoiceId) {
      setError("Please select a voice.");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch("/api/tts/synthesize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text,
          voice_name: requestVoiceId,
          voice_mode: requestVoiceMode,
          speaking_rate: currentSpeed,
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        setError(data.error || "Synthesis failed.");
        return;
      }

      syncController.renderTokens(data.tokens || [], data.mark_to_token || {}, async (tokenId, wrapper) => {
        if (currentReaderMode === "dictionary") {
          await dictionaryController.lookupAtIndex(tokenId, wrapper);
          return;
        }

        if (!syncEnabled) return;
        syncController.seekAndPlay(tokenId);
      });

      currentRenderedText = (data.tokens || []).map((token) => token.char || "").join("");
      dictionaryController.clearView();
      syncController.buildTimeIndex(data.timepoints || [], data.mark_to_token || {});
      syncEnabled = Boolean(data.sync_supported);
      setDownloadState(data.audio_url, voiceController.getVoiceLabelById(requestVoiceMode, requestVoiceId));

      audio.src = data.audio_url;
      audio.playbackRate = currentSpeed;
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
      if (playPromise && typeof playPromise.catch === "function") playPromise.catch(() => {});
    } catch (_err) {
      setError("Network or server error.");
    } finally {
      setLoading(false);
    }
  }

  textInput.addEventListener("input", updateCounter);

  if (speedDecreaseBtn) {
    speedDecreaseBtn.addEventListener("click", () => setSpeed(currentSpeed - SPEED_STEP));
  }
  if (speedIncreaseBtn) {
    speedIncreaseBtn.addEventListener("click", () => setSpeed(currentSpeed + SPEED_STEP));
  }

  readBtn.addEventListener("click", synthesize);
  translationController.bind();

  audio.addEventListener("play", () => syncController.startSyncLoop());
  audio.addEventListener("pause", () => syncController.stopSyncLoop());
  audio.addEventListener("ended", () => syncController.stopSyncLoop());
  audio.addEventListener("seeking", () => syncController.handleSeeking());

  if (readerModeToggle) {
    readerModeToggle.addEventListener("change", () => {
      applyReaderMode(readerModeToggle.checked ? "dictionary" : "read");
    });
  }

  voiceController.bind({
    onModeChangeHandler: (mode) => {
      applyVoiceUi(mode);
    },
  });

  document.addEventListener("click", (event) => {
    voiceController.handleDocumentClick(event);
    dictionaryController.handleDocumentClick(event);
  });

  window.addEventListener("resize", () => {
    dictionaryController.handleResize();
  });

  (async function init() {
    updateCounter();
    setSpeed(1.0);
    setDownloadState("", "");
    await voiceController.init();
    applyVoiceUi(voiceController.getCurrentVoiceMode());
    applyReaderMode("read");
  })();
})();
