<script setup>
import FileUpload from 'primevue/fileupload'
import Toast from 'primevue/toast'
import { useToast } from 'primevue/usetoast'
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import historiaService from '@/service/historiaService'   // ✅ usar tu servicio
import axios from 'axios'

const route = useRoute()
const pacienteId = route.params.id

const toast = useToast()

const paciente = ref(null)
const historias = ref([])
const evoluciones = ref([])
const loading = ref(true)
const error = ref(null)

const showForm = ref(false)
const fecha = ref(new Date().toISOString().split('T')[0])
const contenido = ref('')
const archivos = ref([])

const fetchHistoria = async () => {
  try {
    loading.value = true
    // 🔹 paciente básico
    const resPaciente = await axios.get(`/api/pacientes/${pacienteId}`, { withCredentials: true })
    paciente.value = resPaciente.data

    // 🔹 historias clínicas vía service
    const resHistorias = await historiaService.getHistorias(pacienteId)
    historias.value = resHistorias.data

    // 🔹 evoluciones
    const resEvoluciones = await axios.get(`/api/pacientes/${pacienteId}/evoluciones`, { withCredentials: true })
    evoluciones.value = resEvoluciones.data
  } catch (err) {
    error.value = 'Error cargando la historia clínica.'
    console.error(err)
  } finally {
    loading.value = false
  }
}

const onFileSelect = (event) => {
  archivos.value = event.files
}

const fileUploader = ref(null)

const guardarEvolucion = async () => {
  try {
    const formData = new FormData()
    formData.append('fecha', fecha.value)
    formData.append('contenido', contenido.value)

    for (let i = 0; i < archivos.value.length; i++) {
      formData.append('archivos', archivos.value[i])
    }

    await axios.post(`/api/pacientes/${pacienteId}/evolucion`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      withCredentials: true
    })

    toast.add({ severity: 'success', summary: 'Éxito', detail: 'Evolución guardada ✅', life: 3000 })

    showForm.value = false
    contenido.value = ''
    archivos.value = []
    fileUploader.value.clear()

    await fetchHistoria()
  } catch (err) {
    console.error('Error al guardar evolución:', err)
    toast.add({ severity: 'error', summary: 'Error', detail: 'Error al guardar evolución', life: 3000 })
  }
}

onMounted(() => {
  fetchHistoria()
})
</script>

<template>
  <div class="p-4">
    <Toast />

    <h1 class="text-2xl font-bold mb-4">
      Historia Clínica de {{ paciente?.apellido?.toUpperCase() }} {{ paciente?.nombre?.toUpperCase() }}
    </h1>

    <p v-if="loading">Cargando...</p>
    <p v-if="error" class="text-red-500">{{ error }}</p>

    <div v-if="paciente && !loading" class="mb-6 border p-4 rounded bg-gray-50">
      <p><strong>DNI:</strong> {{ paciente.dni }}</p>
      <p><strong>Cobertura:</strong> {{ paciente?.cobertura }}</p>
      <p><strong>Nro HC:</strong> {{ paciente.nro_hc }}</p>
    </div>

    <!-- 🔹 HISTORIAS CLÍNICAS -->
    <div v-if="historias.length">
      <h2 class="text-xl font-semibold mt-6 mb-2">Historias Clínicas</h2>
      <div v-for="h in historias" :key="h.id" class="border p-4 rounded mb-3 bg-white shadow">
        <p><strong>Fecha:</strong> {{ new Date(h.fecha).toLocaleString() }}</p>
        <p><strong>Motivo:</strong> {{ h.motivo_consulta }}</p>
        <p><strong>Diagnóstico:</strong> {{ h.diagnostico }}</p>
        <p>
          <strong>Hash:</strong>
          <span class="font-mono">{{ h.hash?.slice(0, 15) }}...</span>
        </p>
        <p>
          <strong>Estado:</strong>
          <span v-if="h.tx_hash" class="text-green-600 font-semibold">🟢 Registrado en Blockchain</span>
          <span v-else class="text-red-600 font-semibold">🔴 No registrado</span>
        </p>
      </div>
    </div>

    <!-- 🔹 EVOLUCIONES -->
    <div v-if="evoluciones.length === 0 && !loading">
      <p>No hay evoluciones registradas aún.</p>
    </div>

    <div v-else>
      <h2 class="text-xl font-semibold mt-6 mb-2">Evoluciones</h2>
      <div
        v-for="evo in evoluciones"
        :key="evo.id"
        class="border rounded-lg mb-4 p-4 shadow bg-white"
      >
        <h3 class="text-lg font-semibold">Fecha: {{ new Date(evo.fecha).toLocaleDateString() }}</h3>
        <p>{{ evo.contenido }}</p>
        <div v-if="evo.archivos && evo.archivos.length">
          <strong>Archivos adjuntos:</strong>
          <ul>
            <li v-for="archivo in evo.archivos" :key="archivo.nombre">
              <a :href="archivo.url" target="_blank">{{ archivo.nombre }}</a>
            </li>
          </ul>
        </div>
      </div>
    </div>

    <!-- 🔹 FORMULARIO NUEVA EVOLUCIÓN -->
    <button
      @click="showForm = !showForm"
      class="p-button p-component bg-green-500 text-white mt-6"
    >
      {{ showForm ? 'Cancelar' : 'Agregar Evolución' }}
    </button>

    <div v-if="showForm" class="mt-6 border p-4 rounded bg-white">
      <label for="fecha" class="block font-medium mb-2">Fecha</label>
      <input type="date" v-model="fecha" class="p-2 border rounded w-full mb-4" />

      <label for="contenido" class="block font-medium mb-2">Evolución</label>
      <textarea v-model="contenido" rows="5" class="p-2 border rounded w-full mb-4" placeholder="Escribí la evolución clínica..."></textarea>

      <label class="block font-medium mb-2">Archivos adjuntos</label>
      <FileUpload
        ref="fileUploader"
        name="archivos"
        customUpload
        :multiple="true"
        @select="onFileSelect"
        :auto="false"
        accept=".pdf,image/*"
        class="mb-4"
      />

      <button @click="guardarEvolucion" class="p-button p-component bg-blue-600 text-white">
        Guardar Evolución
      </button>
    </div>
  </div>
</template>

<style scoped>
/* Opcional: personalización extra */
</style>
