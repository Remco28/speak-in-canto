export function createTranslationController({
  translateBtn,
  translationStatus,
  translationError,
  translationOutput,
  textInput,
  maxTranslationInputChars,
}) {
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

  function bind() {
    if (translateBtn) translateBtn.addEventListener("click", translateToEnglish);
  }

  return {
    bind,
  };
}
