import Link from "next/link";
import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Brain,
  Check,
  CheckCircle2,
  Cloud,
  Compass,
  Cpu,
  Database,
  FileSearch,
  Gauge,
  Globe,
  Inbox,
  KeyRound,
  Layers,
  LayoutDashboard,
  Lightbulb,
  Lock,
  Mail,
  MemoryStick,
  MessageSquareText,
  Play,
  Radar,
  ScrollText,
  Search,
  Server,
  ShieldAlert,
  ShieldCheck,
  Siren,
  Sparkles,
  Stethoscope,
  Ticket,
  UserCheck,
  UserRound,
  Workflow,
  Wrench,
  type LucideIcon,
} from "lucide-react";
import { LandingEffects, MobileMenuButton } from "@/components/landing/LandingEffects";
import { ScrollToTop } from "@/components/ui/ScrollToTop";
import "./landing.css";

export const metadata = {
  title: "CloudDesk — Resolve Beyond the Ticket",
  description:
    "CloudDesk — autonomous customer support and resolution platform, engineered by Saffronyx.",
};

const WORKFLOW: ReadonlyArray<readonly [string, string, string, LucideIcon]> = [
  ["01 / INTAKE", "Understand", "Extract intent, context and issue signals.", Inbox],
  ["02 / TRIAGE", "Classify", "Category, severity and risk assessment.", Compass],
  ["03 / CONTEXT", "Investigate", "Customer, subscription and history.", UserRound],
  ["04 / EVIDENCE", "Retrieve", "Knowledge articles and similar cases.", BookOpen],
  ["05 / DIAGNOSIS", "Troubleshoot", "Probable causes and guided steps.", Stethoscope],
  ["06 / DECISION", "Decide", "Policy, risk and approval boundaries.", Gauge],
  ["07 / PLAN", "Resolve", "Grounded plan and customer reply.", Lightbulb],
  ["08 / EXECUTION", "Act", "Permissioned, verified tool actions.", Wrench],
  ["09 / SAFETY", "Escalate", "Route sensitive cases to specialists.", Siren],
  ["10 / MEMORY", "Remember", "Capture safe, useful resolution context.", Brain],
];

const AGENTS: ReadonlyArray<readonly [LucideIcon, string, string, string, readonly string[], string]> = [
  [Compass, "Support Supervisor", "Coordinator", "Understands the issue, classifies intent, assesses severity and keeps the workflow aligned.", ["Classification & severity", "Policy-aware routing", "Injection detection"], "#059669"],
  [UserRound, "Customer Agent", "Context", "Builds a contextual picture of the customer, their account and their support history.", ["Customer profile", "Subscription context", "Previous ticket history"], "#0d9488"],
  [Search, "Knowledge Agent", "Evidence", "Finds relevant evidence through semantic and keyword retrieval with ranking.", ["Hybrid retrieval", "Source citations", "Similar resolved cases"], "#0891b2"],
  [Stethoscope, "Troubleshooting Agent", "Diagnosis", "Turns evidence into likely causes and practical, numbered diagnostic steps.", ["Cause analysis", "Playbook enrichment", "Service-status checks"], "#d97706"],
  [Sparkles, "Resolution Agent", "Planner", "Creates a grounded resolution plan, customer response and deterministic actions.", ["Reply drafting", "Action planning", "Output validation"], "#16a34a"],
  [Siren, "Escalation Agent", "Safety net", "Recognizes policy-sensitive cases and directs them to the right human team.", ["Security & data-loss cases", "Disputes & deletion", "Confidence-based handoff"], "#e11d48"],
];

const TRUST: ReadonlyArray<readonly [LucideIcon, string, string]> = [
  [UserCheck, "Human approval", "Refunds, account changes and setting resets wait for an authorised agent."],
  [Gauge, "Risk classification", "Every plan is scored low, medium or high before anything runs."],
  [Lock, "Permission boundaries", "Tools run only through the registry, with roles enforced on every route."],
  [Siren, "Safe escalation", "Security, data-loss, dispute and deletion cases go to a named human team."],
  [ScrollText, "Audit trail", "Every node, tool call and decision is recorded and inspectable."],
];

