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
    // Administrators see their role instead of a subscription plan
    const badge =
      user.role === "admin"
        ? `<span class="plan-badge">admin</span>`
        : `<span class="plan-badge ${user.plan}">${user.plan}</span>`;
    links.push(`<a href="/profile.html">${UI.escape(user.name)} ${badge}</a>`);
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

// Show/hide button for every password field (replaces the browser's own reveal icon)
const EYE = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>';
const EYE_OFF = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/><path d="M14.12 14.12a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>';

function addPasswordToggles() {
  document.querySelectorAll('input[type="password"]').forEach((input) => {
    const wrap = document.createElement("div");
    wrap.className = "password-field";
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);

    const button = document.createElement("button");
    button.type = "button";
    button.className = "password-toggle";
    button.title = "Show password";
    button.innerHTML = EYE;
    button.addEventListener("click", () => {
      const show = input.type === "password";
      input.type = show ? "text" : "password";
      button.innerHTML = show ? EYE_OFF : EYE;
      button.title = show ? "Hide password" : "Show password";
    });
    wrap.appendChild(button);
  });
}

document.addEventListener("DOMContentLoaded", addPasswordToggles);