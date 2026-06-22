# Capstone Project Deep Dive: M&A Swarm Security and Evaluation Report

## 1. Executive Summary
Merging and Acquisition (M&A) operations involve processing highly confidential, multi-million dollar corporate assets. Deploying an autonomous Multi-Agent Swarm for due diligence introduces unprecedented risks: code generation engine escapes, credential leakage, prompt injection attacks, and "Denial of Wallet" infinite loop vulnerabilities. Furthermore, because M&A objectives are inherently open-ended and underspecified, traditional unit tests cannot verify if the swarm has accurately captured the investor's strategic intent.

To operationalize the M&A Due Diligence Swarm in a production environment, we establish a two-pronged governance framework:
1. **The Security Harness**: A Context-as-a-Perimeter safety envelope that enforces continuous **Effective Trust** across all runtime boundaries.
2. **The Evaluation Suite**: A multi-dimensional, "Glass Box" verification system that measures intent satisfaction, visual rendering correctness, trajectory path quality, and self-repair behavior.

---

## 2. The 7-Pillar Security Harness for M&A Swarms

Traditional Identity-as-a-Perimeter models (like role-based access control) fail when an autonomous agent is hijacked via prompt injection. We deploy a layered, defense-in-depth architecture structured across seven distinct security pillars:

### Pillar 1: Infrastructure & Networking
- **Ephemeral Sandbox Isolation**: The *Financial Auditor Agent* runs untrusted Python scripts (pandas, openpyxl) to parse corporate financials. This execution is confined to ephemeral, kernel-level sandboxes (using gVisor) that completely reset state between runs, preventing container escape attacks.
- **Strict Egress Governance**: External network egress is blocked by default. The *Brand Sentiment Agent* is restricted to fetching external news and filings strictly through pre-sanitized proxies and offline data caches, neutralizing data exfiltration channels.

### Pillar 2: Data Security & Privacy
- **Vector Database Tenant Partitioning**: The *Legal Agent* utilizes Retrieval-Augmented Generation (RAG) over sensitive contracts. To prevent **Cross-Tenant Vector Poisoning**, vector collections enforce cryptographic tenant partitioning.
- **Zero-Retention API Policies**: All calls to remote LLMs (e.g. Gemini Enterprise) are configured with zero-data-retention agreements, ensuring private financial statements are never used for model training.

### Pillar 3: Model & Prompt Attestation
- Prompts, instructions, and system configuration files are treated as source code. They are stored as cryptographically signed artifacts to prevent unauthorized modification or local tampering.

### Pillar 4: Application & Runtime Gating
- **LLM Firewalls**: A runtime firewall intercepts inputs to the Orchestrator, dynamically blocking adversarial payloads and jailbreak attempts.
- **Centralized Agent Gateway**: Enforces **Contextual Authorization** to verify that any tool call requested by a sub-agent perfectly matches the Orchestrator's original delegated intent.

### Pillar 5: Identity and Access Management (IAM)
- **SPIFFE Agentic Identities**: Every agent runs under a unique, cryptographically verifiable identity (SPIFFE ID), distinguishing agentic actions from direct human modifications in audit logs.
- **Just-In-Time (JIT) Downscoping**: Agents receive hyper-restricted, short-lived tokens scoped to specific folders or databases (Zero Ambient Authority), expiring the millisecond the task concludes.
- **The "Vibe Diff" Review**: Before executing high-stakes tool calls (e.g., writing a final purchase recommendation), an Evaluator Quorum translates generated code into plain English. The human investor must provide physical cryptographic MFA consent (via hardware key) to authorize the transaction.

### Pillar 6: Observability & SecOps Triad
We run a parallel, autonomous security triad monitoring the swarm's state:
- **Red Team (Agent Attacker)**: Proactively injects semantic jailbreaks and poisoned context to stress-test agent boundaries.
- **Blue Team (Agent Defender)**: Uses **Agent Behavioral Analytics (ABA)** to monitor the dynamic Runtime Agent Bill of Materials (AgBOM), instantly flagging abnormal tool usage or intent drift.
- **Green Team (Agent Fixer)**: Initiates stateful quarantines when anomalies are detected, freezing short-term memory for analysis and auto-refactoring insecure agent scripts on the fly.

### Pillar 7: Governance & Compliance
- Builds immutable, cryptographically signed audit trails tracing every recommendation back to a specific model step, data source, and human approval, ensuring compliance with the EU AI Act and standard regulatory due diligence requirements.

---

## 3. Context Hygiene & Policy Gating

In an M&A swarm, context pollution leads to hallucinated risks or missed liabilities. We implement the following runtime gating flow:

```
                  Raw User Prompt / Context Files
                                ↓
                 [Context Hygiene & Sanitization]
                  • Dynamic ContextResolver
                  • Zero-width character scanning
                                ↓
                  [Tool Policy Engine Middleware]
                                ↓
                    [Hybrid Policy Server]
                    ├── Structural Gating (Allowlists)
                    └── Semantic Gating (Intent Check)
                                ↓
                    Safe Agent Execution Loop
```

- **Dynamic ContextResolver**: Automatically strips noisy boilerplate, zero-width Unicode homoglyphs (used in repository poisoning), and out-of-scope files from the prompt context, protecting the working memory from attention dilution.
- **Structural Gating**: Validates paths, file types, and tool parameters against a rigid structural schema before execution.
- **Semantic Gating**: Uses a semantic similarity check to ensure that the task goals generated by the agents remain strictly aligned with the original due diligence scope.

---

## 4. Multi-Dimensional Evaluation Suite

Evaluating an M&A due diligence agent is fundamentally different from verifying standard software because there is no rigid specification. The evaluation suite is designed around seven distinct dimensions:

| Dimension | Metric / Target | Verification Method |
| :--- | :--- | :--- |
| **1. Intent Satisfaction** | Strategic alignment with unstated user intent | **LLM-as-a-Judge**: Autonomously derives acceptance criteria from the session prefix and scores outcomes. |
| **2. Functional Correctness** | Syntactic correctness and execution stability | **CI Pipeline**: Automated build checks, linters (mypy, eslint), and pytest test execution. |
| **3. Visual Correctness** | Interactive dashboard layout and styling | **Browser Testing**: Playwright scripts execute UI workflows with multimodal screenshot verification. |
| **4. Cost & Efficiency** | Token consumption and API runtime overhead | **OTel Tracing**: Span-level measurement of token latencies and total execution costs. |
| **5. Code Quality** | Coding idioms, conventions, and security best practices | **Static Scanners**: Codeql, Semgrep, and SCA scanners verifying dependency signatures. |
| **6. Trajectory Quality** | Coherence of plan execution and tool routing | **Trace Replay**: Graph-based analysis of the path taken by the orchestrator. |
| **7. Self-Repair Behavior** | Recovery rate from compile/runtime test failures | **Drift Monitoring**: Evaluates whether the agent corrects errors or enters computational resource loops. |

### Mining User Corrections
Every manual correction (e.g. "Ignore the pending zoning lawsuit, focus on corporate debt") is captured, vectorized using text embeddings, and clustered into prioritised failure modes. This creates a feedback loop that highlights systematic gaps in the swarm's domain expertise.

---

## 5. Kaggle SAE and Zero-Setup Calibration

To rigorously benchmark the cognitive capabilities of our agents under pressurized conditions, we integrate the **Kaggle Standardised Agent Exams (SAE)**.
- **Zero-Setup Execution**: Deployed via a specialized `SKILL.md` hook. The agent registers with the Kaggle platform, retrieves multi-step business evaluation tasks, executes them in its local isolated container, and publishes scores directly to the Kaggle leaderboard.
- **Overfitting Trade-off**: Standardized benchmarks calibrate raw reasoning under pressure, but do not guarantee aesthetic or domain alignment. SAE is used as a gating mechanism for cognitive capabilities, supplemented by custom M&A simulation test cases.

---

## 6. Codebase Implementation Blueprint

To deploy these systems, we propose the following workspace additions:

```text
ma-due-diligence-swarm/
├── security/                   # Security Harness Module
│   ├── sandbox.py              # Ephemeral sandbox and subprocess isolation
│   ├── policy_engine.py        # ToolPolicyEngine, ContextResolver, PolicyServer
│   └── identity.py             # SPIFFE ID mapping & ephemeral JIT tokens
│
├── eval/                       # Evaluation Suite Module
│   ├── intent_judge.py         # LLM-as-a-judge session-prefix criteria scoring
│   ├── visual_eval.py          # Playwright test harness & screenshot analyzer
│   └── convergence.py          # OpenTelemetry tracing, cost logs, ABA tracker
│
└── tests/                      # Automated Verification
    ├── test_security.py        # pytest suite for sandboxing & policy gating
    └── test_eval.py            # pytest suite for judge accuracy & metrics
```

### Verification Pipeline
When a developer or agent proposes an update to the swarm logic, the CI/CD pipeline triggers the following validation:
1. **SCA & Dependency Validation**: Checks the AgBOM and SBOM for unverified libraries, neutralizing slopsquatting vectors.
2. **Deterministic Rules Scan**: Ensures all files map to the project file-tree allowlist.
3. **Intent Judge Gate**: Re-plays historical M&A due diligence traces to verify that intent satisfaction scores do not degrade.
