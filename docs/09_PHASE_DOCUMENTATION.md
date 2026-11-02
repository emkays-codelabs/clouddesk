# MANDATORY PHASE-WISE DOCUMENTATION, SYSTEM DESIGN EVOLUTION, INFRASTRUCTURE DOCUMENTATION, AND INTERVIEW PREPARATION

> **Layout revised 2026-11-02, at the owner's instruction.** The four documents for a phase now sit together in one folder per phase, `internal/PhaseN/`, numbered in reading order. The earlier layout, one folder per category, is superseded. Nothing else in this specification has changed.

## 1. PRIMARY OBJECTIVE

During the development of this application, every phase and its associated subtasks will introduce, modify, or improve multiple code components, architectural decisions, infrastructure configurations, and system capabilities.

I require comprehensive documentation that explains what was implemented, why it was implemented, how the components work together, and how the system evolved throughout development.

These documents will serve four purposes:

1. **Codebase Understanding:** Enable me to explain the implemented code and application functionality to recruiters and interview boards, including non-technical participants.
2. **System Design Understanding:** Document how the application's architecture evolves from a simple design to the more advanced design implemented at the end of each phase.
3. **Infrastructure Understanding:** Explain Docker containers, networking, service dependencies, routing, communication, and deployment architecture.
4. **Interview Preparation:** Prepare me to answer technical and architectural questions about every phase of development.

These are mandatory project deliverables, not optional documentation tasks.

The documentation must be generated from the actual implementation, configuration, tests, and architectural decisions made during development.

**Never document a feature as implemented unless it actually exists in the codebase. Clearly distinguish implemented functionality, partially implemented functionality, planned functionality, and future recommendations.**

---

# 2. DOCUMENTATION DIRECTORY STRUCTURE

Maintain the following directory structure at the project root.

```text
project-root/
│
├── internal/
│   │
│   ├── Phase1/
│   │   ├── 01_CODEBASE_EXPLAINED.md
│   │   ├── 02_DESIGN_EVOLUTION.md
│   │   ├── 03_INFRA_EVOLUTION.md
│   │   └── 04_INTERVIEW_QNA.md
│   │
│   ├── Phase2/
│   │   ├── 01_CODEBASE_EXPLAINED.md
│   │   ├── 02_DESIGN_EVOLUTION.md
│   │   ├── 03_INFRA_EVOLUTION.md
│   │   └── 04_INTERVIEW_QNA.md
│   │
│   ├── Phase3/
│   │   └── ...
│   │
│   └── ...
```

### Directory rules

- Use `internal/` as the documentation root, unless the repository already establishes a different naming convention. If an alternative is necessary, document the reason and use it consistently.
- Create one folder for every phase, holding one separate document for each of the four documentation categories.
- Preserve all existing documentation.
- Update an existing phase document when that phase's implementation changes.
- Do not overwrite earlier phase documentation with information belonging exclusively to a later phase.
- Maintain consistent terminology, naming conventions, Markdown formatting, and diagram styles.
- Use relative links between related documents wherever practical.
- If a phase has multiple subtasks, document significant architectural changes at the subtask level within the corresponding phase document. Create additional subtask documents only when their complexity justifies separate documentation.

---

# 3. DOCUMENT 1: EXPLAINABLE CODEBASE DOCUMENTATION

## File naming convention

For Phase N:

`internal/PhaseN/01_CODEBASE_EXPLAINED.md`

Example:

`internal/Phase1/01_CODEBASE_EXPLAINED.md`

## 3.1 Purpose

Create an explanation of the actual code implemented during the phase.

I will use this document to explain the application to recruiters, hiring managers, and interview boards.

Some participants may not have a software engineering background.

Therefore, the document must explain the system in simple, natural language without losing technical accuracy.

The document must be understandable to someone who has basic computer knowledge but may not understand programming, APIs, databases, distributed systems, Docker, or AI architecture.

