# GitHub Reviewer-Landing Audit — 2026-05-04

What a cold reviewer sees when they hit `github.com/AaronCarney/ttb-label-verification`.

**Captured against:** `main` at audit time (commit `9a5db08`, README.md as last pushed). The Task B/C fixes in this branch (`docs/post-e8-decisions`) are local — not on `main`.

## Gaps

### Critical

1. **Dead canonical URL in README on `main`.** `README.md:16` and the GitHub-rendered landing page still advertise `https://ttb.aaroncarney.me` as the demo URL. That hostname is not wired (D-DEPLOY-001 — HF custom domain is Pro-tier-gated). A reviewer who clicks the link gets a TLS error or 404. **Highest-priority fix on landing.** This branch's Task C commit (`b307307`) replaces the URL on main when merged + pushed.

### High

2. **No CI workflows.** Repo has no `.github/` directory; no Actions runs; no green check or badges in README. For a take-home, the absence of CI signals "no test discipline" even though `tests/` is substantial and `uv run pytest -v` is wired in `pyproject.toml`. Adding a minimal workflow that runs `uv sync && uv run pytest -v` against `python:3.12-slim` would close this gap with one file (~30 lines). A `frontend/` lint+typecheck step is similarly cheap.

3. **`homepage` repo metadata is empty.** GitHub renders a "🔗 site" link in the right rail when set; reviewer eyeballs land there before the README. Set to `https://context31415-ttb-label.hf.space` (or whatever the canonical demo URL is at merge time).

### Medium

4. **No LICENSE file / no license metadata.** GitHub flags this as "No license" in the right rail. For a take-home this can read either as "no rights granted" (intended) or "we forgot." If the candidate intends a permissive demo, add `LICENSE` (MIT or Apache-2.0). If not, leave but be aware of the optic.

5. **Repo Description is generic.** "TTB AI-Powered Alcohol Label Verification Prototype" is fine but adds nothing the README's first line doesn't. A one-sentence variant naming the deployed URL or the candidate's role-fit signal could replace it. Minor.

6. **No topics / tags.** Empty `topics` array. `python`, `fastapi`, `llm`, `regulatory-compliance`, `ttb`, `take-home` would help discoverability. Cosmetic.

### Low

7. **`feat/e7-ui` branch is publicly visible and is ~30 commits ahead of `main`.** Acceptable for a take-home that openly shows its development trajectory, but a meticulous reviewer scanning the branch list will see in-progress E7 work that isn't on main. No action required unless the candidate wants to suppress it before submission (delete remote branch after merging, or rename to a non-default-sort prefix).

8. **No PR history.** Zero open or closed PRs. The repo's history is direct-to-`main` commits. Defensible for a one-person take-home but reads as "no review process" if the reviewer expects PR-driven workflow. No action recommended for a take-home.

9. **GitHub Wiki is enabled but empty.** Wiki tab in nav with a 404. Disable in repo settings if not used. Cosmetic.

10. **No release / no tags.** `gh api .../tags` returns empty. A single `v0.1` release tagged at the take-home submission commit would let reviewers download a frozen snapshot. Optional.

## Notable non-gaps (for the record)

- Repo is public ✓
- README renders well-structured headings, code blocks, profile setup ✓
- `docs/` directory listing is browsable and has clear hierarchy ✓
- No secrets in tree (spot-checked `.env.example`, no leaked keys) ✓

## Priority pass (post project-instructions review)

Re-tiered against the project-instructions filter: D-001 (Sarah's team grades
the application, not branding), D-DEPLOY-001 ("cost > benefit for a one-shot
demo" applied to repo cosmetics), and the `Don't push without explicit permission`
constraint.

### T1 — Reviewer-blocking; must land before submission

- **#1 dead `ttb.aaroncarney.me` URL on `main`.** Fixed locally by `b307307`. Action required: merge `docs/post-e8-decisions` → `main` + push. **Gated on user permission.**

### T2 — Cheap, high-signal; recommend now

- **#3 empty `homepage` metadata.** Single `gh repo edit AaronCarney/ttb-label-verification --homepage https://context31415-ttb-label.hf.space`. Adds the "🔗 site" link in GitHub's right-rail — one-click reviewer path to the demo. **Remote state; gated on user permission.**

### T3 — Follow-up (track, not now)

- **#2 CI workflow.** Real engineering signal but adding before E6/E7/E8 lands risks a red X mid-flight. Defer until post-E8 with `uv run pytest -v` verified green on `main`.
- **#4 LICENSE.** Candidate IP-intent question; genuinely ambiguous — not auto-answerable.
- **#9 disable empty Wiki.** One-click cosmetic; bundle into post-E8 polish.
- **#10 `v0.1` tag at submission.** Optional convenience; tag at submission commit if/when the candidate cuts the deliverable.
- **#7 `feat/e7-ui` publicly visible.** Defensible (shows real development); no action unless the candidate wants a tidier branch list at submission.

### T4 — Skip (low reviewer signal)

- **#5 generic repo description, #6 empty topics, #8 no PR history.** Take-home doesn't benefit. Explicitly not pursuing.