type Cap = readonly [LucideIcon, string, string, "bars" | "lines" | "tiers" | "stack" | "lock" | "cloud"];
const CAPABILITIES: ReadonlyArray<Cap> = [
  [FileSearch, "Knowledge intelligence", "Heading-aware content ingestion, hybrid retrieval, reranking and source-grounded evidence.", "lines"],
  [KeyRound, "Permissioned actions", "Registry-controlled tools, risk policies, idempotency and verification for write operations.", "lock"],
  [Activity, "Workflow observability", "Inspectable node progress, tool activity, token usage, timing, errors and workflow outcomes.", "bars"],
  [MemoryStick, "Customer memory", "Safe, de-duplicated long-term notes and short-term workflow context, with privacy boundaries.", "stack"],
  [Cpu, "LLM flexibility", "Works with different language models, routing each task to a fast, balanced or deep-reasoning tier, with fallback if one is unavailable.", "tiers"],
  [Cloud, "Cloud-ready delivery", "Container-first design that is planned to run on the major cloud platforms.", "cloud"],
];

const LAYERS: ReadonlyArray<readonly [LucideIcon, string, string, readonly string[], string]> = [
  [LayoutDashboard, "Experience", "Where support teams work", ["Ticket inbox", "Approvals", "Workflow view"], "#059669"],
  [Server, "Services", "Secure access to every capability", ["Authentication", "Role-based access", "Audit logging"], "#0d9488"],
  [Workflow, "Orchestration", "Coordinates each step of a resolution", ["Routing", "Pause for approval", "Step budgets"], "#0891b2"],
  [Brain, "Specialist agents", "Focused roles with structured output", ["Understand", "Investigate", "Resolve", "Escalate"], "#d97706"],
  [Sparkles, "Intelligence", "Evidence and judgement", ["Knowledge retrieval", "Language models", "Safety checks"], "#16a34a"],
  [Database, "Data and memory", "What the platform knows and remembers", ["Tickets and customers", "Knowledge base", "Customer memory"], "#7c3aed"],
  [Layers, "Operations", "Running it reliably", ["Containerised delivery", "Structured logs", "Traceability"], "#64748b"],
];

function Logo() {
  return (
    <span className="logo">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M5 17.5 12 4l7 13.5M8 13h8M7 17.5h10" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </span>
  );
}

function CapArt({ kind }: { kind: Cap[3] }) {
  switch (kind) {
    case "bars":
      return <div className="art-bars"><i /><i /><i /><i /><i /></div>;
    case "lines":
      return <div className="art-lines"><i /><i className="hit" /><i /><i className="hit" /></div>;
    case "tiers":
      return <div className="art-tiers"><span>fast</span><span>smart</span><span>reasoning</span></div>;
    case "stack":
      return <div className="art-stack"><i /><i /><i /></div>;
    case "lock":
      return <div className="art-lock"><span className="tg" /><span className="tg off" /><Lock size={26} aria-hidden="true" /></div>;
    default:
      return <div className="art-tiers"><span>build</span><span>ship</span><span>run</span></div>;
  }
}

