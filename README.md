# CamWatch

Contador en vivo de Stripchat y Chaturbate. Entras con tu cuenta de Statbate,
eliges la plataforma con el selector, escribes el nombre de una modelo y ves si está en línea, quién está en la sala y cuántos
tokens ha dado cada espectador.

Los datos vienen de [Statbate Plus](https://plus.statbate.com) mediante
«Sign in with Statbate». Cada persona usa su propia cuenta y necesita un plan
Simple Plus o Studio Plus para recibir datos.

## Aspecto

Al abrir, la app tiene su aspecto de acero pulido. Al elegir plataforma, toda
la interfaz cambia al instante a un aspecto que imita el de su web (colores,
formas y tipografía); pulsar de nuevo la tecla elegida, o el título, vuelve al acero.
Los tres aspectos son variables CSS al principio de `app/index.html`. No se
usan logotipos ni recursos de las plataformas.

## Puesta en marcha

1. **Registrar la app en Statbate.** Se hace por correo (ver su
   [documentación](https://docs.statbate.com/docs/plus/integrations/sign-in-with-statbate/)):
   nombre del producto, direcciones de retorno y permisos `profile` y
   `members:read`. Te devuelven un `client_id`.
2. **Configurar.** Copia `.env.example` como `.env` y pon tu `client_id`.
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

y abrir https://localhost:8443. La dirección de retorno a registrar es
`PUBLIC_URL` + `/oauth/statbate/callback`.

## Estructura

- `backend/statbate.py` — inicio de sesión (OAuth 2.0 con PKCE) y consultas a Statbate.
- `backend/server.py` — servidor web (FastAPI): sesiones, modelos seguidas y salas.
- `backend/database.py` — SQLite en `database/app.db` (sesiones y modelos seguidas).
- `backend/config.py` — configuración leída de `.env`; aquí están el nombre de la app y las plataformas.
- `app/index.html` — la interfaz.

## Límites

- Statbate refresca cada sala como mucho una vez por minuto: no es instantáneo.
- Los tokens mostrados son los que han dado en esa sala los espectadores que
  están dentro en ese momento. No hay propinas una a una ni chat.
- Una sala desconectada y un nombre que no existe se ven igual.
- Cada cuenta puede seguir hasta 10 modelos por plataforma.

## Privacidad

Los accesos de Statbate se guardan solo en el servidor. Al pulsar «Salir» se
revocan y se borran junto con la lista de modelos seguidas. No se guarda
ningún dato de espectadores.

## Author

Manu
