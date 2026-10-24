# Phase 05 Owner Decision Packet

**Status:** Proposal for owner review. No cloud account, provider, budget, recovery target, security scope, or production environment is approved by this document.

## Recommendation

For an initial OOSYS staging environment, use AWS in `ap-southeast-5` (Malaysia), subject to a cost estimate, service-availability check, and owner approval. Run the existing Dockerized API on Amazon ECS with Linux Fargate tasks, use Amazon RDS for PostgreSQL, and use CloudWatch Logs/Metrics/Alarms with an SNS notification destination. Use RDS automated backups for point-in-time recovery and AWS Backup only where the approved retention policy needs longer-lived recovery points. Use GitHub Actions OIDC to assume a narrowly scoped AWS role for deployments; do not store long-lived AWS access keys in GitHub secrets.

This is a proposed fit for the approved Docker/PostgreSQL stack and a Malaysia-based project, not a procurement or deployment decision. AWS lists `ap-southeast-5` as Malaysia, and Linux ECS on Fargate is supported there. The region is opt-in for AWS accounts, so an account owner must enable it before deployment. Verify that every required service and feature is available in the account and selected region before provisioning. [AWS Regions](https://docs.aws.amazon.com/global-infrastructure/latest/regions/aws-regions.html), [Fargate supported Regions](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate-Regions.html)

## Proposed Phase 05 decisions

| Decision | Proposed starting point | Owner approval still needed |
|---|---|---|
| Cloud and region | AWS `ap-southeast-5`; staging first; keep the production target unprovisioned until costs, service availability, and data-residency requirements are confirmed. | Account owner enables the region; product owner approves provider and data-location policy. |
| Application hosting | ECS/Fargate for the API container; keep frontend delivery and ingress design within a separately reviewed staging plan. | Platform owner approves network, ingress, TLS, and monthly budget. |
| PostgreSQL | RDS for PostgreSQL. Start with a non-production staging database; choose production availability and instance sizing only after workload and budget review. | Database/platform owner approves sizing, encryption/key ownership, network access, and maintenance windows. |
| Backups and recovery | RDS automated backups/PITR for operational recovery; use AWS Backup for longer retention only if approved policy requires it. Begin with the existing proposed targets of RPO ≤15 minutes and RTO ≤4 hours, then measure them in a timed isolated restore. | Product owner approves retention, data residency, key ownership, RPO/RTO and cost. Database/platform owner runs restore and access-denial drills. |
| Central monitoring | CloudWatch Logs, service/database metrics, alarms, and an SNS email destination for the first staging alert route. Keep metric labels bounded and free of tenant/user identifiers and secrets. | Operations owner names the monitored recipient, on-call role, escalation path, thresholds, and alert budget. |
| Deployment identity | GitHub Actions OIDC with short-lived credentials and a role restricted to this repository and approved deployment environment. | Platform/security owner reviews the trust policy and least-privilege permissions. |
| Rollback | ECS deployment alarms and rollback to the last completed deployment, followed by a staging rehearsal and data-integrity checks. | Release owner defines triggers, approval, operator, and rehearsal evidence. |
| Independent security test | Commission an independent tester against an approved staging target; use the Phase 05 scope in `PHASE_05_OPERATIONAL_ACCEPTANCE_PLAN.md`. | Security owner approves tester, rules of engagement, budget, remediation owner, and residual-risk disposition. |

RDS automated backup retention is configurable from 1 to 35 days, and its point-in-time restore can target a time within the retention period. AWS documents that longer retention may increase storage cost; actual restore duration must be measured and is not guaranteed by the service feature alone. [RDS backup and restore](https://docs.aws.amazon.com/AmazonRDS/latest/gettingstartedguide/managing-backup-restore.html)

CloudWatch alarms can notify an SNS topic, ECS can send container logs to CloudWatch Logs, and ECS can roll back a deployment when configured alarms detect a failed deployment. [ECS monitoring](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/monitoring-automated-manual.html), [ECS alarm-based rollback](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/deployment-alarm-failure.html)

GitHub Actions OIDC avoids keeping long-lived AWS access keys in GitHub secrets, but it still requires a tightly scoped trust policy and IAM role. [GitHub OIDC with AWS](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws)

## Cost and deployment guardrails

- Do not create cloud resources until the account owner approves a monthly budget and the AWS Pricing Calculator estimate. The estimate must include database compute/storage, backup storage, task runtime, ingress/load balancing, logs/metrics/alarms, network transfer, and security services. [AWS Pricing Calculator](https://docs.aws.amazon.com/pricing-calculator/latest/userguide/getting-started.html)
- Start with staging and synthetic data. Do not copy production/customer data into staging without a documented data-handling approval.
- Keep production separate from staging and require a later explicit production-release approval.
- Do not copy backups across regions until data residency and cross-region transfer are approved.
- Store credentials in an approved cloud secret store; never commit credentials or generated environment files.
- No RPO/RTO proposal becomes an accepted commitment until the product owner approves it and a timed drill demonstrates it.

## Decisions needed to unblock Phase 05

Reply with either **approve the AWS proposal for a costed staging design** or the preferred provider/region. Also name or assign:

1. The account/budget owner and maximum monthly staging spend.
2. The operations/on-call recipient for test alerts.
3. The backup/data-residency policy owner and whether to accept, revise, or defer the proposed RPO/RTO targets.
4. The security owner who can commission and disposition an independent penetration test.
5. The release owner for staging approval and rollback rehearsal.

Until these are recorded, Phase 05 remains in progress and Phase 06 business-data implementation remains gated by the roadmap dependency.
