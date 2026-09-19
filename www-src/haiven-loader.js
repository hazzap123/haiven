/* =========================================================================
 * Haiven Native — loader
 * =========================================================================
 *
 * This file is registered ONCE, in configuration.yaml under
 * frontend.extra_module_url, and then never changes again. It exists to kill
 * the manual step in the deploy loop.
 *
 * Home Assistant serves /local with Cache-Control: max-age=2678400, so a
 * Lovelace resource pinned at /local/haiven-cards.js?v=1 keeps serving the
 * same bytes for 31 days. The only way to ship a change was to hand-edit the
 * resource's ?v= in Settings > Dashboards > Resources, which lives in
 * .storage and cannot be committed. Forgetting it ships nothing, and the
 * deploy still looks clean.
 *
 * So: ask the server what the file's ETag is right now, and import a URL
 * carrying that ETag. Unchanged file, same URL, served from cache. Changed
 * file, new ETag, new URL, fresh module. Deploying is a copy and nothing
 * else: no restart, no UI, no version to remember.
 *
 * The probe URL carries a throwaway query string, and that is the whole
 * trick. Home Assistant registers a service worker (sw-modern.js) which
 * caches /local/ stale-while-revalidate, so a plain fetch — even with
 * cache:"no-cache", which only instructs the HTTP cache and not the worker —
 * is answered from the worker's copy while it revalidates in the background.
 * The first page load after a deploy therefore read the PREVIOUS ETag and
 * imported the previous module, and only the second load picked up the
 * change. A URL the worker has never seen misses its cache and reaches the
 * network, so the ETag is always the live one.
 * ====================================================================== */

(async () => {
  const SRC = "/local/haiven-cards.js";
  try {
    const r = await fetch(`${SRC}?probe=${Date.now()}`, { cache: "no-store" });
    const tag = (r.headers.get("etag") || r.headers.get("last-modified") || String(Date.now()))
      .replace(/[^A-Za-z0-9]/g, "");
    await import(`${SRC}?e=${tag}`);
  } catch (e) {
    // Never leave the dashboard with no cards because one probe failed.
    console.error("HAIVEN loader: falling back to an unversioned import", e);
    await import(SRC);
  }
})();
