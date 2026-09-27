---
name: variant-lab
description: Try 4 to 6 working versions of one part of a project side by side before committing to any of them, then ship the one the person picks and delete the rest. Works for UI (a component, a page section, an animation) and for rendered media (a video title card, captions, a logo placement). Use when the user says "show me ideas", "give me options", "try some versions", "make it better", or names one element to rethink.
---

# Variant lab

People pick faster by trying than by reading descriptions. This skill turns "make it better"
into a short loop: build several real versions, check them yourself, let the person choose,
ship one, remove the rest.

## 1. Look at what's there
- Find the one element being rethought and say in one line what is wrong with it now.
- Check what the element can actually use: data fields, API scopes, existing components,
  render options. An idea that needs new permissions or a new dependency goes last and says so.
- Note the project's constraints: design tokens and fonts for UI; resolution, safe zones and
  platform chrome for video (for 1080x1920 vertical video a common guide is 220 px top,
  420 bottom, 60 left, 120 right).

## 2. Make 4 to 6 variants that differ in kind
- Differ in placement, metaphor, timing or amount of motion, not six colours of one idea.
- Always include **1 = now** as the baseline, so the person can compare against it.
- At least one variant should reuse a motif the project already has.
- Keep each variant self-contained: one component per variant, or one render config per
  variant. Shared code goes in one helper, not copied into each.

## 3. Put them side by side
- **UI:** a development-only page (for example `/lab`) that lists the variants, numbered, each
  on the background it would really sit on, with one line for where it goes and one for how to
  try it. Guard the page so it cannot ship to production (return 404 outside development).
  If a state is hard to reach on demand, add a query switch that only works on that page.
- **Rendered media:** render a short clip of each variant and one comparison sheet (a grid of
  stills with the variant numbers and the safe zone marked).

## 4. Test before showing anyone
- The project's build must pass with the lab in it.
- Drive the real interaction for each variant (hover, click, scroll, tap, or play the clip) in
  a real browser or player and look at the result yourself. For UI, assert a DOM or style
  change and take a screenshot; background tabs often pause animation, so use a foreground
  or headless browser for motion.
- Fix what is broken before step 5. Say which states you could not exercise.

## 5. Let the person pick
- Give the lab address or send the comparison sheet, then list the variants, one line each.
- Ask with the `quiz` skill: pick one, several, "combine N and M", or "show me more".
  If they ask for a mix or more, add it to the lab and go again.

## 6. Ship the winner
- Wire the chosen variant into the real place, matching the surrounding type and spacing.
- Delete the lab page and every variant that was not chosen. Rebuild and confirm the lab
  route is gone.
- Test the real page or render at desktop and phone width, or at the target resolution.
- Write the decision down wherever the project records design decisions. Commit.
- If pushing deploys something live, show what changes and get an explicit yes first.

## Done when
The person picked, the winner is in place and tested at every target size, the lab and the
unchosen variants are deleted, the decision is written down, and any deploy was approved or
explicitly deferred.
