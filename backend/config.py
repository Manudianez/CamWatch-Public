from dotenv import load_dotenv
import os

load_dotenv()

# Plataformas entre las que se puede elegir. La clave es el nombre que usa Statbate.
SITES = {
    "stripchat": {"label": "Stripchat", "url": "https://stripchat.com/", "accent": "#1f6fa8"},
    "chaturbate": {"label": "Chaturbate", "url": "https://chaturbate.com/", "accent": "#a8591f"},
}


class Config:
    # Nombre provisional: cámbialo aquí o con APP_NAME en .env.
    APP_NAME = os.getenv("APP_NAME", "CamWatch")
    VERSION = "0.4.0"

    DEBUG = os.getenv("DEBUG", "False") == "True"

    # Dirección pública de la app. Debe ser HTTPS: Statbate no acepta otra cosa.
    PUBLIC_URL = os.getenv("PUBLIC_URL", "https://localhost:8443").rstrip("/")

    # Identificador que entrega Statbate al registrar la aplicación.
    STATBATE_CLIENT_ID = os.getenv("STATBATE_CLIENT_ID", "")
    STATBATE_BASE = os.getenv("STATBATE_BASE", "https://plus.statbate.com").rstrip("/")

    REDIRECT_URI = PUBLIC_URL + "/oauth/statbate/callback"
    SCOPES = "profile members:read"

    MAX_FOLLOWS = 10          # modelos por cuenta y plataforma
    ROOM_CACHE_SECONDS = 45   # Statbate refresca cada sala una vez por minuto
