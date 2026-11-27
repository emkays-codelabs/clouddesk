# CloudDesk glossary: abbreviations and labels

Every abbreviation used in this repository's documents, written out. The documents themselves write an abbreviation in full the first time it appears in a file, with the abbreviation in brackets; this page is the one place to look one up. Code, file names, HTTP methods and product names (for example Next.js, LangGraph, Qdrant) are not abbreviations and are not listed.

## Abbreviations

| Abbreviation | Meaning |
|---|---|
| ACM | AWS Certificate Manager |
| ACR | Azure Container Registry |
| ACSRP | Autonomous Customer Support and Resolution Platform |
| ADR | Architecture decision record |
| AI | Artificial intelligence |
| AKS | Azure Kubernetes Service |
| ALB | Application Load Balancer |
| API | Application programming interface |
| ASGI | Asynchronous Server Gateway Interface |
| AWS | Amazon Web Services |
| BO | Business objective |
| BRD | Business requirements document |
| CDN | Content delivery network |
| CI | Continuous integration |
| CLI | Command-line interface |
| CMEK | Customer-managed encryption keys |
| CORS | Cross-Origin Resource Sharing |
| CPU | Central processing unit |
| CRM | Customer relationship management |
| CRUD | Create, read, update and delete |
| CSAT | Customer satisfaction score |
| CSI | Container Storage Interface |
| CSP | Content Security Policy |
| CSRF | Cross-site request forgery |
| CSS | Cascading Style Sheets |
| CSV | Comma-separated values |
| DB | Database |
| DDL | Data definition language |
| DLQ | Dead-letter queue |
| DNS | Domain Name System |
| DOM | Document Object Model |
| DR | Disaster recovery |
| DRY | Don't repeat yourself |
| E2E | End-to-end |
| ECR | Elastic Container Registry |
| ECS | Elastic Container Service |
| EKS | Elastic Kubernetes Service |
| ETL | Extract, transform and load |
| FAQ | Frequently asked questions |
| FR | Functional requirement |
| FRT | First response time |
| FS | File system |
| GCP | Google Cloud Platform |
| GCS | Google Cloud Storage |
| GDPR | General Data Protection Regulation |
| GKE | Google Kubernetes Engine |
| HA | High availability |
| HITL | Human in the loop |
| HLD | High-level design |
| HMAC | Hash-based message authentication code |
| HPA | Horizontal Pod Autoscaler |
| HS256 | HMAC with SHA-256 |
| HTML | Hypertext Markup Language |
| HTTP | Hypertext Transfer Protocol |
| HTTPS | Hypertext Transfer Protocol Secure |
| IaC | Infrastructure as code |
| IAM | Identity and access management |
| ID | Identifier |
| IDE | Integrated development environment |
| INR | Indian rupees |
| IP | Internet Protocol |
| IRSA | IAM Roles for Service Accounts |
| JSON | JavaScript Object Notation |
| JSONB | JSON binary |
| JWKS | JSON Web Key Set |
| JWT | JSON Web Token |
| KB | Knowledge base |
| KEDA | Kubernetes Event-driven Autoscaling |
| KMS | Key Management Service |
| KPI | Key performance indicator |
| LB | Load balancer |
| LLD | Low-level design |
| LLM | Large language model |
| MCP | Model Context Protocol |
| MFA | Multi-factor authentication |
| MIME | Multipurpose Internet Mail Extensions |
| ML | Machine learning |
| MRR | Monthly recurring revenue |
| MTTR | Mean time to resolution |
| MVP | Minimum viable product |
| NAT | Network address translation |
| NFR | Non-functional requirement |
| NLP | Natural language processing |
| OAuth | Open Authorization |
| OCR | Optical character recognition |
| OIDC | OpenID Connect |
| ORM | Object-relational mapper |
| OS | Operating system |
| OTP | One-time password |
| OWASP | Open Worldwide Application Security Project |
| P95 | 95th percentile |
| PDF | Portable Document Format |
| PID | Process identifier |
| PII | Personally identifiable information |
| PITR | Point-in-time recovery |
| PKCE | Proof Key for Code Exchange |
| PR | Pull request |
| PRD | Product requirements document |
| QA | Quality assurance |
| RAG | Retrieval-augmented generation |
| RAM | Random-access memory |
| RBAC | Role-based access control |
| RCA | Root cause analysis |
| RDS | Relational Database Service |
| REST | Representational State Transfer |
| RFC | Request for Comments |
| RLS | Row-level security |
| RPO | Recovery point objective |
| RPS | Requests per second |
| RRF | Reciprocal rank fusion |
| RS256 | RSA signature with SHA-256 |
| RTO | Recovery time objective |
| S3 | Simple Storage Service |
| SaaS | Software as a service |
| SAML | Security Assertion Markup Language |
| SBOM | Software bill of materials |
| SDK | Software development kit |
| SES | Simple Email Service |
| SHA | Secure Hash Algorithm |
| SLA | Service level agreement |
| SLO | Service level objective |
| SMTP | Simple Mail Transfer Protocol |
| SOC | System and Organization Controls |
| SPA | Single-page application |
| SQL | Structured Query Language |
| SQS | Simple Queue Service |
| SRE | Site reliability engineering |
| SSE | Server-sent events |
| SSH | Secure Shell |
| SSL | Secure Sockets Layer |
| SSO | Single sign-on |
| SVG | Scalable Vector Graphics |
| TCP | Transmission Control Protocol |
| TDD | Test-driven development |
| TLS | Transport Layer Security |
| TTL | Time to live |
| UI | User interface |
| URL | Uniform resource locator |
| USD | United States dollars |
| UTC | Coordinated Universal Time |
| UUID | Universally unique identifier |
| UX | User experience |
| VPC | Virtual private cloud |
| WAF | Web application firewall |
| WCAG | Web Content Accessibility Guidelines |
| WS | WebSocket |
| YAML | YAML Ain't Markup Language |

## Label schemes used in the requirement, decision and task tables

| Label | Meaning |
|---|---|
| F1 to F14 | Functional requirement of this project (`CLAUDE.md` section 3) |
| N1 to N8 | Non-functional requirement of this project (`CLAUDE.md` section 3) |
| FR-01 to FR-42 | Functional requirement in the upstream product requirements document |
| NFR-01 to NFR-16 | Non-functional requirement in the upstream product requirements document |
| BO-1 to BO-7 | Business objective in the upstream business requirements document |
| D1 to D6 | Open or settled design decision (`CLAUDE.md` section 20 and `docs/adr/`) |
| P1-1 to P14-5 | Phase number and task number in `TASKS.md` (phase, then task within the phase) |
| CD-1001 to CD-1013 | The 13 demo tickets in `sample_data/tickets.json` |
| J1 to J5 | User journey in the upstream product requirements document |
| M1 to M4 | Mermaid diagram numbers in `docs/design/05_ARCHITECTURE.md` |
| ADR-0001 to ADR-0012 | Architecture decision record number in `docs/adr/` |

## Plain words used instead of short forms

The documents write "for example" rather than "e.g.", "that is" rather than "i.e.", "versus" rather than "vs", "repository" rather than "repo", "configuration" rather than "config", "environment" rather than "env", "specification" rather than "spec" and "infrastructure" rather than "infra". Environment names such as `dev`, `staging` and `prod` are literal names in file paths and variable files, so they stay as written.
