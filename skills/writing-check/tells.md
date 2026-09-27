# AI writing tells

The patterns `scripts/slop_check.py` flags, and the ones only a reread catches. The test for a
place on this list: the pattern appears constantly in generated text and rarely in careful
human writing.

## What the checker flags

**Dashes inside sentences.** At most one per 500 words. Use a period, a comma or a new line.

**"It's not X, it's Y."** Also "not only X but also Y" and "X isn't just Y, it's Z". State the
point directly instead of manufacturing a contrast.

**Forced rule of three.** Three adjectives, three clauses, three examples, again and again. One
three-item list in a piece is fine, six is a tell. Vary it: one item for emphasis, two for
contrast, sometimes four.

**Significance inflation.** "Marks a pivotal moment", "a testament to", "underscores the
importance of", "in today's landscape". Say what happened.

**Copula avoidance.** "Serves as", "functions as", "acts as" where "is" would do.

**Tier-one vocabulary.** leverage, robust, seamless, pivotal, crucial, vital, delve, tapestry,
landscape, realm, harness, unlock, elevate, navigate, foster, underscore, myriad, plethora,
comprehensive, holistic. One is survivable, a cluster is diagnostic.

**Filler constructions.** "in order to", "it is important to note that", "when it comes to",
"the fact that", "a wide range of".

**Rhetorical questions used as transitions.** "So what does this mean?" Answer it instead.

**Stock openers and closers.** "Let's dive in", "Here's the kicker", "The truth is", "Let that
sink in", "I hope this helps", endings like "as this space continues to evolve".

**Hedge stacking.** "may potentially", "could possibly help to", "arguably one of the most".

**Uniform paragraphs.** Every paragraph the same length. Human writing is lumpy: a four-word
sentence next to a long one.

**Wall of text.** Paragraphs over about 120 words where a person would break or cut.

## What only a reread catches

1. **Sentences that parse but say nothing.** If a sentence needs rereading to find its point,
   cut it or say the point.
2. **The wrong register for the destination.** Formal report prose in a chat message, or chat
   tone in a graded document. Where the text goes sets the register.
3. **Length inflation.** Writing long and trimming again and again, instead of writing to an
   agreed length once.
4. **Bare noun-phrase bullets.** Bullets with no verb, all the same length and shape.

## Sources

- [avoid-ai-writing](https://github.com/wanchenxing/avoid-ai-writing): a catalogue of 56+
  patterns with a three-tier word table
- [sloplint](https://github.com/benjaminjackson/sloplint): a command-line linter for LLM prose tells
- The Vale style registry: proselint, write-good and alex
