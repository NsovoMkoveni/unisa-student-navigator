# UNISA Student Navigator

I want you to build a complete, production-ready rule-based chatbot for UNISA 
(University of South Africa) that helps prospective and current students navigate 
the university's website and processes.

 

## CRITICAL CONSTRAINTS (DO NOT DEVIATE)

 

1. DO NOT use LLMs, AI models, agents, vector databases, or machine learning of any kind.
2. DO NOT use LangChain, LlamaIndex, OpenAI API, Anthropic API, or any AI service.
3. This must be a 100% rule-based chatbot using ONLY:
   - Keyword matching
   - Decision trees
   - Pre-written (hard-coded) responses stored in JSON
   - Simple state management
4. The bot must be fully deterministic — the same input always produces the same output.
5. The bot must run without any external API calls or paid services.

 

## TECH STACK (MANDATORY)

 

- Backend: Python 3.11+ with Flask
- Frontend: Single HTML file with vanilla JavaScript and CSS (no React, no frameworks)
- Data storage: JSON files (no database required for v1)
- Dependencies: Only Flask and standard Python libraries. No other pip packages unless 
  absolutely necessary (and justify each one).

 

## PROJECT STRUCTURE

 

Create the following file structure:

 

unisa-chatbot/
├── app.py                  # Flask server with /chat endpoint
├── chatbot.py              # Core bot logic (intent matching, state management)
├── intents.json            # All intents, keywords, and responses
├── flows.json              # Multi-step conversation flows
├── fallback.json           # Fallback and human escalation responses
├── templates/
│   └── index.html          # Chat UI
├── static/
│   ├── style.css           # Chat styling
│   └── script.js           # Frontend chat logic
├── sessions.json           # (Runtime) User session storage
└── README.md               # Setup and deployment instructions

 

## FUNCTIONAL REQUIREMENTS

 

### 1. Intent Matching Engine (chatbot.py)

 

- Accept user input as a string
- Convert to lowercase
- Score each intent in intents.json based on how many of its keywords appear 
  in the user input
- Pick the highest-scoring intent
- If no intent scores above 0, return the fallback intent
- Support partial keyword matches (e.g., "login" matches "login", "log in", "logging in")
- Support synonym lists per keyword

 

### 2. Conversation State Management

 

- Track each user's session using a unique session_id (generated on first message)
- Store session state in sessions.json with: current_flow, current_step, timestamp
- When a user is in the middle of a flow, numeric replies (1, 2, 3) or button clicks 
  should advance to the next step in the flow
- Provide a global "menu" command that resets to the main menu
- Provide a global "human" command that shows human contact options
- Sessions expire after 30 minutes of inactivity

 

### 3. Response Format

 

Every bot response must be a JSON object with this structure:

 

{
  "message": "The text response shown to the user",
  "quick_replies": [
    {"label": "Button text", "value": "value to send back"}
  ],
  "links": [
    {"label": "Link text", "url": "https://..."}
  ],
  "session_id": "abc123"
}

 

The frontend must render:
- message as chat bubble text (support \n line breaks)
- quick_replies as clickable buttons below the message
- links as clickable buttons that open in a new tab

 

### 4. Intents to Implement (intents.json)

 

Build comprehensive intents covering these topics. Include at least 10 keyword 
variations per intent to handle how real students type:

 

**LOGIN & ACCOUNTS**
- login_help (main entry)
- login_new_student (claim UNISA login)
- login_returning_student (reset password)
- mylife_email (activation, 24-hour wait, troubleshooting)
- password_requirements (12+ chars, uppercase, lowercase, number, special char)
- login_invalid_credentials (troubleshooting steps)

 

**APPLICATIONS**
- application_help (main entry)
- application_undergraduate (dates: 17 Aug – 9 Oct; requirements)
- application_honours (dates: 17 Aug – 9 Oct; requirements)
- application_masters_doctoral (dates: 1 Sept – 20 Nov; supervisor contact)
- application_documents (certified copies, ID, transcripts, sworn translations)
- application_upload_specs (2MB max, PDF/DOC/TIF, one file per document)
- application_fee (payment methods, confirmation)
- application_status (how to check status)
- foreign_qualifications (SAQA evaluation process)

 

**REGISTRATION**
- registration_help (main entry)
- registration_steps (how to register on myUnisa)
- add_module (step-by-step)
- cancel_module (step-by-step, cooling-off period)
- cooling_off_period (10 calendar days for full refund)
- prerequisites_corequisites (explanation + how to check)
- re_registration (yearly requirement, fees)

 

**FEES & FUNDING**
- fees_help (main entry)
- fee_payment_methods
- refund_policy
- nsfas_info (NSFAS funding basics, link to NSFAS site)
- fee_errors (common payment issues)

 

**SUPPORT & ESCALATION**
- contact_help (main entry)
- contact_admissions
- contact_fees
- contact_ict
- contact_regional_offices
- contact_nsrc (student representatives)
- human_escalation (toll-free, WhatsApp, email)

 

