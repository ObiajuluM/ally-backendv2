#!/bin/sh
# ---------------------------------------------------------------------------
# entrypoint.sh
# This script runs every time the container starts — like a morning routine.
# It prepares the app before handing control to the web server.
# ---------------------------------------------------------------------------

# Exit immediately if any command fails.
# Without this, a failed migration would be silently ignored and
# the server would start in a broken state.
set -e

# Apply any pending database migrations.
# This keeps the database schema in sync with the Django models.
# --noinput means don't ask for confirmation — we're running unattended.
echo "Running migrations..."
python manage.py migrate --noinput

# Copy all static files (CSS, JS, images) into STATIC_ROOT.
# Whitenoise (our static file server) serves them from there.
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start the Daphne ASGI server.
#   -b 0.0.0.0  — listen on ALL network interfaces inside the container
#                 (not just localhost, otherwise nothing outside can reach it)
#   -p 8000     — on port 8000
# exec replaces this shell process with Daphne so signals (like Ctrl+C)
# are passed through correctly.
echo "Starting Daphne..."
exec daphne -b 0.0.0.0 -p 8000 config.asgi:application
