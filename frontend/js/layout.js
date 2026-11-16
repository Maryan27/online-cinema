// Shared UI helpers and the site header rendered on every page.

const UI = {
  /** Escapes text coming from the API before inserting it into HTML (XSS protection). */
  escape(value) {
    const div = document.createElement("div");
    div.textContent = value ?? "";
    return div.innerHTML;
  },

  /** Poster with a generated gradient fallback when the image is missing. */
  poster(media) {
    const hue = (media.id * 47) % 360;
    const image = media.poster_url
      ? `<img src="${UI.escape(media.poster_url)}" alt="" loading="lazy" onerror="this.remove()">`
      : "";
    return `<div class="poster" style="--hue: ${hue}">
              <span class="poster__title">${UI.escape(media.title)}</span>${image}
            </div>`;
  },

  card(media) {
    const genres = media.genres.map((g) => g.name).join(", ");
    const kind = media.kind === "series" ? "Series" : "Movie";
    return `<a class="card" href="/media.html?id=${media.id}">
              ${UI.poster(media)}
              <div class="card__title">${UI.escape(media.title)}</div>
              <div class="card__meta">${kind} · ${media.release_year} ·
                <span class="rating">★ ${media.rating.toFixed(1)}</span></div>
              <div class="card__meta">${UI.escape(genres)}</div>
            </a>`;
  },

  message(container, text, type = "error") {
    container.innerHTML = `<div class="message ${type}">${UI.escape(text)}</div>`;
  },

  param(name) {
    return new URLSearchParams(window.location.search).get(name);
  },
};

/** Renders the header and returns the current user, or null for a guest. */
async function renderHeader() {
  let user = null;
  if (Api.isLoggedIn()) {
    try {
      user = await Api.get("/api/users/me");
    } catch {
      Api.clearToken();
    }
  }

  const links = [`<a href="/">Catalog</a>`];
  if (user) {
    links.push(
      `<a href="/profile.html">${UI.escape(user.name)}
         <span class="plan-badge ${user.plan}">${user.plan}</span></a>`
    );
    if (user.role === "admin") links.push(`<a href="/admin.html">Admin</a>`);
    links.push(`<a href="#" id="logout-link">Log out</a>`);
  } else {
    links.push(`<a href="/login.html">Log in</a>`, `<a class="btn" href="/register.html">Sign up</a>`);
  }

  document.getElementById("site-header").innerHTML = `
    <div class="container">
      <a class="logo" href="/">Kickoff <span>Cinema</span></a>
      <nav class="nav">${links.join("")}</nav>
    </div>`;

  document.getElementById("logout-link")?.addEventListener("click", (event) => {
    event.preventDefault();
    Api.clearToken();
    window.location.href = "/";
  });
  return user;
}