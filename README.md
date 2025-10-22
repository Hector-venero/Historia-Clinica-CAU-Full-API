# 🏥 Historia Clínica CAU - Full API (Flask + Vue 3 + Docker + MySQL + BFA + Auditoría Blockchain)

Este proyecto implementa un sistema web integral para la gestión de **historias clínicas unificadas**, desarrollado como **trabajo final de Ingeniería en Telecomunicaciones** en la **Universidad Nacional de San Martín (UNSAM)**.  
El sistema garantiza la **integridad, trazabilidad y disponibilidad** de la información médica mediante una arquitectura moderna basada en **API REST, frontend desacoplado y tecnología blockchain (BFA)**.  
Además, incluye un sistema automatizado de **verificación y auditoría de integridad** entre el hash local y el registrado en la **Blockchain Federal Argentina (BFA)**.

---

## 📌 Funcionalidades Principales

- 🔐 **Autenticación por roles** (`director`, `profesional`, `administrativo`)
- 📋 **Registro, edición y consulta de pacientes**
- 🩺 **Gestión de historias clínicas y evoluciones médicas**
- 🧩 **Consolidación automática** de historia clínica a partir de evoluciones médicas
- ⛓️ **Publicación y validación de hashes SHA-256 en la Blockchain Federal Argentina (BFA)**
- 🔍 **Verificación automática de integridad** entre MySQL y Blockchain (BFA)
- 📊 **Auditorías históricas** de verificaciones registradas en base local
- 📅 **Agenda de turnos médicos** con recordatorios automáticos
- 🧾 **Exportación de historias clínicas a PDF**
- 📎 **Carga de archivos adjuntos** en evoluciones médicas
- 💬 **Panel de control dinámico** con estadísticas y gráficos
- 💡 **Interfaz moderna basada en PrimeVue + Sakai (estilo UNSAM)**

---

## 🧱 Arquitectura General

El sistema sigue una estructura **frontend–backend desacoplada**, comunicada por API REST y contenedorizada con Docker Compose.

```bash
📦 historia_clinica_bfa/
├── backend_flask/                     # API Flask modular (pacientes, usuarios, historias, blockchain)
│   ├── app/
│   │   ├── routes/                    # Rutas agrupadas por módulo
│   │   ├── utils/                     # Hash, PDF, BFA, auditorías
│   │   ├── main.py                    # Entry point Flask
│   │   └── database.py                # Conexión MySQL
│   ├── Dockerfile
│   └── requirements.txt
│
├── db/                                # Estructura base de datos MySQL
│   └── init.sql                       # Estructura con auditorías y consolidación de historia
│
├── frontend/                          # Vue 3 + Vite + PrimeVue + Sakai
│   ├── src/views/pages/historias/     # HistoriaPaciente.vue + BlockchainVerificar.vue
│   ├── src/service/                   # axios services
│   ├── package.json
│   └── vite.config.js
│
├── bfa-node/                          # Nodo Geth conectado a Blockchain Federal Argentina
│   ├── nucleo/test2network/           # Archivos de red y keystore
│   ├── setup_bfa_node.sh              # Inicialización del nodo
│   └── reset_bfa_node.sh              # Reinicio y desbloqueo automático
│
└── docker-compose.yml                 # Orquestación Flask + MySQL + Nginx + BFA node
```

---

## 🧰 Tecnologías Utilizadas

| Capa              | Tecnología / Framework |
|--------------------|------------------------|
| **Frontend**       | Vue 3, Vite, PrimeVue, Tailwind, Sakai Template |
| **Backend**        | Python (Flask), Flask-Login, Flask-Mail |
| **Base de Datos**  | MySQL 8.0 |
| **Blockchain**     | Blockchain Federal Argentina (BFA) – Nodo Geth |
| **Contenedores**   | Docker + Docker Compose |
| **PDF / Hashing**  | ReportLab, hashlib (SHA-256) |
| **Servidor Web**   | Nginx (reverse proxy) |

---

## 🐳 Instalación con Docker Compose

### 1️⃣ Clonar el repositorio

```bash
git clone https://github.com/Hector-venero/Historia-Clinica-CAU-Full-API.git
cd Historia-Clinica-CAU-Full-API
```

---

### 2️⃣ Configurar entorno (.env)

Crear un archivo `.env` dentro del backend con las variables:

```env
FLASK_ENV=production
MYSQL_HOST=historia_db
MYSQL_USER=root
MYSQL_PASSWORD=root
MYSQL_DATABASE=hc_bfa
SECRET_KEY=unsam2025
```

---

### 3️⃣ Levantar el entorno

```bash
sudo docker-compose up --build
```

Esto desplegará los contenedores:

| Servicio | Descripción |
|-----------|-------------|
| 🐍 `historia_web` | Backend Flask (API REST) |
| 🐬 `historia_db` | Base de datos MySQL |
| 🌐 `historia_nginx` | Servidor web + proxy inverso para Flask y frontend |
| ⛓️ `bfa-node` | Nodo Geth conectado a la Blockchain Federal Argentina |

