---
description: Automatically synthesize project logs, verify show-case assets, and push updated documentation to GitHub.
---

# Publish Showcase Workflow

1. Read the current contents of `retrospective.md`, `walkthrough.md`, and `implementation_plan.md`.
2. Synthesize these files to update the `README.md` with the newest version baseline, SRE guardrails, and metrics.
3. **Verify Documentation Assets (Dual-Presentation Mandate):**
   - Confirm that the recruiter-facing showcase PNG (`docs/assets/architecture_diagram.png`) is referenced at the top of `README.md`.
   - Confirm that the technical Mermaid diagram is present in the flow/architecture section.
4. Show the proposed changes to the user for approval.
5. Once approved, stage the files:
   - Run `git add README.md retrospective.md walkthrough.md docs/assets/architecture_diagram.png`
6. Commit the changes:
   - Run `git commit -m "docs: sync v1.0.0 showcase documentation and SRE assets"`
7. Push to the main GitHub repository:
   - Run `git push origin main`
8. Confirm to the user that the showcase and SRE metrics are live on GitHub.