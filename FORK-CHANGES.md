# PostersPlus test build (AER): what it is and how to update it

How the test copy of PostersPlus is set up, and how to bring it up to date
when PostersPlus releases new changes. Written 2026-10-03.

- **Fork:** `github.com/aRamadi/PostersPlus` (upstream: `UmbraProjects/PostersPlus`,
  branch `dev`).
- **Code on this server:** `~/postersplus-fork` (checked out on `aer`), plus a second
  worktree at `~/postersplus-miniseries` (on `tmdb-miniseries`).
- **Test instance:** `~/postersplus-test` (this folder). Container `postersplus-test`,
  port `127.0.0.1:8002`, on `media-net`, served at **posters-test.<your domain>**.
- **Live PostersPlus is separate:** `~/postersplus`, the official `:dev` image,
  updated through Dockhand, at posters.<your domain>. Nothing here touches it.

## 1. The branches

| Branch | What it holds | Purpose |
|--------|---------------|---------|
| `arabic-labels` | One commit on upstream `dev`: Arabic labels (ar.json, letter joining, Almarai/Tajawal, Arabic digits for rank/dates/year, centring) and the `original_labels` "Title's Own Language" option | Pull request #1 (linked in the GitHub issue) |
| `tmdb-miniseries` | One commit on upstream `dev`: Mini Series also counts TMDB's own "Miniseries" type | Possible pull request #2 |
| `aer` | `arabic-labels` + the extras below + `tmdb-miniseries` | What posters-test runs. **Never open a PR from it.** |

Extras that exist only on `aer`, oldest first:
1. `Version 1.2.0-AER`: `APP_VERSION` in `config.py` and the configurator header button.
2. Liquid Glass badge style (`sash_badge_style` / `landscape_badge_style` = `liquid`).
3. Liquid Glass, Colour (`liquid_tint`).
4. The glass look reworked to read as glass rather than a glossy button.
5. More colour.
6. Glass Colour slider (`liquid_colour`, 0-1, default 0.32).
7. Mini Series fix, cherry-picked from `tmdb-miniseries`.

`arabic-labels-history` (local only) keeps the original step-by-step commits
from before `arabic-labels` was squashed. Nothing uses it.

## 2. Updating to new PostersPlus changes

All commands run in `~/postersplus-fork` unless noted. `git rerere` is on in
this clone, so a conflict fixed while rebasing `arabic-labels` is fixed
automatically when the same commit is replayed onto `aer`.

```bash
cd ~/postersplus-fork
git fetch origin
git log --oneline arabic-labels..origin/dev     # what's new upstream

# Remember where the PR branch was, to move aer's extras across later
OLD=$(git rev-parse arabic-labels)

# 1. PR branch: rebase onto the new dev
git checkout arabic-labels
git rebase origin/dev            # fix conflicts (see below), git add, git rebase --continue

# 2. Mini Series branch (its own worktree)
git -C ~/postersplus-miniseries rebase origin/dev

# 3. aer: replay its extras on top of the new arabic-labels
git checkout aer
git rebase --onto arabic-labels "$OLD" aer
```

