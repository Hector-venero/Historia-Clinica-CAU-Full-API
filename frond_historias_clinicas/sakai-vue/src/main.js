import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { createPinia } from 'pinia'
import Aura from '@primeuix/themes/aura'
import PrimeVue from 'primevue/config'
import ConfirmationService from 'primevue/confirmationservice'
import ToastService from 'primevue/toastservice'

// Componentes globales
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'

// Estilos
import 'primeicons/primeicons.css'
import '@/assets/styles.scss'

// 🧩 Importar el store del usuario
import { useUserStore } from '@/stores/user'

async function bootstrap() {
  const app = createApp(App)
  const pinia = createPinia()

  app.use(pinia)
  app.use(router)
  app.use(PrimeVue, {
    theme: {
      preset: Aura,
      options: { darkModeSelector: '.app-dark' }
    }
  })
  app.use(ToastService)
  app.use(ConfirmationService)

  app.component('Dialog', Dialog)
  app.component('Button', Button)

  // 🧠 Obtener los datos del usuario antes de montar la app
  const userStore = useUserStore()
  try {
    await userStore.fetchUser()
    console.log('✅ Usuario cargado:', userStore.nombre, '| Rol:', userStore.rol)
  } catch (err) {
    console.warn('⚠️ No se pudo cargar el usuario al iniciar:', err)
  }

  // 🔥 Ahora que el store tiene el rol, montamos la app
  app.mount('#app')
}

bootstrap()
