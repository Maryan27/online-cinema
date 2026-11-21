// Catalog page: search, filters, pagination and personal recommendations.

const catalog = { page: 1, pageSize: 12 };

const el = {
  form: document.getElementById("filters"),
  grid: document.getElementById("catalog-grid"),
  pageInfo: document.getElementById("page-info"),
  prev: document.getElementById("prev-page"),
  next: document.getElementById("next-page"),
  recommendations: document.getElementById("recommendations"),
  recommendationsGrid: document.getElementById("recommendations-grid"),
  strategyTag: document.getElementById("strategy-tag"),
};

function fillSelect(name, items) {
  const options = items
    .map((item) => `<option value="${item.id}">${UI.escape(item.name)}</option>`)
    .join("");
  el.form.elements[name].insertAdjacentHTML("beforeend", options);
}

async function loadDictionaries() {
  const [genres, countries] = await Promise.all([
    Api.get("/api/genres"),
    Api.get("/api/countries"),
  ]);
  fillSelect("genre_id", genres);
  fillSelect("country_id", countries);
}

async function loadCatalog() {
  // Only non-empty filters are sent: the server-side Builder skips the rest anyway
  const params = new URLSearchParams();
  for (const [key, value] of new FormData(el.form)) {
    if (value.trim()) params.set(key, value.trim());
  }
  params.set("page", catalog.page);
  params.set("page_size", catalog.pageSize);

  try {
    const data = await Api.get(`/api/media?${params}`);
    const pages = Math.max(1, Math.ceil(data.total / data.page_size));
    el.grid.innerHTML = data.items.length
      ? data.items.map(UI.card).join("")
      : `<div class="empty">Nothing found. Try other filters.</div>`;
    el.pageInfo.textContent = `Page ${data.page} of ${pages} · ${data.total} titles`;
    el.prev.disabled = data.page <= 1;
    el.next.disabled = data.page >= pages;
  } catch (error) {
    UI.message(el.grid, error.message);
  }
}

const STRATEGY_LABELS = {
  top_rated: "Top rated for new viewers",
  genre_based: "Based on what you watched",
  top_rated_fallback: "Top rated you haven't seen yet",
};

async function loadRecommendations() {
  const data = await Api.get("/api/users/me/recommendations?limit=6");
  if (!data.items.length) return;
  el.recommendationsGrid.innerHTML = data.items.map(UI.card).join("");
  el.strategyTag.textContent = STRATEGY_LABELS[data.strategy] || "Recommended";
  el.recommendations.classList.remove("hidden");
}

el.form.addEventListener("submit", (event) => {
  event.preventDefault();
  catalog.page = 1;
  loadCatalog();
});

el.form.addEventListener("reset", () => {
  // The fields are cleared right after this event, so reload on the next tick
  setTimeout(() => {
    catalog.page = 1;
    loadCatalog();
  });
});

el.prev.addEventListener("click", () => {
  catalog.page -= 1;
  loadCatalog();
});

el.next.addEventListener("click", () => {
  catalog.page += 1;
  loadCatalog();
});

(async function init() {
  const user = await renderHeader();
  await loadDictionaries();
  await loadCatalog();
  if (user) loadRecommendations().catch(() => {});
})();