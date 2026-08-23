---
name: feedback-platform-access
description: User grants full permission to access and evaluate the platform (localhost:8000) after every update
metadata:
  type: feedback
---

After each update, always visit the platform via curl/Bash to verify data quality, endpoint correctness, and that the feature works end-to-end before reporting completion.

**Why:** User explicitly granted full permission to do this and expects proactive evaluation, not just "built successfully" reports.

**How to apply:** After every backend or frontend change, run curl checks against localhost:8000 API endpoints and report concrete numbers/status.