## 3.2 Mandatory contents

### A. Executive summary

Explain:

- What the phase accomplished.
- What problem the implementation solves.
- Why this phase was necessary.
- What capabilities were introduced.
- How the phase contributes to the overall application.
- What the application could do before this phase and what it can do afterward.

Begin with a simple explanation that I can deliver verbally during an interview.

### B. Business problem and solution

Describe:

1. The real-world problem being addressed.
2. The limitations of a basic or previous implementation.
3. The solution introduced in this phase.
4. How the solution benefits users or the business.
5. Why the chosen approach is appropriate.

Use relatable examples and analogies wherever they improve understanding.

### C. Application architecture in simple language

Explain the major components introduced or changed during the phase.

For each component, cover:

- Its name.
- Its purpose.
- The problem it solves.
- What information it receives.
- What work it performs.
- What information or result it produces.
- Which other components it communicates with.
- Why it is needed.
- What would happen if it were unavailable or removed.

Introduce technical terminology only after explaining its meaning in ordinary language.

For example:

Instead of saying, "The API gateway routes requests to downstream services," explain:

"The API gateway acts like a reception desk. It receives incoming requests and directs each request to the appropriate service. This gives the application one controlled entry point instead of requiring users to contact individual services directly."

Use the analogy to explain the concept, then clarify the actual technical implementation.

### D. Codebase structure and file-by-file explanation

Inspect the actual repository and document the important files and directories introduced, modified, or relied upon during this phase.

For each significant file, explain:

| Item | Required explanation |
|---|---|
| File path | Exact path relative to the project root |
| Responsibility | What the file does |
| Reason for existence | Why the file is needed |
| Main components | Important classes, functions, schemas, configurations, or constants |
| Inputs | What information the file receives |
| Processing | What happens inside the file |
| Outputs | What it returns, creates, or changes |
| Dependencies | Which other components it relies on |
| Execution point | When or how the file is used |
| Interview explanation | How to explain its purpose in simple language |

Include the important implementation details needed to understand the phase.

Do not list every file indiscriminately. Prioritize application logic, architecture, orchestration, data models, API endpoints, integrations, configuration, testing, security, and deployment-related changes.

However, do not omit a significant file simply because it is difficult to explain.

### E. End-to-end execution flow

Explain how the application works from the user's perspective.

Describe:

1. What initiates the operation.
2. Which component receives the request.
3. How the request moves through the system.
4. Which components process the request.
5. How data is retrieved, transformed, stored, or transmitted.
6. How errors are handled.
7. How the final response reaches the user.

Provide a numbered walkthrough of a realistic example.

Include a Mermaid sequence diagram when it helps explain the interactions.

### F. Technical concepts explained simply

Explain the relevant technical concepts introduced in this phase.

Depending on the actual implementation, these may include:

- API and HTTP request/response cycles.
- Backend and frontend responsibilities.
- Database operations and transactions.
- Authentication and authorization.
- Background processing and queues.
- Caching.
- AI model calls.
- Retrieval-Augmented Generation.
- Agent orchestration.
- State management.
- Docker containers and networking.
- Logging, metrics, and error handling.
- Automated testing.
- Deployment and configuration management.

Include only the concepts relevant to the implementation, while ensuring that important concepts are not overlooked.

### G. Design decisions and trade-offs

Explain:

- Why the selected architecture was chosen.
- What alternatives were considered or could reasonably have been considered.
- What advantages the implementation provides.
- What limitations remain.
- What trade-offs were accepted.
- How the design could evolve as the application grows.

Clearly distinguish actual historical decisions from retrospective recommendations.

### H. Error handling and failure scenarios

Explain what happens when important components fail.

Cover relevant scenarios such as:

- Invalid user input.
- API errors.
- Database connection failures.
- External service timeouts.
- Missing configuration.
- Authentication failures.
- Unexpected exceptions.
- Invalid AI-generated output.

