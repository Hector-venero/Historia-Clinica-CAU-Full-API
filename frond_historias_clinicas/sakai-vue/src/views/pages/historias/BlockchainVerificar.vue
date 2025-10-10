<script setup>
import { ref } from 'vue'
import axios from 'axios'

const historiaId = ref('')
const resultado = ref(null)
const error = ref(null)
const loading = ref(false)

const verificar = async () => {
  error.value = null
  resultado.value = null
  loading.value = true
  try {
    const res = await axios.get(`/api/blockchain/verificar/${historiaId.value}`, { withCredentials: true })
    resultado.value = res.data
  } catch (err) {
    error.value = err.response?.data?.error || '❌ Error verificando hash'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="p-4 max-w-3xl mx-auto">
    <h1 class="text-2xl font-bold mb-4">Verificar Hash</h1>

    <div class="space-y-4">
      <input v-model="historiaId" type="number" placeholder="ID de historia"
             class="w-full border rounded p-2" />

      <button @click="verificar" class="bg-blue-600 text-white px-4 py-2 rounded" :disabled="loading">
        {{ loading ? 'Verificando...' : 'Verificar' }}
      </button>
    </div>

    <div v-if="resultado" class="mt-4 p-3" :class="resultado.valido ? 'bg-green-100' : 'bg-red-100'">
      <p><strong>Hash guardado:</strong> {{ resultado.hash_guardado }}</p>
      <p><strong>Hash recalculado:</strong> {{ resultado.hash_recalculado }}</p>
      <p><strong>Tx Hash:</strong> {{ resultado.tx_hash }}</p>
      <p v-if="resultado.valido">✅ Integridad verificada</p>
      <p v-else>❌ La historia fue modificada</p>
    </div>

    <div v-if="error" class="mt-4 p-3 bg-red-100 rounded">
      {{ error }}
    </div>
  </div>
</template>
