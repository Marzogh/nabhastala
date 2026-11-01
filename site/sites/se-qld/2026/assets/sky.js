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

  const selectedDate = (tool, data) => localToUtc(
    tool.querySelector("[data-sky-date]").value,
    tool.querySelector("[data-sky-time]").value,
    data.timezone,
  );

  const positionForObject = (data, objectId, date) => {
    if (objectId.startsWith("HIP ")) {
      const star = data.starById.get(objectId);
      return star ? horizontalPosition(star[1], star[2], date, data.latitude, data.longitude) : null;
    }
    const bodyName = objectId === "sun" || objectId === "moon"
      ? objectId[0].toUpperCase() + objectId.slice(1)
      : objectId[0].toUpperCase() + objectId.slice(1);
    const coordinates = bodyCoordinates(data.bodies?.[bodyName], data, date);
    return coordinates
      ? horizontalPosition(coordinates.ra, coordinates.dec, date, data.latitude, data.longitude)
      : null;
  };

  const eventLabel = (event, selected, timezone, year, includeAltitude = false) => {
    const moment = new Date(Date.UTC(year, 0, 1) + event[1] * 60000);
    const selectedParts = localParts(selected, timezone);
    const eventParts = localParts(moment, timezone);
    const sameDate = selectedParts.year === eventParts.year
      && selectedParts.month === eventParts.month
      && selectedParts.day === eventParts.day;
    const formatted = new Intl.DateTimeFormat("en-AU", {
      timeZone: timezone,
      ...(sameDate
        ? { hour: "numeric", minute: "2-digit" }
        : { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" }),
    }).format(moment);
    return includeAltitude ? `${formatted}, ${Math.round(event[3])}° altitude` : formatted;
  };

  const renderObjectDetails = (tool, data) => {
    const events = tool.skyEvents;
    const objectId = tool.selectedObjectId;
    if (!events || !objectId || !events.objects[objectId]) return;
    const item = events.objects[objectId];
    const selected = selectedDate(tool, data);
    const position = positionForObject(data, objectId, selected);
    const section = tool.querySelector("[data-sky-selection]");
    section.hidden = false;
    tool.querySelector("[data-sky-selected-name]").textContent = item.name;
    tool.querySelector("[data-sky-position]").textContent = position
      ? `${Math.round(position.altitude)}° altitude, ${Math.round(position.azimuth)}° azimuth (${direction(position.azimuth)})`
      : "Position unavailable for this time.";

    const state = tool.querySelector("[data-sky-horizon-state]");
    if (item.state === "always_above") {
      state.textContent = "Always above the horizon at this location.";
      state.hidden = false;
    } else if (item.state === "always_below") {
      state.textContent = "Does not rise at this location.";
      state.hidden = false;
    } else {
      state.hidden = true;
    }

    const typeNames = events.eventTypeNames;
    const selectedMinute = (selected.getTime() - Date.UTC(events.year, 0, 1)) / 60000;
    const next = (names) => item.events.find(
      (event) => names.includes(typeNames[event[0]]) && event[1] >= selectedMinute,
    );
    const unavailable = `No later event in ${events.year}.`;
    const rise = next(objectId === "sun" ? ["sunrise"] : ["rise"]);
    const transit = next(["upper_transit"]);
    const set = next(objectId === "sun" ? ["sunset"] : ["set"]);
    const fixedState = item.state === "always_above" || item.state === "always_below";
    tool.querySelector("[data-sky-next-rise]").textContent = fixedState
      ? "Not applicable" : rise ? eventLabel(rise, selected, data.timezone, events.year) : unavailable;
    tool.querySelector("[data-sky-next-transit]").textContent = transit
      ? eventLabel(transit, selected, data.timezone, events.year, true) : unavailable;
    tool.querySelector("[data-sky-next-set]").textContent = fixedState
      ? "Not applicable" : set ? eventLabel(set, selected, data.timezone, events.year) : unavailable;
  };

  const populateObjectSearch = (tool, events) => {
    const options = tool.querySelector("[data-sky-options]");
    const searchMap = new Map();
    Object.entries(events.objects)
      .sort(([, first], [, second]) => first.name.localeCompare(second.name))
      .forEach(([objectId, item]) => {
        const value = item.class === "star" && item.name !== objectId
          ? `${item.name} (${objectId})` : item.name;
        const option = document.createElement("option");
        option.value = value;
        options.append(option);
        searchMap.set(value.toLowerCase(), objectId);
        searchMap.set(item.name.toLowerCase(), objectId);
        searchMap.set(objectId.toLowerCase(), objectId);
      });
    tool.skySearchMap = searchMap;
  };

  const loadObjectEvents = async (tool) => {
    if (!tool.skyEventsPromise) {
      tool.skyEventsPromise = fetch(tool.dataset.events).then(async (response) => {
        if (!response.ok) throw new Error("Object event data unavailable");
        const events = await response.json();
        events.eventTypeNames = Object.fromEntries(
          Object.entries(events.event_types).map(([name, code]) => [code, name]),
        );
        tool.skyEvents = events;
        populateObjectSearch(tool, events);
        return events;
      });
    }
    return tool.skyEventsPromise;
  };

  const selectObject = async (tool, data, objectId) => {
    const events = await loadObjectEvents(tool);
    const item = events.objects[objectId];
    if (!item) return;
    tool.selectedObjectId = objectId;
    tool.querySelector("[data-sky-search]").value = (
      item.class === "star" && item.name !== objectId ? `${item.name} (${objectId})` : item.name
    );
    renderObjectDetails(tool, data);
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
      stars.push({
        id: `HIP ${hip}`, point, magnitude: starMagnitude, name,
        altitude: horizontal.altitude, azimuth: horizontal.azimuth,
        constellation: constellationStars.has(hip),
      });
    });

    const bodies = [];
    Object.entries(data.bodies || {}).forEach(([name, series]) => {
      const coordinates = bodyCoordinates(series, data, selected);
      if (!coordinates) return;
      const horizontal = horizontalPosition(coordinates.ra, coordinates.dec, selected, data.latitude, data.longitude);
      if (horizontal.altitude < 0) return;
      bodies.push({
        id: name.toLowerCase(), name, ...horizontal,
        point: project(horizontal.altitude, horizontal.azimuth, centre, radius),
      });
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
    tool.skyHitTargets = [
      ...stars.filter((star) => star.magnitude <= 3),
      ...bodies,
    ];

    const selectedLabel = new Intl.DateTimeFormat("en-AU", {
      dateStyle: "long", timeStyle: "short", timeZone: data.timezone,
    }).format(selected);
    tool.querySelector("[data-sky-status]").textContent = selectedLabel;
    tool.querySelector("[data-sky-print-status]").textContent = `${selectedLabel} local time`;
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
    if (tool.selectedObjectId && tool.skyEvents) renderObjectDetails(tool, data);
  };

  const setCurrentTime = (tool, data) => {
    const parts = localParts(new Date(), data.timezone);
    const currentYear = Number(parts.year);
    tool.querySelector("[data-sky-date]").value = currentYear === data.year
      ? `${parts.year}-${parts.month}-${parts.day}` : `${data.year}-01-01`;
    tool.querySelector("[data-sky-time]").value = currentYear === data.year
      ? `${parts.hour}:${parts.minute}` : "22:00";
  };

  const setInitialTime = (tool, data) => {
    const dateInput = tool.querySelector("[data-sky-date]");
    const timeInput = tool.querySelector("[data-sky-time]");
    const params = new URLSearchParams(window.location.search);
    const dateValue = params.get("date") || "";
    const timeValue = params.get("time") || "";
    const dateIsValid = /^\d{4}-\d{2}-\d{2}$/.test(dateValue)
      && dateValue >= dateInput.min
      && dateValue <= dateInput.max;
    const timeIsValid = /^(?:[01]\d|2[0-3]):[0-5]\d$/.test(timeValue);
    if (dateIsValid && timeIsValid) {
      dateInput.value = dateValue;
      timeInput.value = timeValue;
      return;
    }
    setCurrentTime(tool, data);
  };

  const initialise = async (tool) => {
    const response = await fetch(tool.dataset.source);
    if (!response.ok) throw new Error("Sky chart data unavailable");
    const data = await response.json();
    if (!data.stars?.length) throw new Error("Sky chart data unavailable");
    data.starById = new Map(data.stars.map((star) => [`HIP ${star[0]}`, star]));
    setInitialTime(tool, data);
    const redraw = () => drawChart(tool, data);
    tool.querySelectorAll(
      "[data-sky-date], [data-sky-time], [data-sky-magnitude], [data-sky-constellations]",
    ).forEach((input) => input.addEventListener("input", redraw));
    tool.querySelector("[data-sky-magnitude]").addEventListener("input", (event) => {
      tool.querySelector("[data-sky-magnitude-value]").value = event.target.value;
    });
    tool.querySelector("[data-sky-now]").addEventListener("click", () => {
      setCurrentTime(tool, data);
      redraw();
    });
    tool.querySelector("[data-sky-print]").addEventListener("click", () => window.print());
    const search = tool.querySelector("[data-sky-search]");
    search.addEventListener("focus", () => loadObjectEvents(tool));
    search.addEventListener("input", async () => {
      await loadObjectEvents(tool);
      const objectId = tool.skySearchMap.get(search.value.trim().toLowerCase());
      if (objectId) selectObject(tool, data, objectId);
    });
    tool.querySelector("[data-sky-controls]").addEventListener("submit", (event) => {
      event.preventDefault();
      const objectId = tool.skySearchMap?.get(search.value.trim().toLowerCase());
      if (objectId) selectObject(tool, data, objectId);
    });
    const canvas = tool.querySelector("[data-sky-canvas]");
    canvas.addEventListener("click", (event) => {
      const bounds = canvas.getBoundingClientRect();
      const x = (event.clientX - bounds.left) * (canvas.width / bounds.width);
      const y = (event.clientY - bounds.top) * (canvas.height / bounds.height);
      const target = (tool.skyHitTargets || [])
        .map((item) => ({ item, distance: Math.hypot(item.point.x - x, item.point.y - y) }))
        .filter(({ distance }) => distance <= 16)
        .sort((first, second) => first.distance - second.distance)[0]?.item;
      if (target) selectObject(tool, data, target.id);
    });
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
