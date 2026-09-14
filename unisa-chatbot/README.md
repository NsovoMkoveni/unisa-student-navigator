# UNISA Study Assistant — rule-based chatbot

A 100% deterministic, rule-based chatbot for UNISA students. No AI, no LLMs, no
machine learning, no vector databases, no external APIs. Answers come from
keyword matching and decision trees over hard-coded JSON content.

```
unisa-chatbot/
├── app.py                # Flask server (/, /chat, /feedback, /health)
├── chatbot.py            # Intent matching, flows, session state
├── intents.json          # Intents, keywords, synonyms, responses
├── flows.json            # Multi-step guided flows
├── fallback.json         # Fallback, error and escalation responses
├── requirements.txt      # Flask (+ gunicorn for deployment only)
├── templates/
│   └── index.html        # Chat UI
├── static/
│   ├── style.css         # Chat styling (UNISA blue #003d7c)
│   └── script.js         # Vanilla JS chat logic
├── sessions.json         # Runtime: session state
├── unanswered.json       # Runtime: unmatched questions for weekly review
├── feedback.json         # Runtime: thumbs up/down
└── conversations.log     # Runtime: conversation log
```

**Dependencies justification**
- `Flask` — required by the brief (web server + templating).
- `gunicorn` — production WSGI server, needed only for Render/Railway
  deployment. Delete it from `requirements.txt` if you run locally only.
Everything else uses the Python standard library (`json`, `re`, `uuid`,
`datetime`, `logging`, `os`, `threading`).

---

## 1. Run it locally

```bash
cd unisa-chatbot
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000

Quick checks:

```bash
curl http://localhost:5000/health
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"how do i reset my password","session_id":null}'
```

---

## 2. Deploy free on Render

1. Push this folder to a GitHub repository.
2. On https://render.com choose **New → Web Service** and connect the repo.
3. Settings:
   - Environment: **Python 3**
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app --bind 0.0.0.0:$PORT`
   - Instance type: **Free**
4. Deploy. Render gives you a public `https://<name>.onrender.com` URL.

Railway alternative: **New Project → Deploy from GitHub repo**, start command
`gunicorn app:app --bind 0.0.0.0:$PORT`. Railway injects `$PORT` automatically.

**Important on free hosting:** the filesystem is ephemeral. `sessions.json`,
`unanswered.json`, `feedback.json` and `conversations.log` reset on every
redeploy or sleep cycle. That is fine for v1 — sessions expire after 30
minutes anyway. Download `unanswered.json` before redeploying if you want to
review it, or attach a persistent disk.

---

## 3. Top 20 questions the bot handles

1. How do I claim my UNISA login as a new student?
2. I forgot my password — how do I reset it?
3. What are the password requirements?
4. Why is my myLife email not working?
5. It says "invalid credentials" — what do I do?
6. When do undergraduate applications open and close?
7. When do honours / postgraduate diploma applications close?
8. When do master's and doctoral applications close?
9. What documents do I need for my application?
10. What are the file size and format rules for uploads?
11. How much is the application fee and how do I pay it?
12. How do I check my application status?
13. My qualification is from another country — what do I do?
14. How do I register on myUnisa?
15. How do I add a module?
16. How do I cancel a module and will I get a refund?
17. What is the cooling-off period?
18. What are prerequisites and co-requisites?
19. How do I pay my fees / why is my payment not reflecting?
20. How do I contact admissions, fees, ICT, a regional office, or a human?

---

## 4. How to add a new intent (non-developer guide)

1. Open `intents.json` in any text editor.
2. Find the closing `]` of the `"intents"` list. Add a comma after the last
   intent, then paste this block before the `]`:

```json
{
  "id": "exam_timetable",
  "keywords": ["exam timetable", "exam dates", "when are exams", "timetable",
               "exam schedule", "exam period", "examination dates", "my exams",
               "exam venue", "exam results"],
  "response": {
    "message": "Your exam timetable is published on myUnisa.\nLog in and open the 'Exams' section.",
    "quick_replies": [
      {"label": "Main menu", "value": "menu"}
    ],
    "links": [
      {"label": "myUnisa portal", "url": "https://my.unisa.ac.za"}
    ]
  }
}
```

3. Change `id` (lowercase, underscores, must be unique), the `keywords` (aim
   for 10+ ways students actually phrase it, all lowercase), and the
   `message`. Use `\n` for a new line.
4. Save the file and restart the server (`Ctrl+C`, then `python app.py`).
5. Test by typing one of your keywords in the chat.

Rules of thumb:
- Every `{` needs a matching `}`, every item in a list needs a comma between
  it and the next — but no comma after the last one.
- Paste the file into https://jsonlint.com if the bot fails to start; it will
  point at the broken line.
- To make a topic open a guided step-by-step conversation instead of a single
  answer, add `"start_flow": "login_flow"` next to `"response"` and define the
  steps in `flows.json`.
- Review `unanswered.json` weekly — every question in there is a missing
  intent or a missing keyword.

---

## 5. Recommended next features (not built)

1. Admin page to edit `intents.json` without touching files.
2. Weekly email digest of `unanswered.json`.
3. Analytics dashboard: most-asked topics, fallback rate, flow drop-off.
4. Spelling correction on input (pure `difflib`, still no AI).
5. isiZulu / Sesotho / Afrikaans response sets.
6. WhatsApp Business channel using the same rule engine.
7. Per-message thumbs up/down instead of per-session feedback.
8. SQLite for sessions and logs when the traffic outgrows JSON files.
9. Conversation transcript email to the student.
10. Scheduled content-review reminder for every `[VERIFY WITH UNISA]` marker.

---

## Content accuracy

Verified facts baked into the content:
- Undergraduate applications: 17 August – 9 October
- Honours / PG Diploma applications: 17 August – 9 October
- Master's / Doctoral applications: 1 September – 20 November
- Uploads: max 2MB per file, PDF/DOC/TIF only, one file per document
- Password: 12+ chars, uppercase, lowercase, number, special character
- myLife email activation: up to 24 hours after claiming the UNISA login
- Cooling-off: 10 calendar days from registration activation for a full refund
- Toll-free: 0800 00 1870 · WhatsApp: +27 12 431 2500

Anything uncertain is marked `[VERIFY WITH UNISA]` in `intents.json` and
`flows.json`. Search for that marker and replace it with confirmed details
before going live.
