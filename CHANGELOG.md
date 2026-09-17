# Changelog

## 0.5.0-shadow — Scout Azure Cost runtime package

- Added a create-only, credential-free Azure Cost package manifest and packager for the canonical Scout Runtime Root.
- Added fail-closed Scout preflight checks for Python, `requests`, Azure CLI, package completeness, runtime isolation, and three independent Azure profiles.
- Added a create-only interactive provisioning script for separate Global Power BI and Azure China read profiles; it never copies an OpenClaw CLI profile.
- Added a notification-silent cost Shadow wrapper with package-local immutable evidence output.
- Created the first independent package at `~/.scout/runtime/packages/chengcheng-cost-monitor`; authentication remains intentionally blocked until Scout-owned Azure profiles are provisioned.


## Chengcheng Workbench 0.4.1 (unreleased)

- Hardened remote control with mandatory request IDs, Scout Teams Bot source binding, personal-chat restriction, and explicit confirmation for decisions.
- Added durable remote audit records and idempotent request replay; duplicate Teams deliveries return the original result instead of deciding twice.
- Added a localhost-only Scout Teams client and verified live status plus replay behavior end to end.
- Created a clean pending Skill Workshop proposal for `chengcheng-workbench-remote`; it is intentionally not auto-applied.

## Chengcheng Workbench 0.4.0

- Added a dedicated Chinese engineering action approval center for Pipeline retry, Security Tag, deployment, ADO update, and cloud-change proposals.
- Every proposal requires an exact target and exact action and can carry environment, risk, prechecks, rollback/stop conditions, and evidence.
- Approval records intent only: `executionEnabled=false` remains a hard API contract and no executor exists in this release.
- Added a deterministic Teams remote-control API prototype supporting status, pending proposals, and approve/reject/defer commands.
- Documented Scout Teams Bot integration, identity, anti-replay, digest binding, and local second-confirmation boundaries.

## Chengcheng Workbench 0.3.0

- Added read-only S360 and Pipeline collectors that convert existing local evidence artifacts into the live lane contract.
- S360 cards now summarize scan rows, Past SLA, Near SLA, daily changes, Phase 3 integrity, and evidence paths from the latest deterministic artifacts.
- Pipeline cards now summarize success/failure/running counts and fail closed on known non-retryable builds; collectors never retry or mutate ADO.
- Added deployment/release collection from the deterministic Security Tag plan; it surfaces environment splits and approval candidates without creating tags, builds, or deployments.
- Added Azure cost collection from verified monitoring CSVs, preserving the distinction between actual, run-rate, budget variance, and model verification.
- Added meeting/action collection from locally persisted HTML minutes; missing evidence stays unknown rather than inventing meeting outcomes.
- Added a one-shot `collectors/refresh_workbench.py` runner for all five lanes; scheduling remains opt-in and is not installed automatically.

## Chengcheng Workbench 0.2.0

- Added a SQLite-backed current snapshot contract for five operational lanes and exposed it through `GET/POST /api/ops-lanes`.
- Replaced static homepage shortcuts with live cards that show status, headline, metrics, actionable items, evidence count, owner, and refresh time.
- Kept empty states explicit so a missing data refresh is never presented as a healthy system.
- Updated package metadata and provenance for the Chengcheng Workbench fork.

## Chengcheng Workbench 0.1.0

- Forked the upstream Dream Team into a Chinese-first DevOps and Security workbench.
- Reduced the default roster from eight fictional employees to four explicit responsibility lanes: orchestration/approval, security/release, collaboration/meetings, and operations/cost.
- Added the `chengcheng-workbench` skill covering S360, deployment baselines, pipeline/IcM diagnosis, Azure cost models, and meeting/action follow-through.
- Changed the application timezone to Asia/Shanghai and established read-only/create-only defaults: external sends, ADO/cloud writes, production changes, retries, calendar changes, and deletion always require exact approval.
- Reworked the homepage around Chengcheng's five recurring work lanes while retaining the existing local API and SQLite architecture.

