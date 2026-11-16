// Admin panel: reports (Template Method on the server), content and plan management.
// The role check here only hides the UI; the server rejects non-admins with 403 anyway.

const CLIPS = [
  "big-buck-bunny",
  "elephants-dream",
  "sintel",
  "tears-of-steel",
  "cosmos-laundromat",
  "spring",
  "agent-327-operation-barbershop",
];
const QUALITIES = ["480p", "720p", "1080p"];
const CHART_VALUE = { popularity: "views", activity: "views", revenue: "revenue" };
const CHART_LABEL = { popularity: "title", activity: "user", revenue: "month" };

const $ = (id) => document.getElementById(id);
const state = { genres: [], countries: [], posterTarget: null };

const reportForm = $("report-form");
const mediaForm = $("media-form");
const episodeForm = $("episode-form");

// ------------------------------------------------------------ helpers

function videoFiles(clip) {
  return Object.fromEntries(QUALITIES.map((q) => [q, `/media/videos/${clip}_${q}.mp4`]));
}

function checkboxes(name, items) {
  return items
    .map(
      (item) => `<label class="check">
        <input type="checkbox" name="${name}" value="${item.id}"> ${UI.escape(item.name)}</label>`
    )
    .join("");
}

function checkedIds(form, name) {
  return [...form.querySelectorAll(`input[name="${name}"]:checked`)].map((input) => Number(input.value));
}

function humanize(key) {
  const text = key.replaceAll("_", " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function isoDate(date) {
  return date.toISOString().slice(0, 10);
}

function barChart(rows, labelKey, valueKey) {
  const max = Math.max(1, ...rows.map((row) => row[valueKey]));
  return rows
    .map(
      (row) => `
      <div class="bar-row">
        <span>${UI.escape(String(row[labelKey]))}</span>
        <div class="bar" style="width: ${(row[valueKey] / max) * 100}%"></div>
        <span class="muted">${row[valueKey]}</span>
      </div>`
    )
    .join("");
}

// ------------------------------------------------------------ tabs

document.querySelector(".tabs").addEventListener("click", (event) => {
  const tab = event.target.closest("[data-tab]");
  if (!tab) return;
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t === tab));
  document
    .querySelectorAll(".tab-panel")
    .forEach((panel) => panel.classList.toggle("hidden", panel.id !== `tab-${tab.dataset.tab}`));
});

// ------------------------------------------------------------ reports

function renderReport(report) {
  const { top_genres: topGenres, ...totals } = report.summary;
  const stats = Object.entries(totals)
    .map(
      ([key, value]) => `
      <div class="stat">
        <div class="stat__value">${UI.escape(String(value))}</div>
        <div class="stat__label">${humanize(key)}</div>
      </div>`
    )
    .join("");

  const chartRows = report.rows.slice(0, 10);
  const chart = chartRows.length
    ? `<h3>Top ${chartRows.length}</h3>
       <div class="chart">${barChart(chartRows, CHART_LABEL[report.report_type], CHART_VALUE[report.report_type])}</div>`
    : "";
  const genres = topGenres?.length
    ? `<h3>Top genres</h3><div class="chart">${barChart(topGenres, "genre", "views")}</div>`
    : "";

  const head = report.columns.map((column) => `<th>${humanize(column)}</th>`).join("");
  const body = report.rows.length
    ? report.rows
        .map(
          (row) =>
            `<tr>${report.columns.map((c) => `<td>${UI.escape(String(row[c]))}</td>`).join("")}</tr>`
        )
        .join("")
    : `<tr><td colspan="${report.columns.length}" class="muted">No data for this period</td></tr>`;

  $("report-output").innerHTML = `
    <h2>${UI.escape(report.title)}</h2>
    <p class="muted">${report.period_start} — ${report.period_end}</p>
    <div class="stats">${stats}</div>
    ${chart}
    ${genres}
    <div class="table-wrap">
      <table class="table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>
    </div>`;
}

reportForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(reportForm));
  const params = new URLSearchParams({ start: data.start, end: data.end });
  try {
    renderReport(await Api.get(`/api/admin/reports/${data.type}?${params}`));
  } catch (error) {
    UI.message($("report-output"), error.message);
  }
});

// ------------------------------------------------------------ content: catalog table

