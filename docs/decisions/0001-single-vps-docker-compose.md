# 0001: One Vultr VPS running Docker Compose

**Status:** accepted · 2026-11-14

**Context:** $200 Vultr credit, small team, live demo needed, reproducible setup.

**Decision:** one Cloud Compute instance (2 vCPU / 4 GB, Ubuntu 24.04) running every service
with Docker Compose; Caddy for automatic HTTPS. ML training runs on a laptop; the server only
runs inference.

**Consequences:** cheap (~$20–24/month, verify live pricing), whole stack rebuildable in
minutes. Single point of failure is acceptable for a hackathon. Scaling path (separate broker,
workers, managed Postgres) is documented, not built.
