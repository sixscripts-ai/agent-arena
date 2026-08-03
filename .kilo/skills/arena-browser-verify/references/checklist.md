# Browser Verification Checklist — Agent Arena

## Home ( / )

- [ ] Hero title "Models fight. You watch code." visible
- [ ] LIVE badge pulsing dot
- [ ] Start battle → navigates to /signup if no auth else /battles/new
- [ ] Cards: Formats number >0, engines >=1, avg battle, host free models pill, backend hostname not raw slice
- [ ] Format library: if loading → skeleton (6 cards pulse), if loaded → cards grid, if empty → message "No formats" + explanation not just empty
- [ ] Engine filter pills highlight active (accent bg)
- [ ] No console errors

## NewBattle ( /battles/new )

- [ ] Auth gate: if no user → "Login required" with link
- [ ] Format select populated from /formats
- [ ] Needs X models text correct (playable role count)
- [ ] Slots mapping: label Slot 1: builder etc, order = role
- [ ] Model selects: Host free + Your groups, at least 2 host ids
- [ ] Judge optional select default "Default host judge"
- [ ] Timeout input min 30 max 3600
- [ ] Visibility isolated vs open
- [ ] Save checkbox
- [ ] Start battle button disabled when busy, error shows
- [ ] Live preview panel shows roles mapping live

## LiveBattle ( /battles/:id )

- [ ] Header: battle id slice 8, format_id, status pill (QUEUED/RUNNING pulsating/SUCCESS), phase meta, artifacts count, STOP/SAVE buttons
- [ ] Phase line: build → break → judge, accent trail for done
- [ ] Dual CodePane: builder/breaker labels, line numbers, code monospace, cursor blink when running, footer kb size, win condition highlight WARN
- [ ] Judge section: scores per model, winner accent border
- [ ] Event stream: max-h 160, last 20 truncated, uuid deduped header, auto-scroll but not thrash
- [ ] SSE network: /battles/:id/stream 200 text/event-stream
- [ ] Cancel works, save works

## Leaderboard ( /leaderboard )

- [ ] H1 Leaderboard, Overall + format filter
- [ ] Table # / Model / Format / Elo / Games
- [ ] Empty state "No rankings yet — run a battle" + CTA
- [ ] No 404 for /leaderboard?format=...

## History ( /history )

- [ ] Redirect to login if no user
- [ ] Cards: id mono, format, status color, model_ids, Open button
- [ ] Saved filter working (backend saved=true)
- [ ] localStorage fallback: arena_battle_ids parsing

## Providers ( /providers )

- [ ] List host + your providers, masked_key shown
- [ ] Create form: name, base_url, api_key (password), auth_style, model_name
- [ ] Health check button
- [ ] No raw key in DOM after create (masked only)

## Global

- [ ] SiteHeader sticky, backdrop-blur, nav active state with border-accent? active class
- [ ] Mobile 375px: hamburger ☰ toggles nav list, links work
- [ ] Dark/light: code-bg stays dark intentional, text-muted contrast
- [ ] 404 route: "404 — Not found" centered
- [ ] Vercel rewrite: direct /leaderboard URL load not 404
- [ ] No console errors except font
- [ ] Network: /formats 200 <800ms, /health 200

## Prod URL https://agent-arena-blond.vercel.app Specific

- [ ] formats count >0 (if 0 bug exists -> report)
- [ ] engines count >0 (if 0 bug)
- [ ] VITE_MODAL_URL env set in Vercel dashboard
- [ ] CORS: backend allow *.vercel.app regex
- [ ] favicon.svg loads
