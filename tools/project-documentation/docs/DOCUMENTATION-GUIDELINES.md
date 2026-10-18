# Claude Documentation Generation Prompt

## Goal

Create extensive, human- and AI-readable documentation for this codebase, detailing the coherences, relationships and dependencies. The output must serve 4 audiences simultaneously:

1. **Agentic / AI use** — compact, structured, machine-navigable files that minimize token load when an agent needs to answer a question or plan a change.
2. **Developer onboarding** - detailed, structured, extensive explanation of what the code does, rich narrative explanations of *why* things, extensively describe how to get started, how to compile or similar, and extensively describe where the none-obvious gotchas live.
3. **Architecture Showcase**-  detailed, structured, extensive explanation of the overall architecture and concepts used as base for future architectural decisions.
4. **Techstack/Concept change feasbility check** - detailed, structured, extensive explanation of techstack decisions and feasability to change parts or full techstack and concepts

---

## Step 1 — Explore Project Deeply

Read all relevant source files to answer all of the following accurately and extensively. Do not guess. Do not summarize from filenames alone. Do not make assumptions of content, always read the files.

### Per Project

- What it does and why it exists in an extensive manner as technical purpose and business purpose (not just technical function)
- Technology stack — language and version, runtime and version, frameworks, ORMs, test tooling, build tooling, linters, container runtime, virtualization environment, all not obvious tech stack components.
- All external interfaces: HTTP routes, GraphQL schema, gRPC service definitions, WebSocket events, binary protocol frames, CLI commands, SDK public API surface, library APIs, all other external interfacing methods.
- Async communication: queues, topics, streams, pub/sub channels, other async communication monikers — both produced and consumed, with exact technology description and details (for example channel names)
- Domain model: all entities, value objects, aggregates, repositories, domain events
- Persistence: databases, schemas, migrations, caching strategy, file formats, all other persistence methods in detail
- Background jobs and scheduled tasks — triggers, concurrency, failure handling
- Configuration: every env var, config file section, feature flag, secret reference, configuration files and other configuration methods in detail
- Startup and shutdown lifecycle
- all non obvious workflows as extensive text and mermaid diagrams, including purpose
- Cross-cutting concerns: auth/authz model, logging conventions, error handling strategy, distributed tracing, metrics, exception handling, all other non-obvious cross-cutting concerns.
- Extensively description of how to build and detailed list of prerequisites, library and project dependencies
- if it consumes or exposes a protocol, extensive description of the protocol and the technical purpose
- does this code create or use a protocol, if so add it to the protocol list

### Cross-project / system-wide

- How projects discover, interact and call each other and the purpose behind that
- Shared libraries and what contract they enforce, including version pinning
- Deployment topology: how many instances of what, on what infrastructure, in what network zone, in what environment, virtualization environment if any, all other non obvious deployment details
- Security perimeter: what is public, what is internal, how credentials are managed and rotated, what is stored, how can it affect or compromise overall security constraints
- End-to-end data flow: trace a representative stimulus from entry point across all services to final persistence as extensive description and mermaid diagrams if it makes sense
- extensively document how are protocol relationship between projects, which project consumes or exposes what and to what purpose on single command/data exchange level
- are implemented protocols in use that are created or consumed between the projects that are not in the protocol list, if so add it to the protocol list

### Non-obvious things to capture explicitly

- Why a particular design decision was made (if inferable from code, comments, or config), be very extensive
- extensive pro and cons of the design decisions
- Known constraints (e.g. "must run as single instance because of distributed lock", "cannot upgrade X because of Y dependency")
- Surprising or counterintuitive behaviour
- Anything a new developer would waste time discovering
- Anything that is not obvious to a new developer without asking
- Cross-project coupling and relations that is not obvious from a single repo's imports
- extensively describe References to domain knowledge that is not technically visible or not obvious on the first sight

---

## Step 2 — Output Files

Create these files in the project's documentation directory:

### Core Files (Required)

1. **index.md** - Project overview and navigation hub
   - One-paragraph description of what this project does
   - Links to all other documentation files
   - Cross-references to other projects

2. **techstack.md + techstack.yaml** - Complete technology inventory
   - Language and runtime with versions
   - Frameworks and libraries with versions
   - Build and packaging tools
   - Persistence technologies
   - Messaging and async communication
   - Observability tools
   - Infrastructure and deployment
   - Version constraints and known limitations

3. **project-summary.md** - Business and technical context
   - Business context: what problem this solves, who the users are
   - Technical responsibilities: what this project owns
   - Key design decisions and their rationale
   - Known limitations and constraints
   - Operational concerns
   - Cross-project dependencies

4. **architecture.md** - System architecture documentation
   - C4 Context diagram (this project in relation to users and external systems)
   - C4 Container diagram (internal runtime components)
   - C4 Component diagram (internal code structure)
   - Data flow diagrams
   - Security architecture

