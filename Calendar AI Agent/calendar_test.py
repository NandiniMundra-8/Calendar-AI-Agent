from flask import Flask, redirect, request, session, url_for,flash
from flask import render_template
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os
import json
import pytz
from datetime import datetime,timedelta
from google.cloud import aiplatform
from gemini_agent import interpret_event_prompt  
from google.oauth2.credentials import Credentials 
from db_utils import get_email_by_name
import sqlite3
import secrets


app = Flask(__name__)
app.secret_key = secrets.token_urlsafe(16)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # Only for testing locally
CLIENT_SECRETS_FILE = "client_secrets.json"
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/calendar"
]

REDIRECT_URI = "http://localhost:5000/callback"

conn = sqlite3.connect("D:/00-Research/Calendar AI Agent/contacts.db")


@app.route("/")
def index():
    if not session.get("credentials"):
        return redirect(url_for("login"))
    return render_template("index.html")


@app.route("/login")
def login():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    # Get authorization URL and state
    authorization_url, state = flow.authorization_url(prompt='consent')
    session['state'] = state  # Store state in session for later validation
    return redirect(authorization_url)

@app.route("/callback")
def callback():
    try:
        state = session['state']
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        flow.fetch_token(authorization_response=request.url, state=state)
        credentials = flow.credentials
        session['credentials'] = credentials_to_dict(credentials)

        
        service = build("calendar", "v3", credentials=credentials)
        calendar_info = service.calendars().get(calendarId='primary').execute()
        user_timezone = calendar_info.get("timeZone", "UTC")
        session['user_timezone'] = user_timezone  # store for later use

        print(f"User's default calendar timezone: {user_timezone}")


        return redirect(url_for('handle_prompt'))


    except Exception as e:
        return f"Error during callback: {str(e)}"
      

@app.route("/calender")
def get_calender_events():
    
    try: 
        credentials = session.get('credentials')
        if credentials is None:
            return redirect(url_for('login'))

        credentials = Credentials(**credentials)
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())

        
        # Build Google Calendar API service
        service = build('calendar', 'v3', credentials=credentials)
        # Get current date
        today = datetime.utcnow()

        # Calculate start and end of the current month
        start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        next_month = today.replace(month=today.month % 12 + 1, day=1)
        end_of_month = next_month - timedelta(seconds=1)

        time_min = start_of_month.isoformat() + "Z"  # Start of the month
        time_max = end_of_month.isoformat() + "Z"  # End of the month

        # Fetch events for the current month

        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            maxResults=10,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])

        if not events:
            return "No events found for this month."

        # Display the events
        event_list = "<h1>Upcoming Events:</h1><ul>"
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            event_list += f"<li>{start} - {event['summary']}</li>"
        event_list += "</ul>"

        return event_list

    except Exception as e:
        return f"Error fetching calendar events: {str(e)}"
   

def credentials_to_dict(creds):
    """Convert the credentials to a dictionary to store in session."""
    return {
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': creds.scopes
    
    }

