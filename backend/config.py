from dotenv import load_dotenv
import os

load_dotenv()


# El mismo código sirve dos apps; APP elige cuál arranca.
APPS = {
    "stripwatch": {
        "name": "StripWatch", "site": "stripchat", "platform": "Stripchat",
        "model_url": "https://stripchat.com/", "accent": "#1f6fa8", "port": 8443,
    },
    "chaturwatch": {
        "name": "ChaturWatch", "site": "chaturbate", "platform": "Chaturbate",
        "model_url": "https://chaturbate.com/", "accent": "#a8591f", "port": 8444,
    },
}

APP = os.getenv("APP", "stripwatch").strip().lower()
if APP not in APPS:
    raise SystemExit(f"APP debe ser una de: {', '.join(APPS)}")
_app = APPS[APP]


class Config:
    APP = APP
    APP_NAME = _app["name"]
    SITE = _app["site"]             # nombre de la plataforma en la API de Statbate
    PLATFORM = _app["platform"]
    MODEL_URL = _app["model_url"]
    ACCENT = _app["accent"]
    PORT = _app["port"]
    VERSION = "0.3.0"

    DEBUG = os.getenv("DEBUG", "False") == "True"

    # Dirección pública de la app. Debe ser HTTPS: Statbate no acepta otra cosa.
    PUBLIC_URL = os.getenv("PUBLIC_URL", f"https://localhost:{_app['port']}").rstrip("/")

    # Identificador que entrega Statbate al registrar la aplicación.
    # Cada app se registra por separado: STRIPWATCH_CLIENT_ID / CHATURWATCH_CLIENT_ID.
    STATBATE_CLIENT_ID = os.getenv(f"{APP.upper()}_CLIENT_ID") or os.getenv("STATBATE_CLIENT_ID", "")
    STATBATE_BASE = os.getenv("STATBATE_BASE", "https://plus.statbate.com").rstrip("/")

    REDIRECT_URI = PUBLIC_URL + "/oauth/statbate/callback"
    SCOPES = "profile members:read"

    MAX_FOLLOWS = 10          # modelos por cuenta
    ROOM_CACHE_SECONDS = 45   # Statbate refresca cada sala una vez por minuto
