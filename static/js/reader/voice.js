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

  async function togglePin(voiceId, voiceMode) {
    try {
      const response = await fetch("/api/user/voice-pins/toggle", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ voice_id: voiceId, voice_mode: voiceMode }),
      });
      if (!response.ok) return;
      const data = await response.json();
      if (data.pinned) voicePins.add(voiceId);
      else voicePins.delete(voiceId);
      renderVoiceMenu();
    } catch (_err) {
      // Non-fatal.
    }
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
      });

      const pinBtn = document.createElement("button");
      pinBtn.type = "button";
      pinBtn.className = "pin-btn";
      pinBtn.textContent = "★";
      if (voicePins.has(id)) pinBtn.classList.add("pinned");
      pinBtn.addEventListener("click", async (event) => {
        event.stopPropagation();
        await togglePin(id, currentVoiceMode);
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

  async function loadPins() {
    try {
      const response = await fetch("/api/user/voice-pins");
      if (!response.ok) return;
      const data = await response.json();
      voicePins = new Set((data.pins || []).map((pin) => pin.voice_id));
    } catch (_err) {
      // Non-fatal.
    }
  }

  function applyVoiceMode(mode) {
    if (mode === "high_quality" && (!voiceCatalog.high_quality || voiceCatalog.high_quality.length === 0)) {
      currentVoiceMode = "standard";
      if (voiceModeToggle) voiceModeToggle.checked = false;
      syncModeNote.hidden = false;
      syncModeNote.textContent = "High Quality voices are unavailable in this project.";
      if (speedNote) speedNote.hidden = true;
      if (onModeChange) onModeChange("standard");
      return;
    }

    currentVoiceMode = mode;
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

  function bind({ onModeChangeHandler }) {
    onModeChange = onModeChangeHandler || null;

    if (voiceModeToggle) {
      voiceModeToggle.addEventListener("change", () => {
        applyVoiceMode(voiceModeToggle.checked ? "high_quality" : "standard");
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
    await loadPins();
    applyVoiceMode("standard");
  }

  return {
    bind,
    init,
    handleDocumentClick,
    getCurrentVoiceMode: () => currentVoiceMode,
    getSelectedVoiceId: () => selectedVoiceId,
    getVoiceLabelById,
  };
}
