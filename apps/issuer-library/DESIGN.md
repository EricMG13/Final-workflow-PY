---
name: Issuer research workspace
description: A working research desk for dated issuer evidence and decisions.
colors:
  navy: "#000533"
  action: "#0017E5"
  ground: "#EEF0F5"
  panel: "#FFFFFF"
  quiet: "#F6F7FA"
  rule: "#DDE1EA"
  secondary: "#4A5068"
  selection: "#E7ECFF"
  caution: "#8A5300"
  caution-tint: "#FFF1C7"
  positive: "#0E7A46"
  negative: "#B3261E"
typography:
  title:
    fontFamily: Red Hat Display
    fontSize: 25px
    fontWeight: 700
    letterSpacing: -0.02em
  body:
    fontFamily: Red Hat Text
    fontSize: 13px
    fontWeight: 400
    lineHeight: 1.65
  measurement:
    fontFamily: Red Hat Mono
    fontSize: 20px
    fontWeight: 500
rounded:
  inline: 4px
  surface: 12px
  control: 8px
  status: 999px
spacing:
  small: 8px
  medium: 16px
  large: 24px
components:
  button-primary:
    backgroundColor: "{colors.action}"
    textColor: "{colors.panel}"
    rounded: "{rounded.control}"
    padding: 0 14px
    height: 40px
---

## Overview

A research desk: a dark, persistent navigation area frames a raised white working
surface. Issuer identity, run context and actions precede analytical content.
The user’s symbol is the only brand mark. This is an Operate / Read surface.

## Colors

The Deploy VII primitives are the custom properties at the top of web/screen.css. Navy provides structure;
blue means action, selection or the issuer data series. Module availability uses
visible neutral words: saved outputs, inputs and checks only or no files found.
Amber with an explicit label signals open questions or unavailable operations.
Green and red are reserved for qualified producer-declared positive/adverse states;
the frontend does not assign credit judgements from ratios or file counts.
Grey means neutral, missing or unassessed. Every state includes text.

## Typography

Red Hat Display supplies issuer and task headings, Red Hat Text supplies reading
and controls, and Red Hat Mono supplies measurements and identifiers. Main prose
is 13–14px. Compact metadata is 11–12px, retaining the established data-workspace
roles. The ramp is four roles (label 11px, compact 12px, body 13px, control 14px) as
`--fs-label`, `--fs-compact`, `--fs-body`, `--fs-control`; no text renders below 11px.
Exact decimal strings remain visible independently of chart geometry.

## Layout

Desktop discovery uses a 56px symbol rail and 228px issuer navigation. Module
reading collapses issuer navigation into Browse issuers and uses a 210px module
navigator alongside the analysis. The run has five tabs: Overview, Modules,
Calendar, Reports and Evidence. An observed toolbar height governs sticky navigation
and anchor offsets. The selected output and section controls stay visible while
reading. At 700px, module navigation and content stack. Tables/charts may scroll
inside their own labelled regions; the page must not overflow horizontally.
Report reading keeps issuer/run and revision selectors.

## Elevation & Depth

A single 0 6px 24px rgba(0,5,51,.07) shadow lifts the research surface from the cool
ground. Tonal backgrounds group context and measurements. Internal tables use
rules. Do not add nested shadow cards or decorative glow.

## Shapes

12px working-surface corners; 8px controls; 4px for inline chips, codes and keys; pill-shaped status labels. Lucide line icons
are bundled locally with their ISC/MIT license notices. Icons accompany labels.

## Components

