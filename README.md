# StripWatch y ChaturWatch

Contadores en vivo de Stripchat (StripWatch) y Chaturbate (ChaturWatch). Entras con tu cuenta de Statbate, escribes el
nombre de una modelo y ves si está en línea, quién está en la sala y cuántos
tokens ha dado cada espectador.

Los datos vienen de [Statbate Plus](https://plus.statbate.com) mediante
«Sign in with Statbate». Cada persona usa su propia cuenta y necesita un plan
Simple Plus o Studio Plus para recibir datos.

## Dos apps, un mismo código

La variable `APP` elige cuál arranca:

| App | Plataforma | Arranque | Dirección local |
|---|---|---|---|
| StripWatch | Stripchat | `python -m backend.server` | https://localhost:8443 |
| ChaturWatch | Chaturbate | `APP=chaturwatch python -m backend.server` | https://localhost:8444 |

Cada una tiene su propio registro en Statbate, su base de datos y sus sesiones,
y pueden funcionar a la vez.

## Puesta en marcha

1. **Registrar la app en Statbate.** Se hace por correo (ver su
   [documentación](https://docs.statbate.com/docs/plus/integrations/sign-in-with-statbate/)):
   nombre del producto, direcciones de retorno y permisos `profile` y
   `members:read`. Te devuelven un `client_id`.
2. **Configurar.** Copia `.env.example` como `.env` y pon el `client_id` de cada app.
3. **Instalar y arrancar:**

   ```bash
   pip install -r requirements.txt
   python -m backend.server
   ```

Statbate solo acepta direcciones HTTPS. Para probar en tu Mac puedes crear un
certificado local con [mkcert](https://github.com/FiloSottile/mkcert):

```bash
brew install mkcert && mkcert -install && mkcert localhost
```

y abrir la dirección local de la app. La dirección de retorno a registrar es
`PUBLIC_URL` + `/oauth/statbate/callback`.

## Estructura

- `backend/statbate.py` — inicio de sesión (OAuth 2.0 con PKCE) y consultas a Statbate.
- `backend/server.py` — servidor web (FastAPI): sesiones, modelos seguidas y salas.
- `backend/database.py` — SQLite en `database/` (un archivo por app) (sesiones y modelos seguidas).
- `backend/config.py` — configuración leída de `.env`.
- `app/index.html` — la interfaz.

## Límites

- Statbate refresca cada sala como mucho una vez por minuto: no es instantáneo.
- Los tokens mostrados son los que han dado en esa sala los espectadores que
  están dentro en ese momento. No hay propinas una a una ni chat.
- Una sala desconectada y un nombre que no existe se ven igual.
- Cada cuenta puede seguir hasta 10 modelos.

## Privacidad

Los accesos de Statbate se guardan solo en el servidor. Al pulsar «Salir» se
revocan y se borran junto con la lista de modelos seguidas. No se guarda
ningún dato de espectadores.

## Author

Manu
