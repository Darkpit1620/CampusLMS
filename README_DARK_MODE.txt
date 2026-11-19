CampusLMS - LIGHT + DARK MODE ADD-ON
====================================
Designed for the previously installed colorful CampusLMS UI pack.
Your current light theme remains intact. The top navigation now has a
moon/sun button, remembers the selected mode locally and also honors
your Windows/system theme until you make a manual choice.

INCLUDED:
 dashboard/templates/dashboard/base.html (updated shared base with toggle)
 dashboard/static/dashboard/css/dark-mode.css (dark colors, all pages)
 dashboard/static/dashboard/js/theme-toggle.js (theme switching + saved preference)
 PREVIEW_DarkMode_Home.html (static preview, open in a browser)
 README_DARK_MODE.txt (this guide)

INSTALL IN VS CODE WINDOWS POWERSHELL
-------------------------------------
1) Stop the server with Ctrl+C.
2) Go to the CampusLMS project root:
   cd "C:\Users\USER\Documents\assignment\New folder\CampusLMS"
3) Back up the shared template before replacing it:
   Copy-Item .\dashboard\templates\dashboard\base.html .\dashboard\templates\dashboard\base.before-dark.html
4) Download CampusLMS_Dark_Mode_Addon.zip into your Downloads folder.
5) Extract into project ROOT (where manage.py lives):
   Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\CampusLMS_Dark_Mode_Addon.zip" -DestinationPath . -Force
6) If needed, activate your venv:
   .\.venv\Scripts\Activate.ps1
7) Run Django:
   python manage.py check
   python manage.py runserver 8001
8) Open http://127.0.0.1:8001/ and press Ctrl+F5.
9) Use the 'Dark mode' button in the top nav. Click again for 'Light mode'.

NOTES
-----
- Only one existing file is replaced: dashboard/templates/dashboard/base.html.
  Two new CSS/JavaScript files are added. Python and database files are untouched.
- If you made custom edits to base.html since the original colorful UI
  install, merge the new link tags, script tag and button manually instead.
- This controls your custom CampusLMS pages, not Django's /admin/ UI.
  Django admin has a separate appearance toggle in its own interface.
- If no preference has been saved, the user's system theme is applied.
- No new Django apps, packages, database migrations, or Python code needed.
- The previous SyntaxError in assignments/views.py, if still present,
  needs to be fixed separately for the server to start.
- This is a client-side display preference. No personal data is transmitted.
