# 🛡️ TeamEngine v5.0 — TEAM RULES Manifest

1.  **LIFO Stacking (Last-In, First-Out)**: Agent runs the newest high-priority task before continuing previous work.
2.  **5-Fail Skip Rule**: If an agent hits the same error 5 times, it MUST stop, log it in the `error_registry.md`, and skip the task or escalate to `/pol`.
3.  **Phase Gates (Bramki)**: No agent can advance to Phase N+1 until Phase N meets its DoD.
4.  **Zero-Knowledge Secrets**: No credentials in prompts. Use SmartMyVault.
5.  **Farm & Scout**: Operations are coordinated locally, invisible to git (`.agents/` and `TeamEngine/` are ignored).
