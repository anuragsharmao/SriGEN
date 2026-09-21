import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import "./LoginPage.css";

const STEPS = [
  { title: "UNDERSTAND", body: "Extract facts, entities and relationships." },
  { title: "CONTROL", body: "Classify sensitivity and protect what matters." },
  { title: "GENERATE", body: "Create audience-aware deliverables." },
  { title: "VERIFY", body: "Check grounding, consistency and policy." },
  { title: "REVIEW", body: "Inspect evidence and approve the result." },
  { title: "PROVE", body: "Record provenance only after approval." },
];

function BrandMark() {
  return (
    <svg viewBox="0 0 48 58" aria-hidden="true">
      <path
        d="M24 2 44 9v18c0 13.2-8.4 23.3-20 28C12.4 50.3 4 40.2 4 27V9L24 2Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.5"
      />
      <path
        d="M24 11v27M15 19h18M17 31h14"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
      />
    </svg>
  );
}

function PersonIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="8" r="4"></circle>
      <path d="M4.5 20c.8-3.5 3.3-5.5 7.5-5.5s6.7 2 7.5 5.5"></path>
    </svg>
  );
}

function MailIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <rect x="3.5" y="5.5" width="17" height="13" rx="2"></rect>
      <path d="M4.5 7 12 12.5 19.5 7"></path>
    </svg>
  );
}

function LockIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <rect x="5" y="10" width="14" height="11" rx="2"></rect>
      <path d="M8 10V7a4 4 0 0 1 8 0v3"></path>
    </svg>
  );
}

function EyeIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z"></path>
      <circle cx="12" cy="12" r="2.5"></circle>
    </svg>
  );
}

const initialSignIn = { workId: "", password: "" };
const initialSignUp = {
  fullName: "",
  email: "",
  workId: "",
  password: "",
  confirmPassword: "",
};