Describe the actual behavior and identify any missing safeguards.

### I. Testing and verification

Document:

- Tests introduced or modified.
- What each significant test verifies.
- How to execute the tests.
- What the test results establish.
- What remains untested.
- Any relevant linting, formatting, type-checking, or security checks.

Do not claim that tests passed unless the results have been verified.

### J. Interview-ready explanation

Provide a ready-to-deliver explanation that I can speak during an interview.

Include:

1. A 30-second explanation of the phase.
2. A 2-minute explanation of the implementation.
3. A 5-minute explanation of the architecture and execution flow.
4. A simple explanation for a non-technical interviewer.
5. A more technical explanation for a software architect or engineering manager.

The explanations must accurately reflect the actual implementation.

Write these sections in natural spoken English, not as disconnected technical bullet points.

### K. Key takeaways and next-phase dependencies

Summarize:

- What was implemented.
- What I should understand before explaining this phase.
- Which architectural decisions are important.
- Which limitations remain.
- Which components will be extended or reused in later phases.

---

# 4. DOCUMENT 2: SYSTEM DESIGN EVOLUTION

## File naming convention

For Phase N:

`internal/PhaseN/02_DESIGN_EVOLUTION.md`

Example:

`internal/Phase1/02_DESIGN_EVOLUTION.md`

## 4.1 Purpose

Document how the application's system architecture evolved during the phase.

The document must explain the progression from the simplest reasonable design at the beginning of the phase to the final architecture actually implemented at its conclusion.

It must not simply describe the final architecture.

The objective is to understand the architectural journey: what existed initially, what was added, why the design changed, and what the final result achieved.

## 4.2 Mandatory contents

### A. Phase overview

Document:

- Phase objectives.
- Initial system state.
- Requirements addressed.
- Major architectural additions.
- Important design changes.
- Final system capabilities.

### B. Initial architecture

Describe the system as it existed at the beginning of the phase.

If this is the first phase, show the simplest reasonable design that satisfies the initial requirements.

If the phase extends an existing application, document the actual architecture inherited from the previous phase.

Include:

- Main components.
- External dependencies.
- Data stores.
- Request entry points.
- Communication paths.
- Major limitations.

Provide a Mermaid diagram showing the initial architecture.

### C. Intermediate architectural evolution

Document significant architectural changes in chronological or implementation order.

For each change, explain:

1. The original design.
2. The limitation or requirement that motivated the change.
3. The component or architectural pattern introduced.
4. How the change affects existing components.
5. The benefits and trade-offs.
6. Whether the change was completed and verified.

Provide intermediate Mermaid diagrams when they clarify substantial changes.

Avoid creating meaningless diagrams for trivial code edits.

### D. Final architecture

Document the architecture at the end of the phase.

Include, where applicable:

- Presentation layer.
- API or application layer.
- Business logic.
- Domain components.
- Orchestration.
- Data access.
- Databases and vector stores.
- External integrations.
- AI models and tools.
- Background workers.
- Observability.
- Security boundaries.
- Deployment components.

Explain the responsibilities and interactions of the components.

Include a Mermaid diagram representing the final architecture.

### E. End-to-end execution and data flow

Document the complete lifecycle of a representative request.

Show:

- Request initiation.
- Authentication and validation.
- Routing and orchestration.
- Business logic execution.
- Data access.
- External service calls.
- Response construction.
- Error propagation and recovery.

Use Mermaid sequence diagrams where useful.

### F. Architectural decisions and trade-offs

Document significant architectural decisions using the following structure:

| Field | Description |
|---|---|
| Decision | What was selected |
| Context | Why a decision was needed |
| Alternatives | Other reasonable approaches |
| Rationale | Why the selected approach was appropriate |
| Benefits | What the decision improves |
| Trade-offs | What it makes more difficult |
| Status | Implemented, partially implemented, or proposed |