This page lists what changed in each release of The Dream Team for Microsoft Scout, newest first.

## What the Dream Team does today

The Dream Team is a local command center with eight digital employees that run on Microsoft Scout. Here is what it does as of the latest release.

- It watches your email, Teams, and calendar for things that need you, and lines them up in one approval inbox.
- You approve an item and it carries out what you asked, whether that is a reply, a thumbs up, a forward, or a send. It only drafts when you ask it to.
- It preps your meetings, pulls notes into action items, and flags scheduling risk before it bites.
- It does research with real sources, and it writes documents, decks, and sheets for you.
- It keeps a running record of what you got done, framed for a performance review if you give it your goals.
- You set how far each employee can go on its own, from draft-only up to fully autonomous, and confidential content always waits for you.
- You can add your own employees, or remove any of them except Major.

Everything runs on your machine, and the team never sends anything to other people without your go-ahead.

## Releases

### 4.3.1

- Fixed approved work sitting in the queue instead of running. When you pressed **Attention Major**, or approved something in the inbox, the request was recorded correctly but the background worker could not read it back, so it waited rather than starting. It now picks the work up on its next check, which is within five minutes.
- Stopped the background sweep from running twice. The hourly pass across your email, Teams, and calendar was also handing a second copy of the same sweep to the five-minute worker, so the same work was done twice and billed twice. The hourly pass now does it once, on its own. Nothing about what gets scanned has changed.
- Slowed that hourly pass from every 30 minutes to every hour. Together with the duplicate fix, a normal day goes from 96 full sweeps to 24. The **Attention Major** button is still there when you want the board refreshed immediately, and you can set the pulse back to 30 minutes in Scout if you prefer.
- Fixed Send on a prepared draft. When you clicked Send on something the team had written for you, the worker was not told that counted as work it should carry out, so the item could sit unsent. It now delivers exactly what you approved, without rewriting it.
- Wrote down the rules the background workers actually follow. The internal notes the team reads had drifted from how the app really behaves, which is what allowed the duplicate sweep and the stuck queue to go unnoticed through a release. They now describe the real behavior, including that a pending job is always your work and should never be skipped for looking unfamiliar.
- Corrected the setup notes, which still described the old timings from before 4.3.0.

### 4.3.0

- Cut what the background workers read, which is the main thing you pay for. The every-few-minutes worker used to pull your whole board just to find out whether anything needed doing, and on most runs the answer was no. It now asks a small question first, and that check is over 99 percent smaller than what it replaced. When a run does have work, it reads a trimmed view instead of the full one. That saving grows with your history, because what it leaves out is the completed-job and event backlog: on a fresh install there is barely any difference, and on a board with a few weeks of real use the trimmed view is roughly 85 to 90 percent smaller. What the team does has not changed, only how much it reads to decide. The dashboard in your browser still gets everything.
- Slowed the Attention Major worker from every minute to every five minutes. Running it every minute was a large share of the running cost, and the button it serves does not get pressed sixty times an hour. Five minutes still feels immediate when you press it. You can set it back to every minute in Scout if you prefer the old behavior.
- Moved the team onto Claude Opus 5, which is what it is now tuned for. Setup still shows whatever models your Scout offers and falls back to the best one available, so nothing breaks if you do not have Opus 5 yet.
- Added a warning on the dashboard when any of the four automations is switched off or missing. A paused automation does nothing, and until now the only sign was a board that quietly stopped updating, which is easy to mistake for a quiet day. The dashboard now reads your Scout automation settings and names the ones that are off.

### 4.2.1