async function loadMedia() {
  const { items } = await Api.get("/api/media?page_size=50");

  $("media-table").innerHTML = `
    <thead><tr><th>Title</th><th>Type</th><th>Year</th><th>Rating</th><th></th></tr></thead>
    <tbody>${items
      .map(
        (m) => `
      <tr>
        <td><a href="/media.html?id=${m.id}">${UI.escape(m.title)}</a></td>
        <td>${m.kind}</td>
        <td>${m.release_year}</td>
        <td class="rating">★ ${m.rating.toFixed(1)}</td>
        <td><div class="row-actions">
          <button class="btn secondary" type="button" data-action="edit" data-id="${m.id}">Edit</button>
          <button class="btn secondary" type="button" data-action="poster" data-id="${m.id}">Poster</button>
          ${m.kind === "series"
            ? `<button class="btn secondary" type="button" data-action="season" data-id="${m.id}">+ Season</button>`
            : ""}
          <button class="btn danger" type="button" data-action="delete" data-id="${m.id}">Delete</button>
        </div></td>
      </tr>`
      )
      .join("")}</tbody>`;

  // keep the series list in the episode form up to date
  const select = episodeForm.elements.series;
  const selected = select.value;
  select.innerHTML =
    `<option value="">Choose a series…</option>` +
    items
      .filter((m) => m.kind === "series")
      .map((m) => `<option value="${m.id}">${UI.escape(m.title)}</option>`)
      .join("");
  select.value = selected;
}

$("media-table").addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const id = Number(button.dataset.id);
  const message = $("media-message");

  try {
    switch (button.dataset.action) {
      case "edit":
        await startEdit(id);
        break;
      case "poster":
        state.posterTarget = id;
        $("poster-input").click();
        break;
      case "season": {
        const number = Number(prompt("Season number:"));
        if (!number) return;
        await Api.post(`/api/admin/series/${id}/seasons`, { number });
        UI.message(message, `Season ${number} added.`, "success");
        if (Number(episodeForm.elements.series.value) === id) await loadSeasons(id);
        break;
      }
      case "delete":
        if (!confirm("Delete this title? This cannot be undone.")) return;
        await Api.delete(`/api/admin/media/${id}`);
        UI.message(message, "Title deleted.", "success");
        await loadMedia();
        break;
    }
  } catch (error) {
    UI.message(message, error.message);
  }
});

$("poster-input").addEventListener("change", async (event) => {
  const file = event.target.files[0];
  event.target.value = ""; // allow choosing the same file again later
  if (!file || !state.posterTarget) return;

  const data = new FormData();
  data.append("poster", file);
  try {
    await Api.post(`/api/admin/media/${state.posterTarget}/poster`, data);
    UI.message($("media-message"), "Poster uploaded.", "success");
  } catch (error) {
    UI.message($("media-message"), error.message);
  }
});

// ------------------------------------------------------------ content: add / edit form

function toggleMovieFields() {
  const isMovie = mediaForm.elements.kind.value === "movie";
  const editing = Boolean(mediaForm.elements.id.value);
  $("movie-fields").classList.toggle("hidden", !isMovie);
  $("clip-field").classList.toggle("hidden", !isMovie || editing);
  mediaForm.elements.duration_minutes.required = isMovie;
}

function resetMediaForm() {
  mediaForm.reset();
  mediaForm.elements.id.value = ""; // reset() keeps the value of hidden inputs
  mediaForm.elements.kind.disabled = false;
  $("media-form-title").textContent = "Add title";
  $("cancel-edit").classList.add("hidden");
  toggleMovieFields();
}

async function startEdit(id) {
  const media = await Api.get(`/api/media/${id}`);
  const f = mediaForm.elements;
  resetMediaForm();

  f.id.value = media.id;
  f.kind.value = media.kind;
  f.kind.disabled = true;
  f.title.value = media.title;
  f.description.value = media.description;
  f.release_year.value = media.release_year;
  f.rating.value = media.rating;
  f.duration_minutes.value = media.duration_minutes ?? "";
  mediaForm.querySelectorAll('input[name="genre"]').forEach((input) => {
    input.checked = media.genres.some((g) => g.id === Number(input.value));
  });
  mediaForm.querySelectorAll('input[name="country"]').forEach((input) => {
    input.checked = media.countries.some((c) => c.id === Number(input.value));
  });

  $("media-form-title").textContent = `Edit: ${media.title}`;
  $("cancel-edit").classList.remove("hidden");
  toggleMovieFields();
  mediaForm.scrollIntoView({ behavior: "smooth" });
}

mediaForm.elements.kind.addEventListener("change", toggleMovieFields);
$("cancel-edit").addEventListener("click", resetMediaForm);

mediaForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const f = mediaForm.elements;
  const id = f.id.value;
  const kind = f.kind.value;
  const body = {
    title: f.title.value.trim(),
    description: f.description.value.trim(),
    release_year: Number(f.release_year.value),
    rating: Number(f.rating.value || 0),
    genre_ids: checkedIds(mediaForm, "genre"),
    country_ids: checkedIds(mediaForm, "country"),
  };
  if (kind === "movie") body.duration_minutes = Number(f.duration_minutes.value);

  try {
    if (id) {
      await Api.put(`/api/admin/media/${id}`, body);
    } else if (kind === "movie") {
      await Api.post("/api/admin/movies", { ...body, video_files: videoFiles(f.clip.value) });
    } else {
      await Api.post("/api/admin/series", body);
    }
    UI.message($("media-form-message"), id ? "Changes saved." : "Title added to the catalog.", "success");
    resetMediaForm();
    await loadMedia();
  } catch (error) {
    UI.message($("media-form-message"), error.message);
  }
});

