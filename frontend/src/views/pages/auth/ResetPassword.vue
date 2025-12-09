<template>
  <div class="bg-surface-50 dark:bg-surface-950 flex items-center justify-center min-h-screen min-w-[100vw] overflow-hidden">
    <div class="flex flex-col items-center justify-center">
      <div
        style="border-radius: 56px; padding: 0.3rem; background: linear-gradient(180deg, var(--primary-color) 10%, rgba(33,150,243,0) 30%)"
      >
        <div
          class="w-full bg-surface-0 dark:bg-surface-900 py-20 px-8 sm:px-20"
          style="border-radius: 53px"
        >
          <div class="text-center mb-8">
            <img :src="logoUnsam" alt="Logo CAU" class="mb-6 w-24 mx-auto" />
            <div class="text-surface-900 dark:text-surface-0 text-3xl font-medium mb-4">
              Restablecer Contraseña
            </div>
            <span class="text-muted-color font-medium">
              Ingresá tu nueva contraseña para continuar.
            </span>
          </div>

          <!-- Formulario -->
          <form @submit.prevent="resetear" class="space-y-6 w-full md:w-[28rem]">
            <div>
              <label
                for="password"
                class="block text-surface-900 dark:text-surface-0 text-xl font-medium mb-2"
              >
                Nueva contraseña
              </label>
              <input
                id="password"
                v-model="password"
                type="password"
                placeholder="********"
                class="w-full border border-gray-300 rounded-lg p-3 text-base focus:outline-none focus:ring-2 focus:ring-primary transition"
              />
            </div>

            <div>
              <label
                for="confirmPassword"
                class="block text-surface-900 dark:text-surface-0 text-xl font-medium mb-2"
              >
                Confirmar contraseña
              </label>
              <input
                id="confirmPassword"
                v-model="confirmPassword"
                type="password"
                placeholder="********"
                class="w-full border border-gray-300 rounded-lg p-3 text-base focus:outline-none focus:ring-2 focus:ring-primary transition"
              />
            </div>

            <button
              type="submit"
              class="w-full bg-primary text-white py-3 rounded-lg text-lg font-medium hover:opacity-90 transition"
              :disabled="loading"
            >
              <span v-if="!loading">Guardar nueva contraseña</span>
              <span v-else>Cargando...</span>
            </button>

            <!-- Mensajes -->
            <p
              v-if="mensaje"
              class="text-green-600 text-center mt-4 text-sm font-medium"
            >
              {{ mensaje }}
            </p>
            <p
              v-if="error"
              class="text-red-600 text-center mt-4 text-sm font-medium"
            >
              {{ error }}
            </p>

            <div class="text-center mt-6">
              <router-link
                to="/auth/login"
                class="text-sm text-primary hover:underline"
              >
                ← Volver al inicio de sesión
              </router-link>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import logoUnsam from '@/assets/logo_unsam_sin_letras.png'
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { validarPasswordFuerte } from '@/utils/validators'

const route = useRoute()
const router = useRouter()

const password = ref('')
const confirmPassword = ref('')
const mensaje = ref('')
const error = ref('')
const loading = ref(false)

async function resetear() {
  mensaje.value = ''
  error.value = ''

  const errPw = validarPasswordFuerte(password.value)
  if (errPw) {
    error.value = errPw;
    return;
  }

  if (password.value !== confirmPassword.value) {
    error.value = 'Las contraseñas no coinciden'
    return
  }

  loading.value = true
  try {
    const res = await fetch(`/api/reset/${route.params.token}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        new_password: password.value,
        confirm_password: confirmPassword.value
      })
    })
    const data = await res.json()
    if (res.ok) {
      mensaje.value = data.message
      setTimeout(() => router.push('/auth/login'), 2500)
    } else {
      error.value = data.error || 'No se pudo restablecer la contraseña'
    }
  } catch (err) {
    error.value = 'Error de conexión con el servidor'
  } finally {
    loading.value = false
  }
}
</script>
