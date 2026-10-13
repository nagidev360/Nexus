(() => {
  const cfg = window.NEXUS_SUPABASE_CONFIG || {};
  const message = (text, good = false) => {
    const box = document.getElementById("authMessage");
    if (!box) return;
    box.hidden = false; box.textContent = text;
    box.classList.toggle("success", good);
  };
  if (!cfg.url || !cfg.key || !window.supabase?.createClient) {
    message("Login setup is incomplete. Add SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY in Render Environment settings.");
    const cb = document.getElementById("callbackMessage");
    if (cb) cb.textContent = "Authentication is not configured yet. Please try again later.";
    return;
  }
  const client = window.supabase.createClient(cfg.url, cfg.key);
  const redirectTo = new URL("/auth/callback", window.location.origin).toString();
  const login = document.getElementById("loginForm");
  const signup = document.getElementById("signupForm");
  if (login) login.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = login.querySelector('button[type="submit"]'); button.disabled = true; message("Signing in…");
    const { data, error } = await client.auth.signInWithPassword({
      email: login.email.value.trim(), password: login.password.value
    });
    button.disabled = false;
    if (error) return message(error.message);
    if (data.session) window.location.assign("/");
  });
  if (signup) signup.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = signup.querySelector('button[type="submit"]'); button.disabled = true; message("Creating your account…");
    const { data, error } = await client.auth.signUp({
      email: signup.email.value.trim(), password: signup.password.value,
      options: { data: { display_name: signup.name.value.trim() }, emailRedirectTo: redirectTo }
    });
    button.disabled = false;
    if (error) return message(error.message);
    if (data.session) window.location.assign("/");
    else message("Account created. Check your email to confirm your address, then log in.", true);
  });
  document.querySelectorAll("[data-provider]").forEach(button => button.addEventListener("click", async () => {
    button.disabled = true; message("Redirecting to " + button.dataset.provider + "…");
    const { error } = await client.auth.signInWithOAuth({
      provider: button.dataset.provider, options: { redirectTo }
    });
    if (error) { button.disabled = false; message(error.message); }
  }));
  const cb = document.getElementById("callbackMessage");
  if (cb) (async () => {
    const { error } = await client.auth.exchangeCodeForSession(window.location.href);
    if (error) {
      // The client may already have consumed the PKCE code during initialization.
      const { data } = await client.auth.getSession();
      if (!data.session) { cb.textContent = error.message; return; }
    }
    cb.textContent = "Signed in successfully. Redirecting…";
    window.location.replace("/");
  })();
})();