### G. Architectural improvements

Explain the difference between the initial and final designs.

Cover:

- Separation of responsibilities.
- Modularity.
- Maintainability.
- Scalability.
- Performance.
- Reliability.
- Security.
- Testability.
- Extensibility.

Only claim improvements supported by the actual implementation or verified measurements.

### H. Limitations and future evolution

Document:

- Remaining architectural weaknesses.
- Known bottlenecks.
- Technical debt.
- Missing resilience mechanisms.
- Scalability constraints.
- Security gaps.
- Potential improvements for future phases.

Distinguish existing capabilities from recommendations.

### I. Phase completion summary

Include:

- Final architecture diagram.
- Major components introduced.
- Important design decisions.
- Verified outcomes.
- Outstanding work.
- Dependencies carried into the next phase.

## 4.3 Mermaid requirements

Use Mermaid diagrams that render in standard Markdown viewers supporting Mermaid.

Choose the diagram type according to its purpose:

- `flowchart`: component relationships and request flow.
- `sequenceDiagram`: runtime interactions.
- `classDiagram`: important object-oriented relationships.
- `stateDiagram-v2`: state transitions.
- `erDiagram`: database entities and relationships.

Label connections meaningfully.

Use subgraphs when they clarify logical boundaries, such as frontend, backend, data, external services, and infrastructure.

Diagrams must reflect the actual implementation, not an idealized architecture that does not exist.

---

# 5. DOCUMENT 3: INFRASTRUCTURE AND DOCKER DESIGN EVOLUTION

## File naming convention

For Phase N:

`internal/PhaseN/03_INFRA_EVOLUTION.md`

Example:

`internal/Phase1/03_INFRA_EVOLUTION.md`

## 5.1 Purpose

Explain how the application's infrastructure works and how its infrastructure architecture evolves throughout each phase.

The document must be understandable to someone who knows the purpose of an application but does not necessarily understand Docker, networking, containers, reverse proxies, or deployment infrastructure.

## 5.2 Mandatory contents

### A. Infrastructure overview

Explain:

- Where each major component runs.
- Which components run locally.
- Which components run in Docker containers.
- Which services are externally hosted.
- How the application is started.
- How components communicate.
- How configuration is supplied.
- How the application is stopped and restarted.

Document the actual development and deployment configurations separately when they differ.

### B. Initial infrastructure design

Describe the infrastructure at the beginning of the phase.

Include the initial container arrangement, services, dependencies, and communication paths.

Provide a Mermaid infrastructure diagram.

### C. Infrastructure evolution

Document the infrastructure changes introduced during the phase.

For every significant change, explain:

- What existed before.
- What was added, removed, or modified.
- Why the change was required.
- Which services were affected.
- How communication or routing changed.
- How the change was verified.

Provide intermediate diagrams when necessary.

### D. Docker and container explanation

For every significant container or service, document:

| Field | Explanation |
|---|---|
| Service name | Name in the Docker Compose configuration |
| Image or build | Image used or build context |
| Purpose | Why the service exists |
| Ports | Published and container ports, where applicable |
| Networks | Networks to which the service connects |
| Volumes | Persistent or mounted data |
| Environment | Important configuration variables, without exposing secrets |
| Dependencies | Services it requires |
| Health checks | Actual health-check configuration |
| Startup behavior | Relevant startup or readiness behavior |
| Failure behavior | What happens when the service is unavailable |

Use the actual Dockerfiles and Compose configurations as the source of truth.

### E. Docker networking

Explain:

- Docker network types used by the application.
- Network names and their purpose.
- Which services belong to each network.
- How containers resolve each other by service name.
- Which ports are exposed to the host.
- Which services are reachable only internally.
- How frontend-to-backend communication works.
- How backend-to-database communication works.
- How external APIs are reached.
- How DNS, port mapping, and network isolation affect the system.

Clarify the difference between:

