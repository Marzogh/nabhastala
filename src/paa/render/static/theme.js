(() => {
  const button = document.querySelector("[data-theme-toggle]");
  if (!button) return;

  const choices = ["system", "light", "dark"];
  const icons = { system: "◐", light: "☀", dark: "☾" };
  let current = "system";

  try {
    const saved = localStorage.getItem("nabhastala-theme");
    if (saved === "light" || saved === "dark") current = saved;
  } catch (_) {}

  const apply = (choice) => {
    current = choice;
    if (choice === "system") {
      delete document.documentElement.dataset.theme;
    } else {
      document.documentElement.dataset.theme = choice;
    }
    const next = choices[(choices.indexOf(choice) + 1) % choices.length];
    button.textContent = icons[choice];
    button.setAttribute("aria-label", `Colour theme: ${choice}. Switch to ${next}.`);
    button.title = `Colour theme: ${choice}`;
    try {
      if (choice === "system") localStorage.removeItem("nabhastala-theme");
      else localStorage.setItem("nabhastala-theme", choice);
    } catch (_) {}
  };

  button.addEventListener("click", () => {
    apply(choices[(choices.indexOf(current) + 1) % choices.length]);
  });
  apply(current);
})();
