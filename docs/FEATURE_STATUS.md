# Feature status against the original specification

**Built and tested** means there is code plus an automated test or a real-browser check. Items marked *needs your account* are implemented but only work once you add credentials; they were not exercised against the real third-party service.

## MVP modules
| Spec item | Status |
|---|---|
| Authentication, JWT + refresh, RBAC, audit log, session expiry | Built and tested (rotating refresh tokens, device sessions, lockout, rate limits) |
| Email verification, password reset, change password | Built and tested (real SMTP test); sending needs your SMTP settings |
| Clinic creation, onboarding checklist, staff, roles, per-role permissions | Built and tested (owner can allow reception to view clinical notes) |
| Dashboard widgets (appointments, waiting, completed, revenue, pending invoices, follow-ups, new patients, cancellation rate) | Built; browser-checked |
| Patients: full profile, emergency contact, medications, documents, timeline | Built and tested |
| Appointments: calendar day/week, doctor and location filters, walk-ins, recurring, reschedule, cancel, all 8 statuses | Built and tested |
| Live queue with Call next | Built and tested; browser-checked |
| Consultations: vitals, notes, prescription, follow-up, AI draft summary | Built and tested (AI summary with a mocked model) |
| Prescriptions: templates, printable, PDF, copy to patient portal | Built and tested |
| Billing: items, discount, tax, partial payment, refund, payment method, receipt PDF | Built and tested |
| Patient portal: appointments (book/cancel), prescriptions, documents, invoices, messages, follow-ups | Built and tested |
| Notifications: in-app, real-time | Built and tested |
| Email / SMS / WhatsApp notifications and automatic reminders | Built (SMTP tested for real; SMS/WhatsApp use Twilio, *needs your account*) |
| AI assistant: answers about the system, searches records, summarises patient history, performs actions after confirmation | Built; tested with mocked Groq replies, *needs GROQ_API_KEY* |
| Analytics: revenue, new/returning, no-show, volume, doctor utilisation, consultation time, revenue by service, retention | Built and tested |
| Security: hashing, HTTPS-ready, RBAC, audit, rate limiting, secure file serving | Built; HTTPS and encryption at rest depend on how you host it |
| Backups | Scripts provided (`scripts/backup.sh`, `restore.sh`); scheduling is up to you |

## Added in the latest round
| Item | Status |
|---|---|
| Admin console: overview, clinics (+detail), users (disable/enable), audit log with filters, support inbox, messaging log, health, settings | Built and tested |
| Change Groq API key, model, e-mail and SMS settings from the admin panel (encrypted at rest) | Built and tested; the live Groq service was not called |
| Role-specific real-time notifications with chime, toast and red dots per feature; opening the feature clears the dot | Built; tested in the backend and in a real browser |
| Doctor profiles and schedules; doctor dashboard; doctors cannot add patients | Built and tested |
| Patient appointment requests shown to reception, owner and the chosen doctor, with approve / decline / other time | Built and tested |
| Public patient sign-up and separate patient login | Built and tested |
| Easier dates and times: day chips, free time slots from the doctor's real schedule, readable in light and dark | Built; screenshot-checked |
| Back button that retraces screens and tabs | Built and tested in a browser |

## Added in the latest round
| Item | Status |
|---|---|
| New website and web app palettes (light and dark) from the brand guide; website light theme fully light | Built; checked by pixel-level tests and screenshots in both themes |
| Patient and admin options in the left sidebar | Built; browser-tested |
| Clinic owner's audit log limited to his own clinic, covering staff and patients, filterable by role | Built and tested (another clinic's entries never appear) |
| Settings restricted by role (doctor: own profile only; nurse: none) | Built; browser-tested. The server still protects each action by role |
| Pop-up forms stay open while scrolling | Built; browser-tested, including dragging the scroll bar |
| Clear chat that only affects the person who cleared it (team, staff-patient, patient) | Built and tested in the backend and the browser |
| Patient chat readable in light and dark | Fixed and checked against WCAG contrast (4.5:1) for owner, receptionist and doctor |

## Phase 2 / 3 items
| Item | Status |
|---|---|
| Multi-location clinics | Basic: locations, appointments tagged and filtered by location |
| Inventory | Built and tested |
| Automated reminders | Built and tested |
| AI search over records | Built as an assistant tool |
| Super admin: clinics, plans, suspend, support messages, system health | Built and tested (create the first one with `python -m app.cli create-superadmin`) |
| Subscription plans | Plan limits are enforced; plans are assigned by the super admin |
| Mobile app | Installable web app (PWA manifest), responsive layout with bottom navigation. No native iOS/Android app |
| **Online payment gateway** | **Not built.** Needs a gateway account (e.g. JazzCash, Easypaisa, Stripe). Payments are recorded as cash, card, bank or online |
| **Insurance claims, lab-system and diagnostic-device integrations** | **Not built.** These depend on partner APIs and agreements |
| **Multi-country support, public API ecosystem, native apps** | **Not built** |
| Two-factor authentication | Not built |
| Redis-backed real-time for several servers | Not built (single-server hub) |

## Not verified
Third-party delivery (Twilio, real Groq calls), production HTTPS/hosting, load behaviour, accessibility audit, legal text (privacy policy and terms are drafts).
