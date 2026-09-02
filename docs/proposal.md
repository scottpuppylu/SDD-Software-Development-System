# SDD Software Development System - Current Product Proposal

## 1. Authority and scope

This document is the approved CURRENT prospective `PRODUCT_INTENT` authority for the SDD Software Development System. Project authority has explicitly approved the substantive product-intent decisions recorded here.

This document is not recovered or reconstructed historical Phase01 authority. Historical COMPLETE / PASS evidence is not used to invent product intent, requirements, goals, scope, or outcomes. Historical evidence remains bounded to its original evidentiary purpose.

This approval owns only the `PRODUCT_INTENT` domain. It does not create product requirements, acceptance criteria, priorities, technical contracts, architecture, APIs, database design, implementation design, governance artifacts, execution tasks, implementation authorization, verification decisions, release decisions, or project-completion authority.

## 2. Product vision

Build an SDD software-development assistance system that works together with AI to help users develop many kinds of programs and apps through a structured, governed, and verifiable development process from idea clarification through design, implementation, testing, and maintenance.

## 3. User problem

Software development commonly fails because requirements are unclear, system logic or process is inconsistent, architecture becomes unnecessarily complex, error and exception handling is incomplete, tests are insufficient, security is weak, or later maintenance and modification are difficult.

The desired development discipline is:

```text
clear requirements
-> reasonable architecture
-> correct logic and process
-> simple implementation
-> controlled errors/exceptions
-> complete testing
-> controlled security
-> easy maintenance and modification
```

## 4. Target users

The primary users are:

- the project owner; and
- other users who do not know how to program but have ideas they want to turn into working software or apps.

## 5. Usage context

When users have an idea, they use the SDD system to turn that idea into working software through governed requirement clarification, specification, design, task decomposition, AI-assisted implementation, testing, validation, and later maintenance or modification.

## 6. Desired outcome

Programs and apps developed through SDD should run stably and correctly and remain easy to maintain, modify, extend, and repair without unnecessarily breaking existing behavior.

## 7. Core value proposition

Combine structured SDD governance with AI reasoning and development assistance to turn software development from an experience-dependent, omission-prone process into a controlled flow that preserves clarity, logical correctness, simplicity, testability, security, and maintainability.

## 8. Core interaction concept

The intended end-state is cloud-hosted SDD operation with remote interaction, primarily through:

```text
LINE
-> webhook
-> SDD Orchestrator
-> AI/development execution capability
-> repository/Git/verification flow
```

Users should be able to submit development requests, continue development, inspect status, receive Human Decision requests, and approve or reject important product, technical, or lifecycle decisions remotely.

LINE is the intended primary remote interface, not an exclusive permanent interface.

## 9. Product goals

### G-01 - Governed idea-to-software journey

Provide a structured and verifiable development journey that carries a user's idea through clarification, specification, design, task decomposition, AI-assisted implementation, testing, validation, and ongoing maintenance or modification.

### G-02 - Accessible AI-assisted development

Enable the project owner and people without programming knowledge to work with AI to turn software ideas into working programs and apps while important decisions remain governed by appropriate human authority.

### G-03 - Stable and maintainable software outcomes

Promote software outcomes that run stably and correctly and remain straightforward to maintain, modify, extend, and repair without unnecessary regression of existing behavior.

### G-04 - Controlled development quality

Preserve clarity, reasonable architecture, correct logic and process, implementation simplicity, controlled error and exception handling, complete testing, controlled security, and maintainability throughout the development flow.

### G-05 - Truthful, authority-preserving remote operation

Support remote development interaction and Human Decision while preserving domain-specific authority, lifecycle gates, repository/Git traceability, truthful state reporting, and observational-only telemetry.

## 10. MVP intent boundary

The MVP is a complete governed core development chain from idea to stable, verifiable, maintainable software. Its product-intent boundary includes:

- idea intake;
- requirement clarification;
- specification;
- design;
- task decomposition;
- AI-assisted coding;
- testing and verification;
- Git traceability and checkpoints; and
- Human Decision.

