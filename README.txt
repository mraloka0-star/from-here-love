FROM HERE, LOVE — NEW PROJECT
================================

WHAT'S INCLUDED
- index.html: the anniversary experience
- styles.css: layout and visual styling
- script.js: page navigation, question flow, music, and event reporting
- assets/: the two existing photos and both music tracks
- app.py: the website server, private admin login, and event database API
- requirements.txt / Procfile: deployment setup
- .env.example: required environment variable names

THE BUTTON / PAGE FLOW
1. Opening envelope button opens the story and starts the main song.
2. Page 1 has Yes and No buttons.
3. Page 2 has Yes and No buttons.
4. Page 3 has Yes and No buttons.
5. The reveal page has Yes (start countdown) and No (show thank-you note) buttons.
6. After the 10-second countdown, the final-letter button opens the letter.

Each question's No button can be pressed up to three times. The first two presses change the response text; the third press ends the questions and shows the thank-you note. A visitor can choose No; the website does not require a Yes answer.

FIRST-PAGE DISCLOSURE
The only note is: "Your answers and basic page activity may be saved."
It appears as a small plain line under the envelope, not inside the envelope button, not in a box, and not in a pop-up.

ADMIN REPORTS
The private admin dashboard is at /admin after deployment. It records anonymous session IDs, visit start/last event timestamps, page views, estimated reading time, envelope opening, page progression, answers and No attempts, countdown and final-letter opening, thank-you activity, and music events. Use the Export CSV control after signing in.

IMPORTANT DEPLOYMENT NOTES
This is a full-stack project. GitHub can store the source, but GitHub Pages alone cannot run app.py or protect the admin dashboard. Deploy the whole folder to a Python web host such as Render, using the included Procfile and requirements.txt.

Set these environment variables on the host:
- ADMIN_USERNAME: your chosen admin username
- ADMIN_PASSWORD: a strong private password (do not use the example)
- SESSION_SECRET: a long random secret
- DATABASE_PATH: persistent storage path if your host supports a persistent disk
- COOKIE_SECURE=1 when the deployed site uses HTTPS

SQLite data may be lost on hosts with an ephemeral filesystem unless you configure a persistent disk. The browser/server connection and admin login should be tested after deployment. Do not put real admin passwords in this folder or commit them to GitHub.

IMAGES AND MUSIC
Both photos use their original proportions (object-fit: contain; no forced image cropping). Both music tracks were loudness-normalized to the same target so they should sound more even, although the source recordings may still differ slightly in tone.

PRIVACY
The dashboard is password-protected server-side. It only records activity from this website and the answers selected on its buttons. Session duration is an estimate, especially if a browser closes without sending the final event.
