import AppLayout from '@/layout/AppLayout.vue';
import { createRouter, createWebHistory } from 'vue-router';
import { useUserStore } from '@/stores/user';
import { usePacienteStore } from '@/stores/paciente';

const router = createRouter({
    history: createWebHistory(),
    routes: [
        // 🔐 Autenticación
        {
            path: '/auth/login',
            name: 'login',
            component: () => import('@/views/pages/auth/Login.vue')
        },
        {
            path: '/logout',
            name: 'logout',
            component: () => import('@/views/pages/auth/Logout.vue')
        },
        {
            path: '/recuperar',
            name: 'RecuperarContraseña',
            component: () => import('@/views/pages/auth/RecoverPassword.vue')
        },
        {
            path: '/reset/:token',
            name: 'ResetContraseña',
            component: () => import('@/views/pages/auth/ResetPassword.vue')
        },
        // 🆕 Alta autoservicio. Vive en el dominio raíz de la plataforma, no en
        // el de un consultorio: quien se registra todavía no tiene subdominio.
        {
            path: '/registro',
            name: 'Registro',
            component: () => import('@/views/pages/registro/Registro.vue')
        },
        {
            path: '/verificar/:token',
            name: 'VerificarRegistro',
            component: () => import('@/views/pages/registro/Verificar.vue')
        },
        // Cuenta suspendida. No lleva AppLayout: el menú de una aplicación que
        // no se puede usar sería una burla. Y no exige sesión en el guard porque
        // se llega acá justamente cuando las peticiones devuelven 402.
        {
            path: '/cuenta/suspendida',
            name: 'CuentaSuspendida',
            component: () => import('@/views/pages/cuenta/CuentaSuspendida.vue')
        },
        // 🌐 App principal (protegida)
        {
            path: '/',
            component: AppLayout,
            children: [
                {
                    path: '',
                    name: 'dashboard',
                    component: () => import('@/views/Dashboard.vue')
                },
                // 📌 Pacientes
                {
                    path: 'pacientes',
                    name: 'pacientes',
                    component: () => import('@/views/pages/historias/Pacientes.vue')
                },
                {
                    path: 'pacientes/registrar',
                    name: 'registrarPaciente',
                    component: () => import('@/views/pages/historias/RegistrarPaciente.vue')
                },
                {
                    path: 'pacientes/:id/editar',
                    name: 'editarPaciente',
                    component: () => import('@/views/pages/historias/EditarPaciente.vue')
                },
                {
                    path: 'historias',
                    name: 'historias',
                    component: () => import('@/views/pages/historias/BuscarHistorias.vue')
                },
                {
                    path: 'pacientes/:id/historias',
                    name: 'historiaPaciente',
                    component: () => import('@/views/pages/historias/HistoriaPaciente.vue'),
                    props: true
                },
                {
                    path: 'pacientes/:id/evolucion/:evoId',
                    name: 'evolucionDetalle',
                    component: () => import('@/views/pages/evolucion/EvolucionDetalle.vue'),
                    props: true
                },
                // 📌 Turnos
                {
                    path: 'turnos',
                    name: 'turnos',
                    component: () => import('@/views/pages/historias/Turnos.vue')
                },
                {
                    path: 'turnos/nuevo',
                    name: 'nuevoTurno',
                    component: () => import('@/views/pages/historias/NuevoTurno.vue')
                },
                {
                    path: 'turnos/agenda-publica',
                    name: 'AgendaPublica',
                    component: () => import('@/views/pages/turnos/AgendaPublica.vue'),
                    // Solo quien atiende pacientes: un administrativo no tiene
                    // agenda propia que publicar.
                    meta: { roles: ['profesional', 'director'] }
                },
                {
                    path: 'turnos/configuracion',
                    name: 'configuracionTurnos',
                    component: () => import('@/views/pages/turnos/ConfiguracionTurnos.vue'),
                    // Permitimos a todos los que gestionan agenda
                    meta: { roles: ['profesional', 'director', 'area'] }
                },

                // 📌 Usuarios (🔒 SECCIÓN BLINDADA - SOLO DIRECTOR)
                {
                    path: 'usuarios',
                    name: 'usuarios',
                    component: () => import('@/views/pages/usuarios/Usuarios.vue'),
                    meta: { roles: ['director'] }
                },
                {
                    path: 'usuarios/crear',
                    name: 'crearUsuario',
                    component: () => import('@/views/pages/usuarios/CrearUsuario.vue'),
                    meta: { roles: ['director'] }
                },
                {
                    path: 'usuarios/inactivos',
                    name: 'usuariosInactivos',
                    component: () => import('@/views/pages/usuarios/UsuariosInactivos.vue'),
                    meta: { roles: ['director'] }
                },
                {
                    path: 'usuarios/:id/editar',
                    name: 'editarUsuario',
                    component: () => import('@/views/pages/usuarios/EditarUsuario.vue'),
                    props: true,
                    meta: { roles: ['director'] }
                },

                // 📌 Perfil (Para todos)
                {
                    path: 'mi-perfil',
                    name: 'miPerfil',
                    component: () => import('@/views/pages/usuarios/MiPerfil.vue'),
                    meta: { requiresAuth: true }
                },
                {
                    path: '/cambiar-password',
                    name: 'cambiarPassword',
                    component: () => import('@/views/pages/usuarios/CambiarPassword.vue'),
                    meta: { requiresAuth: true }
                },

                // 📌 Disponibilidades
                {
                    path: 'disponibilidad',
                    name: 'disponibilidadProfesional',
                    component: () => import('@/views/pages/disponibilidades/DisponibilidadProfesional.vue')
                },

                // 📌 Grupos
                {
                    path: 'grupos',
                    name: 'GruposProfesionales',
                    component: () => import('../views/pages/grupos/GruposProfesionales.vue'),
                    meta: { requiresAuth: true } // Listado visible para todos
                },
                {
                    path: 'calendario-grupo/:grupoId',
                    name: 'CalendarioGrupo',
                    component: () => import('../views/pages/turnos/CalendarioGrupo.vue'),
                    meta: { requiresAuth: true }
                },
                {
                    path: 'grupos/crear',
                    name: 'CrearGrupo',
                    component: () => import('../views/pages/grupos/CrearGrupo.vue'),
                    meta: { roles: ['director'] }
                },
                {
                    path: 'grupos/editar/:id',
                    name: 'EditarGrupo',
                    component: () => import('../views/pages/grupos/EditarGrupo.vue'),
                    props: true,
                    meta: { roles: ['director'] }
                },

                // 📌 Blockchain
                {
                    path: 'blockchain/verificar',
                    name: 'blockchainVerificar',
                    component: () => import('@/views/pages/historias/BlockchainVerificar.vue')
                },

                // 📌 Recetas
                {
                    path: 'recetas',
                    name: 'recetasElectronicas',
                    component: () => import('@/views/pages/recetas/RecetasElectronicas.vue'),
                    // El backend ya exige estos dos roles en /api/recetas. Sin
                    // el meta, un administrativo podia abrir la pantalla y
                    // completarla entera para recibir un 403 recien al emitir.
                    meta: { roles: ['director', 'profesional'] }
                },
                // 💬 Posteos internos de un grupo profesional
                {
                    path: 'grupos/:grupoId/posteos',
                    name: 'posteosGrupo',
                    // El acceso real lo controla el backend: solo miembros del
                    // grupo, mas director y administrativo.
                    meta: { requiresAuth: true },
                    component: () => import('@/views/pages/grupos/PosteosGrupo.vue')
                },
                // 📢 Comunicados internos
                {
                    path: 'comunicados',
                    name: 'comunicados',
                    // Los lee todo el equipo; publicar y borrar lo restringe el
                    // backend a director y administrativo.
                    meta: { requiresAuth: true },
                    component: () => import('@/views/pages/comunicados/Comunicados.vue')
                }
            ]
        },

        // 👤 Portal del paciente.
        //
        // Vive en el subdominio `mi.<dominio>`, pero el SPA es el mismo build
        // servido en todos los hosts, así que las rutas llevan prefijo `/portal`
        // para no chocar con las del sistema del consultorio (donde `/` es el
        // dashboard). El guard de más abajo redirige `/` a `/portal` cuando se
        // entra por ese subdominio, así la dirección que ve el paciente queda
        // limpia.
        {
            path: '/portal/login',
            name: 'PortalLogin',
            component: () => import('@/views/pages/portal/PortalLogin.vue')
        },
        {
            path: '/portal/registro',
            name: 'PortalRegistro',
            component: () => import('@/views/pages/portal/PortalRegistro.vue')
        },
        {
            path: '/portal/verificar/:token',
            name: 'PortalVerificar',
            component: () => import('@/views/pages/portal/PortalVerificar.vue')
        },
        // Buscar profesional y elegir horario se ven SIN sesión: alguien tiene
        // que poder ver con quién puede atenderse, y si hay lugar, antes de
        // decidir si se registra. Lo único que exige cuenta es confirmar.
        {
            path: '/portal/buscar',
            name: 'PortalBuscar',
            component: () => import('@/views/pages/portal/BuscarProfesional.vue')
        },
        {
            path: '/portal/reservar/:clienteId/:usuarioId',
            name: 'PortalReservar',
            component: () => import('@/views/pages/portal/ReservarTurno.vue')
        },
        {
            path: '/portal',
            component: () => import('@/layout/PortalLayout.vue'),
            children: [
                {
                    path: '',
                    name: 'PortalDocumentos',
                    component: () => import('@/views/pages/portal/MisDocumentos.vue'),
                    meta: { paciente: true }
                }
            ]
        },

        // 🚫 Ruta no encontrada
        {
            path: '/:pathMatch(.*)*',
            name: 'notfound',
            component: () => import('@/views/pages/NotFound.vue')
        }
    ]
});