---

### 4️⃣ Inicializar nodo BFA (opcional)

Si deseas probar la publicación de hashes en la Blockchain Federal Argentina:

```bash
./setup_bfa_node.sh
```

> Ver `setup_bfa_node.sh` y `reset_bfa_node.sh` para los detalles de configuración y desbloqueo automático.

---

## ▶️ Acceso a la Aplicación

Una vez desplegado el entorno, accedé desde tu navegador a:

- 🌍 **Frontend:** [http://localhost](http://localhost)
- 🔗 **API Backend:** [http://localhost/api](http://localhost/api)

Usuario inicial (modo demo):

| Campo | Valor |
|--------|--------|
| **Usuario** | `admin` |
| **Contraseña** | `admin123` |

---

## 🧭 Flujo de Integridad y Auditoría Blockchain (BFA)

1. Cada evolución médica se guarda en MySQL.  
2. El sistema genera automáticamente un **hash SHA-256 consolidado** de todas las evoluciones del paciente.  
3. El hash se registra localmente y opcionalmente se publica en la **Blockchain Federal Argentina (BFA)**.  
4. Los usuarios pueden **verificar la integridad** desde la interfaz (ver “Verificar Integridad”), comparando el hash local y el registrado en BFA.  
5. Cada verificación queda registrada en la tabla `auditorias_blockchain`, disponible desde el módulo visual de auditorías.

---

## 🧾 Módulo de Auditoría Blockchain

El sistema incorpora un módulo visual (Vue 3) donde se puede:

- 🔗 Verificar la integridad de una historia clínica puntual.  
- 📜 Consultar el historial de auditorías (válido / no válido).  
- ⚙️ Ejecutar nuevas publicaciones de hash en la BFA.

Este módulo se implementa en:  
`frontend/src/views/pages/historias/BlockchainVerificar.vue`  
y consume las rutas `/api/blockchain/verificar` y `/api/blockchain/auditorias`.

---

## 🧮 Dashboard y Estadísticas

El **panel de control** presenta:

- Turnos del día y próximos turnos.
- Actividad médica semanal (gráfico dinámico).
- Ausencias y bloqueos registrados.
- Próximos eventos médicos (congresos, licencias, etc.).

Los gráficos se construyen con **Chart.js + PrimeVue**,  
y usan códigos de color dinámicos (verde = alta carga, gris = ausencias).  
Además, el dashboard tiene un modo **"UNSAM Pro"** con transiciones suaves y estilo institucional.

---

## 🛡️ Seguridad

- 🔑 Contraseñas encriptadas con `Werkzeug + Scrypt`
- ⏱️ Sesiones limitadas (expiran automáticamente a 1 hora)
- 🧩 Permisos basados en rol (`director`, `profesional`, `administrativo`)
- 🧍 Control de sesión con `Flask-Login`
- ✅ Acceso protegido mediante `@login_required`
- 📧 Recuperación de contraseña y recordatorios automáticos por email

---

## 🧹 Limpieza y Modularización

A partir de **octubre 2025**, el repositorio fue reorganizado con una arquitectura modular y limpia:

- Eliminación de entornos virtuales antiguos (`venv/`) y versiones previas del sistema.  
- `.gitignore` actualizado para prevenir commits de dependencias o entornos locales.  
- Reescritura del historial remoto para optimizar tamaño y performance del repo.  
- Integración del nodo BFA directamente bajo estructura `bfa-node/` con configuración automatizada.

---

## 🖥️ Capturas (versión UNSAM Pro UI)

> Próximamente disponibles en `/docs/screens/`

- Dashboard principal  
- Listado de pacientes  
- Visualización y verificación de hash blockchain

---

## 📚 Documentación Técnica

Incluye:

- 🧩 Diagrama de arquitectura general  
- 🗃️ Diagrama entidad-relación MySQL  
- 🔗 Flujo de publicación y verificación de hash (Flask → BFA)  
- ⚙️ Descripción técnica de la red permisionada BFA  
- ⚡ Comparativa PoW vs PoA aplicada al sector salud  
- 🔐 Análisis de seguridad y trazabilidad de la información

---

## 🪪 Licencia

Proyecto académico desarrollado en el marco del **Proyecto Final Integrador**  
de la carrera de **Ingeniería en Telecomunicaciones (UNSAM - ECyT)**.

> Uso autorizado únicamente con fines **educativos e institucionales**.

---

## 📬 Contacto

**Autor:** Héctor Venero  
**Carrera:** Ingeniería en Telecomunicaciones  
**Universidad:** Universidad Nacional de San Martín (UNSAM)  
**Año:** 2025  
**LinkedIn:** [linkedin.com/in/hector-venero-8493a1154](https://www.linkedin.com/in/hector-venero-8493a1154/)  
**GitHub:** [github.com/Hector-venero](https://github.com/Hector-venero)

---

🧠 *"Integridad, interoperabilidad y transparencia médica —  
Blockchain aplicada a la gestión sanitaria en Argentina."*