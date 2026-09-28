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

  const observingVerdict = ({ cloud, rain, wind, visibility, particles }) => {
    if (rain > 0) return "Poor for observing: rain is falling.";
    if (cloud >= 80) return "Poor for observing: cloud is likely to block the sky.";
    if (visibility < 10 || particles > 25) {
      return "Limited for observing: haze may wash out faint objects.";
    }
    if (cloud <= 20 && wind <= 20 && visibility >= 20 && particles <= 15) {
      return "Good for observing: the sky is mostly clear with manageable wind.";
    }
    if (cloud <= 50 && wind <= 25) {
      return "Fair for observing: clear gaps should be possible.";
    }
    return "Mixed conditions: check outside before setting up.";
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
    const verdict = panel.querySelector("[data-conditions-verdict]");
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
      const rain = Number(current.precipitation);
      const wind = Number(current.wind_speed_10m);
      const visibility = Number(current.visibility) / 1000;
      verdict.textContent = observingVerdict({
        cloud,
        rain,
        wind,
        visibility,
        particles,
      });
      addValue(values, "Cloud", `${number(cloud)}%`, describeCloud(cloud));
      addValue(
        values,
        "Rain",
        `${number(rain, 1)} mm`,
        rain > 0 ? "Falling now" : "None now",
      );
      addValue(
        values,
        "Wind",
        `${number(wind)} km/h`,
        wind <= 15 ? "Usually manageable" : "Check equipment",
      );
      addValue(
        values,
        "Visibility",
        `${number(visibility, 1)} km`,
        visibility >= 20 ? "Good transparency" : "Reduced transparency",
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
      verdict.textContent = "Live conditions are unavailable.";
      status.textContent = "Use the date planner and check the local forecast before setting out.";
    }
  };

  document.querySelectorAll("[data-conditions]").forEach(load);
})();
