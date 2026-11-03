# ADR-0011: Kubernetes and Helm as the parity target

## Status

Proposed. This is decision D5 in `CLAUDE.md` section 20 and relates to upstream ADR-06. It is not taken.

## Context

The upstream HLD makes Kubernetes and one Helm chart the parity target across EKS, AKS and GKE, and treats
serverless containers as the lighter profile. This repository builds the serverless profile first: ECS
Fargate, Container Apps and Cloud Run, with Terraform modules shared across the three clouds.

## Decision

Not taken. The question is whether to add a Helm chart and make Kubernetes the target.

## Consequences

If adopted: every file in Phase 14 changes, and operating a cluster becomes part of the project. If not
adopted: the three clouds each use their own container service, and the parity claim is weaker. Nothing is
deployed either way; no cloud credentials have been used.