export default function LandingPage() {
  return (
    <div className="landing" id="top">
      <LandingEffects />
      <ScrollToTop />
      <nav className="nav" aria-label="Site">
        <div className="wrap navin">
          <a className="brand" href="#top">
            <Logo />
            CloudDesk
          </a>
          <div className="navlinks" id="landing-links">
            <a href="#top">Home</a>
            <a href="#platform">Platform</a>
            <a href="#agents">AI Agents</a>
            <a href="#workflow">Workflow</a>
            <a href="#security">Trust &amp; Safety</a>
            <a href="#architecture">Architecture</a>
            <Link className="signin" href="/login">Sign in</Link>
            <a className="navcta" href="#contact">
              Explore CloudDesk <ArrowUpRight size={14} style={{ verticalAlign: "-2px" }} aria-hidden="true" />
            </a>
          </div>
          <MobileMenuButton />
        </div>
      </nav>

      <main>
        <section className="hero">
          <div className="hero-content wrap">
            <div className="eyebrow">
              <span className="pulse" /> Autonomous support intelligence · Built for teams
            </div>
            <h1>
              Resolve beyond
              <br />
              <span className="grad-text">the ticket.</span>
            </h1>
            <p className="lead">
              Meet the support platform that thinks through every issue. CloudDesk investigates,
              retrieves evidence, diagnoses, recommends, and resolves, with humans in control of
              consequential actions.
            </p>
            <div className="actions">
              <Link className="btn btn-primary" href="/login">
                Open the console <ArrowRight size={18} aria-hidden="true" />
              </Link>
              <a className="btn btn-secondary" href="#workflow">
                <Play size={16} aria-hidden="true" /> Explore the workflow
              </a>
            </div>
            <div className="fine">AI-powered resolution · Human oversight · Evidence-led decisions</div>
          </div>

          <div className="stage" aria-label="Example of a ticket being resolved">
            <div className="float-badge fb1">
              <ShieldCheck size={20} color="#059669" aria-hidden="true" />
              <div>Approval gate<small>Refund waits for a human</small></div>
            </div>
            <div className="float-badge fb2">
              <BookOpen size={20} color="#d97706" aria-hidden="true" />
              <div>3 cited sources<small>Hybrid retrieval</small></div>
            </div>
            <div className="float-badge fb3">
              <Radar size={20} color="#0891b2" aria-hidden="true" />
              <div>Risk: medium<small>Policy checked</small></div>
            </div>
            <div className="dash">
              <div className="dash-top">
                <div className="dots" aria-hidden="true"><i /><i /><i /></div>
                <div className="dash-title">CloudDesk · Resolution Intelligence</div>
                <span className="live">Workflow active</span>
              </div>
              <div className="dash-body">
                <div className="dash-side" aria-hidden="true">
                  <div className="side-item on"><Ticket size={15} /> Tickets</div>
                  <div className="side-item"><CheckCircle2 size={15} /> Approvals</div>
                  <div className="side-item"><UserRound size={15} /> Customers</div>
                  <div className="side-item"><BookOpen size={15} /> Knowledge</div>
                  <div className="side-item"><Siren size={15} /> Escalations</div>
                  <div className="side-item"><ScrollText size={15} /> Audit</div>
                </div>
                <div className="dash-main">
                  <div className="tk-head">
                    <div>
                      <div className="tk-id">TICKET CD-1003 · API</div>
                      <div className="tk-title">API rate limit reached during nightly sync</div>
                    </div>
                    <span className="chip warn">High priority</span>
                  </div>
                  <div className="progress" aria-hidden="true">
                    <span className="p-dot"><Check size={12} /></span><span className="p-line done" />
                    <span className="p-dot"><Check size={12} /></span><span className="p-line done" />
                    <span className="p-dot"><Check size={12} /></span><span className="p-line run" />
                    <span className="p-dot todo" /><span className="p-line" />
                    <span className="p-dot todo" />
                  </div>
                  <div className="evid">
                    <div><b>Customer</b>Business plan · 5 seats · 2 open tickets</div>
                    <div><b>Evidence</b>API rate limits <em>0.91</em></div>
                    <div><b>Diagnosis</b>Burst above 60 req/min; add backoff</div>
                  </div>
                </div>
                <div className="dash-right">
                  <div className="feed-h">Agent activity</div>
                  <div className="feed">
                    {[
                      [Compass, "Supervisor", "Classified · api_failure", "#059669"],
                      [Search, "Knowledge", "3 sources cited", "#0891b2"],
                      [Stethoscope, "Troubleshooting", "Cause found", "#d97706"],
                      [Sparkles, "Resolution", "Drafting reply", "#16a34a"],
                    ].map(([Icon, name, note, colour]) => {
                      const I = Icon as LucideIcon;
                      return (
                        <div className="feed-row" key={name as string}>
                          <span className="ic" style={{ background: colour as string }}><I size={15} aria-hidden="true" /></span>
                          <div><b>{name as string}</b><small>{note as string}</small></div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="wrap stats reveal">
            <div className="stat"><strong>10-stage</strong><span>End-to-end resolution lifecycle</span></div>
            <div className="stat"><strong>6 specialists</strong><span>Purpose-built AI agents</span></div>
            <div className="stat"><strong>Human-in-loop</strong><span>Approval for consequential actions</span></div>
            <div className="stat"><strong>Evidence-led</strong><span>Knowledge-grounded responses</span></div>
          </div>
        </section>

        <section className="section alt" id="workflow">
          <div className="wrap">
            <div className="section-head reveal">
              <div className="kicker">From ticket to resolution</div>
              <h2 className="title">
                One intelligent workflow.
                <br />
                <span className="grad-text">Every step accounted for.</span>
              </h2>
              <p>
                CloudDesk coordinates a complete investigation and resolution lifecycle, rather than
                treating support as a simple prompt-and-response interaction.
              </p>
            </div>
            <div className="timeline reveal">
              <div className="tl-line" aria-hidden="true" />
              {WORKFLOW.map(([num, title, text, Icon], i) => (
                <div className="tl-item" key={num}>
                  <div className="tl-card">
                    <span className="tl-ico"><Icon size={22} aria-hidden="true" /></span>
                    <div>
                      <span className="tl-num">{num}</span>
                      <h3>{title}</h3>
                      <p>{text}</p>
                    </div>
                  </div>
                  <span className="tl-node" style={{ animationDelay: `${i * 0.5}s` }} aria-hidden="true">
                    {i + 1}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="section" id="agents">
          <div className="wrap">
            <div className="section-head reveal">
              <div className="kicker">Specialist intelligence</div>
              <h2 className="title">
                Not one AI. <span className="grad-text">A coordinated team.</span>
              </h2>
              <p>
                Dedicated agents collaborate through a controlled workflow, each with a clear
                responsibility, structured output and governed tool access.
              </p>
            </div>
            <div className="agents reveal">
              {AGENTS.map(([Icon, name, role, text, points, colour]) => (
                <article className="agent" key={name} style={{ ["--c" as string]: colour }}>
                  <div className="agent-top">
                    <span className="agent-ico"><Icon size={26} aria-hidden="true" /></span>
                    <span className="status">Active</span>
                  </div>
                  <span className="role">{role}</span>
                  <h3>{name}</h3>
                  <p>{text}</p>
                  <div className="chips">
                    {points.map((point) => <span key={point}>{point}</span>)}
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="section alt" id="security">
          <div className="wrap trust">
            <div className="reveal">
              <div className="kicker">Trust &amp; Safety</div>
              <h2 className="title">
                Autonomy with <span className="grad-text">guardrails.</span>
              </h2>
              <p style={{ color: "var(--muted)", lineHeight: 1.75, fontSize: 17, margin: 0 }}>
                CloudDesk makes useful progress while keeping sensitive decisions accountable.
                Policy rules, not model confidence, define where automation stops.
              </p>
              <div className="trust-list">
                {TRUST.map(([Icon, title, text]) => (
                  <div className="trust-item" key={title}>
                    <span className="trust-ico"><Icon size={22} aria-hidden="true" /></span>
                    <div><h3>{title}</h3><p>{text}</p></div>
                  </div>
                ))}
              </div>
            </div>
            <div className="approval-ui reveal" aria-label="Example of an approval request">
              <div className="approval-head">
                <span style={{ display: "inline-flex", gap: 9, alignItems: "center" }}>
                  <ShieldAlert size={18} aria-hidden="true" /> Human approval required
                </span>
                <span className="chip warn">Pending</span>
              </div>
              <div className="approval-body">
                <div className="kv">
                  <div>Action<b>create_refund_request</b></div>
                  <div>Amount<b>₹ 7,200</b></div>
                  <div>Risk<b>High</b></div>
                  <div>Ticket<b>CD-1002</b></div>
                </div>
                <ul className="rules">
                  <li><Check size={15} aria-hidden="true" /> Amount comes from the subscription record, not the ticket text</li>
                  <li><Check size={15} aria-hidden="true" /> Idempotency key set; a retry cannot refund twice</li>
                  <li><Check size={15} aria-hidden="true" /> Nothing runs until an authorised agent decides</li>
                </ul>
                <div className="approval-actions">
                  <span className="abtn ok"><Check size={15} aria-hidden="true" /> Approve</span>
                  <span className="abtn no">Reject</span>
                  <span className="abtn up"><Siren size={15} aria-hidden="true" /> Escalate</span>
                </div>
                <div className="audit">
                  <div><i /> 10:42 Resolution Agent proposed refund</div>
                  <div><i /> 10:42 Risk check raised the plan to high</div>
                  <div><i /> 10:43 Waiting for sam.agent</div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="section" id="platform">
          <div className="wrap">
            <div className="section-head reveal">
              <div className="kicker">Platform capabilities</div>
              <h2 className="title">
                Everything connected.
                <br />
                <span className="grad-text">Every decision traceable.</span>
              </h2>
              <p>
                AI orchestration sits inside a dependable SaaS foundation: APIs, data, retrieval,
                policy, observability and deployment.
              </p>
            </div>
            <div className="caps reveal">
              {CAPABILITIES.map(([Icon, title, text, art]) => (
                <article className="cap" key={title}>
                  <div className="cap-art"><CapArt kind={art} /></div>
                  <div className="cap-top">
                    <span className="cap-ico"><Icon size={20} aria-hidden="true" /></span>
                    <h3>{title}</h3>
                  </div>
                  <p>{text}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="section alt" id="architecture">
          <div className="wrap">
            <div className="section-head reveal">
              <div className="kicker">A platform, not a prompt</div>
              <h2 className="title">
                From interface to <span className="grad-text">intelligence layer.</span>
              </h2>
              <p>
                Seven clear layers, each with one job, so every decision stays secure,
                traceable and easy to change.
              </p>
            </div>
            <div className="arch reveal">
              {LAYERS.map(([Icon, name, note, chips, colour], i) => (
                <div key={name}>
                  {i > 0 && <div className="connector" aria-hidden="true"><i style={{ animationDelay: `${i * 0.3}s` }} /></div>}
                  <div className="layer" style={{ ["--lc" as string]: colour }}>
                    <div className="layer-name">
                      <span className="li"><Icon size={19} aria-hidden="true" /></span>
                      <div><b>{name}</b><small>{note}</small></div>
                    </div>
                    <div className="layer-chips">
                      {chips.map((c) => <span key={c}>{c}</span>)}
                    </div>
                  </div>
                </div>
              ))}
              <div className="arch-note">
                A high-level view of how CloudDesk is organised, from the console to the data it relies on
              </div>
            </div>
          </div>
        </section>

        <section className="section" id="contact">
          <div className="wrap">
            <div className="cta reveal">
              <div className="kicker">The next era of support</div>
              <h2>
                Turn support into
                <br />
                resolution intelligence.
              </h2>
              <p>
                See how CloudDesk combines specialist AI agents, grounded knowledge and human
                approval into a complete resolution workflow.
              </p>
              <a className="btn" href="mailto:hello@saffronyx.in?subject=CloudDesk%20Platform%20Enquiry">
                Connect with Saffronyx <ArrowUpRight size={18} aria-hidden="true" />
              </a>
            </div>
          </div>
        </section>
      </main>

      <footer>
        <div className="wrap">
          <div className="footgrid">
            <div className="footbrand">
              <a className="brand" href="#top">
                <Logo />
                CloudDesk
              </a>
              <p>
                Autonomous customer support and resolution intelligence. Understand the issue.
                Investigate the evidence. Resolve with confidence.
              </p>
              <div className="socials">
                <a href="https://saffronyx.in" target="_blank" rel="noopener noreferrer" aria-label="Saffronyx website"><Globe size={17} /></a>
                <a href="mailto:hello@saffronyx.in" aria-label="Email Saffronyx"><Mail size={17} /></a>
                <a href="#platform" aria-label="Platform overview"><MessageSquareText size={17} /></a>
              </div>
            </div>
            <div className="footcol">
              <h4>Platform</h4>
              <a href="#platform">Platform overview</a>
              <a href="#agents">AI specialist agents</a>
              <a href="#workflow">Resolution workflow</a>
              <a href="#architecture">Architecture</a>
            </div>
            <div className="footcol">
              <h4>Trust &amp; Safety</h4>
              <a href="#security">Human approval</a>
              <a href="#security">Safety &amp; guardrails</a>
              <a href="#platform">Knowledge grounding</a>
              <a href="#platform">Observability</a>
            </div>
            <div className="footcol">
              <h4>Company</h4>
              <a href="https://saffronyx.in" target="_blank" rel="noopener noreferrer">Saffronyx.in</a>
              <a href="mailto:hello@saffronyx.in">Contact · hello@saffronyx.in</a>
              <Link href="/login">Sign in</Link>
              <a href="#top">Back to top</a>
            </div>
          </div>
          <div className="copyright">
            <span>© 2026 CloudDesk. All rights reserved.</span>
            <span className="credit">
              Designed &amp; engineered by <strong>Saffronyx AI Engineering Studio</strong> ·
              Designing Intelligent Systems That Last.
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}
