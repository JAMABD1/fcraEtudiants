# FCRA Étudiants — Application design

This document describes the **software design** of the **FCRA Admin** student and community management system (`craStudentManagement`). It is intended for developers onboarding to the codebase or planning changes.

---

## 1. Purpose and scope

The application is an **internal administrative web system** (“FCRA ADMIN — Système de Gestion”) for managing:

- **Students** (`Etudiant`) across multiple tracks: general students, orphans, university, elites, international programs, sortants (leavers), etc.
- **Community structures**: Jamats, Madrassahs, cemeteries (`Cimitiere`), pensions.
- **Staff** (`Personnel`), leave (`Conge`), and related dossiers.
- **Academic and operational data**: grades/notes, attendance (`Presence`), warnings (`Avertissement`), file uploads (dossiers, images).
- **AI chatbot** for assisted interaction, backed by persisted conversations.

The **default UI language** is French (`LANGUAGE_CODE = 'fr'`), with i18n enabled.

---

## 2. High-level architecture

| Layer | Technology |
|--------|------------|
| Web framework | **Django 5.x** |
| Primary app | **`main`** — server-rendered pages, large `views.py`, Django templates |
| API app | **`api`** — **Django REST Framework** (DRF) + chatbot HTTP endpoints |
| Admin UI | **Django Admin** with **Jazzmin** (AdminLTE-style) |
| Public/custom UI | **Tailwind CSS** via **`django-tailwind`** and app **`theme`** |
| Static files | **WhiteNoise** (compressed static storage) |
| Database (default dev) | **SQLite** (`db.sqlite3`) |
| Optional production DB | **MySQL** (configuration exists but is commented in settings; use env-based config rather than hardcoding credentials) |

**Request flow (typical page):**

1. Browser → Django URL (`main.urls` or root `craStudentManagement.urls`).
2. View function in `main/views.py` loads ORM models, builds context.
3. Template extends `main/templates/main/base.html` (Tailwind layout, sidebar, optional Chart.js).
4. Context processors inject **navigation** and **user profile** snippets globally.

**API flow:**

- `/api/` includes `api.urls`: DRF `DefaultRouter` registers ViewSets; separate paths serve the chatbot UI and JSON chat/history APIs.

---

## 3. Project layout (logical)

```
craStudentManagement/     # Project package: settings, root urls, wsgi
main/                     # Core domain: models, views, templates, static
api/                      # REST + chatbot, lightweight models for chat
theme/                    # Tailwind source/build (TAILWIND_APP_NAME)
static/ / staticfiles/    # Collected and vendor assets
media/                    # User uploads (images, dossiers, actes, etc.)
templates/                # Shared templates (e.g. admin overrides)
```

---

## 4. Domain model (data design)

The **`main.models`** module is the **single source of truth** for business entities. Representative models:

| Model | Role |
|--------|------|
| `Etudiant` | Central student record: identity, designation (track), class, centre, status, dates, links to files |
| `CenterAlias` | Maps alternate centre names to a main centre for filtering and consistent UX |
| `Orphelin`, `HistoriqueEtudiant`, `HistoriqueSanteEtudiant` | Specialized / historical student data |
| `NoteEtudiant`, `NoteElite`, `NotesUpload`, `ImageUpload`, `DossierUpload` | Grades and document storage |
| `Presence` | Attendance |
| `Avertissement` | Warnings / disciplinary notes |
| `Personnel`, `Conge`, `DossierPersonnel` | HR and leave |
| `Jamat`, `ArchiveJamat`, `Madrassah`, `ArchiveMadrassah` | Community and education sites |
| `Elite`, `Universite`, `International`, `Sortant`, `Archive` | Program-specific records and archives |
| `Pension`, `DossierPension`, `Paiementpension` | Pension workflows |
| `Cimitiere`, `DossierCimitiere` | Cemetery-related records |
| `Profile` | Extension of Django `User` for app-specific user profile |

**`api.models`** holds only **`ChatConversation`** and **`ChatMessage`**, isolating chat persistence from the main domain.

**Design notes:**

- Many **choices** (centres, designations, classes) are defined as module-level tuples or callables (e.g. `get_centre_choices()`) to merge static and DB-driven alias choices.
- **Foreign keys** tie satellite records to `Etudiant` or `User` as appropriate.
- Some models expose **admin-friendly HTML** via methods using `mark_safe` (tight coupling to Django admin / display layer).

---

## 5. Presentation and UI design

### 5.1 Main application shell (`base.html`)

