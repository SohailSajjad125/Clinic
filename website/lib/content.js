export const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";
export const APP_URL = process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3001";
export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export const nav = [
  { href: "/features", label: "Features" },
  { href: "/solutions", label: "Solutions" },
  { href: "/pricing", label: "Pricing" },
  { href: "/security", label: "Security" },
  { href: "/resources", label: "Resources" },
  { href: "/about", label: "About" },
];

export const features = [
  { icon: "Users", title: "Patient records", body: "One profile per patient: history, allergies, medications, documents, visits and bills, in a single timeline.",
    points: ["Searchable profiles and visit timeline", "Allergy and medication lists", "Upload reports and scans", "Everything linked to appointments and invoices"] },
  { icon: "CalendarClock", title: "Appointments and live queue", body: "A shared calendar for every doctor and a queue that updates on every screen the moment a patient arrives.",
    points: ["Day and week calendar per doctor", "Walk-ins, recurring visits, rescheduling and no-show tracking", "Day and week views, per doctor and per location", "Call-next queue for the doctor", "Real-time status on reception and doctor screens"] },
  { icon: "Stethoscope", title: "Consultations", body: "Structured notes for vitals, complaint, examination, assessment and plan, written by the clinician.",
    points: ["Vitals and history in one screen", "Follow-up scheduling from the note", "AI-drafted summaries, clearly labelled and always editable"] },
  { icon: "Pill", title: "Prescriptions", body: "Build a prescription from medicine, dose, frequency and duration, then print it or send it to the patient portal.",
    points: ["Printable and PDF prescriptions", "Reusable medicine templates", "Copy delivered to the patient portal"] },
  { icon: "Receipt", title: "Billing", body: "Invoices for consultations, procedures and medicines with discounts, tax and part-payments.",
    points: ["Paid, partial, pending and refunded states", "Receipts for patients", "Daily and monthly revenue views"] },
  { icon: "MessagesSquare", title: "Notifications and chat", body: "Reminders and updates reach patients and staff in real time, and the team can talk inside the product.",
    points: ["Appointment confirmations and automatic reminders", "In-app notification centre", "Email, SMS and WhatsApp when your clinic connects its own providers", "Staff chat and patient messages"] },
  { icon: "HeartPulse", title: "Patient portal", body: "Patients sign in to see their appointments, prescriptions, shared reports and invoices, book or cancel visits, and message the clinic.",
    points: ["Prescriptions and receipts as PDFs", "Only documents you choose to share are visible", "Book and cancel appointments online", "Secure messaging with the clinic"] },
  { icon: "FileText", title: "Documents and reports", body: "Attach lab results, scans and reports to the patient's record and share them with the patient when you are ready.",
    points: ["PDF and image uploads, checked for type and size", "Shown on the patient timeline", "Optional sharing to the portal with a notification"] },
  { icon: "Package", title: "Inventory", body: "Track medicines and supplies and get an alert when stock runs low.",
    points: ["Stock in and out with a reason", "Reorder levels per item", "Low-stock alerts to the owner"] },
  { icon: "BarChart3", title: "Analytics", body: "See how the clinic is actually running, not how it feels like it is running.",
    points: ["No-show and cancellation rates", "Doctor utilisation and consultation time", "Revenue by service", "New versus returning patients and retention"] },
  { icon: "Bot", title: "ClinicOS Assistant", body: "Ask how something works or tell it what to do. It acts with your permissions and asks before it changes anything.",
    points: ["Answers questions about the system", "Books, reschedules and drafts messages on request", "Confirmation before every change, with a log of what it did", "Never diagnoses or prescribes"] },
  { icon: "Trash2", title: "Deleted history", body: "Deleting moves an item to history where it can be restored. Removing it from history deletes it permanently.",
    points: ["Restore mistakes in one click", "Permanent removal from the database", "Owner-only controls and an audit trail"] },
];

export const solutions = [
  { title: "General physicians", pain: "High patient volume, short visits, repeat prescriptions.", fix: "Fast registration, a one-screen consultation and reusable prescriptions keep the queue moving." },
  { title: "Dentists", pain: "Multi-visit treatment plans and patients who forget follow-ups.", fix: "Follow-up reminders and a visit timeline per patient make treatment plans easy to continue." },
  { title: "Physiotherapists", pain: "Recurring sessions that depend on attendance.", fix: "Recurring appointments, session notes and no-show tracking in one place." },
  { title: "Dermatologists", pain: "Image-heavy records and long-running follow-ups.", fix: "Documents and reports attach to the visit, with follow-up dates the front desk can see." },
  { title: "Multi-doctor clinics", pain: "Shared reception, several calendars, one cash desk.", fix: "Role-based access, per-doctor calendars and consolidated billing and analytics." },
  { title: "Diagnostic centres", pain: "Reports that must reach patients quickly.", fix: "Upload a report once and the patient sees it in their portal with a notification." },
];

