(() => {
  const cfg = window.NEXUS_SUPABASE_CONFIG || {};
  const message = (text, good = false) => {
    const box = document.getElementById("authMessage");
    if (!box) return;
    box.hidden = false;
    box.textContent = text;
    box.classList.toggle("success", good);
  };
  const callbackMessage = document.getElementById("callbackMessage");
  const showCallback = (text) => {
    if (callbackMessage) callbackMessage.textContent = text;
  };

  if (!cfg.url || !cfg.key || !window.supabase?.createClient) {
    message("Login setup is incomplete. Check SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY in Render Environment settings.");
    showCallback("Authentication is not configured yet. Please try again later.");
    return;
  }

  let client;
  try {
    client = window.supabase.createClient(cfg.url.replace(/\/$/, ""), cfg.key);
  } catch (error) {
    message("Could not initialize login. Check the Supabase URL and publishable key.");
    showCallback("Could not initialize authentication. Please try again later.");
    return;
  }

  const redirectTo = new URL("/auth/callback", window.location.origin).toString();
  const login = document.getElementById("loginForm");
  const signup = document.getElementById("signupForm");

  if (login) login.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = login.querySelector('button[type="submit"]');
    button.disabled = true;
    message("Signing in…");
    try {
      const { data, error } = await client.auth.signInWithPassword({
        email: login.querySelector('[name="email"]').value.trim(),
        password: login.querySelector('[name="password"]').value
      });
      if (error) return message(error.message);
      if (data.session) window.location.assign("/");
      else message("Login did not create a session. Please try again.");
    } catch (error) {
      message("Unable to reach Supabase. Check your internet connection and project settings.");
    } finally {
      button.disabled = false;
    }
  });

  if (signup) signup.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = signup.querySelector('button[type="submit"]');
    button.disabled = true;
    message("Creating your account…");
    try {
      const { data, error } = await client.auth.signUp({
        email: signup.querySelector('[name="email"]').value.trim(),
        password: signup.querySelector('[name="password"]').value,
        options: {
          data: { display_name: signup.querySelector('[name="name"]').value.trim() },
          emailRedirectTo: redirectTo
        }
      });
      if (error) return message(error.message);
      if (data.session) window.location.assign("/");
      else message("Account created. Check your email to confirm your address, then log in.", true);
    } catch (error) {
      message("Unable to reach Supabase. Check your internet connection and project settings.");
    } finally {
      button.disabled = false;
    }
  });

  document.querySelectorAll("[data-provider]").forEach(button => button.addEventListener("click", async () => {
    button.disabled = true;
    message("Redirecting to " + button.dataset.provider + "…");
    try {
      const { error } = await client.auth.signInWithOAuth({
        provider: button.dataset.provider,
        options: button.dataset.provider === "google"
          ? { redirectTo, queryParams: { prompt: "select_account" } }
          : { redirectTo }
      });
      if (error) {
        button.disabled = false;
        message(error.message);
      }
    } catch (error) {
      button.disabled = false;
      message("Could not start social login. Check the provider configuration in Supabase.");
    }
  }));

  if (callbackMessage) (async () => {
    const params = new URLSearchParams(window.location.search);
    const authError = params.get("error_description") || params.get("error");
    if (authError) {
      showCallback("Sign-in failed: " + authError.replace(/\+/g, " "));
      return;
    }

    try {
      const code = params.get("code");
      if (code) {
        const { error } = await client.auth.exchangeCodeForSession(code);
        if (error) {
          const { data } = await client.auth.getSession();
          if (!data.session) {
            showCallback("Could not finish sign-in: " + error.message + ". Please return to login and try again.");
            return;
          }
        }
      }

      const { data, error } = await client.auth.getSession();
      if (error || !data.session) {
        showCallback("Could not confirm the sign-in. Check the Supabase redirect settings, then try again.");
        return;
      }

      showCallback("Signed in successfully. Redirecting…");
      window.history.replaceState({}, document.title, window.location.pathname);
      window.location.replace("/");
    } catch (error) {
      showCallback("Could not complete sign-in. Check your connection and Supabase OAuth configuration.");
    }
  })();
})();