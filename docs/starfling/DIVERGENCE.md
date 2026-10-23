# Divergence from upstream

Every intentional difference between StarFling and its base,
[L-K-M/FunKey-OS-Starling](https://github.com/L-K-M/FunKey-OS-Starling)
(Starling 3.1.3), is listed here, so the delta stays readable. One row per
change; link the PR.

| Area | Change | Why | PR |
|---|---|---|---|
| Branding | Name, version scheme (`StarFling-X.Y.Z`, restarting at 0.1.0), repo URLs. The `FunKey-` artifact prefix is kept | New fork identity; the prefix is globbed by installed firmware (D7) | Phase 0 |
| CI | Z.ai/GLM review workflow removed (archived in `docs/archive/starling/`) | Not used by StarFling | Phase 0 |
| Boot time | RetroFE patch `0022-no-first-menu-animation.patch`: the first menu after boot appears in its final state, without the theme's enter animations | Input was blocked ~0.28 s while they played (K's decision, 2026-10-23) | Phase 1.4 |