- **Layout**: Full-height flex container — collapsible **sidebar** + **main content** with gradient background (`bg-slate-50`, gray gradients).
- **Branding**: Logo image, “FCRA ADMIN” title, “Système de Gestion” subtitle.
- **Navigation**: Built from **`menuItems`** (see §6). Supports nested submenus and icons from `/static/image/`.
- **Charts**: **Chart.js** and **chartjs-plugin-datalabels** loaded from CDN.
- **CSS**: **`{% tailwind_css %}`** for Tailwind-built styles; legacy CSS may exist under `main/static/css/`.

### 5.2 Django Admin (Jazzmin)

- Used for back-office operations with a customized theme (**Lux** Bootswatch variant, sidebar/navbar tweaks).
- Custom CSS: `jazzmin/css/admin_layout_fix.css` for layout fixes.

### 5.3 Template context

- **`main.context_processing.default`**: Injects `username` and `profileuser` from `Profile` / `User`.
- **`main.context_processors.menu_context`**: Injects **`menuItems`** and **`role`**.

---

## 6. Navigation and authorization (current behavior)

The sidebar menu is **data-driven** from `main/context_processors.py`:

- Structure: sections with `title`, each containing `items` (flat links or parent items with `hasSubmenu` / `submenu`).
- Each entry includes a **`visible`** list of role strings (`admin`, `teacher`, `student`, `parent`).

**Important implementation detail:** `role` is currently **hardcoded** to `"admin"` in `menu_context`. All menu visibility checks use this value, so **per-user role-based menu hiding is not yet wired to Django groups or `Profile`**. Extending this would mean deriving `role` from the authenticated user and aligning it with your real RBAC model.

---

## 7. URL and view design

- **`main/urls.py`**: Large, **function-based** route map: dashboards, CRUD-style paths for students, notes, personnel, jamat, madrassah, pension, cimetière, etc. Many routes follow patterns like `/resource/`, `/resource/edit`, `/resource/search`, `/resource/filter`.
- **`craStudentManagement/urls.py`**: Mounts `admin/`, main app at `''`, `api/` at `api/`, and **`django_browser_reload`** in development.
- **`api/urls.py`**: DRF router for **`etudiants`**, **`orphelins`**, **`international`**, **`universite`** ViewSets; chatbot HTML and JSON endpoints under `chatbot/`.

Views are concentrated in **`main/views.py`** (very large file). New features should consider **splitting by domain** (separate modules) to keep maintainability.

---

## 8. API design (`api` app)

- **REST**: DRF **`ModelViewSet`** (or equivalent) registrations on the default router; **filtering** via `django-filter` (`DjangoFilterBackend` in `REST_FRAMEWORK` settings).
- **Chatbot**:
  - Page: `/api/chatbot/`
  - JSON: e.g. `/api/chatbot/api/chat/`, conversation list/history/delete endpoints.
- Persistence: **`ChatConversation`** per user, **`ChatMessage`** lines with `is_user` flag.

---

## 9. Static media and uploads

- **STATIC_URL** `/static/` → collected to `staticfiles/` with WhiteNoise.
- **MEDIA_URL** `/media/` → `MEDIA_ROOT` for uploads (student images, dossiers, actes, etc.).
- Root URL config serves media in development via `static(..., document_root=MEDIA_ROOT)`.

---

## 10. Internationalization and time

- **`LANGUAGE_CODE`**: `fr`; **`USE_I18N`**: True.
- Templates use **`{% load i18n %}`** in `base.html` for translatable strings.
- **`TIME_ZONE`**: `UTC`; **`USE_TZ`**: True — store datetimes in UTC; display logic should respect user/locale where needed.

---

## 11. Security and operations (design-relevant)

- Standard Django middleware: sessions, CSRF, auth, security headers, clickjacking protection.
- **DEBUG**, **SECRET_KEY**, and **ALLOWED_HOSTS** in the checked-in settings are **development-oriented**; production must use environment variables, strong secrets, and restricted hosts.
- **Do not commit** database passwords; prefer env-based `DATABASES` configuration.

---

## 12. Extension points (recommended)

1. **Role-based menu**: Replace hardcoded `role` with values from `User` groups, `Profile`, or a dedicated role field.
2. **Thin views**: Move query logic into **services** or **selectors** and split `views.py` by domain.
3. **API versioning / docs**: Add OpenAPI schema if external clients consume `/api/`.
4. **Tests**: Add pytest/Django tests around critical flows (student lifecycle, permissions, uploads).

---

## 13. Glossary

| Term | Meaning |
|------|---------|
| FCRA | Organization context for this management system |
| Jamat / Madrassah | Community and religious education structures |
| Sortant | Student leaving / leaver workflow |
| Elite / Université / International | Program designations for subsets of students |
| Pension | Pension benefit / dossier workflow in-app |

---

*This document reflects the repository structure and settings as of the last update. For exact behavior, always refer to `main/models.py`, `main/views.py`, and `craStudentManagement/settings.py`.*
