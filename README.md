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

La app está registrada en Statbate con el `client_id` `stripwatch` y la
dirección de retorno `https://localhost:8443/oauth/statbate/callback`, así que
en tu propio ordenador funciona sin configurar nada más.

1. **Certificado local** (una sola vez). Statbate solo acepta HTTPS; en Mac se
   crea con [mkcert](https://github.com/FiloSottile/mkcert), dentro de la
   carpeta del proyecto:

   ```bash
   brew install mkcert && mkcert -install && mkcert localhost
   ```

2. **Instalar y arrancar:**

   ```bash
   pip install -r requirements.txt
   python -m backend.server
   ```

3. Abre https://localhost:8443 (tal cual: `localhost`, no `127.0.0.1`).

Cada cuenta de Statbate admite hasta 3 instalaciones activas de la app (una
por navegador). Si al entrar aparece un rechazo, libera alguna en la página
«Connected apps» de Statbate.

Para alojarla en internet hay que pedir a Statbate que añada la dirección de
retorno pública y definir `PUBLIC_URL` (ver `.env.example`).

## Estructura

- `backend/statbate.py` — inicio de sesión (OAuth 2.0 con PKCE) y consultas a Statbate.
- `backend/server.py` — servidor web (FastAPI): sesiones, modelos seguidas y salas.
- `backend/database.py` — SQLite en `database/app.db` (sesiones y modelos seguidas).
- `backend/config.py` — configuración leída de `.env`; aquí están el nombre de la app y las plataformas.
- `app/index.html` — la interfaz.

## Límites

- Statbate refresca cada sala como mucho una vez por minuto: no es instantáneo.
- Los tokens mostrados son los que han dado en esa sala los espectadores que
  están dentro en ese momento, en la última hora y en la última semana.
  Statbate no da el total diario de la sala, ni propinas una a una, ni chat.
- Una sala desconectada y un nombre que no existe se ven igual.
- Cada cuenta puede seguir hasta 10 modelos por plataforma.

## Privacidad

Los accesos de Statbate se guardan solo en el servidor. Al pulsar «Salir» se
revocan y se borran junto con la lista de modelos seguidas. No se guarda
ningún dato de espectadores.

## Author

Manu