- Made install and setup one smooth flow in a single chat. Scout now installs the app and then finishes setup right there, so you no longer have to quit Scout, reopen it, and paste a command. When Scout says it is done, your team is on and your dashboard is already showing your real day.
- Fixed the empty-dashboard-after-setup problem at its root. Setup now runs your first sweep itself instead of handing it to a background timer that could not run yet, so the board actually fills before Scout finishes. It also switches the four automations on and double-checks they are on, since a paused automation does nothing.
- Made the restart optional and clearly labeled as such. The team is live without it. Restarting Scout later only registers the `/daily-flow-setup` and `/daily-flow-team` shortcuts for future use.
- Pointed Microsoft employees to the right place to get Scout. The prerequisites now note that Microsoft employees install Microsoft Scout from an internal aka.ms site, while everyone else uses the public link.

### 4.2.0

- Made the install steer itself onto the strongest model. The paste-in prompt and the Scout install guide now ask Scout to run setup on Claude Opus 4.8 when it is available, which is the model the team is tuned for and the one that follows the steps most reliably.
- Fixed setup declaring itself done over an empty dashboard. The wizard now kicks off the first sweep, waits for the board to actually fill, and only then hands off. It also tells you the truth about timing: a first sweep takes about 5 to 10 minutes, not seconds.
- Added a first-run banner on the dashboard so a new user is never staring at a blank board wondering what to do. It says the first sweep is running and the board fills as it goes, switches to a friendly all-caught-up note when there is genuinely nothing to show, and disappears once real items arrive.
- Made the Microsoft-only extras a clear choice instead of a buried afterthought. Signing in as a Microsoft employee now surfaces the depth skills for Dash and Drew, and the internal MSX seller-data plugin, as recommended next steps during setup, each with a guided, verified walkthrough rather than a one-line mention at the end.
- Added a "The Dream Team" shortcut to your desktop during install, so you can reopen the dashboard anytime with one click. It starts the app first if it is not already running, so it always lands on a live board.

### 4.1.0

- Made the background automations install the same for everyone. When Scout sets up the team, it now places each automation's instructions exactly as written and then reads them back to confirm they match, instead of retyping them from memory. Before this, two people could end up with slightly different wording. If one does not match, Scout redoes just that one, once, then tells you rather than looping.
- Slimmed the automation set to the four that run the team: the 7am Morning Brief, the 5pm Evening Wrap-up, the every-30-minute Work Pulse, and the every-minute Attention Major worker. Three extras that used to ship turned off have been removed to keep things simple and predictable. All four now install turned on.
- Fixed the empty dashboard on a fresh install. Right after setup the team does one pass across your email, Teams, calendar, and meeting prep, so the board shows your real day within about a minute instead of opening blank.
- Tightened the every-minute worker so it is plainly a worker only: most minutes it checks once and stops, it never starts its own sweeps, and it cleans up after itself so it does not clutter Scout.

### 4.0.4

- Tidied how release notes are kept. This changelog is now the single place that lists what changed in each version. Previously there was also a separate notes file per version cluttering the project, and those have been removed. The notes shown on each GitHub release are now taken straight from this file.

### 4.0.3

- Changed how you install. The easy way is now to open Microsoft Scout and ask it to install the Dream Team from GitHub. Scout downloads it, sets it up, checks that it worked, and fixes common problems like missing Python or a busy port on its own. If it cannot solve something, it stops and tells you plainly instead of looping.
- Added INSTALL-WITH-SCOUT.md, a short guide Scout follows to do the install, with clear stop conditions so it never gets stuck in a loop.
- Retired the double-click START HERE.cmd and Check Setup.cmd. Those were the most common source of setup trouble, because Windows would sometimes run them from inside the zip or block them. The install now runs through Scout, with a short manual fallback in the README for the rare case Scout cannot do it.
- Rewrote the README around the new flow.

### 4.0.2

- Fixed the most common setup problem. If you started setup from inside the downloaded zip without extracting it first, you used to get a confusing error about a missing install file. START HERE.cmd now notices this and tells you, in plain words, to extract the zip first and try again. Check Setup.cmd does the same.
- Wrote this full changelog so you can see how the project has grown over time, with a short summary of what it does today at the top.
- Cleaned up the README so it reads more plainly.

