# DOST scripts index (check here before writing new code or searching drives)

D = C:\Users\Lenovo\OneDrive\Documents   |   S = D:\DOST_agent_for_windo_LAPTOP_vis_Mobile_Discord\scripts
Run any script with `-h` for usage. Prefer these over one-off snippets.

## General (S)
- S\site_check.py      status, title/desc/H1, canonical, noindex, GA4, robots, sitemap (+ `--urls N` status check). Many sites: `--file`.
- S\excel_tools.py     info / head / find / count / dupes / append (with backup) / tocsv for xlsx+csv. Bounded output.

## Limo prospecting (D\Limo_SEO_Prospecting)
- limo.py              ONE CLI: `status [BATCH]`, `due`, `add BATCH rows.json`, `send BATCH [tz] [--send]`, `track`. Use instead of new add_wN / send_wN copies.
- maintain_tracker.py  rebuild Outreach_Log + Funnel (auto-finds *_emails.json; reads batch_sent_dates.json)
- prospect_finder.py, find_emails.py, audit.py, findings.py   finding + auditing prospects
- followups\send_fu1.py  FU1 + FU2 sender (east/west/ksa, --stage 2, --ids; texts fu1_texts*.py / fu2_texts.py; run_fu_group.cmd for Task Scheduler)

## GBOB guest posting (D\GBOB_Guest_Posting)
- vet_sites.py run | apply   stage-1 vendor vetting (live, link-farm signs, Tranco rank) into Vendor_Tracker.xlsx
- gbob_daily.py next|set|seta|status   stage-2 vetting. set = Semrush AS; seta = Ahrefs free checkers (DR -1 = not checked). Stage 2 FINISHED 20 Oct (queue 0)
- Older per-batch files (add_w2..w9, w*_emails.py, send_w8/w9, mark_w*_sent) = history only, don't copy.

## Rank & rent sites
- D\Plumbing_RnR_Sites\build\engine.py, preview.py   build + preview lead-gen sites
- D\Site_Progress\site_progress.py                    site progress report
- D\indexnow_ping.py                                   IndexNow submit
- D\OffPage_All_Sites\bing_check.py                    Bing checks
- D\Websites_Register_make.py                          Websites_Register.xlsx

## Other
- D\PhD_EMANAIRE\make_dc13.py, make_dc14.py           EMANAIRE deliverables
- D\YouTube_AI_Shorts\make_shorts.py
- D:\PhD_research_secondbrain\99_Meta\scripts\vault_lint.py
- outreach\gbob_send.py PITCH_JSON uk|us|all [--send]   GBOB pitch sender (dry run default), logs sent_log.csv + tracker
  - follow-ups: gbob_send.py FU_JSON SLOT --followup N [--send] (threaded Re:, IMAP reply/bounce skip, fu_log.csv); FU1 texts via make_fu1.py -> gbob_fu1.json
- stage3_check.py   reads WFU pages of Vetted PASS sites (link policy, contact, noindex)

## reel_maker.py (23 Oct 2026)
Text/terminal reels 1080x1920 (dark bg, orange accent, step cards, bar charts, tips, CTA), no footage, no AI images, synth pad audio.
`python scripts/reel_maker.py spec.json out.mp4` (`--still SEC out.png` to preview). Spec format in the file docstring. Example specs: OneDrive\Documents\Reels\2026-W43\*.json
