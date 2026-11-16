// Log-in and sign-up pages share this script; the mode comes from the form.

const form = document.getElementById("auth-form");
const feedback = document.getElementById("form-message");
const mode = form.dataset.mode; // "login" or "register"

/** Go back to the page the user came from, but only within this site. */
function redirectAfterAuth() {
  const next = UI.param("next");
  const isInternal = next && next.startsWith("/") && !next.startsWith("//");
  window.location.href = isInternal ? next : "/";
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(form));
  const submit = form.querySelector('button[type="submit"]');
  submit.disabled = true;
  feedback.innerHTML = "";

  try {
    if (mode === "register") {
      if (data.password !== data.password_confirm) {
        throw new Error("Passwords do not match");
      }
      await Api.post("/api/auth/register", {
        name: data.name,
        email: data.email,
        password: data.password,
      });
    }
    // After sign-up the user is logged in straight away
    const { access_token } = await Api.post("/api/auth/login", {
      email: data.email,
      password: data.password,
    });
    Api.setToken(access_token);
    redirectAfterAuth();
  } catch (error) {
    UI.message(feedback, error.message);
    submit.disabled = false;
  }
});

(async function init() {
  const user = await renderHeader();
  if (user) redirectAfterAuth(); // already logged in
})();