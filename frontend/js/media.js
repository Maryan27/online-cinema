// Media details page: info, favourites, the watch button and the episode list.

const mediaId = Number(UI.param("id"));
const container = document.getElementById("media-details");
let isFavorite = false;

function playUrl(kind, id) {
  return `/player.html?kind=${kind}&id=${id}&media=${mediaId}`;
}

function loginUrl() {
  return `/login.html?next=${encodeURIComponent(location.pathname + location.search)}`;
}

function accessNote(user) {
  if (!user) return "Sign in to watch. Free accounts can watch up to 720p with ads.";
  return user.plan === "premium"
    ? "Premium: up to 1080p, no ads."
    : 'Free: up to 720p, with ads. <a class="rating" href="/profile.html">Go Premium</a> for 1080p without ads.';
}

function watchButton(media, user) {
  if (!user) return `<a class="btn" href="${loginUrl()}">Log in to watch</a>`;
  if (media.kind === "movie") return `<a class="btn" href="${playUrl("movie", media.id)}">▶ Watch</a>`;

  const firstEpisode = media.seasons[0]?.episodes[0];
  return firstEpisode
    ? `<a class="btn" href="${playUrl("episode", firstEpisode.id)}">▶ Watch S1 E1</a>`
    : `<button class="btn" disabled>No episodes yet</button>`;
}

function favoriteButton(user) {
  if (!user) return "";
  const label = isFavorite ? "★ In favorites" : "☆ Add to favorites";
  return `<button id="favorite-button" class="btn secondary" type="button">${label}</button>`;
}

function renderEpisodes(media, user) {
  if (media.kind !== "series") return "";
  const seasons = media.seasons
    .map((season) => {
      const episodes = season.episodes.length
        ? season.episodes
            .map(
              (episode) => `
          <div class="episode">
            <span class="episode__number">${episode.number}</span>
            <div class="episode__info">
              <div>${UI.escape(episode.title)}</div>
              <div class="muted small">${episode.duration_minutes} min</div>
            </div>
            <a class="btn secondary" href="${user ? playUrl("episode", episode.id) : loginUrl()}">▶ Play</a>
          </div>`
            )
            .join("")
        : `<div class="empty">No episodes yet</div>`;
      return `<h3>Season ${season.number}</h3><div class="episode-list">${episodes}</div>`;
    })
    .join("");
  return `<section class="section"><h2>Episodes</h2>${seasons}</section>`;
}

function render(media, user) {
  const genres = media.genres.map((g) => `<span class="tag">${UI.escape(g.name)}</span>`).join("");
  const countries = media.countries.map((c) => c.name).join(", ");
  const kind = media.kind === "series" ? "Series" : "Movie";
  const duration = media.duration_minutes ? ` · ${media.duration_minutes} min` : "";
  const qualities = media.available_qualities.length
    ? `<p class="muted small">Available in: ${media.available_qualities.join(", ")}</p>`
    : "";

  container.innerHTML = `
    <div class="details">
      <div class="details__poster">${UI.poster(media)}</div>
      <div>
        <h1>${UI.escape(media.title)}</h1>
        <p class="muted">${kind} · ${media.release_year} ·
          <span class="rating">★ ${media.rating.toFixed(1)}</span>${duration} · ${UI.escape(countries)}</p>
        <div class="tags">${genres}</div>
        <p class="details__description">${UI.escape(media.description)}</p>
        <div class="actions">${watchButton(media, user)}${favoriteButton(user)}</div>
        <p class="muted small">${accessNote(user)}</p>
        ${qualities}
      </div>
    </div>
    ${renderEpisodes(media, user)}`;

  document.getElementById("favorite-button")?.addEventListener("click", toggleFavorite);
}

async function toggleFavorite(event) {
  const button = event.currentTarget;
  button.disabled = true;
  try {
    if (isFavorite) {
      await Api.delete(`/api/users/me/favorites/${mediaId}`);
    } else {
      await Api.put(`/api/users/me/favorites/${mediaId}`);
    }
    isFavorite = !isFavorite;
    button.textContent = isFavorite ? "★ In favorites" : "☆ Add to favorites";
  } catch (error) {
    alert(error.message);
  } finally {
    button.disabled = false;
  }
}

(async function init() {
  const user = await renderHeader();
  if (!mediaId) {
    UI.message(container, "Media not found");
    return;
  }
  try {
    const [media, favorites] = await Promise.all([
      Api.get(`/api/media/${mediaId}`),
      user ? Api.get("/api/users/me/favorites") : Promise.resolve([]),
    ]);
    isFavorite = favorites.some((favorite) => favorite.id === mediaId);
    document.title = `${media.title} — Kickoff Cinema`;
    render(media, user);
  } catch (error) {
    UI.message(container, error.message);
  }
})();