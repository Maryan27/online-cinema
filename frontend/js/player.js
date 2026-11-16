const ALL_QUALITIES = ["480p", "720p", "1080p"];

const kind = UI.param("kind"); // "movie" or "episode"
const playableId = Number(UI.param("id"));
const mediaId = Number(UI.param("media"));

const el = {
  title: document.getElementById("player-title"),
  subtitle: document.getElementById("player-subtitle"),
  error: document.getElementById("player-error"),
  back: document.getElementById("back-link"),
  video: document.getElementById("video"),
  adBadge: document.getElementById("ad-badge"),
  start: document.getElementById("start-button"),
  qualities: document.getElementById("qualities"),
  notice: document.getElementById("player-notice"),
};

let stream = null; // the latest StreamResponse from the API
let adPlaying = false;

function requestStream(quality) {
  const query = quality ? `?quality=${quality}` : "";
  return Api.get(`/api/play/${kind}/${playableId}${query}`);
}

function renderQualities() {
  el.qualities.innerHTML = ALL_QUALITIES.map((quality) => {
    const allowed = stream.available_qualities.includes(quality);
    const active = quality === stream.quality ? "active" : "";
    return allowed
      ? `<button class="quality ${active}" type="button" data-quality="${quality}">${quality}</button>`
      : `<button class="quality" type="button" disabled title="Available with Premium">${quality} 🔒</button>`;
  }).join("");
}

function renderNotice() {
  const notes = [];
  if (stream.ad_url) notes.push("Free plan: an ad plays before the video.");
  if (stream.downgraded) notes.push(`Playing in ${stream.quality}: higher quality needs Premium.`);

  if (notes.length) {
    el.notice.innerHTML = `${notes.join(" ")} <a class="rating" href="/profile.html">Go Premium</a>`;
    el.notice.classList.remove("hidden");
  } else {
    el.notice.classList.add("hidden");
  }
}

function playMain(startAt = 0) {
  adPlaying = false;
  el.adBadge.classList.add("hidden");
  el.video.controls = true;
  el.video.src = stream.stream_url;
  el.video.addEventListener(
    "loadedmetadata",
    () => {
      el.video.currentTime = startAt;
      el.video.play().catch(() => {});
    },
    { once: true }
  );
}

function playAd() {
  adPlaying = true;
  el.video.controls = false; // the ad cannot be skipped or rewound
  el.video.src = stream.ad_url;
  el.adBadge.classList.remove("hidden");
  el.video.addEventListener("ended", () => playMain(), { once: true });
  el.video.play().catch(() => {});
}

el.video.addEventListener("timeupdate", () => {
  if (!adPlaying || !el.video.duration) return;
  const left = Math.ceil(el.video.duration - el.video.currentTime);
  el.adBadge.textContent = `Ad · ${left} s`;
});

el.start.addEventListener("click", () => {
  el.start.classList.add("hidden");
  if (stream.ad_url) playAd();
  else playMain();
});

el.qualities.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-quality]");
  if (!button || button.dataset.quality === stream.quality) return;

  const position = el.video.currentTime;
  try {
    stream = await requestStream(button.dataset.quality);
  } catch (error) {
    UI.message(el.error, error.message);
    return;
  }
  renderQualities();
  renderNotice();
  // During the ad only the next source changes; otherwise continue from the same moment
  if (!adPlaying && el.start.classList.contains("hidden")) playMain(position);
});

async function loadTitle() {
  if (!mediaId) {
    el.title.textContent = "Now playing";
    return;
  }
  el.back.href = `/media.html?id=${mediaId}`;
  const media = await Api.get(`/api/media/${mediaId}`);
  el.title.textContent = media.title;
  document.title = `${media.title} — Kickoff Cinema`;

  if (kind === "episode") {
    for (const season of media.seasons) {
      const episode = season.episodes.find((e) => e.id === playableId);
      if (episode) {
        el.subtitle.textContent = `Season ${season.number}, episode ${episode.number}: ${episode.title}`;
      }
    }
  }
}

(async function init() {
  const user = await renderHeader();
  if (!user) {
    window.location.href = `/login.html?next=${encodeURIComponent(location.pathname + location.search)}`;
    return;
  }
  try {
    [stream] = await Promise.all([requestStream(null), loadTitle()]);
  } catch (error) {
    el.title.textContent = "Cannot play this video";
    UI.message(el.error, error.message);
    return;
  }
  renderQualities();
  renderNotice();
  el.start.classList.remove("hidden");
})();