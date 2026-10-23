# Divergence from upstream

Every intentional difference between StarFling and its base,
[L-K-M/FunKey-OS-Starling](https://github.com/L-K-M/FunKey-OS-Starling)
(Starling 3.1.3), is listed here, so the delta stays readable. One row per
change; link the PR.

| Area | Change | Why | PR |
|---|---|---|---|
| Branding | Name, version scheme (`StarFling-X.Y.Z`, restarting at 0.1.0), repo URLs. The `FunKey-` artifact prefix is kept | New fork identity; the prefix is globbed by installed firmware (D7) | Phase 0 |
| CI | Z.ai/GLM review workflow removed (archived in `docs/archive/starling/`) | Not used by StarFling | Phase 0 |
| Boot time | RetroFE patch `0021-lazy-quick-menu.patch`: the quick menu (13 fonts incl. the CJK fallback, images, zones) is set up on first MENU press, not at startup or on each return from a game | ~0.2 s on the menu boot path (Phase 1.2 baseline) | Phase 1.4 |
