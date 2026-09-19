(() => {
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  document.querySelectorAll("[data-chart-scroll]").forEach((button) => {
    button.addEventListener("click", () => {
      const target = document.getElementById(button.dataset.chartTarget);
      if (!target) return;
      const direction = button.dataset.chartScroll === "back" ? -1 : 1;
      target.scrollBy({
        left: direction * Math.max(280, target.clientWidth * 0.75),
        behavior: reduceMotion ? "auto" : "smooth",
      });
    });
  });
})();