@app.route("/handle_prompt", methods=["GET", "POST"])
def handle_prompt():
    if not session.get("credentials"):
        return redirect(url_for("login")) # Redirect to login if not logged in
    

    user_timezone = session.get("user_timezone", "UTC")  # Get timezone from session - MOVED OUTSIDE THE IF BLOCK

    if request.method == "GET":
        return render_template("create_event.html")  # same UI

    prompt = request.form.get("prompt")
    if not prompt:
        return "Prompt required!"

    credentials_dict = session.get("credentials")
    if not credentials_dict:
        return redirect(url_for("login"))
    
    credentials = Credentials(**credentials_dict)
    service = build("calendar", "v3", credentials=credentials)

    event_data = interpret_event_prompt(prompt, user_timezone=user_timezone)
    if not event_data or "intent" not in event_data:
        return "Couldn't understand intent. Try rephrasing."

    intent = event_data.get("intent")

    try:
        if intent == "create":
            event_body = {
                "summary": event_data["summary"],
                "start": {"dateTime": event_data["start_time"], "timeZone": user_timezone},
                "end": {"dateTime": event_data["end_time"], "timeZone": user_timezone}
            }

            # Check for attendees (names) and resolve emails from contacts DB
            attendee_names = event_data.get("attendees", [])
            attendees = []

            for name in attendee_names:
                email = get_email_by_name(name)
                if email:
                    attendees.append({"email": email})

            if attendees:
                event_body["attendees"] = attendees

            created_event = service.events().insert(calendarId='primary', body=event_body).execute()
            flash(f"Event created: <a href='{created_event.get('htmlLink')}' target='_blank'>View Event</a>")
            return redirect(url_for("handle_prompt"))
            
                

        elif intent == "list":
            now = datetime.utcnow()
            end_of_month = (now.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(seconds=1)
            events_result = service.events().list(
                calendarId='primary',
                timeMin=now.isoformat() + "Z",
                timeMax=end_of_month.isoformat() + "Z",
                maxResults=10,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])
            if not events:
                return "No upcoming events found."

            html = "<h2>📅 Upcoming Events:</h2><ul>"
            for event in events:
                title = event.get("summary", "Untitled Event")
                link = event.get("htmlLink", "#")
                start = event["start"].get("dateTime", event["start"].get("date"))
                end = event["end"].get("dateTime", event["end"].get("date"))
                attendees = ", ".join([a.get("email") for a in event.get("attendees", [])]) or "None"

                # Convert to readable datetime
                start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
                duration = end_dt - start_dt

                html += f"""
                    <li>
                        <strong>{title}</strong><br>
                        🔗 <a href="{link}" target="_blank">View Event</a><br>
                        👥 Attendees: {attendees}<br>
                        🕒 Start: {start_dt.strftime('%B %d, %Y – %I:%M %p')}<br>
                        ⏱ Duration: {int(duration.total_seconds() // 60)} minutes
                    </li><br>
                """
            html += "</ul>"
            flash(html)
            return redirect(url_for("handle_prompt"))
           

        elif intent == "delete":
            # Get current time and timezone
            now = datetime.utcnow()
            start_time = event_data.get("start_time")
            end_time = event_data.get("end_time")

            # Default range if not provided — today only
            if not start_time:
                start_time = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + "Z"
            if not end_time:
                end_time = now.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat() + "Z"

            events_result = service.events().list(
                calendarId='primary',
                timeMin=start_time,
                timeMax=end_time,
                maxResults=20,
                singleEvents=True,
                orderBy='startTime',
                q=event_data["summary"]  # search with event title like "meeting"
            ).execute()

            events = events_result.get('items', [])

            if not events:
                flash(" No matching events found to delete.")
                return redirect(url_for("handle_prompt"))

            deleted_count = 0
            target_names = [name.lower() for name in event_data.get("attendees", [])]

            for event in events:
                matched = True
                if target_names:
                    attendee_emails = [att.get("email", "").lower() for att in event.get("attendees", [])]
                    # If at least one attendee name matches email in DB, keep
                    matched = any(get_email_by_name(name).lower() in attendee_emails for name in target_names)

                if matched:
                    service.events().delete(calendarId='primary', eventId=event['id']).execute()
                    deleted_count += 1

            if deleted_count:
                flash(f" Deleted {deleted_count} event(s).")
            else:
                flash(" No event matched the attendees provided.")
            return redirect(url_for("handle_prompt"))
        
        elif intent == "reschedule":
            #  relevant data from parsed event JSON
            target_start = event_data["start_time"]
            target_end = event_data.get("end_time")
            attendee_names = event_data.get("attendees", [])

            # Convert start and end time to UTC for accurate event search
            start_dt = datetime.fromisoformat(target_start).astimezone(pytz.utc)
            end_dt = datetime.fromisoformat(target_end).astimezone(pytz.utc) if target_end else start_dt + timedelta(hours=1)
            start_iso = start_dt.isoformat().replace("+00:00", "Z")
            end_iso = end_dt.isoformat().replace("+00:00", "Z")

            # Search for events in the given time window
            events_result = service.events().list(
                calendarId='primary',
                timeMin=start_iso,
                timeMax=end_iso,
                maxResults=20,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])
            if not events:
                flash("No event found to reschedule in that time window.")
                return redirect(url_for("handle_prompt"))

            attendee_emails = [get_email_by_name(name).lower() for name in attendee_names if get_email_by_name(name)]

            # Match event based on attendees
            matched_event = None
            for event in events:
                event_attendees = [att.get("email", "").lower() for att in event.get("attendees", [])]
                if not attendee_emails or any(email in event_attendees for email in attendee_emails):
                    matched_event = event
                    break

            if not matched_event:
                flash("No matching event found with the given attendees.")
                return redirect(url_for("handle_prompt"))

            # Get original event duration
            original_start = datetime.fromisoformat(matched_event['start']['dateTime'])
            original_end = datetime.fromisoformat(matched_event['end']['dateTime'])
            duration = original_end - original_start

            # New start and end times (if end time missing, use original duration)
            new_start = datetime.fromisoformat(event_data["start_time"])
            new_end = datetime.fromisoformat(event_data["end_time"]) if event_data.get("end_time") else new_start + duration

            matched_event["start"] = {
                "dateTime": new_start.isoformat(),
                "timeZone": user_timezone
            }
            matched_event["end"] = {
                "dateTime": new_end.isoformat(),
                "timeZone": user_timezone
            }

            # Update attendees if provided
            updated_attendees = []
            for name in attendee_names:
                email = get_email_by_name(name)
                if email:
                    updated_attendees.append({"email": email})

            if updated_attendees:
                matched_event["attendees"] = updated_attendees

            # Update the event in Google Calendar
            updated_event = service.events().update(
                calendarId='primary',
                eventId=matched_event['id'],
                body=matched_event
            ).execute()

            flash(f"Event rescheduled: <a href='{updated_event.get('htmlLink')}' target='_blank' style='color: white;'>View Event</a>")
            return redirect(url_for("handle_prompt"))


        elif intent == "query":
            question_type = event_data.get("question_type")
            attendee_names = event_data.get("attendees", [])
            start_time = event_data.get("start_time")
            end_time = event_data.get("end_time")

            filters = {
                "calendarId": "primary",
                "singleEvents": True,
                "orderBy": "startTime",
                "timeMin": datetime.utcnow().isoformat() + "Z",
                "maxResults": 50
            }

            if question_type == "next_event_with_person":
                filters["q"] = " ".join(attendee_names)

            elif question_type == "count_events_this_week":
                filters["timeMin"] = start_time or datetime.utcnow().isoformat() + "Z"
                filters["timeMax"] = end_time

            elif question_type == "meetings_today":
                today = datetime.now(pytz.timezone(user_timezone))
                start = today.replace(hour=0, minute=0, second=0, microsecond=0)
                end = start + timedelta(days=1)
                filters["timeMin"] = start.isoformat()
                filters["timeMax"] = end.isoformat()

            events = service.events().list(**filters).execute().get("items", [])

            if question_type == "next_event_with_person":
                if events:
                    next_event = events[0]
                    start = next_event["start"].get("dateTime", next_event["start"].get("date"))
                    title = next_event.get("summary", "Untitled")
                    flash(f" Next meeting with {', '.join(attendee_names)} is: <strong>{title}</strong> at {start}")
                else:
                    flash(f"No upcoming meetings with {', '.join(attendee_names)} found.")

            elif question_type == "count_events_this_week":
                flash(f"You have {len(events)} meetings this week.")

            elif question_type == "meetings_today":
                names = []
                for event in events:
                    attendees = event.get("attendees", [])
                    for a in attendees:
                        if "email" in a:
                            names.append(a["email"].split("@")[0])
                flash(f"You are meeting: {', '.join(set(names)) or 'No one'} today.")

            return redirect(url_for("handle_prompt"))

        else:
            return "Unrecognized intent."

    except Exception as e:
        print("Full exception:", e)
        return f"Failed to handle request: {str(e)}"


if __name__ == "__main__":
    app.run("localhost", 5000, debug=True)
