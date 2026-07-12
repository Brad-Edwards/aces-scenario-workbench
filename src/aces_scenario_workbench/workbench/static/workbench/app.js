(function () {
  "use strict";

  const root = document.documentElement;

  function prefersDark() {
    return globalThis.matchMedia("(prefers-color-scheme: dark)").matches;
  }

  function currentTheme() {
    return root.dataset.theme || (prefersDark() ? "dark" : "light");
  }

  function persist(key, value) {
    try {
      globalThis.localStorage.setItem(key, value);
    } catch (error) {
      console.warn("Unable to persist browser preference", error);
    }
  }

  function stored(key) {
    try {
      return globalThis.localStorage.getItem(key);
    } catch (error) {
      console.warn("Unable to read browser preference", error);
      return null;
    }
  }

  function setupThemeToggle() {
    const button = document.querySelector("[data-theme-toggle]");
    if (!button) {
      return;
    }
    const syncButton = () => {
      const dark = currentTheme() === "dark";
      button.setAttribute("aria-pressed", dark ? "true" : "false");
      button.textContent = dark ? "Light theme" : "Dark theme";
      button.setAttribute("aria-label", dark ? "Switch to light theme" : "Switch to dark theme");
    };

    button.addEventListener("click", () => {
      const next = currentTheme() === "dark" ? "light" : "dark";
      root.dataset.theme = next;
      persist("aces-theme", next);
      syncButton();
    });

    syncButton();
  }

  function setupReviewTabs() {
    const tabs = Array.from(document.querySelectorAll(".tab[data-view]"));
    if (!tabs.length) {
      return;
    }
    const views = Array.from(document.querySelectorAll(".view[id^='view-']"));
    const names = new Set(tabs.map((tab) => tab.dataset.view));
    const selectView = (requested) => {
      const selected = names.has(requested) ? requested : "overview";
      tabs.forEach((tab) => {
        tab.setAttribute("aria-pressed", String(tab.dataset.view === selected));
      });
      views.forEach((view) => {
        view.hidden = view.id !== `view-${selected}`;
      });
    };

    tabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        const view = tab.dataset.view;
        history.replaceState(null, "", `#${view}`);
        selectView(view);
      });
    });

    globalThis.addEventListener("hashchange", () => selectView(location.hash.slice(1)));
    selectView(location.hash.slice(1));
  }

  function setupClickableContainers() {
    document.querySelectorAll("[data-href]").forEach((node) => {
      const open = (event) => {
        const target = event.target;
        if (target instanceof Element && target.closest("a, button, input, select, textarea")) {
          return;
        }
        location.href = node.dataset.href;
      };
      node.addEventListener("click", open);
      node.addEventListener("keydown", (event) => {
        const target = event.target;
        if (target instanceof Element && target.closest("a, button, input, select, textarea")) {
          return;
        }
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          location.href = node.dataset.href;
        }
      });
    });
  }

  function setupCookieNotice() {
    const notice = document.querySelector("[data-cookie-notice]");
    const button = document.querySelector("[data-cookie-accept]");
    if (!notice || !button || stored("aces-cookie-notice") === "accepted") {
      return;
    }
    notice.hidden = false;
    button.addEventListener("click", () => {
      persist("aces-cookie-notice", "accepted");
      notice.hidden = true;
    });
  }

  setupThemeToggle();
  setupReviewTabs();
  setupClickableContainers();
  setupCookieNotice();
})();
