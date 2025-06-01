# Calendar-AI-Agent
Here’s a professional and well-documented `README.md` file for your **AI-powered Google Calendar Assistant using Gemini + Flask**:

---

## 📅 AI-Powered Google Calendar Assistant

This project is a **Flask-based intelligent assistant** that integrates **Google Calendar API** with **Gemini (Generative AI)** to understand and process natural language prompts for calendar operations.

> 💡 Say things like:
>
> * “Create a meeting with Shobha tomorrow at 5PM for 30 minutes”
> * “Reschedule meeting with Juhi from 3PM to 6PM tomorrow”
> * “Delete all meetings with Rohan this week”
> * “Who am I meeting today?”

---

## ✨ Features

- ✅ Create calendar events using natural language  
- ✅ Reschedule events by interpreting your intent  
- ✅ Delete events with specified attendees or time ranges  
- ✅ List upcoming events this month  
- ✅ Query your calendar ("Who am I meeting today?", "How many meetings this week?")  
- ✅ Timezone-aware scheduling using your Google Calendar's timezone  
- ✅ Auto-maps attendees to email addresses from local contacts DB  
- ✅ Uses Google Gemini (Flash model) for prompt interpretation  


## 🧠 How It Works

1. **User logs in with Google Calendar** using OAuth2.
2. User enters a **free-form text prompt** (e.g. "Schedule a call with Rahul at 4PM tomorrow").
3. Prompt is sent to **Gemini**, which returns structured JSON (intent, time, attendees, etc.).
4. Flask handles the request using **Google Calendar API** to create/list/delete/update events.
5. Responses are shown back to the user via a clean HTML UI.

---

## 🛠️ Project Structure

```bash
.
├── app.py                      # Main Flask app
├── gemini_agent.py             # Handles prompt → intent translation using Gemini
├── client_secrets.json         # OAuth2 credentials from Google Cloud Console
├── service_account.json        # Gemini authentication
├── templates/
│   ├── create_event.html       # User input form + result display
│   └── index.html              # Welcome page
├── db_utils.py                 # Maps attendee names to email from contacts.db
├── contacts.db                 # SQLite DB for known contacts
```

---

## ⚙️ Setup Instructions

### 1. Clone this repo

```bash
git clone https://github.com/your-repo/calendar-assistant.git
cd calendar-assistant
```

### 2. Create a Python virtual environment (optional)

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> Sample `requirements.txt`:

```txt
flask
google-auth
google-auth-oauthlib
google-api-python-client
google-cloud-aiplatform
pytz
```

### 4. Set up Google credentials

* Create a project on **Google Cloud Console**
* Enable **Google Calendar API** and **OAuth2.0**
* Download the `client_secrets.json` and place it in the root directory
* Also set up a **service account** for Gemini API and save as `service_account.json`

### 5. Add contacts (optional)

Update the `contacts.db` file with your known contacts and their email addresses. The `db_utils.py` file uses this to resolve names into calendar attendee emails.

---

## 🚀 Run the App

```bash
python app.py
```

Then open `http://localhost:5000` in your browser.

---

## 🧪 Example Prompts

### Create:

```
Schedule a meeting with Rohan at 4pm tomorrow for 30 minutes
```

### Reschedule:

```
Reschedule meeting with Juhi from 3 PM to 5 PM today
```

### Delete:

```
Delete all meetings with Shobha this week
```

### Queries:

```
Who am I meeting today?
How many meetings do I have this week?
When is my next meeting with Shobha?
```

---

## 🧠 Gemini Prompting Strategy

The assistant uses a structured prompt with system guidelines to ensure Gemini returns JSON like:

```json
{
  "intent": "reschedule",
  "summary": "Meeting with Juhi",
  "start_time": "2025-05-15T15:00:00+05:30",
  "new_start_time": "2025-05-15T17:00:00+05:30",
  "attendees": ["Juhi"]
}
```

> This is then processed to apply accurate logic for update/delete/list.

---

## 🛡️ Security Notes

* Tokens are stored in `Flask session` (server-side)
* Only tested locally (`OAUTHLIB_INSECURE_TRANSPORT` is enabled)
* For production, use HTTPS and manage secrets via environment variables

---

## 📬 Contact

Made with ❤️ by **Nandini Mundra**
For suggestions, improvements, or demos — reach out anytime.

