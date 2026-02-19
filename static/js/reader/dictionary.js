export function createDictionaryController({
  dictionaryPopover,
  dictionaryStatus,
  dictionaryTerm,
  dictionaryDefinitions,
  dictionaryAlternativesWrap,
  dictionaryAlternatives,
  tokenView,
  getRenderedText,
  getVoiceSettings,
}) {
  let dictionaryAudio = null;

  function clearView() {
    if (!dictionaryPopover) return;
    dictionaryPopover.hidden = true;
    dictionaryPopover.style.left = "0px";
    dictionaryPopover.style.top = "0px";
    if (dictionaryStatus) {
      dictionaryStatus.hidden = true;
      dictionaryStatus.textContent = "";
    }
    if (dictionaryTerm) dictionaryTerm.textContent = "";
    if (dictionaryDefinitions) dictionaryDefinitions.innerHTML = "";
    if (dictionaryAlternativesWrap) {
      dictionaryAlternativesWrap.hidden = true;
      dictionaryAlternativesWrap.open = false;
    }
    if (dictionaryAlternatives) dictionaryAlternatives.innerHTML = "";
    tokenView.querySelectorAll(".token.dictionary-hit").forEach((node) => node.classList.remove("dictionary-hit"));
  }

  function setStatus(message) {
    if (!dictionaryPopover || !dictionaryStatus) return;
    dictionaryPopover.hidden = false;
    dictionaryStatus.hidden = !message;
    dictionaryStatus.textContent = message || "";
  }

  function placePopover(anchorEl) {
    if (!dictionaryPopover || !anchorEl) return;
    const rect = anchorEl.getBoundingClientRect();
    const margin = 10;
    const viewportW = window.innerWidth;
    const viewportH = window.innerHeight;

    const desiredLeft = rect.left + margin;
    const desiredTop = rect.bottom + margin;

    dictionaryPopover.style.left = `${Math.max(margin, Math.min(desiredLeft, viewportW - dictionaryPopover.offsetWidth - margin))}px`;
    dictionaryPopover.style.top = `${Math.max(margin, Math.min(desiredTop, viewportH - dictionaryPopover.offsetHeight - margin))}px`;
  }

  function renderCandidate(candidate) {
    if (!candidate) return;
    if (dictionaryTerm) {
      const source = candidate.source ? ` (${candidate.source})` : "";
      const jyutping = candidate.jyutping ? ` · ${candidate.jyutping}` : "";
      dictionaryTerm.textContent = `${candidate.term}${jyutping}${source}`;
    }
    if (dictionaryDefinitions) {
      dictionaryDefinitions.innerHTML = "";
      (candidate.definitions || []).forEach((definition) => {
        const li = document.createElement("li");
        li.textContent = definition;
        dictionaryDefinitions.appendChild(li);
      });
    }
  }

  function renderAlternatives(alternatives) {
    if (!dictionaryAlternativesWrap || !dictionaryAlternatives) return;
    dictionaryAlternatives.innerHTML = "";
    if (!alternatives || alternatives.length === 0) {
      dictionaryAlternativesWrap.hidden = true;
      dictionaryAlternativesWrap.open = false;
      return;
    }
    alternatives.forEach((candidate) => {
      const li = document.createElement("li");
      li.textContent = `${candidate.term}: ${(candidate.definitions || []).join("; ")}`;
      dictionaryAlternatives.appendChild(li);
    });
    dictionaryAlternativesWrap.hidden = false;
  }

  function highlightSpan(span) {
    tokenView.querySelectorAll(".token.dictionary-hit").forEach((node) => node.classList.remove("dictionary-hit"));
    if (!span) return;
    for (let tokenId = span.start; tokenId < span.end; tokenId += 1) {
      const node = tokenView.querySelector(`[data-token-id="${tokenId}"]`);
      if (node) node.classList.add("dictionary-hit");
    }
  }

  async function speakTerm(term) {
    const voice = getVoiceSettings();
    if (!term || !voice.voiceName) return;
    try {
      const response = await fetch("/api/dictionary/speak", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: term,
          voice_name: voice.voiceName,
          voice_mode: voice.voiceMode,
        }),
      });
      const data = await response.json();
      if (!response.ok || !data.audio_url) return;

      if (!dictionaryAudio) dictionaryAudio = new Audio();
      dictionaryAudio.src = data.audio_url;
      dictionaryAudio.playbackRate = voice.speed;
      const p = dictionaryAudio.play();
      if (p && typeof p.catch === "function") p.catch(() => {});
    } catch (_err) {
      // Best effort only.
    }
  }

  async function lookupAtIndex(tokenId, anchorEl) {
    const renderedText = getRenderedText();
    if (!renderedText) {
      setStatus("No rendered text to look up yet. Press Read first.");
      placePopover(anchorEl);
      return;
    }

    try {
      setStatus("Looking up...");
      placePopover(anchorEl);
      const response = await fetch("/api/dictionary/lookup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: renderedText, index: tokenId }),
      });
      const data = await response.json();
      if (!response.ok) {
        setStatus(data.error || "Dictionary lookup failed.");
        placePopover(anchorEl);
        return;
      }

      dictionaryPopover.hidden = false;
      setStatus("");
      placePopover(anchorEl);

      if (!data.best) {
        if (dictionaryTerm) dictionaryTerm.textContent = "No definition found";
        if (dictionaryDefinitions) dictionaryDefinitions.innerHTML = "";
        renderAlternatives([]);
        highlightSpan(null);
        return;
      }

      renderCandidate(data.best);
      renderAlternatives(data.alternatives || []);
      highlightSpan({ start: Number(data.best.start), end: Number(data.best.end) });
      await speakTerm(data.best.term);
    } catch (_err) {
      setStatus("Network or server error.");
      placePopover(anchorEl);
    }
  }

  function handleDocumentClick(event) {
    if (
      dictionaryPopover &&
      !dictionaryPopover.hidden &&
      !dictionaryPopover.contains(event.target) &&
      !tokenView.contains(event.target)
    ) {
      clearView();
    }
  }

  function handleResize() {
    if (dictionaryPopover && !dictionaryPopover.hidden) clearView();
  }

  return {
    clearView,
    setStatus,
    lookupAtIndex,
    handleDocumentClick,
    handleResize,
  };
}
