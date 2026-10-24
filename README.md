# ClinicOS

Clinic management SaaS: marketing **website**, product **web app** (staff, patient portal and platform admin), and a **FastAPI + PostgreSQL** backend with real-time updates and a Groq assistant.

```
backend/   FastAPI, SQLAlchemy, Alembic (5 migrations), 55 tests          :8000
website/   Next.js marketing site (JavaScript, Tailwind)                  :3000
webapp/    Next.js product UI (JavaScript, Tailwind), installable PWA      :3001
docs/      SECURITY_AUDIT, FEATURE_STATUS, DEPLOYMENT, SECURITY, BACKUP_RECOVERY, ENVIRONMENT_VARIABLES
scripts/   backup.sh, restore.sh
```

## Run it
```bash
docker compose up -d                                   # local PostgreSQL (127.0.0.1 only)
export POSTGRES_PASSWORD=choose-a-password            # used by docker-compose; put the same one in DATABASE_URL
cd backend && cp .env.example .env                     # set JWT_SECRET and DATABASE_URL; optional: SMTP_*, TWILIO_*, GROQ_API_KEY
pip install -r requirements-dev.txt && export $(grep -v '^#' .env | xargs)   # .env sets ENVIRONMENT=development for local use
alembic upgrade head
uvicorn app.main:app --port 8000                       # docs: http://localhost:8000/docs
python -m app.cli create-superadmin you@example.com "Your Name"    # optional platform admin
cd ../website && cp .env.example .env.local && npm install && npm run dev     # :3000
cd ../webapp  && cp .env.example .env.local && npm install && npm run dev     # :3001
python -m pytest                                       # in backend/ (SQLite by default; set DATABASE_URL for PostgreSQL)
```
Set `CORS_ORIGINS=http://localhost:3000,http://localhost:3001` on the backend. The website's Log in / Sign up buttons open the web app.

## Who sees what
Staff (owner, doctor, receptionist, nurse), **patients** (portal only) and **platform admins** each get their own area after login. See `docs/FEATURE_STATUS.md` for the complete feature-by-feature status against the original specification, including what is **not** built.

## Who uses what
- **Platform admin** (`python -m app.cli create-superadmin`): views and tracks every clinic, user, audit entry and message; switches sign-ups on/off; changes the Groq API key and model, e-mail and SMS settings from the panel (keys are stored encrypted and never shown again).
- **Clinic owner:** adds doctors (specialization, qualifications, licence, fee, working days and hours), reception and nurses; sees everything for the clinic.
- **Doctor:** own login, own dashboard (my queue, my day, follow-ups), own schedule that patients can book into. Doctors cannot add patients.
- **Reception / nurse:** add patients, handle the queue, approve or decline patient appointment requests.
- **Patient:** signs up on their own at `/patient/signup` (choose a clinic), logs in at `/patient/login`, requests appointments (choose a doctor and a free time), sees prescriptions, reports, invoices, messages.
- **Real-time:** each person gets only the notifications relevant to them, with a chime, a toast and a red dot on the exact feature that changed. Opening the feature clears the dot. The speaker button in the header mutes the sound.
- **Back button:** the header Back button retraces the screens (and tabs) you visited, one step at a time.

## Look and feel
Two palettes, each with a light and a dark theme (the theme button is in the header; the website follows the visitor's system setting until they choose):
- **Website:** *Warm Alabaster & Burnished Gold* (light, background `#F8F7F4`, accent `#B8860B`, text `#1C1B18`) and *Matte Graphite & Luminous Gold* (dark, `#121212`, accent `#D4AF37`, text `#F5F4F0`). Light is light all the way down the page; dark is dark all the way.
- **Web app:** *Soft Platinum & Amber* (light, `#EFEEE9`, white cards, button `#A67C00`, text `#212121`) and *Charcoal Black & Amber Gold* (dark, `#0D0D0D`, panels `#171717`, button `#E5C158`, text `#E5E5E5`), with the palette's success, warning and urgent colours for statuses.
- All colours are CSS variables (`webapp/app/globals.css`, `website/app/globals.css`), so a palette change is one file per app. Button text on gold uses a near-black ink for readable contrast.

## Behaviour notes
- **Left sidebar:** patients and platform admins have all their options in the sidebar (patient: Overview, Appointments, Prescriptions, Documents, Invoices, Messages, Notifications; admin: Overview, Clinics, Users, Audit log, Support, Messaging log, System health, Settings, Notifications), with red dots on the relevant ones.
- **Owner's audit log:** only this clinic's activity, from the owner, doctors, reception, nurses and patients who signed up with the clinic (logins, patient sign-ups, appointment requests, messages, record changes, deletions). Filter by role or search.
- **Settings by role:** doctors see only their own doctor profile; nurses have no Settings; reception and the owner keep the clinic pages; only the owner manages Medicine templates.
- **Clear chat** (team chat, a patient conversation, a patient's own thread) clears it from **your** screen only; nobody else's view changes, and new messages still arrive.
- Forms in pop-ups scroll inside the pop-up and no longer close when you drag the scroll bar.

## Security
See `docs/SECURITY_AUDIT.md`: an 18-item checklist (keys, env, admin routes, auth, access control, sanitising, XSS, rate limits, endpoints, CORS, headers, debug mode, dependencies, unused packages, exposed files, database, password hashing) with the evidence for each, the problems that were found and fixed, and the residual risks.


