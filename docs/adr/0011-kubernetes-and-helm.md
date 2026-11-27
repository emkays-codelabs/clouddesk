# ADR-0011: Kubernetes and Helm as the parity target

## Status

Accepted on 2026-11-27 (owner approval in chat). This is decision D5 in `CLAUDE.md` section 20 and relates to upstream ADR-06. The decision is taken; no chart is built, and no cluster is operated.

## Context

The upstream HLD makes Kubernetes and one Helm chart the parity target across EKS, AKS and GKE, and treats
serverless containers as the lighter profile. This repository builds the serverless profile first: ECS
Fargate, Container Apps and Cloud Run, with Terraform modules shared across the three clouds.

## Decision

Kubernetes with one Helm chart becomes the parity target across EKS, AKS and GKE, and the serverless container profile stays as the lighter option. The chart is built after the first deployment, which is AWS (owner decision, 2026-11-27), so the Terraform scaffolds are proven on one real account before a second target is added.

## Consequences

If adopted: every file in Phase 14 changes, and operating a cluster becomes part of the project. If not
adopted: the three clouds each use their own container service, and the parity claim is weaker. Nothing is
deployed either way; no cloud credentials have been used.
