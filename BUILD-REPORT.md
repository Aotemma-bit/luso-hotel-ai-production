# Build Report

Build: Luso Hotel AI 2.0 production candidate

## Verified in the build workspace

- Python compilation: passed
- Dashboard JavaScript syntax: passed
- Automated tests: 6 passed
- Credential-pattern scan: passed
- Tenant ID passed explicitly into RAG retrieval
- Cross-hotel header selection rejected by automated test
- Protected API endpoint rejects unauthenticated requests
- Role dependency rejects an unauthorized role

## Requires verification in the owner's environment

- `production_security.sql` against the live Supabase schema
- Live two-hotel isolation script
- Docker build and container health check
- Render deployment and environment configuration
- Staging load test and measured capacity
- Supabase Security/Performance Advisor review

No fixed concurrency capacity is asserted by this report. Capacity depends on hosting resources, Supabase limits, OpenAI limits, request mix, latency, and autoscaling configuration.
