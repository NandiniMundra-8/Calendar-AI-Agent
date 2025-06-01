import os
import google.generativeai as genai

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "service_account.json"  

# Configure the API using the project and location
# genai.configure(project="sureel-test", location="us-central1")
model = genai.GenerativeModel(model_name="gemini-2.0-flash-001")  # Use the correct model name here
# Example input: asking the model a question
response = model.generate_content("Can I use you to create event on my google calender")
print(response.text)
# gemini_agent.py

# the additional routes I created 
@app.route("/create_event", methods=["GET", "POST"])
def create_event():
    if request.method == "GET":
        return render_template("create_event.html")

    user_timezone = session.get("user_timezone", "UTC")


    prompt = request.form.get("prompt")
    if not prompt:
        return "Prompt required!"

    credentials_dict = session.get("credentials")
    if not credentials_dict:
        return redirect(url_for("login"))

    credentials = Credentials(**credentials_dict)

    # Interpret prompt using Gemini
    event_data = interpret_event_prompt(prompt)
    print(f"Interpreted event data: {event_data}")

    # Check if the required keys are present in the response
    if not event_data or "summary" not in event_data or "start_time" not in event_data or "end_time" not in event_data:
        return "Could not understand your prompt. Please ensure the event details are clear."

    try:
        # Build the calendar service
        service = build("calendar", "v3", credentials=credentials)

        # Create event using interpreted details
        event_body = {
            "summary": event_data["summary"],
            "start": {"dateTime": event_data["start_time"], "timeZone": user_timezone},
            "end": {"dateTime": event_data["end_time"], "timeZone": user_timezone}
        }
        # Insert event into the user's Google Calendar
        created_event = service.events().insert(calendarId='primary', body=event_body).execute()
        return f"Event created: <a href='{created_event.get('htmlLink')}' target='_blank'>View Event</a>"

    except Exception as e:
        # Handle any errors that might occur when interacting with the Google Calendar API
        return f"Failed to create event: {str(e)}"

@app.route("/reschedule_event", methods=["POST"])
def reschedule_event():
    user_timezone = session.get("user_timezone", "UTC")
    credentials_dict = session.get("credentials")
    if not credentials_dict:
        return redirect(url_for("login"))

    prompt = request.form.get("prompt")
    if not prompt:
        return "Prompt required!"

    credentials = Credentials(**credentials_dict)
    service = build("calendar", "v3", credentials=credentials)

    event_data = interpret_event_prompt(prompt, user_timezone=user_timezone)
    if not event_data or "summary" not in event_data:
        return "Could not understand the reschedule request."

    try:
        # 1. Find the event by title
        now = datetime.utcnow().isoformat() + "Z"
        events_result = service.events().list(
            calendarId='primary',
            timeMin=now,
            maxResults=10,
            singleEvents=True,
            orderBy='startTime',
            q=event_data["summary"]  # Use summary to search
        ).execute()

        events = events_result.get('items', [])
        if not events:
            return "Event not found to reschedule."

        event = events[0]  # Just take the first match for now

        # 2. Update its time
        event['start'] = {"dateTime": event_data["start_time"], "timeZone": user_timezone}
        event['end'] = {"dateTime": event_data["end_time"], "timeZone": user_timezone}

        updated_event = service.events().update(
            calendarId='primary',
            eventId=event['id'],
            body=event
        ).execute()

        return f"Event rescheduled: <a href='{updated_event.get('htmlLink')}' target='_blank'>View Event</a>"

    except Exception as e:
        return f"Failed to reschedule event: {str(e)}"