// 🛡️ Guard global para proteger rutas
// 🛡️ Guard global.
//
// La sesión se valida contra el backend, no contra localStorage. El rol sale de
// /api/usuarios/me, que responde en función de la cookie HttpOnly: ya no se
// puede escalar privilegios editando localStorage desde las devtools.
//
// Es async: en un reload sin store cargado hay que esperar la respuesta del
// backend antes de decidir. Ese pedido se hace una sola vez por sesión, porque
// después el store ya tiene el usuario.
router.beforeEach(async (to) => {
    // El portal del paciente se resuelve aparte y se corta acá.
    //
    // Son dos poblaciones de usuarios distintas: validar a un paciente contra
    // /api/usuarios/me daría 401 siempre, porque esa ruta es del personal del
    // consultorio. Es la misma separación que en el backend, donde mezclarlas
    // dejaba a un paciente leer el listado de pacientes de una clínica.
    if (to.path.startsWith('/portal')) {
        const pacienteStore = usePacienteStore();

        const publicasDelPortal = ['/portal/login', '/portal/registro', '/portal/buscar'];
        const esVerificacion = to.path.startsWith('/portal/verificar/');
        // Elegir horario se ve sin cuenta; confirmarlo no. El backend es quien
        // exige la sesión al reservar, así que acá no hace falta guardarla.
        const esReserva = to.path.startsWith('/portal/reservar/');
        if (publicasDelPortal.includes(to.path) || esVerificacion || esReserva) return true;

        if (!pacienteStore.autenticado && !pacienteStore.cerrandoSesion) {
            try {
                await pacienteStore.cargar();
            } catch {
                return '/portal/login';
            }
        }
        return pacienteStore.autenticado ? true : '/portal/login';
    }

    // Entrar por el subdominio del portal lleva al portal, no al dashboard del
    // consultorio: en `mi.<dominio>` no hay consultorio que mostrar.
    if (to.path === '/' && window.location.host.split('.')[0] === 'mi') {
        return '/portal';
    }

    const publicPages = ['/auth/login', '/recuperar', '/logout', '/registro', '/cuenta/suspendida'];
    // El token va en la URL, así que la ruta no puede exigir sesión: quien
    // verifica su correo todavía no tiene cuenta.
    const isResetRoute = to.path.startsWith('/reset/') || to.path.startsWith('/verificar/');
    const authRequired = !publicPages.includes(to.path) && !isResetRoute;
    const userStore = useUserStore();
    const needsUser = authRequired || Boolean(to.meta.roles);

    if (needsUser && !userStore.id) {
        try {
            await userStore.fetchUser();
        } catch {
            // Sin sesión válida: si la ruta la exigía, a login.
            if (authRequired) return '/auth/login';
        }
    }

    if (authRequired && !userStore.id) {
        return '/auth/login';
    }

    // Ya logueado y yendo a login: al inicio. Salvo que se esté cerrando sesión,
    // en cuyo caso rebotarlo al dashboard impediría salir.
    const forcedLogout = String(to.query.logged_out || '') === '1' || userStore.loggingOut;
    if (to.path === '/auth/login' && userStore.id && !forcedLogout) {
        return '/';
    }

    if (to.meta.roles) {
        const userRole = (userStore.rol || '').toLowerCase().trim();
        if (!to.meta.roles.includes(userRole)) {
            console.warn(`⛔ Acceso denegado a ${to.path}. Rol actual: ${userRole}`);
            return '/';
        }
    }

    return true;
});

export default router;
