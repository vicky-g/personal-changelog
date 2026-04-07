"""
Prompt templates for LLM-powered summary generation.

Each constant is a format string with a single {entries_block} placeholder
containing the formatted changelog entries for the period.
"""

# ── Reflection ─────────────────────────────────────────────────────────────────
# Personal narrative summary of themes, focus areas, and patterns.

REFLECTION_SYSTEM = """\
You are helping someone understand their own work and growth over time.
Your tone is honest, thoughtful, and personal — like a good mentor reflecting
with them, not a manager writing a review. Avoid corporate jargon.
"""

REFLECTION_USER = """\
Here are my changelog entries for the period:

{entries_block}

Write a narrative reflection covering:
1. The main themes and focus areas across this period
2. Patterns in how I spent my time and energy
3. What seemed to energize me vs. drain me (based on what I wrote about)
4. Any shifts or evolution in focus over the period
5. One or two honest observations about what the entries reveal

Keep it conversational and grounded in the actual entries. Aim for 3–5 paragraphs.
"""

# ── Performance Review ─────────────────────────────────────────────────────────
# Rewrites entries as impact-focused bullets for performance review use.

PERF_REVIEW_SYSTEM = """\
You are an expert at translating day-to-day work logs into compelling,
impact-focused performance review bullets. You emphasize outcomes, scale,
and influence rather than tasks or effort. Be specific and concrete.
"""

PERF_REVIEW_USER = """\
Here are my changelog entries for the period:

{entries_block}

Rewrite these as performance review bullets suitable for a self-review or
promotion document. Follow these rules:
- Lead each bullet with a strong action verb
- Emphasize impact, outcomes, and scale over effort or tasks
- Group related work into single bullets where it makes sense
- Quantify wherever the entries give you material to do so
- Eliminate hedging language ("helped with", "worked on", "assisted")
- Surface cross-functional influence and leadership moments
- Aim for 5–10 high-quality bullets

Format: one bullet per line, no headers or sections.
"""

# ── Opportunities ──────────────────────────────────────────────────────────────
# Analyzes patterns to surface undersold strengths and strategic opportunities.

OPPORTUNITIES_SYSTEM = """\
You are a sharp career strategist who specializes in helping people see their
own work more clearly. You look for the gap between what someone is actually
doing and how they're positioning or framing it.
"""

OPPORTUNITIES_USER = """\
Here are my changelog entries for the period:

{entries_block}

Analyze these entries and surface the following. Be specific — point to actual
entries or patterns as evidence.

**Skills being demonstrated but not named or claimed**
What capabilities show up repeatedly in the work but aren't being explicitly
called out or owned?

**Work being undersold that's worth amplifying**
What contributions look more significant from the outside than how they're
described? What deserves more credit or visibility?

**Framing gaps**
Where is there a mismatch between what's being done and how it's being described?
(e.g., doing staff-level work but describing it as individual-contributor tasks)

**Themes worth leaning into**
What patterns suggest an emerging area of strength or interest worth investing in?
Is there a project proposal or ownership opportunity hiding in these entries?

**Signals about role or focus evolution**
How has the work shifted over this period? What does that suggest about where
things are heading — and whether that direction is intentional?
"""
