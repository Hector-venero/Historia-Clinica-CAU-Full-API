<script setup>
import { ref } from 'vue'
import axios from 'axios'

const actual = ref('')
const nueva = ref('')
const confirmar = ref('')
const mensaje = ref('')
const error = ref('')
const loading = ref(false)

const cambiar = async () => {
  mensaje.value = ''
  error.value = ''

  if (nueva.value !== confirmar.value) {
    error.value = 'Las contraseñas no coinciden'
    return
  }

  loading.value = true
  try {
    const res = await axios.post(
      '/api/usuario/cambiar-password',
      {
        actual: actual.value,
        nueva: nueva.value,
        confirmar: confirmar.value
      },
      { withCredentials: true }
    )

    mensaje.value = res.data.message
    actual.value = ''
    nueva.value = ''
    confirmar.value = ''
  } catch (err) {
    error.value = err.response?.data?.error || 'No se pudo cambiar la contraseña'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="max-w-lg mx-auto bg-white p-6 rounded-xl shadow">

    <h1 class="text-2xl font-bold mb-6">Cambiar Contraseña</h1>

    <label class="block font-semibold mb-2">Contraseña actual</label>
    <input
      v-model="actual"
      type="password"
      class="w-full p-2 border rounded mb-4"
    />

    <label class="block font-semibold mb-2">Nueva contraseña</label>
    <input
      v-model="nueva"
      type="password"
      class="w-full p-2 border rounded mb-4"
    />

    <label class="block font-semibold mb-2">Confirmar nueva contraseña</label>
    <input
      v-model="confirmar"
      type="password"
      class="w-full p-2 border rounded mb-4"
    />

    <button
      class="mt-4 bg-blue-600 text-white px-4 py-2 rounded-lg"
      @click="cambiar"
      :disabled="loading"
    >
      Guardar nueva contraseña
    </button>

    <p v-if="mensaje" class="text-green-600 mt-4">{{ mensaje }}</p>
    <p v-if="error" class="text-red-600 mt-4">{{ error }}</p>
  </div>
</template>
