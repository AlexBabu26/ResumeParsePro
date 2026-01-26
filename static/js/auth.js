(function () {
  const API_BASE = "/api/v1";
  function $(id) { return document.getElementById(id); }

  function setStorageFromRemember(remember) {
    window.ParsePro?.storage?.setMode(remember ? "local" : "session");
  }

  async function login(username, password, remember) {
    setStorageFromRemember(remember);

    const resp = await fetch(`${API_BASE}/auth/token/`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    if (!resp.ok) throw new Error((await resp.text()) || "Login failed");

    const data = await resp.json();
    if (!data.access || !data.refresh) throw new Error("Invalid token response");

    window.ParsePro.setTokens(data.access, data.refresh);
    window.ParsePro.setUser({ username });
  }

  async function register(payload) {
    const resp = await fetch(`${API_BASE}/auth/register/`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!resp.ok) {
      const d = await resp.json().catch(() => ({}));
      // Try to extract error message from various possible formats
      let msg = null;
      
      // Check non_field_errors first (general validation errors)
      if (d?.non_field_errors) {
        msg = Array.isArray(d.non_field_errors) ? d.non_field_errors.join(". ") : d.non_field_errors;
      }
      // Check field-specific errors (can be string or array)
      else if (d?.password) {
        msg = Array.isArray(d.password) ? d.password.join(". ") : d.password;
      } else if (d?.email) {
        msg = Array.isArray(d.email) ? d.email.join(". ") : d.email;
      } else if (d?.username) {
        msg = Array.isArray(d.username) ? d.username.join(". ") : d.username;
      } else if (d?.password2) {
        msg = Array.isArray(d.password2) ? d.password2.join(". ") : d.password2;
      } else if (d?.detail) {
        msg = d.detail;
      }
      
      // If no specific message found, try to stringify the whole response for debugging
      if (!msg) {
        msg = Object.keys(d).length > 0 ? JSON.stringify(d) : "Registration failed";
      }
      
      throw new Error(msg);
    }
    return resp.json();
  }

  async function forgotPassword(usernameOrEmail) {
    const resp = await fetch(`${API_BASE}/auth/forgot-password/`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      body: JSON.stringify({ username_or_email: usernameOrEmail }),
    });

    if (!resp.ok) {
      const d = await resp.json().catch(() => ({}));
      // Try to extract error message from various possible formats
      let msg = null;
      
      // Check non_field_errors first (general validation errors)
      if (d?.non_field_errors) {
        msg = Array.isArray(d.non_field_errors) ? d.non_field_errors.join(". ") : d.non_field_errors;
      }
      // Check field-specific errors (can be string or array)
      else if (d?.username_or_email) {
        msg = Array.isArray(d.username_or_email) ? d.username_or_email.join(". ") : d.username_or_email;
      } else if (d?.detail) {
        msg = d.detail;
      }
      
      // If no specific message found, try to stringify the whole response for debugging
      if (!msg) {
        msg = Object.keys(d).length > 0 ? JSON.stringify(d) : "Failed to find account";
      }
      
      throw new Error(msg);
    }
    return resp.json();
  }

  async function resetPassword(userId, password, password2) {
    const resp = await fetch(`${API_BASE}/auth/reset-password/`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      body: JSON.stringify({ user_id: userId, password, password2 }),
    });

    if (!resp.ok) {
      const d = await resp.json().catch(() => ({}));
      // Try to extract error message from various possible formats
      let msg = null;
      
      // Check non_field_errors first (general validation errors)
      if (d?.non_field_errors) {
        msg = Array.isArray(d.non_field_errors) ? d.non_field_errors.join(". ") : d.non_field_errors;
      }
      // Check field-specific errors (can be string or array)
      else if (d?.password) {
        msg = Array.isArray(d.password) ? d.password.join(". ") : d.password;
      } else if (d?.password2) {
        msg = Array.isArray(d.password2) ? d.password2.join(". ") : d.password2;
      } else if (d?.user_id) {
        msg = Array.isArray(d.user_id) ? d.user_id.join(". ") : d.user_id;
      } else if (d?.detail) {
        msg = d.detail;
      }
      
      // If no specific message found, try to stringify the whole response for debugging
      if (!msg) {
        msg = Object.keys(d).length > 0 ? JSON.stringify(d) : "Failed to reset password";
      }
      
      throw new Error(msg);
    }
    return resp.json();
  }


  document.addEventListener("DOMContentLoaded", () => {
    const loginForm = $("loginForm");
    if (loginForm) {
      loginForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const alert = $("loginAlert");
        const btn = $("loginBtn");
        btn.disabled = true;
        alert.innerHTML = "";

        const fd = new FormData(loginForm);
        const username = String(fd.get("username") || "").trim();
        const password = String(fd.get("password") || "");
        const remember = $("rememberMe")?.checked ?? true;

        try {
          await login(username, password, remember);
          window.location.href = "/dashboard/";
        } catch (err) {
          window.ParsePro.renderAlert(alert, err.message || "Login failed", "danger");
        } finally {
          btn.disabled = false;
        }
      });
    }

    // Ensure forgot password link works correctly
    const forgotPasswordLink = $("forgotPasswordLink");
    if (forgotPasswordLink) {
      forgotPasswordLink.addEventListener("click", (e) => {
        // Allow normal navigation
        e.stopPropagation();
      });
    }

    const regForm = $("registerForm");
    if (regForm) {
      regForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const alert = $("registerAlert");
        const btn = $("registerBtn");
        btn.disabled = true;
        alert.innerHTML = "";

        const fd = new FormData(regForm);
        const payload = {
          username: String(fd.get("username") || "").trim(),
          email: String(fd.get("email") || "").trim(),
          password: String(fd.get("password") || ""),
          password2: String(fd.get("password2") || ""),
        };

        try {
          await register(payload);
          window.location.href = "/login/";
        } catch (err) {
          window.ParsePro.renderAlert(alert, err.message || "Registration failed", "danger");
        } finally {
          btn.disabled = false;
        }
      });
    }

    const forgotPasswordForm = $("forgotPasswordForm");
    if (forgotPasswordForm) {
      forgotPasswordForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const alert = $("forgotPasswordAlert");
        const btn = $("forgotPasswordBtn");
        btn.disabled = true;
        alert.innerHTML = "";

        const fd = new FormData(forgotPasswordForm);
        const usernameOrEmail = String(fd.get("username_or_email") || "").trim();

        try {
          const data = await forgotPassword(usernameOrEmail);
          // Store user_id in sessionStorage to use in reset password page
          sessionStorage.setItem("reset_user_id", data.user_id);
          window.location.href = "/reset-password/";
        } catch (err) {
          window.ParsePro.renderAlert(alert, err.message || "Failed to find account", "danger");
        } finally {
          btn.disabled = false;
        }
      });
    }

    const resetPasswordForm = $("resetPasswordForm");
    if (resetPasswordForm) {
      // Get user_id from sessionStorage
      const userId = sessionStorage.getItem("reset_user_id");
      const userIdField = $("userId");
      if (userId && userIdField) {
        userIdField.value = userId;
      } else if (!userId) {
        // Redirect to forgot password if no user_id found
        window.location.href = "/forgot-password/";
      } else {
        // If userId exists but field doesn't, create it
        const hiddenInput = document.createElement("input");
        hiddenInput.type = "hidden";
        hiddenInput.id = "userId";
        hiddenInput.name = "user_id";
        hiddenInput.value = userId;
        resetPasswordForm.appendChild(hiddenInput);
      }

      resetPasswordForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const alert = $("resetPasswordAlert");
        const btn = $("resetPasswordBtn");
        btn.disabled = true;
        alert.innerHTML = "";

        const fd = new FormData(resetPasswordForm);
        const userId = parseInt(fd.get("user_id") || "0");
        const password = String(fd.get("password") || "");
        const password2 = String(fd.get("password2") || "");

        if (!userId || isNaN(userId)) {
          window.ParsePro.renderAlert(alert, "Invalid session. Please start over.", "danger");
          btn.disabled = false;
          return;
        }

        if (!password || password.length < 8) {
          window.ParsePro.renderAlert(alert, "Password must be at least 8 characters long.", "danger");
          btn.disabled = false;
          return;
        }

        if (password !== password2) {
          window.ParsePro.renderAlert(alert, "Passwords do not match.", "danger");
          btn.disabled = false;
          return;
        }

        try {
          await resetPassword(userId, password, password2);
          sessionStorage.removeItem("reset_user_id");
          window.ParsePro.renderAlert(alert, "Password reset successfully! Redirecting to login...", "success");
          setTimeout(() => {
            window.location.href = "/login/";
          }, 2000);
        } catch (err) {
          window.ParsePro.renderAlert(alert, err.message || "Failed to reset password", "danger");
        } finally {
          btn.disabled = false;
        }
      });
    }
  });
})();