1. A container's internal listening port.
2. A port published on the host.
3. A port used by another container on the Docker network.

Do not assume that `localhost` inside a container refers to the host machine or another container.

Explain the correct hostname and port for each actual communication path.

### F. Component wiring and routing

Document the routing path from the user's browser to the application.

Where applicable, explain:

- Browser to frontend.
- Frontend to backend API.
- Reverse proxy to application services.
- Backend to databases.
- Backend to external AI providers.
- Background workers to queues or data stores.
- Monitoring services to application metrics endpoints.

Describe routing in local development and production separately if their configurations differ.

Include a Mermaid diagram illustrating component wiring and routing.

### G. Docker Compose lifecycle

Explain the actual commands and configuration needed to:

- Build the required images.
- Start the services.
- Stop the services.
- Restart individual services.
- View logs.
- Inspect container status.
- Inspect network configuration.
- Check health status.
- Rebuild a changed service.
- Clean up resources safely.

Use commands appropriate to the repository's actual setup.

Explain destructive commands and their effects before recommending them.

### H. Environment variables and secrets

Document:

- Required environment variables.
- Their purpose.
- Which services consume them.
- Which values are safe defaults.
- Which values must be supplied by the developer or deployment environment.
- How secrets are managed.
- How configuration differs between development and production.

Never expose actual API keys, credentials, passwords, tokens, or other secrets in documentation.

Provide variable names and safe placeholders where appropriate.

### I. Persistent storage and data management

Explain:

- Named volumes.
- Bind mounts.
- Database persistence.
- Application file storage.
- Cache persistence, if relevant.
- Data initialization.
- Backup and restore procedures.
- The impact of removing containers versus removing persistent volumes.

Clearly identify any missing backup or recovery mechanisms.

### J. Health checks, startup order, and resilience

Explain:

- Service dependencies.
- Startup ordering.
- Health checks.
- Readiness versus process availability.
- Restart policies.
- Timeout behavior.
- Failure propagation.
- Recovery procedures.

Do not imply that a running container guarantees that its application is ready.

Document only mechanisms that actually exist, and identify recommended improvements separately.

### K. Observability and troubleshooting

Explain the actual logging, monitoring, and metrics setup.

Where applicable, cover:

- Application logs.
- Container logs.
- Health endpoints.
- Prometheus metrics.
- Grafana dashboards.
- Distributed tracing.
- Common network failures.
- Database connectivity problems.
- Configuration errors.
- Port conflicts.

Provide practical troubleshooting commands and explain what their output indicates.

### L. Final infrastructure architecture

Include a Mermaid diagram showing the final infrastructure design for the phase.

Identify:

- Containers.
- Native processes.
- Networks.
- Ports.
- Volumes.
- External dependencies.
- Routing paths.
- Monitoring components.

Include only components that exist in the actual configuration.

### M. Infrastructure verification

Document the checks used to establish that:

- Services start successfully.
- Required ports are reachable.
- Internal DNS resolution works.
- Application-to-database connectivity works.
- Health checks pass.
- Persistent storage behaves as expected.
- External integrations are configured correctly.

Distinguish verified results from assumptions and untested behavior.

---

# 6. DOCUMENT 4: PHASE-WISE INTERVIEW QUESTIONS AND ANSWERS

## File naming convention

For Phase N:

`internal/PhaseN/04_INTERVIEW_QNA.md`

Example:

`internal/Phase1/04_INTERVIEW_QNA.md`

## 6.1 Purpose

Create a comprehensive interview preparation document covering the implementation, architecture, infrastructure, engineering decisions, and lessons learned during the phase.

The goal is to help me confidently explain the project and defend its design decisions during interviews.

Questions must be derived from the actual phase implementation, not from a generic question bank alone.

## 6.2 Mandatory question categories

### Category A: Project overview

Include questions such as:

- What problem does this phase solve?
- What did you implement?
- Why was this phase necessary?
- What was the most important engineering challenge?
- What changed compared with the previous phase?
- What would you improve if you implemented it again?

### Category B: Codebase and implementation

Cover:

- Important modules and files.
- Responsibilities of individual components.
- Function and class design.
- Data models and validation.
- API contracts.
- Dependency management.
- Error handling.
- Configuration management.
- Testing strategies.
- Separation of concerns.

### Category C: System design and architecture

Cover:

- Architecture choices.
- Component responsibilities.
- Request and data flows.
- Design patterns.
- Dependency relationships.
- Architectural trade-offs.
- Scalability.
- Reliability.
- Performance.
- Extensibility.
- Alternative architectures.

### Category D: APIs and backend engineering

Include relevant questions about:

- API design.
- HTTP methods and status codes.
- Request validation.
- Authentication and authorization.
- Middleware.
- Database access.
- Transactions.
- Concurrency.
- Timeouts.
- Retries.
- Rate limiting.
- API versioning.

Only include topics relevant to the phase or clearly label them as potential extensions.

### Category E: Database and data engineering

Cover relevant topics such as:

- Schema design.
- Data relationships.
- Indexing.
- Query performance.
- Transactions.
- Connection management.
- Data validation.
- Migrations.
- Data consistency.
- Caching.
- Vector databases and embeddings, if applicable.

### Category F: Docker and infrastructure

Include questions about:

- Containers versus virtual machines.
- Dockerfiles.
- Docker Compose.
- Container networking.
- Port mapping.
- Volumes.
- Environment variables.
- Service discovery.
- Health checks.
- Startup dependencies.
- Logs.
- Troubleshooting.
- Development versus production environments.

### Category G: Security

Cover applicable topics such as:

- Authentication.
- Authorization.
- Secret management.
- Input validation.
- Injection risks.
- Network exposure.
- Dependency vulnerabilities.
- Data protection.
- Logging sensitive information.
- Secure deployment practices.

### Category H: Testing and quality assurance

Cover:

- Unit testing.
- Integration testing.
- End-to-end testing.
- Mocking.
- Test data.
- Failure scenarios.
- Regression testing.
- Coverage limitations.
- CI/CD checks.

### Category I: Performance, reliability, and scalability

Cover:

- Latency.
- Throughput.
- Resource consumption.
- Database bottlenecks.
- Concurrency.
- Caching.
- Retry strategies.
- Failure isolation.
- Horizontal scaling.
- Monitoring.
- Service-level objectives, where applicable.

### Category J: AI and agentic engineering

Include these topics only where they apply to the actual implementation.

Potential topics include:

- LLM integration.
- Prompt design.
- Retrieval-Augmented Generation.
- Embedding models.
- Vector search.
- Hybrid retrieval.
- Reranking.
- Hallucination mitigation.
- Agent orchestration.
- Tool calling.
- State management.
- Human-in-the-loop workflows.
- Evaluation metrics.
- Model latency and cost.
- Guardrails and output validation.

Questions must reflect the specific AI architecture actually implemented.

### Category K: Scenario-based questions

Include realistic engineering scenarios, such as:

- What happens if the database becomes unavailable?
- How would you investigate a slow API?
- How would you prevent duplicate processing?
- What happens if an external service times out?
- How would you add a new capability without changing unrelated components?
- How would you diagnose a Docker networking issue?
- How would you handle invalid or unexpected input?
- How would you scale the application to support more users?

Answers must explain both the current implementation and any proposed improvements.

### Category L: Design challenges and trade-offs

Include questions about:

- Why a particular library or framework was selected.
- Why an alternative was not used.
- What limitations exist.
- What assumptions were made.
- How the design could be improved.
- How the architecture would change under increased load.
- What technical debt remains.

### Category M: Behavioral and project ownership questions

Prepare answers for questions such as:

- What was your contribution to the project?
- What was the most difficult decision?
- What did you learn during this phase?
- What would you do differently?
- How did you verify the implementation?
- How would you explain the business value of the work?

Do not invent personal experiences, achievements, performance results, or decisions. Build answers from documented project evidence and leave placeholders where personal input is required.

## 6.3 Required answer format

Use the following format for each question.

### Q1. What problem does this component solve?

**Short answer:**

Provide a direct answer suitable for a quick interview response.

**Detailed explanation:**

Explain the technical reasoning and relevant implementation details.

**Simple analogy:**

Use an analogy when it genuinely improves understanding.

**Implementation reference:**

Identify the relevant source files, functions, classes, configuration, or tests.

**Follow-up questions:**

Include likely questions an interviewer may ask next.

**Common mistake to avoid:**

Explain any misleading or technically incorrect answer that should be avoided.

Not every question needs an elaborate analogy. Keep answers proportional to the complexity of the subject.

## 6.4 Answer quality requirements

- Answers must be technically accurate.
- Explain the implementation before discussing hypothetical improvements.
- Include concrete references to the codebase.
- Explain why a decision was made, not merely what was done.
- Clearly identify limitations and unresolved issues.
- Avoid generic answers that could apply to any project.
- Provide both concise interview responses and deeper technical explanations.
- Include follow-up questions for important architectural decisions.
- Never fabricate implementation details or claim unverified performance improvements.

## 6.5 Suggested difficulty levels

Organize the questions into:

1. Beginner: Fundamentals and basic project understanding.
2. Intermediate: Implementation details and engineering decisions.
3. Advanced: System design, failure handling, security, performance, and scalability.
4. Expert: Deep architectural trade-offs, alternatives, and production-readiness challenges.

Include questions relevant to the actual phase at each level.

The objective is comprehensive preparation, not an arbitrary question count.

---

# 7. MANDATORY DOCUMENTATION WORKFLOW

Documentation must be part of the development workflow itself.

It must not be postponed until all development phases are completed.

## Step 1: Inspect the current implementation

Before documenting a phase, inspect:

- Repository structure.
- Source files.
- Existing documentation.
- Configuration files.
- Dockerfiles and Docker Compose files.
- Environment variable definitions.
- Database schemas and migrations.
- API routes.
- Tests.
- Build and deployment scripts.
- Relevant changes introduced during the phase.

Use Git history and diffs when available to identify what changed during the phase.

If historical information is unavailable, clearly distinguish the inferred starting state from verified historical facts.

## Step 2: Identify the phase scope

Establish:

- The phase's objectives.
- The implementation completed.
- The components added or modified.
- The significant architectural decisions.
- The infrastructure changes.
- The tests and verification performed.
- The remaining limitations.

Do not assume that every file in the repository was created during the current phase.

## Step 3: Update all four documentation categories

Create or update the following files:

1. `internal/PhaseN/01_CODEBASE_EXPLAINED.md`
2. `internal/PhaseN/02_DESIGN_EVOLUTION.md`
3. `internal/PhaseN/03_INFRA_EVOLUTION.md`
4. `internal/PhaseN/04_INTERVIEW_QNA.md`

Each document must cover its own purpose without simply duplicating the other three.

Use consistent component names, architecture terminology, and file references across all documents.

## Step 4: Update documentation during subtasks

When a subtask introduces a significant new component, modifies an architectural boundary, changes networking, or alters an important execution flow, update the relevant documentation.

Do not wait until the entire phase is finished if doing so would lose important implementation details.

For substantial changes, include the intermediate design in the relevant system design or infrastructure evolution document.

At the end of the phase, consolidate these updates into a coherent phase-level explanation.

## Step 5: Validate the documentation

Verify that:

- Referenced files exist.
- Function and class names are correct.
- Diagrams match the implementation.
- API routes and service names are accurate.
- Docker ports and networks match the configuration.
- Environment variable names are correct.
- Commands are appropriate for the repository.
- Test results are supported by actual execution.
- Internal document links resolve correctly.
- No secrets have been included.
- Implemented features are not confused with planned features.
- Earlier phase documentation remains historically accurate.

