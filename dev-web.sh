#!/bin/bash

# Run Gunicorn for local development
# Uses a single worker so the Pyramid Debug Toolbar works
# Reloads the application when Python files change

gunicorn --workers=1 --reload 'meshinfo.web:create_app()'
