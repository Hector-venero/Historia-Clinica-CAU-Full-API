<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'

const route = useRoute()
const router = useRouter()

const pacienteId = route.params.id
const evolucionId = route.params.evoId

const evolucion = ref(null)
const loading = ref(true)
const error = ref(null)

const fetchEvolucion = async () => {
  try {
    loading.value = true
    const res = await axios.get(`/api/pacientes/${pacienteId}/evoluciones`, {
      withCredentials: true
    })
    const todas = res.data
    const encontrada = todas.find(e => e.id === parseInt(evolucionId))
    if (!encontrada) {
      error.value = 'Evolución no encontrada'
    } else {
      evolucion.value = encontrada
    }
  } catch (err) {
    console.error('Error al obtener evolución:', err)
    error.value = 'Error al cargar la evolución'
  } finally {
    loading.value = false
  }
}

const descargarEvolucionPDF = async () => {
  try {
    const res = await axios.get(`/api/pacientes/${pacienteId}/evolucion/${evolucionId}/pdf`, {
      responseType: 'blob',
      withCredentials: true
    })
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `evolucion_${evolucionId}.pdf`)
    document.body.appendChild(link)
    link.click()
  } catch (err) {
    console.error('Error al descargar PDF:', err)
  }
}

onMounted(fetchEvolucion)
</script>

<template>
  <div class="p-6 md:p-10 bg-gray-50 min-h-screen flex justify-center items-start">
    <div class="max-w-3xl w-full">
      <!-- 🔙 Volver -->
      <button
        @click="router.back()"
        class="text-blue-600 hover:text-blue-800 flex items-center mb-6 font-medium"
      >
        <i class="pi pi-arrow-left mr-2"></i> Volver a la Historia Clínica
      </button>

      <!-- ⏳ Cargando -->
      <div v-if="loading" class="text-gray-600 text-center py-8">
        <i class="pi pi-spin pi-spinner text-blue-600 text-lg mr-2"></i>
        Cargando evolución...
      </div>

      <!-- ⚠️ Error -->
      <div v-else-if="error" class="text-red-600 font-medium text-center py-6">
        {{ error }}
      </div>

      <!-- ✅ Contenido principal -->
      <div
        v-else-if="evolucion"
        class="bg-white rounded-2xl shadow-md border border-gray-100 p-8 hover:shadow-lg transition"
      >
        <div class="flex justify-between items-start mb-5">
          <h2 class="text-2xl font-semibold text-gray-800">
            Evolución del {{ new Date(evolucion.fecha).toLocaleDateString() }}
          </h2>

          <!-- 🧾 Exportar PDF -->
          <button
            @click="descargarEvolucionPDF"
            class="bg-blue-600 text-white px-4 py-2 rounded-lg shadow-sm hover:bg-blue-700 transition flex items-center text-sm"
          >
            <i class="pi pi-file-pdf mr-2"></i> Exportar esta evolución
          </button>
        </div>

        <p class="text-gray-500 mb-4 flex items-center text-sm">
          <i class="pi pi-user mr-2 text-gray-400"></i>
          <span class="font-medium">{{ evolucion.nombre_usuario }}</span>
          <span class="mx-2 text-gray-400">•</span>
          <span>{{ evolucion.especialidad_usuario || 'Director' }}</span>
        </p>

        <hr class="my-4 border-gray-200" />

        <!-- 🩺 Texto principal -->
        <p class="text-gray-800 text-base leading-relaxed whitespace-pre-line mb-6">
          {{ evolucion.contenido }}
        </p>

        <!-- 📎 Archivos adjuntos -->
        <div
          v-if="evolucion.archivos?.length"
          class="bg-gray-50 border border-gray-200 rounded-xl p-4"
        >
          <h3 class="font-semibold text-gray-700 mb-3 flex items-center">
            <i class="pi pi-paperclip mr-2 text-gray-500"></i> Archivos adjuntos
          </h3>
          <ul class="list-disc pl-6 space-y-1">
            <li
              v-for="archivo in evolucion.archivos"
              :key="archivo.url"
              class="text-blue-600 hover:underline text-sm"
            >
              <a :href="archivo.url" target="_blank">{{ archivo.nombre }}</a>
            </li>
          </ul>
        </div>

        <div v-else class="text-gray-400 italic text-sm">
          No hay archivos adjuntos.
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 🌙 Estilo general tipo Sakai Vue */
body {
  background-color: #f9fafb;
}
button {
  transition: all 0.2s ease;
}
button:focus {
  outline: none;
  ring: none;
}
</style>
