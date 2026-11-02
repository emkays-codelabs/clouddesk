---
name: test
description: Write or run targeted pytest tests and return a digest only. Use for test work, not production code.
context: fork
agent: test-engineer
background: false
argument-hint: "[test path, or what to cover]"
---

Test this: $ARGUMENTS

Run the narrowest target first, then the whole suite. Return pass or fail and the digest only.
