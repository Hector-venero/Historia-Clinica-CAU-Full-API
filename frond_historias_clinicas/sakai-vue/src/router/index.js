import AppLayout from '@/layout/AppLayout.vue'
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
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
        // 📌 Usuarios
        {
          path: 'usuarios',
          name: 'usuarios',
          component: () => import('@/views/pages/usuarios/Usuarios.vue')
        },
        {
          path: 'usuarios/crear',
          name: 'crearUsuario',
          component: () => import('@/views/pages/usuarios/CrearUsuario.vue')
        },
        {
          path: 'usuarios/inactivos',
          name: 'usuariosInactivos',
          component: () => import('@/views/pages/usuarios/UsuariosInactivos.vue')
        },
        {
          path: 'usuarios/:id/editar',
          name: 'editarUsuario',
          component: () => import('@/views/pages/usuarios/EditarUsuario.vue'),
          props: true
        },
        // 📌 Disponibilidades
        {
          path: 'disponibilidad',
          name: 'disponibilidadProfesional',
          component: () => import('@/views/pages/disponibilidades/DisponibilidadProfesional.vue')
        },
        // 📌 Blockchain
        {
          path: 'blockchain/verificar',
          name: 'blockchainVerificar',
          component: () => import('@/views/pages/historias/BlockchainVerificar.vue')
        }
      ]
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'notfound',
      component: () => import('@/views/pages/NotFound.vue')
    }
  ]
})

// 🛡️ Guard global para proteger rutas
router.beforeEach((to, from, next) => {
  const publicPages = ['/auth/login']
  const authRequired = !publicPages.includes(to.path)
  const loggedIn = localStorage.getItem('loggedIn')

  if (authRequired && !loggedIn) {
    return next('/auth/login')
  }
  next()
})

export default router
