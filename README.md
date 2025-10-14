# 🏥 Historia Clínica CAU - Full API (Flask + Vue + Docker + BFA)

Este proyecto implementa un sistema web integral para la gestión de **historias clínicas unificadas**, desarrollado como **trabajo final de Ingeniería en Telecomunicaciones** en la **Universidad Nacional de San Martín (UNSAM)**.  
El sistema garantiza la **integridad, trazabilidad y disponibilidad** de la información médica mediante una arquitectura moderna basada en **API REST, frontend desacoplado y tecnología blockchain (BFA)**.

---

## 📌 Funcionalidades Principales

- 🔐 **Autenticación por roles** (`director`, `profesional`, `administrativo`)
- 📋 **Registro, edición y consulta de pacientes**
- 🩺 **Gestión de historias clínicas y evoluciones médicas**
- 📅 **Agenda de turnos médicos** con recordatorios automáticos
- 🧾 **Exportación de historias clínicas a PDF**
- 📎 **Carga de archivos adjuntos** en evoluciones médicas
- 🧱 **Validación de integridad** con hash SHA-256 por historia clínica
- ⛓️ **Registro de hash en la Blockchain Federal Argentina (BFA)**
- 💬 **Panel de control dinámico** con estadísticas y gráficos
- 💡 **Interfaz moderna basada en PrimeVue + Sakai (estilo UNSAM)**

---

## 🧱 Arquitectura General

El sistema sigue una estructura **frontend–backend desacoplada**, comunicada por API REST y contenedorizada con Docker Compose.

```bash
📦 Historia-Clinica-CAU-Full-API/
├── frond_historias_clinicas/                # Frontend Vue 3 (Vite + PrimeVue + Sakai)
│   ├── src/                                 # Componentes, vistas y lógica de UI
│   ├── public/                              # Recursos estáticos
│   └── vite.config.mjs                      # Configuración de build
│
├── historia_clinica_bfa/                    # Backend Flask
│   ├── app/                                 # Código backend Flask
│   │   ├── main.py                          # Entry point (Flask)
│   │   ├── routes/                          # Rutas API (pacientes, turnos, usuarios, blockchain)
│   │   ├── auth.py                          # Manejo de login y roles
│   │   ├── database.py                      # Conexión MySQL
│   │   └── utils/                           # Hash, PDF, blockchain, etc.
│   ├── docker-compose.yml                   # Orquestación de servicios backend
│   ├── db/init.sql                          # Estructura base de datos
│   ├── bfa-node/                            # Nodo Geth conectado a BFA
│   └── reset.sh / reset_web.sh              # Scripts de mantenimiento
│
└── docker-compose.yml                       # Entorno integrado Flask + MySQL + Nginx

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

---

### 4️⃣ Inicializar nodo BFA (opcional)

Si deseas probar la publicación de hashes en la Blockchain Federal Argentina:

```bash
./reset_bfa_node.sh
```

> Ver `setup_bfa_node.sh` y `reset_bfa_node.sh` para los detalles de configuración.

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

## 🧭 Flujo de Integridad Blockchain (BFA)

1. Cada historia clínica genera un **hash SHA-256** único.  
2. El hash se almacena en MySQL y opcionalmente se publica en la **Blockchain Federal Argentina (BFA)**.  
3. Los usuarios pueden **verificar la integridad** de las historias mediante el módulo “Verificar Hash”.  
4. El sistema incluye soporte para ejecutar el nodo `geth` BFA dentro de `bfa-node/`.

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
- 🔗 Flujo de publicación de hash (Flask → BFA)  
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