(() => {
  "use strict";

  const radians = (degrees) => (degrees * Math.PI) / 180;
  const degrees = (value) => (value * 180) / Math.PI;
  const wrap = (value, range = 360) => ((value % range) + range) % range;

  const localParts = (date, timezone) => {
    const parts = new Intl.DateTimeFormat("en-CA", {
      timeZone: timezone,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23",
    }).formatToParts(date);
    return Object.fromEntries(parts.map((part) => [part.type, part.value]));
  };

  const localToUtc = (dateValue, timeValue, timezone) => {
    const assumedUtc = Date.parse(`${dateValue}T${timeValue}:00Z`);
    let result = assumedUtc;
    for (let pass = 0; pass < 2; pass += 1) {
      const parts = localParts(new Date(result), timezone);
      const represented = Date.UTC(
        Number(parts.year), Number(parts.month) - 1, Number(parts.day),
        Number(parts.hour), Number(parts.minute),
      );
      result += assumedUtc - represented;
    }
    return new Date(result);
  };

  const siderealDegrees = (date, longitude) => {
    const days = date.getTime() / 86400000 + 2440587.5 - 2451545.0;
    return wrap(280.46061837 + 360.98564736629 * days + longitude);
  };

  const horizontalPosition = (ra, dec, date, latitude, longitude) => {
    const lat = radians(latitude);
    const declination = radians(dec);
    const hourAngle = radians(wrap(siderealDegrees(date, longitude) - ra + 180) - 180);
    const altitude = Math.asin(
      Math.sin(declination) * Math.sin(lat)
        + Math.cos(declination) * Math.cos(lat) * Math.cos(hourAngle),
    );
    const azimuth = wrap(degrees(Math.atan2(
      -Math.sin(hourAngle) * Math.cos(declination),
      Math.sin(declination) * Math.cos(lat)
        - Math.cos(declination) * Math.sin(lat) * Math.cos(hourAngle),
    )));
    return { altitude: degrees(altitude), azimuth };
  };

  const project = (altitude, azimuth, centre, radius) => {
    const distance = ((90 - altitude) / 90) * radius;
    const angle = radians(azimuth);
    return {
      x: centre - distance * Math.sin(angle),
      y: centre - distance * Math.cos(angle),
    };
  };

  const bodyCoordinates = (series, data, date) => {
    if (!series?.length || !data.ephemeris_start_utc) return null;
    const start = Date.parse(data.ephemeris_start_utc);
    const step = data.ephemeris_step_hours * 3600000;
    const raw = (date.getTime() - start) / step;
    const position = Math.max(0, Math.min(series.length - 1, raw));
    const first = Math.floor(position);
    const second = Math.min(series.length - 1, first + 1);
    const fraction = position - first;
    const deltaRa = wrap(series[second][0] - series[first][0] + 180) - 180;
    return {
      ra: wrap(series[first][0] + deltaRa * fraction),
      dec: series[first][1] + (series[second][1] - series[first][1]) * fraction,
    };
  };

  const palette = (daylight, printing) => {
    if (printing) {
      return {
        background: "#ffffff", ink: "#000000", fieldStar: "#555555",
        constellationStar: "#000000", soft: "#555555", line: "#777777",
        bodies: {},
      };
    }
    const explicit = document.documentElement.dataset.theme;
    const dark = explicit === "dark"
      || (explicit !== "light" && matchMedia("(prefers-color-scheme: dark)").matches);
    const bodies = dark
      ? { Sun: "#f4c95d", Moon: "#e3ded0", Mercury: "#b7afa1", Venus: "#f0c27a", Mars: "#f0785f", Jupiter: "#d7a46d", Saturn: "#d9bd75", Uranus: "#71c5c9", Neptune: "#648fd8" }
      : { Sun: "#b87b00", Moon: "#756f65", Mercury: "#69645d", Venus: "#a96c15", Mars: "#b13b2a", Jupiter: "#96633d", Saturn: "#88702e", Uranus: "#277f83", Neptune: "#365f9d" };
    if (daylight) {
      return dark
        ? { background: "#26333b", ink: "#f3ead9", fieldStar: "#d9dfdd", constellationStar: "#b7ca98", soft: "#a8b5b6", line: "#81979d", bodies }
        : { background: "#dbe8ec", ink: "#253037", fieldStar: "#566066", constellationStar: "#536047", soft: "#718086", line: "#7f969b", bodies };
    }
    return dark
      ? { background: "#12140f", ink: "#f0eadc", fieldStar: "#e7e2d8", constellationStar: "#a8bc8c", soft: "#98978e", line: "#71806b", bodies }
      : { background: "#f4efe5", ink: "#28251f", fieldStar: "#45413a", constellationStar: "#536047", soft: "#777064", line: "#89927d", bodies };
  };

  const direction = (azimuth) => {
    const names = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
    return names[Math.round(azimuth / 45) % 8];
  };

  const drawCompass = (context, centre, radius, colours) => {
    context.strokeStyle = colours.soft;
    context.fillStyle = colours.ink;
    context.textAlign = "center";
    context.textBaseline = "middle";
    for (let bearing = 0; bearing < 360; bearing += 5) {
      const angle = radians(bearing);
      const inner = radius - (bearing % 30 === 0 ? 20 : bearing % 10 === 0 ? 13 : 7);
      context.beginPath();
      context.moveTo(centre - inner * Math.sin(angle), centre - inner * Math.cos(angle));
      context.lineTo(centre - radius * Math.sin(angle), centre - radius * Math.cos(angle));
      context.stroke();
      if (bearing % 30 === 0) {
        context.font = "10px Atkinson Hyperlegible, sans-serif";
        context.fillText(`${bearing}°`, centre - (radius - 34) * Math.sin(angle), centre - (radius - 34) * Math.cos(angle));
      }
    }
    ["N", "NE", "E", "SE", "S", "SW", "W", "NW"].forEach((label, index) => {
      const angle = radians(index * 45);
      context.font = "700 16px Atkinson Hyperlegible, sans-serif";
      context.fillText(label, centre - (radius + 24) * Math.sin(angle), centre - (radius + 24) * Math.cos(angle));
    });
  };

  const drawBody = (context, body, colours, printing) => {
    const { x, y } = body.point;
    context.lineWidth = 1.5;
    context.strokeStyle = colours.ink;
    if (body.name === "Moon") {
      context.fillStyle = printing ? "#ffffff" : colours.bodies.Moon;
      context.beginPath();
      context.arc(x, y, 7, 0, Math.PI * 2);
      context.fill();
      context.stroke();
    } else if (body.name === "Sun") {
      context.fillStyle = printing ? "#ffffff" : colours.bodies.Sun;
      context.beginPath();
      context.arc(x, y, 8, 0, Math.PI * 2);
      context.fill();
      context.stroke();
      context.beginPath();
      context.arc(x, y, 11, 0, Math.PI * 2);
      context.stroke();
    } else {
      context.fillStyle = printing ? "#000000" : colours.bodies[body.name];
      context.beginPath();
      context.arc(x, y, 5, 0, Math.PI * 2);
      context.fill();
    }
    context.font = "700 12px Atkinson Hyperlegible, sans-serif";
    context.textAlign = "left";
    context.fillStyle = printing ? "#000000" : colours.bodies[body.name];
    context.fillText(body.name, x + 9, y - 7);
  };

  const drawChart = (tool, data, printing = false) => {
    const canvas = tool.querySelector("[data-sky-canvas]");
    const context = canvas.getContext("2d");
    const dateValue = tool.querySelector("[data-sky-date]").value;
    const timeValue = tool.querySelector("[data-sky-time]").value;
    const magnitude = Number(tool.querySelector("[data-sky-magnitude]").value);
    const showLines = tool.querySelector("[data-sky-constellations]").checked;
    const selected = localToUtc(dateValue, timeValue, data.timezone);
    const centre = 450;
    const radius = 372;
    const positions = new Map();
    const constellationStars = new Set(
      data.constellations.flatMap(([, , pairs]) => pairs.flat()),
    );
    const stars = [];
    data.stars.forEach(([hip, ra, dec, starMagnitude, name]) => {
      if (starMagnitude > magnitude) return;
      const horizontal = horizontalPosition(ra, dec, selected, data.latitude, data.longitude);
      if (horizontal.altitude < 0) return;
      const point = project(horizontal.altitude, horizontal.azimuth, centre, radius);
      positions.set(hip, point);
      stars.push({ point, magnitude: starMagnitude, name, constellation: constellationStars.has(hip) });
    });

    const bodies = [];
    Object.entries(data.bodies || {}).forEach(([name, series]) => {
      const coordinates = bodyCoordinates(series, data, selected);
      if (!coordinates) return;
      const horizontal = horizontalPosition(coordinates.ra, coordinates.dec, selected, data.latitude, data.longitude);
      if (horizontal.altitude < 0) return;
      bodies.push({ name, ...horizontal, point: project(horizontal.altitude, horizontal.azimuth, centre, radius) });
    });

    const sun = bodies.find((body) => body.name === "Sun");
    const colours = palette(Boolean(sun && sun.altitude > -6), printing);
    context.clearRect(0, 0, 900, 900);
    context.fillStyle = colours.background;
    context.fillRect(0, 0, 900, 900);
    context.lineWidth = 1;
    context.strokeStyle = colours.soft;
    [radius / 3, (radius * 2) / 3, radius].forEach((ring) => {
      context.beginPath();
      context.arc(centre, centre, ring, 0, Math.PI * 2);
      context.stroke();
    });
    drawCompass(context, centre, radius, colours);

    if (showLines) {
      context.strokeStyle = colours.line;
      context.globalAlpha = 0.72;
      data.constellations.forEach(([, , pairs]) => pairs.forEach(([first, second]) => {
        const start = positions.get(first);
        const end = positions.get(second);
        if (!start || !end || Math.hypot(end.x - start.x, end.y - start.y) > 300) return;
        context.beginPath();
        context.moveTo(start.x, start.y);
        context.lineTo(end.x, end.y);
        context.stroke();
      }));
      context.globalAlpha = 1;
    }

    stars.forEach((star) => {
      context.fillStyle = star.constellation ? colours.constellationStar : colours.fieldStar;
      context.beginPath();
      context.arc(star.point.x, star.point.y, Math.max(0.7, 3.8 - star.magnitude * 0.48), 0, Math.PI * 2);
      context.fill();
      if (star.name && star.magnitude <= 1.6) {
        context.font = "11px Atkinson Hyperlegible, sans-serif";
        context.fillStyle = colours.soft;
        context.textAlign = "left";
        context.fillText(star.name, star.point.x + 5, star.point.y - 5);
      }
    });
    bodies.forEach((body) => drawBody(context, body, colours, printing));

    tool.querySelector("[data-sky-status]").textContent = new Intl.DateTimeFormat("en-AU", {
      dateStyle: "long", timeStyle: "short", timeZone: data.timezone,
    }).format(selected);
    const objects = tool.querySelector("[data-sky-objects]");
    objects.replaceChildren();
    bodies.filter((body) => body.name !== "Sun")
      .sort((first, second) => second.altitude - first.altitude)
      .forEach((body) => {
        const item = document.createElement("li");
        const name = document.createElement("strong");
        const detail = document.createElement("span");
        name.textContent = body.name;
        detail.textContent = `${Math.round(body.altitude)}° high, ${direction(body.azimuth)}`;
        item.append(name, detail);
        objects.append(item);
      });
    if (!objects.children.length) {
      const item = document.createElement("li");
      item.textContent = "No Moon or planet is above the horizon.";
      objects.append(item);
    }
  };

  const setCurrentTime = (tool, data) => {
    const parts = localParts(new Date(), data.timezone);
    const currentYear = Number(parts.year);
    tool.querySelector("[data-sky-date]").value = currentYear === data.year
      ? `${parts.year}-${parts.month}-${parts.day}` : `${data.year}-01-01`;
    tool.querySelector("[data-sky-time]").value = currentYear === data.year
      ? `${parts.hour}:${parts.minute}` : "22:00";
  };

  const initialise = async (tool) => {
    const response = await fetch(tool.dataset.source);
    if (!response.ok) throw new Error("Sky chart data unavailable");
    const data = await response.json();
    if (!data.stars?.length) throw new Error("Sky chart data unavailable");
    setCurrentTime(tool, data);
    const redraw = () => drawChart(tool, data);
    tool.querySelectorAll("input").forEach((input) => input.addEventListener("input", redraw));
    tool.querySelector("[data-sky-magnitude]").addEventListener("input", (event) => {
      tool.querySelector("[data-sky-magnitude-value]").value = event.target.value;
    });
    tool.querySelector("[data-sky-now]").addEventListener("click", () => {
      setCurrentTime(tool, data);
      redraw();
    });
    tool.querySelector("[data-sky-print]").addEventListener("click", () => window.print());
    new MutationObserver(redraw).observe(document.documentElement, {
      attributes: true, attributeFilter: ["data-theme"],
    });
    window.addEventListener("beforeprint", () => drawChart(tool, data, true));
    window.addEventListener("afterprint", redraw);
    redraw();
  };

  document.querySelectorAll("[data-sky-tool]").forEach((tool) => {
    initialise(tool).catch(() => {
      tool.querySelector("[data-sky-status]").textContent = "The chart could not be loaded. Use a monthly chart below.";
    });
  });
})();
