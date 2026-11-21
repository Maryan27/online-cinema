// Profile page: subscription (State + Adapter on the server), account settings, favourites.

const el = {
  subscriptionMessage: document.getElementById("subscription-message"),
  facts: document.getElementById("subscription-facts"),
  plans: document.getElementById("plans"),
  profileForm: document.getElementById("profile-form"),
  profileMessage: document.getElementById("profile-message"),
  favorites: document.getElementById("favorites-grid"),
};

const PLAN_PERKS = {
  free: ["Whole catalog", "Ads before every video", "Up to 720p"],
  premium: ["Whole catalog", "No ads", "Up to 1080p"],
};

function formatDate(value) {
  return value ? new Date(value).toLocaleDateString() : "—";
}

function renewalText(subscription) {
  if (subscription.plan !== "premium") return "—";
  return subscription.auto_renew
    ? `Automatic on ${formatDate(subscription.expires_at)}`
    : `Cancelled: Premium until ${formatDate(subscription.expires_at)}, then Free`;
}

function renderSubscription(subscription) {
  el.facts.innerHTML = `
    <dt>Current plan</dt><dd><span class="plan-badge ${subscription.plan}">${subscription.plan}</span></dd>
    <dt>Active until</dt><dd>${subscription.expires_at ? formatDate(subscription.expires_at) : "No end date"}</dd>
    <dt>Renewal</dt><dd>${renewalText(subscription)}</dd>
    <dt>Ads</dt><dd>${subscription.requires_ad ? "Yes" : "No"}</dd>
    <dt>Max quality</dt><dd>${subscription.max_quality}</dd>`;
}

function planAction(plan, subscription) {
  const onPremium = subscription.plan === "premium";
  if (plan.type === "premium") {
    if (!onPremium) return `<button class="btn" data-action="upgrade">Upgrade to Premium</button>`;
    return subscription.auto_renew
      ? `<button class="btn danger" data-action="cancel">Cancel Premium</button>`
      : `<button class="btn" data-action="resume">Resume Premium</button>`;
  }
  if (!onPremium) return `<button class="btn secondary" disabled>Current plan</button>`;
  return subscription.auto_renew
    ? `<button class="btn secondary" disabled>Not active</button>`
    : `<button class="btn secondary" disabled>From ${formatDate(subscription.expires_at)}</button>`;
}

function renderPlans(plans, subscription) {
  el.plans.innerHTML = plans
    .map((plan) => {
      const current = plan.type === subscription.plan;
      const price = plan.price > 0 ? `${plan.price} UAH` : "Free";
      const period = plan.duration_days ? ` / ${plan.duration_days} days` : "";
      const perks = PLAN_PERKS[plan.type].map((perk) => `<li>${perk}</li>`).join("");
      return `
        <div class="plan ${plan.type} ${current ? "current" : ""}">
          <div class="plan__name">${plan.type}</div>
          <div class="plan__price">${price}<span class="muted small">${period}</span></div>
          <ul>${perks}</ul>
          ${planAction(plan, subscription)}
        </div>`;
    })
    .join("");
}

async function loadSubscription() {
  const [subscription, plans] = await Promise.all([
    Api.get("/api/subscription"),
    Api.get("/api/plans"),
  ]);
  renderSubscription(subscription);
  renderPlans(plans, subscription);
}

el.plans.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const action = button.dataset.action;
  if (
    action === "cancel" &&
    !confirm("Cancel Premium? It stays active until the end of the paid period and will not be renewed.")
  ) return;

  button.disabled = true;
  el.subscriptionMessage.innerHTML = "";
  try {
    if (action === "upgrade") {
      await Api.post("/api/subscription/premium");
      UI.message(el.subscriptionMessage, "Payment approved. Welcome to Premium!", "success");
    } else if (action === "resume") {
      await Api.post("/api/subscription/premium");
      UI.message(el.subscriptionMessage, "Auto-renewal is on again. No extra payment needed.", "success");
    } else {
      const subscription = await Api.delete("/api/subscription/premium");
      UI.message(
        el.subscriptionMessage,
        `Premium cancelled. It stays active until ${formatDate(subscription.expires_at)} and will not be renewed.`,
        "success",
      );
    }
    await loadSubscription();
    await renderHeader(); // refresh the plan badge in the header
  } catch (error) {
    UI.message(el.subscriptionMessage, error.message);
    button.disabled = false;
  }
});

el.profileForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(el.profileForm));
  const changes = { name: data.name.trim() };
  if (data.password) changes.password = data.password; // only send the password if it was typed

  try {
    const user = await Api.put("/api/users/me", changes);
    el.profileForm.elements.password.value = "";
    UI.message(el.profileMessage, "Profile saved.", "success");
    el.profileForm.elements.name.value = user.name;
    await renderHeader();
  } catch (error) {
    UI.message(el.profileMessage, error.message);
  }
});

async function loadFavorites() {
  const favorites = await Api.get("/api/users/me/favorites");
  el.favorites.innerHTML = favorites.length
    ? favorites.map(UI.card).join("")
    : `<div class="empty">No favorites yet. Add titles from their pages.</div>`;
}

(async function init() {
  const user = await renderHeader();
  if (!user) {
    window.location.href = `/login.html?next=${encodeURIComponent(location.pathname)}`;
    return;
  }
  document.getElementById("email").value = user.email;
  el.profileForm.elements.name.value = user.name;

  try {
    await Promise.all([loadSubscription(), loadFavorites()]);
  } catch (error) {
    UI.message(el.subscriptionMessage, error.message);
  }
})();