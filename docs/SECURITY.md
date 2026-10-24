# Security notes
See **SECURITY_AUDIT.md** for the full checklist, evidence, fixed problems and residual risks. Summary of the design:

- **Passwords:** bcrypt (cost 12); weak/common passwords refused; accounts created by someone else must change the temporary password before anything else works.
- **Sessions:** short-lived access tokens, rotating refresh tokens stored per device, replay detection, instant revocation (logout, password change/reset, clinic suspension). Every request re-checks session, membership and clinic status.
- **Sign-in protection:** account lockout, per-IP and per-user rate limits, request size limits.
- **Access control:** roles plus an owner-controlled permission for reception to read clinical notes; every query scoped by clinic; the patient portal exposes only the patient's own, explicitly shared data.
- **Input and output:** server-side validation and control-character stripping on every body; React escaping; nonce-based CSP in the web app; uploads checked by type and content and served as downloads.
- **Transport and headers:** HSTS, CSP, frame denial, nosniff, referrer and permissions policies on API and frontends; strict CORS.
- **Database:** parameterised queries only, CHECK constraints, least-privilege application role (`scripts/create_db_roles.sql`).
- **Deletion:** soft delete with owner-only restore; permanent delete removes rows and files; the audit log keeps only anonymous ids.
- **AI assistant:** acts with the user's role, only proposes changes until the user confirms, and sends Groq only what its tools return. Review Groq's data terms before using real patient data.
- **Not done:** 2FA, httpOnly-cookie refresh tokens, independent penetration test, compliance assessment.
