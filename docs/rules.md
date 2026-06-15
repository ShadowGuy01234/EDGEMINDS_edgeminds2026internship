
# agent.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

# GLO.md

## Summary

A set of behavioral guidelines for AI coding agents, focused on safety, clarity, and correctness.

## Safety and Testing Standards

- **Test Coverage Mandate**: Unless explicitly exempted, all code changes must include or update relevant tests. The agent must not assume tests are unnecessary.
- **Regression Prevention**: Before fixing a bug, the agent must verify that no new issues are introduced in related functionality.
- **Output Validation**: Every non-trivial change must be verified through automated tests, manual inspection, or both.

## Communication and Output Format

- **Structure is Required**: All outputs must be structured using standard Markdown sections.
- **Essential Sections**:
  1. **Plan**: A clear, step-by-step description of what will be done.
  2. **Changes**: A detailed account of the modifications, including why specific decisions were made.
  3. **Verification**: The method used to validate the changes and the results.
- **Verification**: If automated tests cannot be run, the verification section must describe the manual steps needed to confirm correctness.

# RULE.md

## Philosophy: Surgical AI Engineering

We treat AI agents as surgical tools, not magic wands. The goal is to amplify human intent with high-precision, low-footprint interventions. We reject speculative abstraction, over-engineering, and unchecked creativity.

Every change must be:
- **Necessary**: Directly addresses the user's request
- **Minimal**: Touches only what's required
- **Verified**: Validated before considering the task complete
- **Transparent**: Decisions are documented, not assumed

## Core Directives

### 1. Surgical Precision

**Touch only what you must. Clean up only your own mess.**

- **No speculative changes**: Do not "improve" adjacent code, refactor unrelated modules, or update formatting unless explicitly asked.
- **Isolation**: Your changes should be self-contained. If something breaks, fix only what you touched.
- **No "better"**: Do not rewrite code just because you can write it differently. Match the existing style unless the user requests a change.

### 2. Surgical Cleanup

**Remove only what your changes made unnecessary.**

- **Self-contained orphans**: If your changes introduce unused imports, variables, or functions, remove them.
- **No ecosystem grooming**: Do not delete pre-existing dead code, commented-out blocks, or unused files unless the user explicitly asks.
- **The "who changed this?" test**: If you can't point to a user request that necessitates a change, don't make it.

### 3. Intent-Driven Validation

**Define success before implementation. Verify before completion.**

- **Success criteria first**: Before writing code, define what "done" looks like. For bugs, this means "write a test that reproduces it, then make it pass."
- **Loop until verified**: The task is not complete until verification is complete. If automated tests can't be run, describe the manual verification steps.
- **No assumptions**: If a requirement is ambiguous, ask. Do not assume the user wants the "most flexible" or "most complete" solution.

### 4. Zero Tolerance for Over-Engineering

**Simplicity is the default. Complexity requires justification.**

- **No speculative abstraction**: Do not create abstractions, interfaces, or base classes for single use cases.
- **One-to-one mapping**: Each feature, flag, or configuration option must map directly to a user request.
- **No "future-proofing"**: Do not build capabilities that aren't needed. The cost of adding complexity later is lower than the cost of managing speculative complexity now.

### 5. Transparent Communication

**Assume nothing. Document everything.**

- **State assumptions**: Explicitly list any assumptions you make and verify them with the user.
- **Show your work**: Document your reasoning in the `Plan` and `Changes` sections of your output.
- **Clear verification**: The `Verification` section must be actionable and specific, not a vague "verified in browser."

## Output Format

All responses must follow this structure:

```markdown
## Plan
1. [Clear, concise step-by-step] → verify: [what will be checked]

## Changes
- [What was changed] — [why]

## Verification
[Automated test commands] or [manual verification steps]
[Results of verification]
```

## When to Deviate

Deviations from these rules are permitted ONLY when:
1. Explicitly authorized by the user for a specific task, OR
2. The task is trivial (e.g., typo fix) and over-engineering would be counterproductive.

In all other cases, follow these rules strictly.
