# Handoff: voice pass on the 0.19.6 patch notes

You are doing an EDITING pass, not a rewrite from source. The facts are settled and
verified. What needs work is the prose, which reads like a machine wrote it, because
one did.

## The files

Repo: `/Users/grahamtj/Documents/Game_development/Roguefort_Patch_Notes_Website/`
(This is the canonical site. A stale export in `~/Downloads/roguefort-patch-site/`
has drifted. Never author there.)

- `notes/0.19.6.md` — the source you edit. 145 lines, 96 bullets, 13 sections.
- `notes/0.19.6.steam.txt` — DERIVED. Do not hand-edit. Regenerate after editing:
  `python3 md-to-steam.py notes/0.19.6.md notes/0.19.6.steam.txt` (script is in the repo root)
  (the script asserts BBCode tags balance and no markdown leaked through)
- `docs/0.19.6.html` — built. Re-run `python3 build.py` after editing.

Read `notes/0.19.3.md` and `notes/0.19.4.md` first. That is the target voice, and it
is Tim's own.

## What is wrong with it, measured

The draft leans on one construction to describe almost every fix: state the old
broken behaviour, negate it, explain the mechanism. Counted across 96 bullets:

  "no longer"    22
  "stops"        12
  "rather than"   9

That is 43 bullets out of 96 built the same way. It is the single loudest tell.

  bullets opening "The" or "A"   0.19.6: 37 of 96 (39%)   Tim's 0.19.3: 7 of 30 (23%)
  bullet length, words           0.19.6: median 19        Tim's 0.19.3: median 26

So: more bullets, shorter, flatter, and starting the same way. Tim's run longer and
vary their entry.

Four more habits to break:

1. **Mechanism before experience.** Most bullets open with the internal cause and
   reach the player's experience second, or never. Lead with what the player saw.
   The cause is worth keeping when it is genuinely interesting, and most of these
   are, but it belongs after the hook.
2. **Numbers used as decoration.** 1694 tiles, 19,768, 35 to 61 percent, 242 maps,
   9.90 MB, 73.4 MB, 237 creature rows, 5,177 tiles. Every one is true and load
   bearing somewhere, but stacked together they read as a lab report. Keep the ones
   that land a point (1694 tiles of vision is funny and awful). Cut or soften the
   rest.
3. **No warmth and no jokes anywhere in 145 lines.** Tim's notes have both.
   "Non Travolta." is a font joke used as a lede.
4. **Balance constructions.** "which was the right call, but", "X and not Y". These
   hedge. Commit to the sentence.

## Do not change

- **Any fact, number, or causal claim.** They were measured, not estimated. If a
  sentence has to lose a number to read better, cut the number. Do not round it,
  and do not invent one.
- **The trailing `(handle)` credits.** They are community reporters and each one is
  attached to the right fix. 78 of them. Keep them on their bullets.
- **The structural conventions**: `<!-- date: -->` / `<!-- lede: -->` / `<!-- tag: -->`
  header comments, `# Roguefort 0.19.6 — Patch Notes`, `## Section`, `- ` bullets,
  and the section literally named "Known issues" (build.py renders that one as a
  caveat block, keyed on the name).
- **The legendary-items section's substance.** It is a save-affecting change and the
  three claims are deliberate and were specified by Tim: existing items repair
  themselves on load, the repair is one way, and damage / armour / HP / lifesteal /
  thorns are untouched. Make it read better. Do not let any of those three drop out.
- **Section order and grouping**, unless a merge genuinely reads better. The
  legendary fix leads on purpose.

## House style, which still applies

All player-facing prose parses through the AI-tells blacklist at
`~/.claude/projects/-Users-grahamtj-.../memory/feedback_ai_writing_tells_blacklist.md`.
Draft against it, then audit the diff. Short version: no contrastive binaries
("not X, but Y"), no decorative rule-of-three, no aphoristic enders, no semicolons,
no emoji, and the vocabulary list (tapestry, testament, realm, journey, crucial,
delve, profound, showcase, boast...).

⚠️ **One judgement call to put to Tim rather than decide alone.** The blacklist bans
em-dashes as the top Claude signature, and the current draft has none. But Tim's own
0.19.3 and 0.19.4 notes use them naturally, and they predate the 08-29 blacklist
rule. Making the prose sound human may want a few back. Ask him before adding any.

## The lede

Tim owns this line and writes his own. Derive a candidate anyway, and offer two or
three so he has something to react to. The four so far:

  0.19.0  Hamsters!
  0.19.2  Suitably Wilder.
  0.19.3  Non Travolta.
  0.19.4  Mahargekdar's Plane of Heroes.
  0.19.6  The plinths go global.        <- placeholder, mine, too dry

The pattern: very short. Two to four words. Often a joke, a pun, or an oblique
reference rather than a summary. Ends with a full stop, or an exclamation mark when
it earns one. "Non Travolta." is about a font.

What 0.19.6 actually has to work with: the plinth leaderboards going global, a
legendary bow that could see 1694 tiles, the Retracing, abilities you now fire by
hand, a world clock that froze while you could still walk around it, and a Ship of
the Line with no masts.

Also check `<!-- tag: Playtest -->`. It is live on the default branch now too, so
that may want changing. Ask.

## When you are done

1. `python3 build.py`
2. Regenerate the Steam twin with the converter above.
3. **Do not push.** A push to this repo is publication, because Pages redeploys
   itself. Tim reviews the notes first. That is a standing rule.
4. Show him the diff, the built page, and your lede candidates.
