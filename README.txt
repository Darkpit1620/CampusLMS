CampusLMS Creator Footer (safe add-on)
======================================

What it does:
- Shows 'Created by Lance Baraka' (or a name you choose) on the shared footer.
- Adds a clickable 'Email the creator' link when a full email is entered.
- Uses the same colors in light and dark mode.
- Backs up the original dashboard/templates/dashboard/base.html.
- Does NOT edit Python models, your database, accounts, courses, or grades.

Install on Windows PowerShell:
1. Stop Django with Ctrl+C.
2. cd "C:\Users\USER\Documents\assignment\New folder\CampusLMS"
3. Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\CampusLMS_Creator_Footer.zip" -DestinationPath . -Force
4. python install_creator_footer.py
5. Type the creator name (or press Enter for Lance Baraka).
6. Type your COMPLETE email address for a working Contact link.
7. python manage.py check
8. python manage.py runserver 8001
9. Refresh the homepage with Ctrl+F5 and scroll to the bottom.

You can run the installer again to change name or contact email.
It will UPDATE the existing credit instead of duplicating it.

Note: A mailto link opens a visitor's email app. It does not submit a
server-side contact form or send messages on its own.