export default function LoginPage({ onSignIn, onSignUp }) {
  const navigate = useNavigate();
  const [mode, setMode] = useState("signin"); // "signin" | "signup"
  const [signIn, setSignIn] = useState(initialSignIn);
  const [signUp, setSignUp] = useState(initialSignUp);
  const [errors, setErrors] = useState({});
  const [remember, setRemember] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [activeStep, setActiveStep] = useState(0);
  const [toast, setToast] = useState({ text: "", show: false });
  const toastTimer = useRef(null);

  useEffect(() => {
    const id = setInterval(() => {
      setActiveStep((prev) => (prev + 1) % STEPS.length);
    }, 2600);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    return () => clearTimeout(toastTimer.current);
  }, []);

  function showToast(text) {
    setToast({ text, show: true });
    clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => {
      setToast((t) => ({ ...t, show: false }));
    }, 2800);
  }

  function switchMode(nextMode) {
    setMode(nextMode);
    setErrors({});
    setStatusMessage("");
  }

  function validateSignIn() {
    const next = {};
    if (!signIn.workId.trim()) {
      next.workId = "Please enter your Work ID / Username.";
    }
    if (!signIn.password) {
      next.password = "Please enter your password.";
    } else if (signIn.password.length < 6) {
      next.password = "Password must contain at least 6 characters.";
    }
    return next;
  }

  function validateSignUp() {
    const next = {};
    if (!signUp.fullName.trim()) {
      next.fullName = "Please enter your full name.";
    }
    if (!signUp.email.trim()) {
      next.email = "Please enter your work email.";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(signUp.email.trim())) {
      next.email = "Please enter a valid email address.";
    }
    if (!signUp.workId.trim()) {
      next.workId = "Please choose a Work ID / Username.";
    }
    if (!signUp.password) {
      next.password = "Please enter a password.";
    } else if (signUp.password.length < 6) {
      next.password = "Password must contain at least 6 characters.";
    }
    if (!signUp.confirmPassword) {
      next.confirmPassword = "Please confirm your password.";
    } else if (signUp.confirmPassword !== signUp.password) {
      next.confirmPassword = "Passwords do not match.";
    }
    return next;
  }

  function handleSignInSubmit(event) {
    event.preventDefault();
    const nextErrors = validateSignIn();
    setErrors(nextErrors);
    setStatusMessage("");

    if (Object.keys(nextErrors).length > 0) {
      showToast("Please check the highlighted fields.");
      return;
    }

    setSubmitting(true);
    setStatusMessage("Authenticating securely…");

    // Demo behavior — replace this block with your backend/API call.
    setTimeout(() => {
      setSubmitting(false);
      setStatusMessage("Demo login successful. Connect your backend here.");
      showToast("Welcome to SriGEN.");
      onSignIn?.({ ...signIn, remember });
      navigate("/dashboard");
    }, 1000);
  }

  function handleSignUpSubmit(event) {
    event.preventDefault();
    const nextErrors = validateSignUp();
    setErrors(nextErrors);
    setStatusMessage("");

    if (Object.keys(nextErrors).length > 0) {
      showToast("Please check the highlighted fields.");
      return;
    }

    setSubmitting(true);
    setStatusMessage("Creating your account…");

    // Demo behavior — replace this block with your backend/API call.
    setTimeout(() => {
      setSubmitting(false);
      setStatusMessage("Account created. You can now sign in.");
      showToast("SriGEN account created.");
      onSignUp?.(signUp);
      switchMode("signin");
      setSignIn({ workId: signUp.workId, password: "" });
      setSignUp(initialSignUp);
    }, 1000);
  }

  function handleForgotPassword(event) {
    event.preventDefault();
    showToast("Password recovery is handled by your organization.");
  }

  function handleSSO() {
    showToast("Opening Government SSO…");
    setStatusMessage("Connecting to the secure SSO gateway…");
    setTimeout(() => {
      setStatusMessage("SSO demo mode: connection ready.");
    }, 1100);
  }

  const isSignIn = mode === "signin";

  return (
    <main className="login-shell">
      {/* LEFT: SriGEN visual / process panel */}
      <section className="visual-panel">
        <div className="visual-overlay"></div>

        <div className="brand brand-light">
          <div className="brand-mark">
            <BrandMark />
          </div>
          <span>SriGEN</span>
        </div>

        <div className="visual-content">
          <p className="eyebrow">SECURE INTELLIGENCE PLATFORM</p>
          <h1>
            Secure intelligence
            <br />
            transformation.
          </h1>

          <div className="steps">
            {STEPS.map((step, index) => (
              <article
                key={step.title}
                className={`step${index === activeStep ? " active" : ""}`}
              >
                <div className="step-number">
                  {String(index + 1).padStart(2, "0")}
                </div>
                <div>
                  <h3>{step.title}</h3>
                  <p>{step.body}</p>
                </div>
              </article>
            ))}
          </div>
        </div>

        <div className="visual-footer">
          <span>CONTROLLED INTELLIGENCE</span>
          <span>v1.0.0</span>
        </div>
      </section>

      {/* RIGHT: auth form */}
      <section className="form-panel">
        <div className="form-inner">
          <div className="brand brand-dark">
            <div className="brand-mark">
              <BrandMark />
            </div>
            <span>SriGEN</span>
          </div>

          <div className="welcome">
            <h2>{isSignIn ? "Welcome to SriGEN" : "Create your account"}</h2>
            <p>
              {isSignIn
                ? "Secure access to controlled intelligence transformation."
                : "Register for controlled access to the platform."}
            </p>
          </div>

          <div className="mode-toggle" role="tablist" aria-label="Sign in or sign up">
            <button
              type="button"
              role="tab"
              aria-selected={isSignIn}
              className={`mode-tab${isSignIn ? " mode-tab-active" : ""}`}
              onClick={() => switchMode("signin")}
            >
              Sign In
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={!isSignIn}
              className={`mode-tab${!isSignIn ? " mode-tab-active" : ""}`}
              onClick={() => switchMode("signup")}
            >
              Sign Up
            </button>
          </div>

          {isSignIn ? (
            <form id="loginForm" noValidate onSubmit={handleSignInSubmit}>
              <div className={`field${errors.workId ? " has-error" : ""}`}>
                <label htmlFor="workId">Work ID / Username</label>
                <div className="input-wrap">
                  <span className="field-icon">
                    <PersonIcon />
                  </span>
                  <input
                    id="workId"
                    name="workId"
                    type="text"
                    placeholder="Enter your work ID"
                    autoComplete="username"
                    value={signIn.workId}
                    onChange={(e) =>
                      setSignIn((s) => ({ ...s, workId: e.target.value }))
                    }
                  />
                </div>
                <small className="error-message">{errors.workId}</small>
              </div>

              <div className={`field${errors.password ? " has-error" : ""}`}>
                <label htmlFor="password">Password</label>
                <div className="input-wrap">
                  <span className="field-icon">
                    <LockIcon />
                  </span>
                  <input
                    id="password"
                    name="password"
                    type={showPassword ? "text" : "password"}
                    placeholder="Enter your password"
                    autoComplete="current-password"
                    value={signIn.password}
                    onChange={(e) =>
                      setSignIn((s) => ({ ...s, password: e.target.value }))
                    }
                  />
                  <button
                    className="icon-button"
                    type="button"
                    aria-label={showPassword ? "Hide password" : "Show password"}
                    onClick={() => setShowPassword((v) => !v)}
                  >
                    <EyeIcon />
                  </button>
                </div>
                <small className="error-message">{errors.password}</small>
              </div>

              <div className="form-options">
                <label className="remember">
                  <input
                    type="checkbox"
                    checked={remember}
                    onChange={(e) => setRemember(e.target.checked)}
                  />
                  <span className="custom-check"></span>
                  <span>Remember this device</span>
                </label>
                <a href="#" id="forgotPassword" className="forgot-link" onClick={handleForgotPassword}>
                  Forgot password?
                </a>
              </div>

              <button className="primary-btn" type="submit" disabled={submitting}>
                <span>{submitting ? "Signing In…" : "Sign In"}</span>
                <span className="arrow">→</span>
              </button>

              <div className="divider">
                <span>OR</span>
              </div>

              <button className="sso-btn" type="button" onClick={handleSSO}>
                Use SSO (Government)
              </button>

              <p className="status-message">{statusMessage}</p>

              <p className="switch-line">
                New to SriGEN?{" "}
                <button
                  type="button"
                  className="switch-link"
                  onClick={() => switchMode("signup")}
                >
                  Create an account
                </button>
              </p>
            </form>
          ) : (
            <form id="signupForm" noValidate onSubmit={handleSignUpSubmit}>
              <div className={`field${errors.fullName ? " has-error" : ""}`}>
                <label htmlFor="fullName">Full Name</label>
                <div className="input-wrap">
                  <span className="field-icon">
                    <PersonIcon />
                  </span>
                  <input
                    id="fullName"
                    name="fullName"
                    type="text"
                    placeholder="Enter your full name"
                    autoComplete="name"
                    value={signUp.fullName}
                    onChange={(e) =>
                      setSignUp((s) => ({ ...s, fullName: e.target.value }))
                    }
                  />
                </div>
                <small className="error-message">{errors.fullName}</small>
              </div>

              <div className={`field${errors.email ? " has-error" : ""}`}>
                <label htmlFor="email">Work Email</label>
                <div className="input-wrap">
                  <span className="field-icon">
                    <MailIcon />
                  </span>
                  <input
                    id="email"
                    name="email"
                    type="email"
                    placeholder="Enter your work email"
                    autoComplete="email"
                    value={signUp.email}
                    onChange={(e) =>
                      setSignUp((s) => ({ ...s, email: e.target.value }))
                    }
                  />
                </div>
                <small className="error-message">{errors.email}</small>
              </div>

              <div className={`field${errors.workId ? " has-error" : ""}`}>
                <label htmlFor="signupWorkId">Work ID / Username</label>
                <div className="input-wrap">
                  <span className="field-icon">
                    <PersonIcon />
                  </span>
                  <input
                    id="signupWorkId"
                    name="signupWorkId"
                    type="text"
                    placeholder="Choose a work ID"
                    autoComplete="username"
                    value={signUp.workId}
                    onChange={(e) =>
                      setSignUp((s) => ({ ...s, workId: e.target.value }))
                    }
                  />
                </div>
                <small className="error-message">{errors.workId}</small>
              </div>

              <div className={`field${errors.password ? " has-error" : ""}`}>
                <label htmlFor="signupPassword">Password</label>
                <div className="input-wrap">
                  <span className="field-icon">
                    <LockIcon />
                  </span>
                  <input
                    id="signupPassword"
                    name="signupPassword"
                    type={showPassword ? "text" : "password"}
                    placeholder="Create a password"
                    autoComplete="new-password"
                    value={signUp.password}
                    onChange={(e) =>
                      setSignUp((s) => ({ ...s, password: e.target.value }))
                    }
                  />
                  <button
                    className="icon-button"
                    type="button"
                    aria-label={showPassword ? "Hide password" : "Show password"}
                    onClick={() => setShowPassword((v) => !v)}
                  >
                    <EyeIcon />
                  </button>
                </div>
                <small className="error-message">{errors.password}</small>
              </div>

              <div className={`field${errors.confirmPassword ? " has-error" : ""}`}>
                <label htmlFor="confirmPassword">Confirm Password</label>
                <div className="input-wrap">
                  <span className="field-icon">
                    <LockIcon />
                  </span>
                  <input
                    id="confirmPassword"
                    name="confirmPassword"
                    type={showConfirm ? "text" : "password"}
                    placeholder="Re-enter your password"
                    autoComplete="new-password"
                    value={signUp.confirmPassword}
                    onChange={(e) =>
                      setSignUp((s) => ({
                        ...s,
                        confirmPassword: e.target.value,
                      }))
                    }
                  />
                  <button
                    className="icon-button"
                    type="button"
                    aria-label={showConfirm ? "Hide password" : "Show password"}
                    onClick={() => setShowConfirm((v) => !v)}
                  >
                    <EyeIcon />
                  </button>
                </div>
                <small className="error-message">{errors.confirmPassword}</small>
              </div>

              <button className="primary-btn" type="submit" disabled={submitting}>
                <span>{submitting ? "Creating Account…" : "Create Account"}</span>
                <span className="arrow">→</span>
              </button>

              <p className="status-message">{statusMessage}</p>

              <p className="switch-line">
                Already have an account?{" "}
                <button
                  type="button"
                  className="switch-link"
                  onClick={() => switchMode("signin")}
                >
                  Sign in
                </button>
              </p>
            </form>
          )}

          <footer className="form-footer">
            <span>SriGEN&nbsp; / &nbsp;SECURE INTELLIGENCE PLATFORM</span>
            <span>v1.0.0</span>
          </footer>
        </div>
      </section>

      <div className={`toast${toast.show ? " show" : ""}`} role="status">
        {toast.text}
      </div>
    </main>
  );
}
