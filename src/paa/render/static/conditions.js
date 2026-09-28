(() => {
  "use strict";

  const number = (value, digits = 0) => {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed.toFixed(digits) : "Unavailable";
  };

  const addValue = (list, label, value, note) => {
    const group = document.createElement("div");
    const term = document.createElement("dt");
    const description = document.createElement("dd");
    const detail = document.createElement("small");
    term.textContent = label;
    description.textContent = value;
    detail.textContent = note;
    group.append(term, description, detail);
    list.append(group);
  };

  const describeCloud = (value) => {
    if (value <= 15) return "Mostly clear";
    if (value <= 40) return "Some cloud";
    if (value <= 70) return "Cloudy intervals";
    return "Mostly overcast";
  };

  const describeParticles = (value) => {
    if (value <= 10) return "Low haze risk";
    if (value <= 25) return "Some haze possible";
    return "Haze may reduce contrast";
  };

  const localTimestamp = (value, abbreviation) => {
    const [date, time] = String(value).split("T");
    if (!date || !time) return "just now";
    const readableDate = new Date(`${date}T00:00:00Z`).toLocaleDateString([], {
      day: "numeric",
      month: "short",
      year: "numeric",
      timeZone: "UTC",
    });
    return `${readableDate}, ${time.slice(0, 5)} ${abbreviation || "local"}`;
  };

  const load = async (panel) => {
    const latitude = panel.dataset.latitude;
    const longitude = panel.dataset.longitude;
    const status = panel.querySelector("[data-conditions-status]");
    const values = panel.querySelector("[data-conditions-values]");
    const weatherUrl = new URL("https://api.open-meteo.com/v1/forecast");
    weatherUrl.search = new URLSearchParams({
      latitude,
      longitude,
      current: "cloud_cover,precipitation,wind_speed_10m,visibility",
      timezone: "auto",
    });
    const airUrl = new URL("https://air-quality-api.open-meteo.com/v1/air-quality");
    airUrl.search = new URLSearchParams({
      latitude,
      longitude,
      current: "pm2_5,aerosol_optical_depth,dust",
      timezone: "auto",
    });

    try {
      const [weatherResponse, airResponse] = await Promise.all([
        fetch(weatherUrl),
        fetch(airUrl),
      ]);
      if (!weatherResponse.ok || !airResponse.ok) throw new Error("conditions unavailable");
      const [weather, air] = await Promise.all([
        weatherResponse.json(),
        airResponse.json(),
      ]);
      const current = weather.current || {};
      const currentAir = air.current || {};
      const cloud = Number(current.cloud_cover);
      const particles = Number(currentAir.pm2_5);
      addValue(values, "Cloud", `${number(cloud)}%`, describeCloud(cloud));
      addValue(
        values,
        "Rain",
        `${number(current.precipitation, 1)} mm`,
        Number(current.precipitation) > 0 ? "Falling now" : "None now",
      );
      addValue(
        values,
        "Wind",
        `${number(current.wind_speed_10m)} km/h`,
        Number(current.wind_speed_10m) <= 15 ? "Usually manageable" : "Check equipment",
      );
      addValue(
        values,
        "Visibility",
        `${number(Number(current.visibility) / 1000, 1)} km`,
        Number(current.visibility) >= 20000 ? "Good transparency" : "Reduced transparency",
      );
      addValue(
        values,
        "Fine particles",
        `${number(particles, 1)} µg/m³`,
        describeParticles(particles),
      );
      status.textContent = `Updated ${localTimestamp(
        current.time,
        weather.timezone_abbreviation,
      )}`;
      values.hidden = false;
    } catch (_) {
      status.textContent = "Live conditions are unavailable. Use the date planner and check the local forecast before setting out.";
    }
  };

  document.querySelectorAll("[data-conditions]").forEach(load);
})();
