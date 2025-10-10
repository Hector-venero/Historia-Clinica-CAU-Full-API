import { createApp } from 'vue'
import App from './App.vue'
import router from './router'

import Aura from '@primeuix/themes/aura'
import PrimeVue from 'primevue/config'
import ConfirmationService from 'primevue/confirmationservice'
import ToastService from 'primevue/toastservice'

import Button from 'primevue/button'
import Dialog from 'primevue/dialog'

// ✅ Importar estilos globales de PrimeVue y PrimeIcons
import 'primeicons/primeicons.css'
//import 'primevue/resources/primevue.min.css'
//import 'primevue/resources/themes/lara-light-indigo/theme.css'; // O el tema que uses

// ✅ Tus estilos globales
import '@/assets/styles.scss'

const app = createApp(App)

app.use(router)
app.use(PrimeVue, {
    theme: {
        preset: Aura,
        options: {
            darkModeSelector: '.app-dark'
        }
    }
})
app.use(ToastService)
app.use(ConfirmationService)

// ✅ Registrar componentes globales
app.component('Dialog', Dialog)
app.component('Button', Button)

app.mount('#app')
