ANNIVERSARY WEBSITE + PRIVATE BACKEND
====================================

The original website content, HTML layout, CSS, photos, animations and background music are preserved from the separated project. The script adds backend analytics and a visitor-facing analytics notice/choice. Tracking starts only if the visitor chooses “Allow analytics”; choosing “Continue without analytics” leaves the website usable without sending analytics events.

WHAT IS INCLUDED
- Original website files: index.html, styles.css, script.js, assets/
- Flask backend: app.py
- SQLite database stored under data/events.sqlite3 by default
- Private admin dashboard at /admin (server-side username/password)
- Activity timeline, anonymous repeat-visit grouping, question answer counts, envelope opening time, approximate visit duration, reading time, and CSV export

RUN LOCALLY ON WINDOWS
1. Install Python 3.10 or newer.
2. Extract this folder.
3. Open Command Prompt in this folder and run:
   py -m venv .venv
   .venv\Scripts\activate
   py -m pip install -r requirements.txt
4. Set private credentials in the same terminal (change the password):
   set ADMIN_USERNAME=admin
   set ADMIN_PASSWORD=use-a-long-private-password
   set SESSION_SECRET=use-a-long-random-secret
5. Start: py app.py
6. Website: http://127.0.0.1:5000
7. Private dashboard: http://127.0.0.1:5000/admin

HOSTING
GitHub Pages is static-only and cannot run this Python backend. Keep the project in GitHub if desired, but deploy the full folder to a Python-compatible host. Install command: pip install -r requirements.txt. Start command: gunicorn app:app. Configure ADMIN_USERNAME, ADMIN_PASSWORD, SESSION_SECRET, and DATABASE_PATH to a persistent disk path on the host. Set COOKIE_SECURE=1 when served over HTTPS. Do not commit real credentials or database files.

TRACKING DETAILS
- Events are stored only after the visitor accepts the analytics notice.
- Question structure matches the original website: three question pages (P1, P2, P3), followed by reveal/countdown/letter/thank-you screens.
- Every Yes/No answer attempt is recorded; No attempts are counted per question.
- First envelope open time and time from session start are calculated from event timestamps.
- Reading time is recorded on screen transitions and page exit where possible. Browser closure, network loss, or abrupt shutdown can prevent the final event from being received; total time is therefore approximate.
- Repeat visits can be grouped using a random anonymous browser ID. It does not identify a real person and is lost if browser storage is cleared or a different browser/device is used.
- The private dashboard is protected by server-side login. Keep your password secret and use HTTPS.
