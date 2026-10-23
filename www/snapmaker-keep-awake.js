/*
 * Snapmaker U1 dashboard - keep the screen awake while the dashboard is showing.
 *
 * Uses the browser's Screen Wake Lock API: while a Home Assistant tab whose address contains
 * one of the words in PATH_MATCH is visible, the computer is asked not to dim or sleep the display.
 * When you switch tab or dashboard, or minimize the window, the request is released again.
 *
 * Requirements: Chrome/Edge/Safari/Firefox recent enough to support Wake Lock, and Home Assistant
 * opened over HTTPS (Nabu Casa, a reverse proxy) or at localhost. Plain http://<ip>:8123 is not
 * allowed by browsers. The tab must be the visible one.
 *
 * Install: INSTALL.md, "Keep the screen awake (optional)".
 */
(() => {
  // Edit: the screen stays awake only when the dashboard address contains one of these words.
  // For example, if your dashboard is at /dashboard-printer/overview, "printer" matches.
  const PATH_MATCH = ["printer"];

  if (!("wakeLock" in navigator)) {
    console.info("[snapmaker-keep-awake] Screen Wake Lock is not available here (needs HTTPS or localhost).");
    return;
  }

  let lock = null;
  const wanted = () =>
    document.visibilityState === "visible" &&
    PATH_MATCH.some((word) => location.pathname.toLowerCase().includes(word.toLowerCase()));

  async function sync() {
    try {
      if (wanted() && !lock) {
        lock = await navigator.wakeLock.request("screen");
        lock.addEventListener("release", () => { lock = null; });
      } else if (!wanted() && lock) {
        await lock.release();
        lock = null;
      }
    } catch (err) {
      lock = null; // refused (battery saver, no permission, hidden tab): try again on the next check
    }
  }

  document.addEventListener("visibilitychange", sync);
  window.addEventListener("location-changed", sync); // fired by Home Assistant when you change page
  window.addEventListener("popstate", sync);
  setInterval(sync, 30000);                           // also re-acquires after the browser drops the lock
  sync();
})();