Controls follow Untitled UI React (MIT): 40px buttons, inputs and selects with
8px corners and an xs shadow; a 4px blue focus ring; pill badges; removable
chips; tables with a grey header row. Colours, fonts and the rail stay the
company's, and the greys lean toward its navy. Every screen uses
them except the embedded context form. The run header is one line:
issuer name, the run as a grey mono badge, Change case, and the period with a
calendar icon on the right. Underline tabs follow: grey text, the current tab
blue with a 2px underline; on phones they scroll sideways without icons.
Content tables sit in a bordered 12px card with a grey header row, row rules
and no stripes; values stay in Red Hat Mono with tabular figures, and a wide
table scrolls inside its own card. Labels in content (classification, input,
output scope, report status, summary kind) use the same grey badge as the
Library; on the navy summary band it is a white outline.
Charts keep the company series colours (blue, navy, blue-grey; amber for
conditional downside) and drop grey bar tracks. Bars end in a 4px rounded
data-end, the grid and axes are pale greys, scenario points carry a white
ring, and summary charts sit in the same 12px card. Grades are pills: a grey
pill for neutral, a dashed outline for Not Assessable, red tint only where
the handoff declares Weak. Navy and blue-grey fail a generic palette's
lightness and chroma checks, so every series stays labelled in text.
New run and Settings use the same 40px fields (16px text, a chevron on
selects, a styled file button) and the secondary button for every action
but the primary one. Run stages are a progress bar: blue up to the current
stage, grey after it. Run progress lists the modules as numbered steps (Untitled UI Progress, icons with text, number type): a green tick once accepted, a blue marker for the module in progress, amber where a run stopped, grey ahead, with a connector between steps. The last step is Report delivery: grey until the modules are accepted, Delivering while the reports are built, a green tick once Delivered, and amber Stopped where the run stopped there. Recent runs use the content table, with workflow and state as labels. The context form keeps its own contents inside a
framed 12px card. Its literals in context-embed.css (the default tag is the grey badge's colours) mirror the tokens of screen.css, because that sandboxed document cannot read the app's variables.

- The run-state strip (`#run-strip`, the Untitled UI full-width alert anatomy: icon, title, supporting text, actions, Dismiss) sits above the working surface and shows one run: the active one, otherwise the newest run that is not running. Dismiss hides the strip for that run until its state changes; it does not fall back to an older run, and the rail mark and title prefix are not affected by Dismiss. States are running (blue, a count of accepted modules), complete (grey), and stopped, failed or interrupted (amber, the stop sentence and spend). In the strip, amber is used only for those three. Actions are View activity, View reports on a complete run, and Resume where the run can be resumed. Dismiss is kept per viewer, as the state the run was dismissed in, so the strip returns when that run's state changes.
- The Run activity link in the rail carries a small mark: a blue ● while running, a grey ✓ when complete, an amber ! when stopped, failed or interrupted. The glyph is decorative; the link's accessible name states the run's state.
- The Forecast tab's cash flow model never prints “—”. Every gap is n.a., with its reason where the record gives one: “printed as — in the source” or “the model's source table has no value for this period”; n.a. and n.m. cells carry that reason as an aria-label. A “Why cells show n.a.” disclosure lists one line per row and reason, naming the periods. Total rows are semibold with a top rule. Ratio cells (percent, multiple) show their value in a tooltip at four decimals, with ≈ when rounding changed it. The grid sits in a labelled, keyboard-focusable scroll region, and the published model stays behind a closed “Published model (original HTML)” disclosure.
- Built from lists Role · Run · Source · SHA-256 prefix · Status, with plain role words (such as Annual handoff). A source that still matches shows the grey “Matches publication”; a changed or invalid one is amber. When the sources come from different attempts, a note names the files and their attempt numbers; it states the fact and does not judge it.
- A report's acceptance label “Candidate · not accepted” uses the grey badge. Amber is for attention only.

- Run changes preserve the active module; unavailable output remains explicit.
- The module opens selected analytical sections, not the entire Markdown handoff.
  A compact output selector keeps attempts distinct. Findings and a relevant
  analytical panel lead; supporting sections and limitations expand in place.
  Source inventories, requests, calculation transcripts and downstream handoffs
  live in a lazily rendered Evidence & audit disclosure. Unknown sections remain
  accessible. Source-readiness and evidence-trace modules retain substantive
  lineage work as analysis. Files and history are secondary; inputs never acquire
  output status.
- Charts attach to their own source tables. Exact values, row qualifications
  and declared provenance remain visible; a row's line locator shows in the inspector it opens. Chart order is chronological;
  the table twin keeps source order. Source opens the exact row fields in a side inspector in the same module.
- Event registers support calendar and source order. Fiscal/range/combined dates
  stay separate. Markers are neutral; date precision and source classifications
  are words. The frontend does not infer creditor judgements or exact dates.
- Keyboard chart marks open evidence; Back to analysis or Escape restores the trigger.
- The module navigator defaults to available outputs, supports All modules and
  text search, and receives `/` while reading a module. Audit content does not
  compete with the main analytical reading path.
- The 91-item mapping remains a planning reference, not claimed populated figures.

## Do's and Don'ts

Do use source identity, period, unit and limitations as part of the view. Do keep
unknown provenance labelled “Not classified” in the evidence inspector; lists and
source footers show a class only when the handoff declares one. Do use subdued depth and clear
reading hierarchy. Do keep all assets offline. Do not mix fiscal periods, invent
missing figures, treat workflow progress as credit quality, or promote an attempt
because its filename sorts first. Do not use amber for a state that needs no action, and do not print “—” for a missing figure: say n.a. and why.

## Interface terminology

- **Filter runs** opens the cross-run search and filters; **Back to selected run**
  returns to the current run.
- **Primary output** is the file specified for this run. **Saved output** has no
  primary designation. Neither label verifies analytical acceptance.
- **View source** opens the exact module row; **Open source file** opens the
  original file. **Back to analysis** restores the chart, fact or event that opened it.
- **Resume** starts a new run with its own spending cap; the stopped run's accepted modules are kept without a model call. It is offered for a stopped, failed or interrupted run, never after a provider ruling.
- **Evidence & audit** holds production records and technical detail.
  **Not classified** retains the user's chosen unknown-provenance label there.

## The one app

This shell is the application: it replaced the earlier library and reader screens, and
sections above this one are kept for their design rules, not their layout. It extends the
approved Direction C/current-layout hybrid across all analytical modules and the workspace
screens, and its source is `apps/issuer-library/web/`. The left rail reaches Issuer library,
Research workspace, Reports, Run activity, New run, Search, Settings and Help, and marks
where you are; run-level links keep the selected run and are hidden in an empty workspace.

The exact symbol, local Red Hat fonts and colour tokens are retained. A compact
issuer header precedes a 238px searchable module navigator, a raised white
analytical canvas and a 280px adjacent inspector. At 1050px and below, evidence uses a separate reading view;
at 720px the catalogue has a labelled Modules control. The search remains sticky,
the active module’s persistent grouped section outline leads the sidebar, and a
Browse modules & tools disclosure exposes the full catalogue. Names, topics and
absorbed CP aliases are searchable. Unique section labels, disclosure state,
reading position and keyboard focus persist while navigating.

The library provides one restrained discovery strip: issuer/run text,
sector, workflow, as-of year, available content and contained module. Workflow
and as-of year come only from what a run's own manifest recorded; a run without
them is listed under Not recorded, never given an inferred date or workflow.
Modules in the contained-module list sit under the credit question each one
answers. All criteria combine. Controls carry no visible label; each active
filter shows as a chip that names it and removes it, and Clear all appears only
while something is filtered. Counts distinguish issuers, retained runs and
reports. Results are one table row per issuer: an issuer with one run links
straight to it; an issuer with several runs opens a drop-down of its runs, each
with its workflow, period and reports, and stays open on return. Filters remain
when returning from a run within the same page session; Clear all resets every
criterion and focuses search. Empty results explain recovery.
Comparable credit metrics and completeness scores are not offered, so the library
has no metric filters. Only deliberate
disclosure actions persist; workspace-driven catalogue expansion cannot override
the user's choice and bury the grouped module outline on return.

Every saved output of every run in the workspace supplies complete content, with original
bytes, line locators, hashes, amounts, units, periods, qualifications and gaps. A curated view
applies only to the exact file it was built for. Runs retain separate issuer headings and
dates; nothing is presented as one completed pathway. A module with no output in a run shows
No output found. CP-8 shows the retained deliverable comparison.
Top bands, chart readings and cautions quote the handoff or are short legends.
CP-MODEL shows the unpublished state recorded by the
saved deliveries. Missing observations are never plotted as zero.

Visuals sit within their owning module: annual/quarterly comparisons, peer strips,
issuer earnings and cash waterfalls, conditional scenario paths, hedge lanes,
agency comparisons, provision and claim-lineage matrices, recovery comparisons,
funding-case differences, and bull/bear/resolution views. Complete exact data and
qualifications remain adjacent or in named sections. Qualitative presentations
that already contain every table field do not repeat the same table underneath.
The 91-view specification stays in docs/visualisations for builders; the app does
not show it, and it is a plan, not a claim that every figure is populated.

Blue identifies data and action; navy and muted blue-grey distinguish ordinary
comparison series. Amber identifies labelled conditional downside or attention.
Conditional paths also use distinct dash patterns; signed outflows use direction
and exact values instead of receiving an inferred adverse grade. Grey
marks absent/unassessed evidence. Analytical outcomes do not become provenance
labels. Unknown provenance displays Not classified in the evidence inspector. No
probability, numerical credit grade or new analytical result is introduced.

Issuer/run context is encoded in workspace links and deep links. Missing destinations retain
context and offer other runs of the same issuer. Each report lists the run files it was built
from, traced by SHA-256, and a module output links to the deliverables that used it. Calendar
retains date precision and links back to its owner. A deliverable opens inside the app in a
sandboxed reader with report switching, its files, original download and Return to library.
The embedded view uses symbol-only branding; original downloads remain byte-identical.

New run sits inside the shell and keeps its state across navigation. Its steps follow the
launcher: context, issuer folder and budget, review, then an explicit Start. A stopped run
can be resumed from the run-state strip, Run activity or New run.

Browser checks cover laptop widths of 1366px and 1280px. Hash routes support deep
links and browser history; evidence closing restores focus and content scroll.
Narrative claims and every plotted mark have exact-source actions; unknown
provenance remains Not classified. Original source hard wraps do not govern prose.
Functional text uses an 11px floor; prose remains 13–14px. All resources are local.
Native Windows remains outside this browser verification.
