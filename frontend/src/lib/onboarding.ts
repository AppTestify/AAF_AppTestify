const ONBOARDING_COMPLETE_KEY = "aaf_onboarding_complete";

export function isOnboardingComplete(): boolean {
  try {
    return localStorage.getItem(ONBOARDING_COMPLETE_KEY) === "1";
  } catch {
    return false;
  }
}

export function markOnboardingComplete(): void {
  try {
    localStorage.setItem(ONBOARDING_COMPLETE_KEY, "1");
  } catch {
    /* ignore storage errors */
  }
}