5. **api-reference.md + api-reference.yaml** - All external interfaces
   - HTTP REST endpoints (method, path, params, response)
   - GraphQL schema (if applicable)
   - gRPC services (if applicable)
   - WebSocket events (if applicable)
   - CLI commands (if applicable)
   - Library/SDK APIs (if applicable)

6. **domain-model.md + domain-model.yaml** - Domain entities
   - All domain entities with fields
   - Value objects and their invariants
   - Aggregates and aggregate roots
   - Repository interfaces
   - Domain events
   - Entity-relationship or class diagrams

7. **configuration.md + configuration.yaml** - Configuration reference
   - Environment variables
   - Config file sections
   - Feature flags
   - Secret references
   - Hot-reload capabilities

8. **design-decisions.md** - Architecture Decision Records
   - Decision
   - Context
   - Consequences
   - Why this decision was made

9. **integration-guide.md** - Developer integration guide
   - Prerequisites
   - Build instructions
   - Testing strategies
   - Deployment procedures

### Optional Files (as applicable)

10. **messaging.md + messaging.yaml** - Async messaging contracts
    - Message queues, pub/sub topics, event streams
    - Direction (produced/consumed)
    - Channel/topic names
    - Payload schemas
    - Triggers

11. **protocols.md + protocols.yaml** - Protocol specifications
    - Protocol name and purpose
    - Transport layer
    - Connection lifecycle
    - Frame/packet format
    - Message catalogue
    - Error handling

### Diagrams

Create Mermaid diagrams in `docs/diagrams/projects/{project-name}/`:

1. **arch-01-context.mmd** - C4 Context diagram
2. **arch-02-container.mmd** - C4 Container diagram
3. **arch-03-component.mmd** - C4 Component diagram
4. **domain-01-model.mmd** - Domain model class diagram
5. **messaging-01-flow.mmd** - Message/event flow diagram

---

## Step 3 — Content Rules

### Universal Rules

- No emojis
- GitHub-flavored Markdown
- Copy actual names from source: type names, field names, topic strings, enum values, config keys, route paths, error codes — no paraphrasing
- Tables for structured data (endpoints, config, message fields, enum values)
- Include "Why" callouts for design decisions:

```markdown
> **Why:** [explanation of the reasoning behind this decision]
```

- Include "Technical purpose" callouts:

```markdown
> **Technical purpose:** [explanation of the technical reasoning]
```

- Include "Business purpose" callouts where business value is relevant:

```markdown
> **Business purpose:** [explanation of business value]
```

### Diagram Embedding

Embed diagrams as `![alt text](path/to/diagram.png)` with collapsible source:

```markdown
![Descriptive alt text](../../diagrams/projects/repo-name/filename.png)

<details>
<summary>Mermaid source — filename.mmd</summary>

```mermaid
... source ...
```

</details>
```

### YAML Companion Files

For each structured markdown file, create a companion YAML:

| Markdown | YAML | Schema |
|----------|------|--------|
| `api-reference.md` | `api-reference.yaml` | List of endpoints/methods |
| `messaging.md` | `messaging.yaml` | List of message contracts |
| `configuration.md` | `configuration.yaml` | List of config keys |
| `domain-model.md` | `domain-model.yaml` | List of entities |
| `techstack.md` | `techstack.yaml` | Structured tech inventory |
| `protocols.md` | `protocols.yaml` | List of protocol elements |

Each YAML must be valid and self-contained. Use `null` for unknown values.

---

## Step 4 — Quality Checklist

Work through this list before completing:

### Coverage
- [ ] Every required file exists with substantive content
- [ ] Every optional file that applies has been created
- [ ] All diagrams have been created in Mermaid format
- [ ] All .mmd files have corresponding .png renders

### Content Quality
- [ ] Actual type/field/method names from source (no paraphrasing)
- [ ] Every non-obvious design decision has a "Why" callout
- [ ] Tables used for structured data
- [ ] No emojis
- [ ] No invented URLs

### Agentic Companion Files
- [ ] All required YAML files exist
- [ ] All YAML files are valid
- [ ] YAML uses `null` for unknown values

### Navigation
- [ ] index.md links to all documentation files
- [ ] Each file links back to index.md
- [ ] Cross-project dependencies referenced by relative link

---

## Project-Specific Adaptations

### .NET Projects

- Document all public APIs (controllers, services, repositories)
- Include EF Core entities and migrations
- Document Dapr pub/sub topics
- Include CQRS handlers if using MediatR

### Angular Projects

- Document library structure and exports
- Include NgRx state management patterns
- Document component architecture
- Include build configuration

### Java Projects

- Document module structure
- Include D-Bus interfaces
- Document JNI usage
- Include MQTT protocol details

### Rust Projects

- Document async/await patterns
- Include struct and trait definitions
- Document MQTT/WebSocket protocols
- Include Cargo dependencies

### C++ Projects

- Document CMake configuration
- Include header API documentation
- Document D-Bus interfaces
- Include protocol specifications

---

## Output Location

Create all documentation files in:
`docs/projects/{project-name}/`

Create all diagram files in:
`docs/diagrams/projects/{project-name}/`
