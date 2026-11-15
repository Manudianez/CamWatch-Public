# StripWatch

Contador en vivo de Stripchat. Escribes el nombre de una modelo y la app
vigila su emisión: si está en línea, cuántos espectadores tiene, quién está
activo en el chat y qué propinas (tokens) recibe.

## Uso

```bash
pip install -r requirements.txt
python -m backend.server
```

Después abre http://127.0.0.1:8000 en el navegador.

## Cómo funciona

- `backend/stripchat.py` — consulta la API pública de Stripchat. Es el único
  archivo que depende de cómo responde la web.
- `backend/monitor.py` — revisa cada modelo seguida cada 4 segundos y guarda
  las propinas.
- `backend/server.py` — servidor web (FastAPI) y API que usa la interfaz.
- `backend/database.py`, `backend/model_manager.py` — base de datos SQLite
  en `database/stripwatch.db`.
- `app/index.html` — la interfaz.
- `backend/main.py` — menú de consola original (`python -m backend.main`).

Si los datos no aparecen, `http://127.0.0.1:8000/api/debug/NOMBRE` muestra
las respuestas en bruto de Stripchat para esa modelo.

## Límites

- Los tokens solo se cuentan mientras StripWatch está abierto y la modelo en
  línea; lo que ocurra con la app cerrada no se registra.
- Stripchat solo muestra al público el número de espectadores. Los nombres
  que aparecen son los de quienes escriben o dan propina en el chat.

## Author

Manu