**Where conflicts happen:**
- **`CHANGELOG.md`:** both sides add a section under "Unreleased". Keep both.
- **`main.py` `_RENDER_REVISIONS`:** upstream may take the same revision number
  as ours (that's how 19 became 20). Keep upstream's entry, give the Arabic
  one the next free number, and change `tests/test_arabic_labels.py`
  (`r.rev == 20`) to match. The commit message says "Render revision NN" too.
  Fix it with `git commit --amend` once the rebase is done.
- **`config.py` `APP_VERSION` / configurator header (`aer` only):** if upstream
  bumps its version (say to 1.3.0), set ours to `1.3.0-AER` in both places.

**Test before deploying** (about 30 s once built):
```bash
docker build -q -t pp-check .
docker run --rm --entrypoint sh pp-check -c \
  "pip install -q pytest >/dev/null 2>&1; cd /app && python3 -m pytest tests/ -q -p no:cacheprovider | tail -3"
docker rmi pp-check
```
Do this on `aer`. For the PR branch, check it out and run the same commands.

**Deploy to posters-test:** the compose file builds from the `~/postersplus-fork`
working tree, so `aer` must be checked out.
```bash
cd ~/postersplus-test
docker compose up -d --build
# Code changes don't change poster cache keys: clear rendered posters
docker compose stop
sudo rm -f cache/cache.db cache/cache.db-shm cache/cache.db-wal
docker compose start
```
Then press Ctrl+Shift+R on posters-test.<your domain>. The version tile and
configurator header should say `vX.Y.Z-AER`.

**Push:**
```bash
git push --force-with-lease fork arabic-labels
git -C ~/postersplus-miniseries push --force-with-lease fork tmdb-miniseries
git push --force-with-lease fork aer
```
Pushes go through the `github-postersplus` SSH host (`~/.ssh/github_postersplus`,
a deploy key with write access on the fork only). If the fork's `dev` lags
behind (it doesn't need updating), GitHub's "Sync fork" button fixes it.

## 3. Checks after an update

1. **Arabic:** Divorce Me (TMDB movie 1507560) with `original_labels=ar` shows
   **عربي**, **كوميديا • ٢٠٢٥**, and an Arabic title or logo. When Native
   Language = Arabic ★, every poster's labels are Arabic.
2. **English unchanged:** Inception (movie 27205) looks the same with and without
   `original_labels=ar`.
3. **Trending rank:** an Arabic poster shows `#٨ اليوم`, not `#8 اليوم`.
4. **Mini Series:** ولد وبنت وشايب (tv 296043) qualifies. It shows **مسلسل قصير**
   only if Mini Series ranks above Foreign in the sash order.
5. **Liquid Glass:** Sash → Style → Liquid Glass / Liquid Glass, Colour, with the
   Glass Colour slider for the second.
6. **AIOMetadata reaches it:**
   `docker logs --since 5m postersplus-test | grep "GET /poster"` shows requests
   from AIOMetadata's IP (`docker inspect aiometadata` → media-net address).

## 4. How it's wired in

- **Caddy** (`/etc/caddy/Caddyfile`): `posters-test.<your domain> { reverse_proxy localhost:8002 }`.
  Backup from before it was added: `/etc/caddy/Caddyfile.bak-2026-10-02`.
- **DNS:** an A record `posters-test` → `<server IP>` at Cloudflare.
- **Keys:** same `TMDB_API_KEY`, `MDBLIST_API_KEY`, `ACCESS_KEY`, `ADMIN_KEY` and
  AIOStreams settings as the live one (copied into `compose.yaml`, mode 600).
  The admin key is in `~/postersplus/admin-key.txt`.
- **Cache folder** (`./cache`): started from copies of the live instance's IMDb
  ratings, anime ids, commons/company logos and preset art. `settings.json` is
  the live one minus the daily warm-up and trending schedule, with
  `PUBLIC_URL=https://posters-test.<your domain>`.
- **AIOMetadata:** both PostersPlus links in its config (db.sqlite) point at
  `http://postersplus-test:8000/poster?...`. Its `.env` must list the host, or
  the poster proxy refuses it (it only fetches private hosts it's told about):
  ```
  POSTER_CACHE_ALLOWED_HOSTS=postersplus,postersplus-test
  POSTER_CACHE_PROVIDER_POLICIES=[{"domain":"postersplus",...,"ttl":"12h"},{"domain":"postersplus-test",...,"ttl":"12h"}]
  ```
  Backup from before: `~/aiometadata/.env.bak-before-postersplus-test`.

## 5. Going back to the official PostersPlus

1. In AIOMetadata's configurator, change both PostersPlus links from
   `http://postersplus-test:8000` back to `http://postersplus:8000`. Remove
   `original_labels`, `liquid_*` and any `sash_badge_style=liquid*` from them:
   stock PostersPlus ignores them, but they'd be clutter.
2. Optionally stop the test copy: `cd ~/postersplus-test && docker compose down`.
   To remove it entirely, delete this folder and the `posters-test` block in the
   Caddyfile (`sudo systemctl reload caddy`), then the DNS record.

If the pull requests are merged upstream, the Arabic support and the Mini
Series fix arrive in the official image through Dockhand, and only the `aer`
extras (version label, Liquid Glass) would still need this build.

## 6. Related

- The issue text: `~/postersplus/issue-arabic-labels.md`; the PR description:
  `~/postersplus-fork-PR.md`; screenshots `~/postersplus-fork-portrait.png`,
  `~/postersplus-fork-landscape.png`.
- The AIOMetadata fork has its own guide: `~/aiometadata/fork-changes/README.md`.
