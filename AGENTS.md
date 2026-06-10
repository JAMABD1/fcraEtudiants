# FCRA Agents — Simple Guide

This project has **one AI agent**: the **FCRA Chatbot**.  
It answers questions about students, orphans, international students, and university records.

The agent does **not** guess numbers. It always calls a **tool** first, then writes a clear answer (and sometimes a chart).

---

## The agent

| | |
|---|---|
| **Name** | FCRA Chatbot Assistant |
| **Model** | Google Gemini `gemini-2.5-flash` |
| **Role** | Search student data and show statistics in plain language |
| **Data source** | External FCRA REST API (`EXTERNAL_API_BASE` in `api/views.py`) |
| **Auth** | User must be **logged in** to use the chat API |
| **Memory** | Saves conversations in the database (`ChatConversation`, `ChatMessage`) |

### What it can do

- Find students, orphans, internationals, or university rows with filters
- Count and group data (by centre, genre, age, class, etc.)
- Show the **5 first / 5 last** records when you ask (uses `limit` + `order_by`)
- Show **student photos** in answers when relevant
- Build **Chart.js** graphs (pie, bar, doughnut) for statistics

### What it is told to do (rules)

1. Understand the question  
2. **Call a tool** before answering  
3. Explain the results in text  
4. Add a chart only when statistics are useful  

**Categories it knows:** Étudiants, Sortants, Orphelins, Universités, Internationaux.

---

## Tools (9 functions)

These are Python functions registered with Gemini. The agent picks the right one automatically.

### Search tools — return lists of records

| Tool | Purpose | Main filters |
|------|---------|--------------|
| **`get_etudiants`** | Search students | `nom`, `identifiant`, `genre`, `centre`, `Class`, `fillier`, `designation`, `status`, dates, parents, `limit`, `order_by` |
| **`get_orphelins`** | Search orphans | `nom`, `decede`, `centre`, `Class`, `genre`, `age`, `acte_de_dece`, `fillier`, `limit`, `order_by` |
| **`get_internationaux`** | Search international students | `pays`, student fields, `date_depart`, `duree_sejour`, `limit`, `order_by` |
| **`get_universites`** | Search university-track students | `email`, student fields, entry/exit dates, `limit`, `order_by` |

**Tips**

- `limit=5` + `order_by="-date_entre"` → 5 most recent  
- `limit=5` + `order_by="date_entre"` → 5 oldest  
- Genre: `F` / `M` (also accepts fille, garçon, etc.)

---

### Statistics tools — return counts and breakdowns

| Tool | Purpose | Returns (examples) |
|------|---------|---------------------|
| **`get_statistics`** | All-in-one stats | Pick a `category`: `etudiants`, `orphelins`, `internationaux`, `universites`, `sortants`, `all` |
| **`get_statistics_etudiant`** | Student stats only | Total, by centre, genre, class, age, etc. |
| **`get_statistics_orphelin`** | Orphan stats | Total, deceased/alive, by age, centre, genre, class… |
| **`get_statistics_international`** | International stats | Total, by country, genre, centre, stay duration… |
| **`get_statistics_universite`** | University stats | Total, with/without email, by genre, centre, age… |

**Age filter**

- Fixed buckets: `3-10`, `11-14`, `15-18`, …  
- Exact range: `age=10-15` for “students between 10 and 15 years old”

---

## REST API

Base URL: **`/api/`**

### 1. Chatbot (agent)

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| GET | `/api/chatbot/` | No | Chat page (HTML) |
| POST | `/api/chatbot/api/chat/` | Yes | Send a message to the agent |
| GET | `/api/chatbot/api/conversations/` | Yes | List your past chats |
| GET | `/api/chatbot/api/conversations/<id>/` | Yes | Messages in one chat |
| DELETE | `/api/chatbot/api/conversations/<id>/delete/` | Yes | Delete one chat |
| DELETE | `/api/chatbot/api/conversations/delete-all/` | Yes | Delete all your chats |

**Chat request example**

```http
POST /api/chatbot/api/chat/
Content-Type: application/json

{
  "message": "Combien d'étudiants actifs à Andakana ?",
  "conversation_id": 12
}
```

**Chat response example**

```json
{
  "reply": "Il y a ...",
  "conversation_id": 12,
  "conversation_title": "Combien d'étudiants actifs..."
}
```

- `conversation_id` is optional on first message (a new chat is created).
- The server adds today’s date to help age calculations.

---

### 2. Statistics (direct API, no AI)

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| GET | `/api/statistics/` | No* | Same stats as the agent tools |

**Examples**

```
GET /api/statistics/?category=etudiants
GET /api/statistics/?category=orphelins&centre=Andakana
GET /api/statistics/?category=etudiants&age=15-18
GET /api/statistics/?category=all
```

**Response shape**

```json
{
  "success": true,
  "category": "etudiants",
  "data": { ... },
  "filters_applied": { "centre": "Andakana" }
}
```

\*Check production permissions; lock down if needed.

---

### 3. Read-only data (CRUD: list + detail only)

| Resource | List | Detail |
|----------|------|--------|
| Students | `GET /api/etudiants/` | `GET /api/etudiants/{identifiant}/` |
| Orphans | `GET /api/orphelins/` | `GET /api/orphelins/{id}/` |
| International | `GET /api/international/` | `GET /api/international/{id}/` |
| University | `GET /api/universite/` | `GET /api/universite/{id}/` |

Use query parameters to filter (e.g. `?centre=Andakana&genre=F`).

The chatbot tools call the **same data** on the external server:

```
{EXTERNAL_API_BASE}/api/etudiants/
{EXTERNAL_API_BASE}/api/orphelins/
{EXTERNAL_API_BASE}/api/international/
{EXTERNAL_API_BASE}/api/universite/
```

Default external base: `http://102.16.39.246:11802` (see `api/views.py`).

---

## How it works (simple flow)

```
User question
    ↓
POST /api/chatbot/api/chat/
    ↓
Gemini (gemini-2.5-flash)
    ↓
Calls a tool (e.g. get_statistics_etudiant)
    ↓
Tool → HTTP GET → External /api/...
    ↓
Gemini writes answer (+ optional Chart.js JSON)
    ↓
Saved in ChatMessage → returned to user
```

---

## Setup

| Variable | Required | Role |
|----------|----------|------|
| `GEMINI_API_KEY` | Yes | Google Gemini API key (`.env`) |
| `EXTERNAL_API_BASE` | Optional | Where tools fetch student data (hardcoded default in code) |

---

## Example questions for the agent

- “Combien d’étudiants actifs ?”
- “Les 5 derniers étudiants inscrits”
- “Répartition des orphelins par centre”
- “Étudiants internationaux en Inde”
- “Statistiques université avec email”
- “Étudiants entre 10 et 15 ans à Andakana”

For more test ideas, see `student_challenge_questions.md`.

---

## Files to know

| File | Content |
|------|---------|
| `api/views.py` | Agent model, all 9 tools, chat + stats endpoints |
| `api/urls.py` | API routes |
| `api/models.py` | `ChatConversation`, `ChatMessage` |
| `README.md` | Full project + API documentation |
