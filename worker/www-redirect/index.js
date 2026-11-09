/**
 * Cloudflare Worker: permanent redirect www -> non-www.
 *
 * `www.flowmatrix.dev/*` is routed to this Worker. It answers with an HTTP 301
 * to the canonical `https://flowmatrix.dev` host and preserves the path and
 * query string. This removes the duplicate-host signal for search engines.
 */
export default {
  fetch(request) {
    const url = new URL(request.url);
    const target = `https://flowmatrix.dev${url.pathname}${url.search}`;
    return Response.redirect(target, 301);
  },
};