### 4.0.1

- Added an MIT license and a short disclaimer. The disclaimer makes clear this is a personal project, not an official Microsoft product, and provided as is. No change to how the app works.

### 4.0.0

- First public release on GitHub. This is the full eight-person team, packaged so anyone on Microsoft Scout can run it.
- It runs on two bundled skills plus the skills already built into Scout, so it works without a corporate sign-in.
- Setup figures out on its own whether you are signed in with Microsoft and adjusts. If you are a Microsoft employee, it offers some optional extra depth, fetched into your own Scout. That depth is never part of the package.
- Every employee has a plain-Scout way to do its job, so nothing breaks if an optional add-on is missing.
- The document folder now finds your OneDrive on any machine, and falls back to a local folder if OneDrive is not set up.

The releases below were shared as zip files before the project moved to GitHub. They are listed here for history.

### 3.3.9

- Setup now checks that Microsoft Scout is actually installed before it acts ready, instead of leaving you with a dashboard that loads but does nothing.
- Employees you add yourself now get picked up and put to work, and what they produce shows up in your results.
- The roster shows real status for each person, working, blocked, paused, or ready, instead of always saying ready.

### 3.3.8

- The capability map on the architecture page now shows real usage numbers for each skill, instead of dashes.

### 3.3.7

- Fixed the real cause behind "I approved it but nothing went out." The background workers that carry out approved actions were still holding an old draft-only rule. An approved reply now actually sends.

### 3.3.6

- Documents the team prepares for you now open correctly from the results list, including a clean reading view for notes and briefs. They used to fail with a not-found error.

### 3.3.5

- Un-muting an item brings it straight back to the approval inbox, and the muted list stays open when you expand it.

### 3.3.4

- When you tell the team what to do on an item, like reply, react with a thumbs up, or forward, it does that exact thing instead of turning everything into a generic draft. It only drafts when you ask.

### 3.3.3

- Approving an email or Teams message in the inbox now sends it. Approval is your go-ahead. The trust levels only govern work the team starts on its own.

### 3.3.2

- Added links on inbox cards to open the original message. Teams replies now actually reach Teams.

### 3.3.1

- Restored the approval buttons after a bug had quietly broken them, made the trust levels actually change behavior, and made the installer handle upgrades cleanly while keeping your data and any employees you added.

### 3.3.0

- You can build the team you want. Add your own employees through a guided onboarding, or remove anyone except Major and bring them back later.
- Setup got tougher about the one thing it really needs, Python, and can install it for you if it is missing or too old.

### 3.2.1

- A polish pass. The adoption view can be scoped by time, the cockpit sections collapse and stay that way, chat statuses tell the truth instead of getting stuck, and the wording reads in the first person.

### 3.2.0

- Added a private career profile. Paste your job description and how your performance is measured, and the team captures and frames your work against what your review actually rewards. It stays on your machine.

### 3.1.0

- Made the per-employee trust levels real. Draft, Assist, and Autonomous now actually control how far each person goes, with a firm rule that confidential content always waits for you.

### 3.0.1

- Theme polish for the then-new look.

### 3.0.0

- A big step up in trust and transparency. Each employee got a trust level and a clear set of what it will and will not do on its own. Added memory that stops re-surfacing things you already dismissed, a guardrails panel that shows the safety model in plain view, an adoption view, and the ability to spin up short-lived helpers for one-off batch work. Everything the team makes still goes to you only.

### 2.1.0

- Fixed skills installing to the wrong folder on some machines, which had stopped the setup command from being recognized. Started naming releases by version so you can tell builds apart.

### 2.0.0

- One download for everyone, with the setup wizard asking who you are and adapting. Added a model choice at setup, and optional extra depth for signed-in Microsoft employees.

### 1.0.0

- The first shareable build. It included the local dashboard, the team of digital employees, the background automations, the guided setup, a one-click installer, and a check that keeps personal data out of the package.
