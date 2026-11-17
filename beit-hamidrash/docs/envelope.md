# Content envelope — protocol v2

## Why
In v1 (`ledger.make_event`) the author signs the whole body, and the event id is the hash of that payload. A body can therefore never be removed: deleting it breaks `id` and `sig`, and every event that references it. If illegal or harmful content (defamation, privacy, copyright takedown, abuse) is ever published, a node must either keep distributing it or break its ledger. `hide` only removes display; the bytes remain.

v2 separates the *claim* (signed) from the *content* (erasable).

## Format
```
{ v: 2, author, kind, ref, target, body_hash, ts, id, sig }      # the envelope (signed)
body_hash = sha256_hex(canonical(body))                          # canonical = sorted keys, no spaces, UTF-8
id        = sha256_hex(canonical({v, author, kind, ref, target, body_hash, ts}))
sig       = Ed25519(author, canonical(same payload))
```
The body travels beside the envelope (key `body`, unsigned) or is fetched by hash. Storage: `envelope_blobs(hash PK, body, purged, purged_at, reason)`.

`verify_v2(event, blob)`:
- `blob=None` (purged or not fetched): valid if the envelope signature and id are valid.
- blob given: additionally `sha256(canonical(blob)) == body_hash`; a forged body is rejected.

`purge(hash)`: sets `body=NULL, purged=1` and keeps the hash row as a tombstone; a later `put` of the same body does not resurrect it. Works even if the blob was never stored locally (pre-emptive block). The event, its id and signature stay valid, so replies, endorsements and `target` references remain intact.

`v:2` is inside the signed payload, so a v2 id can never equal a v1 id, and the v1 `check_event` rejects v2 events rather than misreading them.

Caveat: a low-entropy body can be guessed from its hash. For sensitive kinds add a random `nonce` field to the body.

## Migration plan
1. Library only (this module; not wired). Nodes ignore it.
2. Ledger: add nullable `body_hash` and `v` columns to `events`, make `body` nullable; `check_event` dispatches on `v` (absent = 1). Inserting a v2 event writes its blob into `envelope_blobs`.
3. Bundle: manifest gains `blobs` (optional per-hash files) and `purged` (list of hashes). A receiving node honors `purged` only from a trusted-authority-signed list. Bundles may omit blobs; events still verify.
4. After a flag day, clients default to v2 for new events; v1 events stay valid forever.
5. Moderation: an authority-signed purge order referencing a hash drives `BlobStore.purge` on every node; `hide` remains for non-illegal moderation.

## v1 to v2 conversion
`convert_v1_to_v2` does not and cannot re-sign: only the author's key signs v2. It returns the untouched v1 event, `body_hash` and the blob. The v1 event still embeds its body, so true erasure of old content needs the author to publish a v2 re-issue (referencing the old id); the old v1 event is then hidden and, where legally required, dropped locally (accepting that its signature is lost on that node).

## Compatibility
- v1 nodes receiving v2: reject (unknown shape), hence the flag-day gate in step 4.
- v2 nodes receiving v1: accept unchanged.
- Dependent events reference `id`, which is stable across purges.
- AI-generated or halachic-content labels live inside the body; purge removes them with it.
