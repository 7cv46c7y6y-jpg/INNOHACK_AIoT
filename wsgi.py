"""배포 서버(gunicorn)용 진입점: gunicorn wsgi:app"""
from app import create_app

app = create_app()