The MVP objective is completion of this governed core chain, not maximum feature breadth.

## 11. Non-goals

The following are not required for the current MVP:

- a Web UI;
- multi-user collaboration;
- a full permission system;
- commercialization features;
- a native mobile app;
- support for many additional AI providers;
- general database-management capability;
- broad one-click deployment across many cloud providers; and
- other extensions not required for the core governed development chain.

These non-goals define the current MVP boundary; they do not establish permanent exclusions.

## 12. Confirmed constraints

1. AI must not independently decide product requirements.
2. AI must not bypass required Human Decision.
3. AI must not independently modify authority.
4. AI must not directly release or deploy without required lifecycle gates and human authorization.
5. The system must not fabricate documents, status, test results, gate results, history, or evidence merely to appear complete.
6. Truthful state takes precedence over apparent completion: when authority, evidence, testing, or decisions are incomplete, the system must state `TBD`, `INCOMPLETE`, or `BLOCKED` rather than manufacture completion.
7. Authority remains domain-specific; linear authority precedence is forbidden.
8. Cross-domain conflict must follow `DETECT -> REPORT -> BLOCK -> ROUTE_TO_AUTHORITATIVE_OWNER`.
9. Repository and Git are the primary persistent execution-state and traceability source; chat memory is not authoritative execution state.
10. AI may reason, analyze, draft, implement, and assist verification only within granted authority and defined gates; it may not create authority.
11. Stage07, Stage09, and Stage10 gate semantics must not be skipped or weakened.
12. Tests are evidence, not requirement authority.
13. Telemetry is observational only and must not determine lifecycle behavior or authority.
14. Where their scope applies, the product must preserve the Phase04 safety invariants that authority coverage equals 100%, authority byte mismatch equals 0, `BASELINE` is canonical and the default, `OPTIMIZED` is explicit-attempt-only, and context optimization must not weaken authority, governance, or lifecycle behavior.

## 13. Evidence / assumptions / TBD

The following remain explicitly unresolved and require future authority decisions in their applicable domains:

- final cloud platform;
- final LINE webhook architecture;
- future Web UI;
- future additional AI providers;
- future collaboration and permission model;
- commercialization model;
- generalized database-management capability; and
- multi-cloud deployment capability.

The current lifecycle, closure, Phase04, and telemetry materials provide bounded context and constraints only. They do not establish historical Phase01 product intent or downstream product, technical, design, task, verification, or release authority.

## 14. Downstream authority boundary

Future downstream artifacts require independent authority approval in their respective domains. This proposal approval does not authorize or predetermine a PRD, specification, design, agent-governance artifact, task decomposition, pre-implementation gate result, implementation, Recovery Gate result, Stage09 verification result, Stage10 decision, release, or deployment.

The `G-*` identifiers in this document are approved current product-intent authority and canonical goal anchors for that authority. They are not requirements, acceptance criteria, technical guarantees, design decisions, tasks, priorities, or implementation instructions.

## 15. Current proposal status

Project authority has explicitly approved this proposal as CURRENT prospective `PRODUCT_INTENT` authority. This approval is not recovered historical Phase01 authority and does not authorize historical Phase01 reconstruction. It creates no PRD, specification, design, task, implementation, Recovery Gate, Stage09, release, or deployment authority.

```text
CURRENT_PRODUCT_INTENT_AUTHORITY =
APPROVED_CURRENT_AUTHORITY

HISTORICAL_PHASE01_RECONSTRUCTION =
NOT_AUTHORIZED

PRODUCT_REQUIREMENTS_DEFINED =
NO

TECHNICAL_CONTRACT_DEFINED =
NO

IMPLEMENTATION_DESIGN_DEFINED =
NO

IMPLEMENTATION_AUTHORIZED =
NO

CURRENT_IMPLEMENTATION_RECOVERY_GATE_RESULT =
NOT_EVALUATED

STAGE09_DECISION =
NOT_EVALUATED

RELEASE_AUTHORIZED =
NO

NEXT_STEP =
CURRENT_PRD_AUTHORITY_DEFINITION
```
