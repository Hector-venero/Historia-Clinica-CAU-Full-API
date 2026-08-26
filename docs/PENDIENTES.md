# Pendientes

Lo que está abierto al **26/08/2026**. Cada punto trae cómo se detectó y cómo
reproducirlo, para no tener que volver a investigarlo desde cero.

El registro de lo ya resuelto está en [MEJORAS-QA.md](MEJORAS-QA.md) (los 15
problemas de la pasada de QA del 25/08) y en el historial de commits.

---

## 1. Rotar los secretos — depende de una acción fuera del repositorio

**Es lo único urgente.**

`SECRET_KEY`, `DB_PASSWORD`, dos `MAIL_PASSWORD` y `PRIVATE_KEY_BFA` quedaron
commiteados en el fork público de GeroGauna222. Borrarlos del HEAD no alcanza:
están en la historia de un repositorio que no controlamos.

**No es teórico.** Al verificar el envío de correo en segundo plano, el log
mostró la sesión SMTP completa: la credencial de Gmail **está activa y
funcionando**. Cualquiera con acceso al fork puede mandar correo desde la
casilla institucional.

Solo lo puede hacer Hector: hay que rotar las cinco en el proveedor
correspondiente y actualizar el `.env` de producción.

---

## 2. "Bloquear un día" en Agenda del profesional está roto

`AgendaProfesional.vue` manda `{ fecha }` y el backend exige `fecha_inicio` y
`fecha_fin`. **Siempre devuelve 400**, así que la función no anda desde que
existe. La tabla, además, muestra una columna `fecha` que la API nunca devuelve,
por lo que sale vacía.

Verificado contra la API:

```bash
# Lo que manda el frontend hoy
curl -b cookies -X POST http://localhost:5000/api/ausencias \
     -H 'Content-Type: application/json' -d '{"fecha":"2026-09-15"}'
# {"error": "Se requieren fecha_inicio y fecha_fin"}  -> HTTP 400

# Lo que la API espera
curl -b cookies -X POST http://localhost:5000/api/ausencias \
     -H 'Content-Type: application/json' \
     -d '{"fecha_inicio":"2026-09-15 08:00:00","fecha_fin":"2026-09-15 18:00:00"}'
# {"id": 2, "message": "Ausencia registrada"}  -> HTTP 201
```

Es el más barato de los tres y el que más se nota. Hay que decidir si un bloqueo
es de día completo (y entonces el frontend arma las dos fechas) o si se pide un
rango horario.

---

## 3. `/api/ausencias` miente sobre la zona horaria

Devuelve los `DATETIME` con `jsonify` por defecto, que los serializa al formato
de fecha HTTP **etiquetado como GMT**, aunque estén guardados en hora argentina:

```
"fecha_inicio": "Thu, 10 Sep 2026 08:00:00 GMT"   <- son las 08:00 de Argentina
```

Cualquier consumidor que lo lea como UTC corre el valor **tres horas**. El
dashboard se salva porque tiene su propia conversión (`isoformat()`), y el
calendario de grupos usa el endpoint nuevo, que ya convierte bien.

La corrección es aplicar `a_iso_arg()` de `app/utils/fechas.py`, igual que hace
`obtener_ausencias_grupo()` en `grupos_routes.py`. **Ojo:** cambiar el formato
de esa respuesta afecta a `AgendaProfesional.vue`, que hoy la consume; conviene
hacerlo junto con el punto 2.

---

## 4. Datos con doble codificación UTF-8 en la base

`/api/usuarios/me` devuelve `"profesion": "MÃ©dico"` para el usuario `admin`:
es "Médico" codificado dos veces. Se va a imprimir mal en la receta, porque el
bloque `medico` sale de esa fila.

Es un problema de **datos**, no de código, pero conviene averiguar por dónde
entró antes de cargar usuarios de verdad: si hay una ruta de importación o un
formulario que guarda mal, cada usuario nuevo va a repetirlo. Revisar el charset
de la conexión y de la carga inicial.

---

## 5. Menores

- **`finally` en las conexiones de las rutas restantes.** Seis archivos de
  `routes/` siguen con el patrón manual `get_connection()` … `close()`. Cierran
  en todos los `return`, así que solo filtran ante una excepción. La forma
  preferida es `db_cursor()`.
- **Node 20 en la máquina.** Vite 7 exige ≥ 20.19 y hay 18.19, así que
  `npm run dev` y `npm run build` locales fallan con `crypto.hash is not a
  function`. Mientras tanto se trabaja con el perfil `docker-compose.dev.yml`,
  que corre sobre `node:20-alpine`.
- **Prueba en navegador del flujo de autenticación.** El ciclo HTTP está
  verificado; falta recarga forzada, enlace directo a una ruta protegida y
  sesión vencida.
- **`ModuloRehabilitacion.vue`** (700 líneas, con su ruta) sigue solo en el fork.
  Se decidió no traerlo. Depende de `calendar-medical.css`, que sí está, así que
  portarlo es viable si alguna vez hace falta.
- **El directorio `bfa-node/` está muerto.** Quedó de cuando el anclaje usaba un
  nodo Geth local. No hay servicio en `docker-compose.yml` que lo use ni código
  que lo referencie: las únicas menciones son comentarios que explican por qué
  se dejó de usar. Se puede borrar; no se hizo por si guarda algo de la etapa
  anterior que convenga conservar para el trabajo final.
