(function () {
  "use strict";
  const root = document.documentElement;
  const button = document.querySelector("[data-theme-toggle]");
  if (!button) {
    return;
  }

  const prefersDark = () => globalThis.matchMedia("(prefers-color-scheme: dark)").matches;
  const currentTheme = () => root.dataset.theme || (prefersDark() ? "dark" : "light");
  const syncButton = () => {
    button.setAttribute("aria-pressed", currentTheme() === "dark" ? "true" : "false");
  };
  const persist = (value) => {
    try {
      globalThis.localStorage.setItem("aces-theme", value);
    } catch (error) {
      console.warn("Unable to persist theme preference", error);
    }
  };

  button.addEventListener("click", () => {
    const next = currentTheme() === "dark" ? "light" : "dark";
    root.dataset.theme = next;
    persist(next);
    syncButton();
  });

  syncButton();
})();