**GENERAL**
- greeting ("hi", "hello", "hey")
- menu (show main menu)
- thanks ("thank you", "thanks")
- goodbye ("bye", "goodbye")
- help (what the bot can do)

 

### 5. Multi-Step Flows (flows.json)

 

Build guided decision trees for these flows. Each flow is an array of steps 
with a question, options, and next-step mapping:

 

- **login_flow**: new vs returning → specific instructions
- **application_flow**: qualification level → dates → requirements → documents
- **registration_flow**: new vs returning → module selection → prerequisites
- **document_upload_flow**: which document → format check → upload steps
- **contact_flow**: which department → contact details

 

Each step must have:
- id
- message
- quick_replies (options)
- next (mapping of option value → next step id)
- optional: links

 

### 6. Fallback Handling (fallback.json)

 

When the bot doesn't understand:
- Show: "I'm not sure I understood that. Here's what I can help with:"
- Display the main menu as quick replies
- Include: "Type 'human' to contact support"
- Log the unanswered question to unanswered.json for weekly review

 

### 7. Human Escalation

 

When user types "human" or clicks the "Contact a human" button, show:

 

- UNISA toll-free: 0800 00 1870
- WhatsApp: +27 12 431 2500
- Email: [relevant department emails]
- Link: https://www.unisa.ac.za/sites/corporate/default/Contact-us
- Regional office locator link

 

### 8. Frontend Requirements (index.html + script.js + style.css)

 

Build a clean, mobile-first chat UI:

 

- Chat window with scrolling message history
- User messages on the right (blue bubble)
- Bot messages on the left (grey bubble)
- Quick reply buttons appear below the latest bot message
- Link buttons appear below the latest bot message (open in new tab)
- Text input at the bottom with a "Send" button
- "Menu" button that always resets to main menu
- "Restart" button that clears the conversation
- Typing indicator ("Bot is typing...") shown for 500ms before bot responds
- Responsive design (works on mobile and desktop)
- UNISA brand colours: use a professional blue (#003d7c) as primary

 

### 9. Flask Backend (app.py)

 

Endpoints:

 

- GET / → serves index.html
- POST /chat → accepts {"message": "...", "session_id": "..."} 
  and returns the response JSON object
- POST /feedback → accepts {"session_id": "...", "helpful": true/false}
- GET /health → returns {"status": "ok"}

 

Include:
- Basic error handling (return a friendly error message, never crash)
- Logging of all conversations to conversations.log
- CORS enabled for local development

 

### 10. Content Accuracy

 

All information in intents.json and flows.json must reflect UNISA's actual 
processes. Use these verified facts:

 

- Undergraduate applications: 17 August – 9 October
- Honours/Postgrad Diploma applications: 17 August – 9 October
- Master's/Doctoral applications: 1 September – 20 November
- Document upload: max 2MB per file, PDF/DOC/TIF only, one file per document
- Password: 12+ characters, uppercase, lowercase, number, special character
- myLife email activation: up to 24 hours after claiming UNISA login
- Cooling-off period: 10 calendar days from registration activation for full refund
- Toll-free: 0800 00 1870
- WhatsApp: +27 12 431 2500

 

For anything else, use placeholder text clearly marked with [VERIFY WITH UNISA] 
so the user can update it before deployment.

 

## DELIVERABLES

 

Provide the complete contents of every file listed in the project structure. 
Do not skip any file. Do not use "..." or "rest of code here" — write every 
line in full.

 

After the code, provide:

 

1. Step-by-step setup instructions (how to run locally)
2. Deployment instructions for a free hosting option (Render or Railway)
3. A list of the top 20 questions the bot currently handles
4. A guide on how to add a new intent (for non-developers)
5. A list of recommended next features (but do not build them yet)

 

## QUALITY REQUIREMENTS

 

- Code must be clean, commented, and PEP-8 compliant
- Every function must have a docstring
- All JSON files must be valid and well-formatted
- The bot must handle edge cases: empty input, very long input, special characters, 
  rapid-fire messages
- The bot must never return an empty response
- The bot must never crash — always fall back gracefully

 

## WHAT NOT TO DO

 

- Do not add any AI, LLM, or ML features
- Do not add a database (use JSON files)
- Do not use React, Vue, Angular, or any JS framework
- Do not add authentication or user accounts
- Do not add features not explicitly listed above
- Do not use external APIs

 

Build the complete chatbot now. Start with the file structure, then provide 
each file in full.

This project was built with [Lovable](https://lovable.dev).

## Build with Lovable

Continue developing this project in the [Lovable editor](https://lovable.dev/projects/ceb7472a-b21f-4839-bb45-5112b674fb49).

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: every change made in Lovable is committed straight to this repository.
- **Full ownership**: this code is yours. Push to `main` on GitHub and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```