If Mermaid rendering can be checked in the available environment, validate the diagrams. Otherwise, verify the syntax and disclose that rendering was not tested.

## Step 6: Report documentation completion

At the end of each phase, provide a concise completion report.

Include:

| Item | Status |
|---|---|
| Phase implementation reviewed | Completed / Partial / Blocked |
| Codebase explanation | Completed / Partial / Blocked |
| System design evolution | Completed / Partial / Blocked |
| Infrastructure evolution | Completed / Partial / Blocked |
| Interview Q&A | Completed / Partial / Blocked |
| Mermaid diagrams | Verified / Syntax-checked / Not verified |
| Documentation links | Verified / Not verified |
| Tests and validation | Actual results |
| Known documentation gaps | List outstanding items |

Do not report a deliverable as complete if it has not been created and checked.

---

# 8. DOCUMENTATION QUALITY STANDARDS

All four documentation categories must follow these standards.

## Accuracy

Document the actual implementation.

Do not invent components, historical decisions, architectural changes, test results, or deployment configurations.

## Completeness

Cover every significant component and design decision introduced or modified during the phase.

If a requirement cannot be verified, state that explicitly.

## Accessibility

The codebase explanation must be understandable to a non-technical audience.

The system design and infrastructure documents must remain technically detailed enough for engineering interviews.

## Traceability

Where possible, reference:

- Source file paths.
- Relevant classes and functions.
- Configuration files.
- Tests.
- API routes.
- Docker Compose services.
- Database migrations.
- Related phase documents.

## Historical integrity

Keep each phase's documentation aligned with the system as it existed at that point in development.

Later improvements must not be presented as if they existed in an earlier phase.

## Maintainability

Use consistent headings, Markdown tables, Mermaid diagrams, and relative links.

Update documents when the implementation changes.

Avoid duplicated explanations that can become inconsistent.

## Confidentiality

Never include secrets, credentials, private keys, access tokens, or sensitive production data.

Use safe placeholders for configuration examples.

---

# 9. DEFINITION OF DONE FOR EVERY PHASE

A phase is not considered fully documented until all of the following conditions are met:

- The implementation has been reviewed.
- The codebase explanation document exists.
- The system design evolution document exists.
- The infrastructure design evolution document exists.
- The interview preparation document exists.
- Important components and their interactions are explained.
- The initial and final system designs are documented.
- Significant intermediate architectural changes are documented.
- Infrastructure networking and routing are explained where applicable.
- Relevant Mermaid diagrams are included.
- Interview questions and answers reflect the actual implementation.
- Relevant source files and configuration are referenced.
- Validation results and known limitations are documented.
- Documentation is consistent across all four files.
- Any incomplete deliverable is explicitly reported.

**Development completion and documentation completion are separate requirements. Both must be tracked.**

---

# 10. FINAL INSTRUCTION TO THE CODING AGENT

Apply these requirements to the existing application and all subsequent development phases.

Do not modify application code merely to satisfy a documentation requirement.

Do not create speculative documentation before inspecting the repository.

First understand the actual implementation, then document it accurately.

Preserve existing project conventions unless a change is justified.

After completing each phase, ensure that all four documentation deliverables have been created or updated and validated.

When a subtask introduces a meaningful architectural or infrastructure change, capture that evolution in the relevant document.

At the end of every phase, summarize the implementation, documentation deliverables, verification performed, and outstanding gaps.

The ultimate objective is to maintain a complete, historically accurate, technically reliable, and interview-ready record of the application's evolution.

I must be able to explain not only what the application does, but also how it works, why it was designed that way, how its infrastructure operates, what engineering trade-offs were made, and how the architecture evolved from the beginning of the phase to its final implementation.