// ------------------------------------------------------------ content: episodes

async function loadSeasons(seriesId) {
  const select = episodeForm.elements.season;
  if (!seriesId) {
    select.innerHTML = `<option value="">—</option>`;
    return;
  }
  const series = await Api.get(`/api/media/${seriesId}`);
  select.innerHTML = series.seasons.length
    ? series.seasons
        .map((s) => `<option value="${s.id}">Season ${s.number} (${s.episodes.length} episodes)</option>`)
        .join("")
    : `<option value="">No seasons yet: add one in the table below</option>`;
}

episodeForm.elements.series.addEventListener("change", (event) => {
  loadSeasons(Number(event.target.value)).catch((error) =>
    UI.message($("episode-message"), error.message)
  );
});

episodeForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const f = episodeForm.elements;
  if (!f.season.value) {
    UI.message($("episode-message"), "Choose a season first.");
    return;
  }
  try {
    await Api.post(`/api/admin/seasons/${f.season.value}/episodes`, {
      number: Number(f.number.value),
      title: f.title.value.trim(),
      duration_minutes: Number(f.duration_minutes.value),
      video_files: videoFiles(f.clip.value),
    });
    UI.message($("episode-message"), "Episode added.", "success");
    f.number.value = "";
    f.title.value = "";
    await loadSeasons(Number(f.series.value));
  } catch (error) {
    UI.message($("episode-message"), error.message);
  }
});

// ------------------------------------------------------------ plans

async function loadPlans() {
  const plans = await Api.get("/api/plans");
  $("plans-admin").innerHTML = plans
    .map((plan) => {
      const free = plan.type === "free";
      return `
      <form class="plan ${plan.type}" data-plan="${plan.id}">
        <div class="plan__name">${plan.type}</div>
        <label>Price, UAH</label>
        <input name="price" type="number" min="0" step="0.01" value="${plan.price}" ${free ? "disabled" : ""}>
        <label>Duration, days</label>
        <input name="duration_days" type="number" min="1" value="${plan.duration_days ?? ""}"
               ${free ? 'disabled placeholder="Never expires"' : ""}>
        <button class="btn" type="submit" ${free ? "disabled" : ""}>Save</button>
        ${free ? `<p class="muted small">The free plan always costs 0 and never expires.</p>` : ""}
      </form>`;
    })
    .join("");
}

$("plans-admin").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.target;
  try {
    await Api.put(`/api/admin/plans/${form.dataset.plan}`, {
      price: Number(form.elements.price.value),
      duration_days: Number(form.elements.duration_days.value),
    });
    UI.message($("plans-message"), "Plan saved.", "success");
    await loadPlans();
  } catch (error) {
    UI.message($("plans-message"), error.message);
  }
});

$("expire-button").addEventListener("click", async () => {
  try {
    const { expired } = await Api.post("/api/admin/subscriptions/expire-overdue");
    UI.message($("plans-message"), `Moved ${expired} overdue subscription(s) to Free.`, "success");
  } catch (error) {
    UI.message($("plans-message"), error.message);
  }
});

// ------------------------------------------------------------ init

(async function init() {
  const user = await renderHeader();
  if (!user) {
    window.location.href = `/login.html?next=${encodeURIComponent(location.pathname)}`;
    return;
  }
  if (user.role !== "admin") {
    UI.message($("admin-guard"), "Administrator access required.");
    return;
  }
  $("admin-app").classList.remove("hidden");

  [state.genres, state.countries] = await Promise.all([
    Api.get("/api/genres"),
    Api.get("/api/countries"),
  ]);
  $("genre-checks").innerHTML = checkboxes("genre", state.genres);
  $("country-checks").innerHTML = checkboxes("country", state.countries);
  const clipOptions = CLIPS.map((clip) => `<option value="${clip}">${clip}</option>`).join("");
  mediaForm.elements.clip.innerHTML = clipOptions;
  episodeForm.elements.clip.innerHTML = clipOptions;
  toggleMovieFields();

  const today = new Date();
  reportForm.elements.end.value = isoDate(today);
  reportForm.elements.start.value = isoDate(new Date(today.getTime() - 90 * 24 * 60 * 60 * 1000));

  await Promise.all([loadMedia(), loadPlans()]);
  reportForm.requestSubmit(); // show the popularity report right away
})();