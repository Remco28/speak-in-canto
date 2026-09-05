const PIN_STORAGE_KEY = "canto-reader.voice-pins";
const SELECTION_STORAGE_KEY = "canto-reader.voice-selection";

export function createVoiceController({
  voiceCatalog,
  voiceDropdownBtn,
  voiceDropdownMenu,
  voiceModeToggle,
  syncModeNote,
  speedNote,
}) {
  let currentVoiceMode = "standard";
  let selectedVoiceId = "";
  let voicePins = new Set();
  let onModeChange = null;

  function getModeOptions(mode) {
    return mode === "high_quality" ? voiceCatalog.high_quality : voiceCatalog.standard;
  }

  function labelForVoice(voice) {
    if (typeof voice === "string") return voice;
    return voice.label || voice.id;
  }

  function getVoiceLabelById(mode, voiceId) {
    const options = getModeOptions(mode);
    const found = (options || []).find((voice) => (typeof voice === "string" ? voice : voice.id) === voiceId);
    if (!found) return voiceId;
    return labelForVoice(found);
  }

  function readPins() {
    try {
      const raw = window.localStorage.getItem(PIN_STORAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : [];
      return new Set(Array.isArray(parsed) ? parsed.filter((v) => typeof v === "string") : []);
    } catch (_err) {
      return new Set();
    }
  }

  function writePins(pins) {
    try {
      window.localStorage.setItem(PIN_STORAGE_KEY, JSON.stringify([...pins]));
    } catch (_err) {
      // Non-fatal (e.g. storage disabled).
    }
  }

  function readSelection() {
    try {
      const raw = window.localStorage.getItem(SELECTION_STORAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : null;
      if (
        parsed &&
        (parsed.mode === "standard" || parsed.mode === "high_quality") &&
        typeof parsed.voiceId === "string"
      ) {
        return parsed;
      }
    } catch (_err) {
      // Fall through.
    }
    return null;
  }

  function writeSelection() {
    try {
      window.localStorage.setItem(
        SELECTION_STORAGE_KEY,
        JSON.stringify({ mode: currentVoiceMode, voiceId: selectedVoiceId })
      );
    } catch (_err) {
      // Non-fatal.
    }
  }

  function sortedOptionsWithPins(options) {
    const pinned = [];
    const unpinned = [];
    (options || []).forEach((voice) => {
      const id = typeof voice === "string" ? voice : voice.id;
      if (voicePins.has(id)) pinned.push(voice);
      else unpinned.push(voice);
    });
    return [...pinned, ...unpinned];
  }

  function updateVoiceButtonLabel() {
    const options = getModeOptions(currentVoiceMode);
    const found = (options || []).find((voice) => (typeof voice === "string" ? voice : voice.id) === selectedVoiceId);
    voiceDropdownBtn.textContent = found ? labelForVoice(found) : "Select voice";
  }

  function togglePin(voiceId) {
    if (voicePins.has(voiceId)) voicePins.delete(voiceId);
    else voicePins.add(voiceId);
    writePins(voicePins);
    renderVoiceMenu();
  }

  function renderVoiceMenu() {
    voiceDropdownMenu.innerHTML = "";
    const options = sortedOptionsWithPins(getModeOptions(currentVoiceMode));
    options.forEach((voice) => {
      const id = typeof voice === "string" ? voice : voice.id;
      const row = document.createElement("div");
      row.className = "voice-option-row";
      if (id === selectedVoiceId) row.classList.add("selected");

      const selectBtn = document.createElement("button");
      selectBtn.type = "button";
      selectBtn.className = "voice-option-select";
      selectBtn.textContent = labelForVoice(voice);
      selectBtn.addEventListener("click", () => {
        selectedVoiceId = id;
        updateVoiceButtonLabel();
        renderVoiceMenu();
        closeVoiceMenu();
        writeSelection();
      });

      const pinBtn = document.createElement("button");
      pinBtn.type = "button";
      pinBtn.className = "pin-btn";
      pinBtn.textContent = "★";
      if (voicePins.has(id)) pinBtn.classList.add("pinned");
      pinBtn.addEventListener("click", (event) => {
        event.stopPropagation();
        togglePin(id);
      });

      row.appendChild(selectBtn);
      row.appendChild(pinBtn);
      voiceDropdownMenu.appendChild(row);
    });
  }

  function closeVoiceMenu() {
    voiceDropdownMenu.hidden = true;
  }

  function openVoiceMenu() {
    voiceDropdownMenu.hidden = false;
  }

  function loadPins() {
    voicePins = readPins();
  }

  function applyVoiceMode(mode) {
    if (mode === "high_quality" && (!voiceCatalog.high_quality || voiceCatalog.high_quality.length === 0)) {
      currentVoiceMode = "standard";
      if (voiceModeToggle) voiceModeToggle.checked = false;
      // Notify first: the Standard-mode UI callback clears the sync note, so
      // the "unavailable" message must be set afterwards to stay visible.
      if (onModeChange) onModeChange("standard");
      syncModeNote.hidden = false;
      syncModeNote.textContent = "High Quality voices are unavailable in this project.";
      if (speedNote) speedNote.hidden = true;
      return;
    }

    currentVoiceMode = mode;
    if (voiceModeToggle) voiceModeToggle.checked = mode === "high_quality";
    const options = getModeOptions(mode);
    if (!options || options.length === 0) {
      selectedVoiceId = "";
    } else {
      const exists = options.some((voice) => (typeof voice === "string" ? voice : voice.id) === selectedVoiceId);
      if (!exists) selectedVoiceId = typeof options[0] === "string" ? options[0] : options[0].id;
    }

    renderVoiceMenu();
    updateVoiceButtonLabel();
    if (onModeChange) onModeChange(currentVoiceMode);
  }

  function restoreVoiceId(voiceId) {
    const options = getModeOptions(currentVoiceMode);
    const exists = options.some((voice) => (typeof voice === "string" ? voice : voice.id) === voiceId);
    if (!exists) return;
    selectedVoiceId = voiceId;
    updateVoiceButtonLabel();
    renderVoiceMenu();
  }

  function applySavedSelection() {
    const saved = readSelection();
    const targetMode = saved && saved.mode === "high_quality" ? "high_quality" : "standard";
    applyVoiceMode(targetMode);
    if (saved && saved.voiceId) restoreVoiceId(saved.voiceId);
  }

  function bind({ onModeChangeHandler }) {
    onModeChange = onModeChangeHandler || null;

    if (voiceModeToggle) {
      voiceModeToggle.addEventListener("change", () => {
        applyVoiceMode(voiceModeToggle.checked ? "high_quality" : "standard");
        writeSelection();
      });
    }

    if (voiceDropdownBtn) {
      voiceDropdownBtn.addEventListener("click", () => {
        if (voiceDropdownMenu.hidden) openVoiceMenu();
        else closeVoiceMenu();
      });
    }
  }

  function handleDocumentClick(event) {
    if (!voiceDropdownMenu || !voiceDropdownBtn) return;
    const within = voiceDropdownMenu.contains(event.target) || voiceDropdownBtn.contains(event.target);
    if (!within) closeVoiceMenu();
  }

  async function init() {
    loadPins();
    applySavedSelection();
  }

  function refresh() {
    applySavedSelection();
  }

  return {
    bind,
    init,
    refresh,
    handleDocumentClick,
    getCurrentVoiceMode: () => currentVoiceMode,
    getSelectedVoiceId: () => selectedVoiceId,
    getVoiceLabelById,
  };
}