export const plans = [
  { id: "starter", name: "Starter", monthly: 0, blurb: "For a solo practitioner getting off paper.", cta: "Start free",
    features: ["1 doctor and 1 staff account", "Up to 200 patients", "Appointments and records", "Prescriptions", "Basic billing", "Deleted history"] },
  { id: "clinic", name: "Clinic", monthly: 7500, blurb: "For a growing clinic with a front desk.", cta: "Start free trial", highlight: true,
    features: ["Up to 5 doctors, unlimited staff", "Unlimited patients", "Live queue and real-time updates", "Patient portal and notifications", "Staff chat", "Analytics", "ClinicOS Assistant"] },
  { id: "group", name: "Group", monthly: 19000, blurb: "For busy multi-doctor practices.", cta: "Start free trial",
    features: ["Unlimited doctors and staff", "Everything in Clinic", "Advanced analytics", "Audit log export", "Priority support"] },
  { id: "enterprise", name: "Enterprise", monthly: null, blurb: "For hospitals and networks with custom needs.", cta: "Talk to us",
    features: ["Custom limits and onboarding", "Data migration help", "Security review support", "Dedicated contact"] },
];

export const faqs = [
  { q: "Is ClinicOS a diagnostic tool?", a: "No. ClinicOS manages the running of a clinic. The AI assistant helps with documentation and administration and always labels its output as a draft. Clinical decisions stay with the clinician." },
  { q: "Can I move my existing patient records in?", a: "You can import patients from a spreadsheet, and the Enterprise plan includes help with larger migrations. Paper records can be added gradually as patients visit." },
  { q: "Who can see patient information?", a: "Only people you give access to. Roles control what each person sees: for example, reception can manage appointments and billing without opening clinical notes unless you allow it." },
  { q: "What happens when I delete something?", a: "It moves to Deleted history, where the owner can restore it. Removing it from history deletes it permanently from our database." },
  { q: "Is ClinicOS HIPAA or GDPR compliant?", a: "We don't claim certifications we haven't earned. Compliance depends on the country you operate in and how the product is configured, and we will publish what we have assessed on the Security page as it happens." },
  { q: "Does it work on a phone?", a: "Yes. The web app is responsive, so reception, doctors and patients can use it from a phone, tablet or computer." },
  { q: "Can I cancel any time?", a: "Yes. You can export your data and cancel from your clinic settings." },
];

export const articles = [
  { slug: "reduce-no-shows-small-clinic", title: "Five ways a small clinic can cut no-shows", date: "2026-09-18", minutes: 4,
    summary: "No-shows cost a clinic its most limited resource: doctor time. These changes help without making patients feel policed.",
    body: [
      "Every empty slot is time a doctor can't get back. Most no-shows are not defiance. Patients forget, get stuck, or can't reach the clinic to cancel.",
      { h: "Remind twice, not once" }, "Send one reminder a day before and one a few hours before. The second one catches people who saw the first and forgot.",
      { h: "Make cancelling easier than ignoring" }, "If cancelling means a phone call during working hours, many people simply don't. A reply to the reminder or a link that frees the slot gives you time to offer it to someone else.",
      { h: "Confirm the slots that matter" }, "Long procedures and first visits are the most expensive to lose. Ask for an explicit confirmation on those.",
      { h: "Keep a waiting list" }, "When a slot opens, a short list of patients who want an earlier time turns a cancellation into a visit.",
      { h: "Measure it" }, "Track the no-show rate by doctor, weekday and time. Patterns usually appear within a month, and you can only fix what you can see.",
    ] },
  { slug: "paper-to-digital-records", title: "Moving a clinic from paper to digital without a shutdown", date: "2026-09-05", minutes: 5,
    summary: "You don't need a weekend of data entry. A gradual migration works better and is safer.",
    body: [
      "The fear behind most delayed migrations is the same: all those paper files. You don't have to type them in before you start.",
      { h: "Start with new information" }, "Register every new patient digitally from day one. Existing patients are added when they next visit, which spreads the effort over weeks and fills the system with records that matter.",
      { h: "Bring in the lists you already have" }, "A spreadsheet of patient names and phone numbers can be imported once, so reception isn't retyping contact details.",
      { h: "Scan what's valuable" }, "Attach important reports and past prescriptions to the patient when they come in, rather than scanning the whole archive.",
      { h: "Train the front desk first" }, "Reception touches the system most. When they are comfortable with registration, booking and billing, doctors adopt it more easily.",
      { h: "Keep paper as a fallback for a short time" }, "Run both for a couple of weeks, then retire the register once the team trusts the new flow.",
    ] },
  { slug: "ai-assistant-in-a-clinic", title: "What an AI assistant should and shouldn't do in a clinic", date: "2026-08-28", minutes: 4,
    summary: "Helpful automation and unsafe automation are separated by a few clear rules.",
    body: [
      "AI is useful in a clinic when it removes administrative friction. It becomes risky when it quietly makes decisions that belong to a clinician.",
      { h: "It should draft, not decide" }, "A summary of a consultation or a patient's last three visits saves time. The clinician reviews and owns the final note.",
      { h: "It should act with the user's permissions" }, "An assistant that can do more than the person asking is a security hole. It should only reach what that user is allowed to reach.",
      { h: "It should ask before changing anything" }, "Booking, rescheduling or deleting should be shown back to the user for confirmation, then recorded in a log.",
      { h: "It should be honest about its limits" }, "If it doesn't know, it should say so. It should never diagnose or prescribe.",
      { h: "Its output should be recognisable" }, "AI-written text must be visibly different from clinician-written records, so nobody mistakes a draft for a decision.",
    ] },
];
