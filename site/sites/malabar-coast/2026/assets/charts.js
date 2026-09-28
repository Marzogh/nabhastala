(() => {
  const svgNS = "http://www.w3.org/2000/svg";
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const clockTime = (minutes) => {
    const wrapped = ((Math.round(minutes) % 1440) + 1440) % 1440;
    const hour = Math.floor(wrapped / 60);
    const minute = wrapped % 60;
    return `${hour % 12 || 12}:${String(minute).padStart(2, "0")} ${hour < 12 ? "am" : "pm"}`;
  };
  const localTime = (value) => {
    if (!value) return "Unavailable";
    const match = String(value).match(/T(\d{2}):(\d{2})/);
    return match ? clockTime(Number(match[1]) * 60 + Number(match[2])) : "Unavailable";
  };
  const localTimeAt = (startValue, elapsedMs) => {
    const match = String(startValue).match(/T(\d{2}):(\d{2})/);
    if (!match) return "Unavailable";
    return clockTime(Number(match[1]) * 60 + Number(match[2]) + elapsedMs / 60000);
  };
  const localDate = (value) => new Intl.DateTimeFormat(undefined, {
    weekday: "short", day: "numeric", month: "short", year: "numeric",
  }).format(new Date(`${value}T12:00:00`));
  const currentDateInZone = (timeZone) => {
    const parts = new Intl.DateTimeFormat("en-CA", {
      timeZone: timeZone || "UTC", year: "numeric", month: "2-digit", day: "2-digit",
    }).formatToParts(new Date());
    const value = Object.fromEntries(parts.map((part) => [part.type, part.value]));
    return `${value.year}-${value.month}-${value.day}`;
  };
  const useCurrentDateWhenAvailable = (input) => {
    const today = currentDateInZone(input.dataset.siteTimezone);
    if (today >= input.min && today <= input.max) input.value = today;
  };
  const element = (name, className, text) => {
    const node = document.createElement(name);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };
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

  document.querySelectorAll("[data-night-planner]").forEach((planner) => {
    const input = planner.querySelector("[data-night-date]");
    const dataNode = planner.querySelector("[data-night-data]");
    const timeline = planner.querySelector("[data-night-timeline]");
    const summary = planner.querySelector("[data-night-summary]");
    const axis = planner.querySelector("[data-night-axis]");
    const facts = planner.querySelector("[data-night-facts]");
    const planetBox = planner.querySelector("[data-night-planets]");
    if (!input || !dataNode || !timeline || !summary || !axis || !facts || !planetBox) return;
    useCurrentDateWhenAvailable(input);
    const plans = new Map(JSON.parse(dataNode.textContent).map((plan) => [plan.date, plan]));
    const render = () => {
      const plan = plans.get(input.value);
      if (!plan) return;
      const dusk = new Date(plan.dusk);
      const dawn = new Date(plan.dawn);
      if (dawn <= dusk) dawn.setDate(dawn.getDate() + 1);
      const duration = dawn - dusk;
      const position = (value) => Math.max(0, Math.min(100, (new Date(value) - dusk) / duration * 100));
      timeline.querySelectorAll(".night-segment").forEach((node) => node.remove());
      const addSegments = (items, kind, label) => items.forEach((item) => {
        const segment = element("span", `night-segment night-segment--${kind}`);
        const left = position(item.start);
        segment.style.left = `${left}%`;
        segment.style.width = `${Math.max(0.8, position(item.end) - left)}%`;
        segment.title = `${label}: ${localTime(item.start)} to ${localTime(item.end)}`;
        timeline.append(segment);
      });
      addSegments(plan.dark, "moon-free", "Low-Moon darkness");
      addSegments(plan.milky, "milky", "Usable Galactic Centre viewing");
      summary.textContent = `${localDate(plan.date)}. Astronomical darkness from ${localTime(plan.dusk)} to ${localTime(plan.dawn)}.`;
      axis.replaceChildren(
        element("span", "", localTime(plan.dusk)),
        element("span", "", "Midnight"),
        element("span", "", localTime(plan.dawn)),
      );
      const fact = (term, value) => {
        const wrap = element("div");
        wrap.append(element("dt", "", term), element("dd", "", value));
        return wrap;
      };
      facts.replaceChildren(
        fact("Moon illumination", plan.illumination == null ? "Unavailable" : `${Math.round(plan.illumination * 100)}%`),
        fact("Moonrise", localTime(plan.moonrise)),
        fact("Moonset", localTime(plan.moonset)),
        fact("Usable core window", plan.milky.length ? plan.milky.map((item) => `${localTime(item.start)}–${localTime(item.end)}`).join(", ") : "None"),
      );
      planetBox.replaceChildren();
      planetBox.append(element("h3", "", "Planets on this night"));
      if (!plan.planets.length) {
        planetBox.append(element("p", "empty-state", "No planet has a supported observing sample for this date."));
      } else {
        const list = element("ul");
        plan.planets.slice(0, 7).forEach((planet) => {
          const item = element("li");
          item.append(
            element("strong", "", planet.planet),
            element("span", "", `${localTime(planet.time)} · ${Math.round(planet.altitude)}° · ${planet.rating}`),
          );
          list.append(item);
        });
        planetBox.append(list);
      }
    };
    input.addEventListener("change", render);
    render();
  });

  document.querySelectorAll("[data-moon-system]").forEach(async (instrument) => {
    const input = instrument.querySelector("[data-moon-date]");
    const chart = instrument.querySelector("[data-moon-chart]");
    const status = instrument.querySelector("[data-moon-status]");
    const caption = instrument.querySelector("[data-moon-caption]");
    const key = instrument.querySelector("[data-moon-key]");
    if (!input || !chart || !status || !caption || !key) return;
    useCurrentDateWhenAvailable(input);
    let payload;
    try {
      const response = await fetch(instrument.dataset.moonSrc);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      payload = await response.json();
    } catch (error) {
      status.textContent = "The locally generated moon data could not be loaded.";
      caption.textContent = "Use the complete CSV download while the chart data is unavailable.";
      return;
    }
    const nights = new Map(payload.map((night) => [night.date, night]));
    const svgElement = (name, attributes = {}, text) => {
      const node = document.createElementNS(svgNS, name);
      Object.entries(attributes).forEach(([attribute, value]) => node.setAttribute(attribute, value));
      if (text !== undefined) node.textContent = text;
      return node;
    };
    const render = () => {
      const night = nights.get(input.value);
      chart.replaceChildren();
      key.replaceChildren();
      if (!night) {
        status.textContent = `${localDate(input.value)} has no observable nighttime samples for this planet.`;
        caption.textContent = "Choose another date, or use the complete CSV for exact records.";
        return;
      }
      status.textContent = `${localDate(night.date)}, ${localTime(night.start_local)} to ${localTime(night.end_local)} local.`;
      const left = 76, right = 735, top = 35, bottom = 370;
      const start = new Date(night.start_local), end = new Date(night.end_local);
      const span = Math.max(1, end - start), extent = Math.max(1, night.extent_arcsec);
      const x = (offset) => left + (Number(offset) / extent + 1) / 2 * (right - left);
      const y = (time) => top + (new Date(time) - start) / span * (bottom - top);
      chart.append(svgElement("line", { x1: x(0), x2: x(0), y1: top, y2: bottom, class: "moon-planet-axis" }));
      [-1, -0.5, 0, 0.5, 1].forEach((ratio) => {
        const xpos = x(extent * ratio);
        chart.append(svgElement("line", { x1: xpos, x2: xpos, y1: top, y2: bottom, class: "moon-grid-line" }));
        chart.append(svgElement("text", { x: xpos, y: 405, class: "moon-axis-label", "text-anchor": "middle" }, ratio === 0 ? "planet" : `${Math.round(extent * ratio)}″`));
      });
      [0, 0.25, 0.5, 0.75, 1].forEach((ratio) => {
        const ypos = top + ratio * (bottom - top);
        chart.append(svgElement("line", { x1: left, x2: right, y1: ypos, y2: ypos, class: "moon-grid-line" }));
        chart.append(svgElement("text", { x: 65, y: ypos + 4, class: "moon-axis-label", "text-anchor": "end" }, localTimeAt(night.start_local, span * ratio)));
      });
      night.moons.forEach((moon, moonIndex) => {
        const points = night.points.filter((point) => point.moon === moon).sort((a, b) => a.datetime_local.localeCompare(b.datetime_local));
        if (!points.length) return;
        const coordinates = points.map((point) => `${x(point.offset_arcsec)},${y(point.datetime_local)}`).join(" ");
        chart.append(svgElement("polyline", { points: coordinates, class: `moon-track-line moon-series-${moonIndex % 8}` }));
        points.forEach((point) => chart.append(svgElement("circle", { cx: x(point.offset_arcsec), cy: y(point.datetime_local), r: 4.5, class: `moon-track-point moon-series-${moonIndex % 8}` })));
        const item = element("li", `moon-key--${moonIndex % 8}`, moon);
        key.append(item);
      });
      caption.textContent = `Offsets from −${Math.round(extent)} to +${Math.round(extent)} arcseconds. Lines show movement through the selected night.`;
    };
    input.addEventListener("change", render);
    render();
  });
})();
