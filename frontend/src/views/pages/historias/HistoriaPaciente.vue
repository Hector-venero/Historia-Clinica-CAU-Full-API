<script setup>
import FileUpload from 'primevue/fileupload'
import Toast from 'primevue/toast'
import { useToast } from 'primevue/usetoast'
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import historiaService from '@/service/historiaService'
import axios from 'axios'
import { useRouter } from 'vue-router'

const route = useRoute()
const pacienteId = route.params.id
const router = useRouter()

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
const fileUploader = ref(null)

/**
 * Carga los datos del paciente, sus historias y evoluciones
 */
const fetchHistoria = async () => {
  try {
    loading.value = true

    const resPaciente = await axios.get(`/api/pacientes/${pacienteId}`, { withCredentials: true })
    paciente.value = resPaciente.data

    const resHistorias = await historiaService.getHistorias(pacienteId)
    historias.value = resHistorias.data

    const resEvoluciones = await axios.get(`/api/pacientes/${pacienteId}/evoluciones`, { withCredentials: true })
    evoluciones.value = resEvoluciones.data
  } catch (err) {
    console.error(err)
    error.value = 'Error cargando la historia clínica.'
  } finally {
    loading.value = false
  }
}

/**
 * Guarda una nueva evolución
 */
const guardarEvolucion = async () => {
  try {
    const formData = new FormData()
    formData.append('fecha', fecha.value)
    formData.append('contenido', contenido.value)
    for (const archivo of archivos.value) {
      formData.append('archivos', archivo)
    }

    await axios.post(`/api/pacientes/${pacienteId}/evolucion`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      withCredentials: true
    })

    toast.add({ severity: 'success', summary: 'Éxito', detail: 'Evolución guardada ✅', life: 3000 })

    showForm.value = false
    contenido.value = ''
    archivos.value = []
    fileUploader.value?.clear()

    await fetchHistoria()
  } catch (err) {
    console.error('Error al guardar evolución:', err)
    toast.add({ severity: 'error', summary: 'Error', detail: 'Error al guardar evolución', life: 3000 })
  }
}

/**
 * Exporta toda la historia clínica en PDF
 */
const descargarHistoriaPDF = async () => {
  try {
    toast.add({ severity: 'info', summary: 'Generando PDF...', life: 2000 })
    const res = await axios.get(`/api/pacientes/${pacienteId}/historia/pdf`, {
      responseType: 'blob',
      withCredentials: true
    })
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `historia_paciente_${pacienteId}.pdf`)
    document.body.appendChild(link)
    link.click()
  } catch (err) {
    console.error(err)
    toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo generar el PDF', life: 3000 })
  }
}

/**
 * Exporta una evolución individual en PDF
 */
const descargarEvolucionPDF = async (evoId) => {
  try {
    toast.add({ severity: 'info', summary: 'Generando PDF...', life: 2000 })
    const res = await axios.get(`/api/pacientes/${pacienteId}/evolucion/${evoId}/pdf`, {
      responseType: 'blob',
      withCredentials: true
    })
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `evolucion_${evoId}.pdf`)
    document.body.appendChild(link)
    link.click()
  } catch (err) {
    console.error(err)
    toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo generar el PDF', life: 3000 })
  }
}

const onFileSelect = (event) => {
  archivos.value = event.files
}

/**
 * Verifica la integridad de toda la historia clínica
 */
const verificarIntegridad = async () => {
  try {
    const { data } = await axios.get(`/api/blockchain/verificar/historia/${pacienteId}`, {
      withCredentials: true
    })
    toast.add({
      severity: data.valido ? 'success' : 'warn',
      summary: 'Verificación Blockchain',
      detail: data.mensaje,
      life: 5000
    })
  } catch (err) {
    console.error('Error al verificar integridad:', err)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudo verificar la integridad de la historia.',
      life: 4000
    })
  }
}

/**
 * Verifica la integridad de una evolución individual
 */
const verificarEvolucion = async (evoId) => {
  try {
    const { data } = await axios.get(`/api/blockchain/verificar/evolucion/${evoId}`, {
      withCredentials: true
    })
    toast.add({
      severity: data.valido ? 'success' : 'warn',
      summary: 'Verificación Blockchain',
      detail: data.mensaje,
      life: 4000
    })
  } catch (err) {
    console.error('Error al verificar evolución:', err)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudo verificar la integridad de la evolución.',
      life: 4000
    })
  }
}

const verAuditoriasBlockchain = () => {
  // ✅ Usamos el id real de la historia consolidada más reciente
  const idHistoria = historias.value?.[0]?.id || null

  if (!idHistoria) {
    toast.add({
      severity: 'warn',
      summary: 'Sin historia registrada',
      detail: 'El paciente aún no tiene una historia consolidada.',
      life: 4000
    })
    return
  }

  toast.add({
    severity: 'info',
    summary: 'Redirigiendo...',
    detail: 'Abriendo auditorías Blockchain',
    life: 800
  })

  setTimeout(() => {
    // ✅ pasamos el id correcto de la tabla `historias`
    router.push({ path: '/blockchain/verificar', query: { id: idHistoria } })
  }, 300)
}

onMounted(fetchHistoria)
</script>

<template>
  <div class="p-4 md:p-8 min-h-screen bg-gray-50 dark:bg-[#121212] transition-colors">

    <Toast />

    <h1 class="text-3xl font-bold mb-4 text-gray-800 flex items-center">
      <i class="pi pi-user mr-3 text-blue-600"></i>
      Historia Clínica de {{ paciente?.apellido?.toUpperCase() }} {{ paciente?.nombre?.toUpperCase() }}
    </h1>

    <p v-if="loading" class="text-gray-500">Cargando...</p>
    <p v-if="error" class="text-red-500">{{ error }}</p>

    <!-- 📋 Datos del paciente -->
    <div v-if="paciente && !loading" class="mb-6 border p-4 rounded-2xl bg-white shadow-sm">
      <div class="grid md:grid-cols-2 gap-2 text-gray-700 text-sm">
        <p><strong>DNI:</strong> {{ paciente.dni }}</p>
        <p><strong>Cobertura:</strong> {{ paciente?.cobertura || '-' }}</p>
        <p><strong>Nº HC:</strong> {{ paciente.nro_hc }}</p>
        <p><strong>Fecha de nacimiento:</strong> {{ paciente.fecha_nacimiento || '-' }}</p>
      </div>
    </div>

    <!-- 🧠 EVOLUCIONES -->
    <div v-if="!loading">
      <div class="flex flex-wrap justify-between items-center mt-6 mb-3 gap-2">
        <h2 class="text-xl font-semibold text-gray-800 flex items-center">
          <i class="pi pi-book mr-2 text-blue-500"></i> Evoluciones
        </h2>

        <div class="flex flex-wrap justify-end gap-2">
          <button
            @click="descargarHistoriaPDF"
            class="flex items-center bg-blue-600 text-white px-4 py-2 rounded-lg shadow-sm hover:bg-blue-700 transition text-sm"
          >
            <i class="pi pi-file-pdf mr-2"></i> Exportar Historia Completa
          </button>

          <button
            @click="verAuditoriasBlockchain"
            class="flex items-center bg-purple-600 text-white px-4 py-2 rounded-lg shadow-sm hover:bg-purple-700 transition text-sm"
          >
            <i class="pi pi-list mr-2"></i> Ver Auditorías Blockchain
          </button>

          <button
            @click="showForm = !showForm"
            class="flex items-center bg-green-600 text-white px-4 py-2 rounded-lg shadow-sm hover:bg-green-700 transition text-sm"
          >
            <i class="pi pi-plus mr-2"></i> {{ showForm ? 'Cancelar' : 'Agregar Evolución' }}
          </button>
        </div>
      </div>

      <!-- Si no hay evoluciones -->
      <p v-if="evoluciones.length === 0" class="text-gray-500 mt-3">No hay evoluciones registradas aún.</p>

      <!-- Cards de evoluciones -->
      <div
        v-for="evo in evoluciones"
        :key="evo.id"
        class="border rounded-2xl mb-4 p-5 shadow-sm bg-white hover:shadow-md transition cursor-pointer"
      >
        <div class="flex justify-between text-sm text-gray-600 mb-2">
          <span class="font-medium">{{ new Date(evo.fecha).toLocaleDateString() }}</span>
          <span>{{ evo.nombre_usuario }} — {{ evo.especialidad_usuario || 'Director' }}</span>
        </div>
        <p class="text-gray-800 text-sm mb-4 line-clamp-3">{{ evo.contenido }}</p>

        <div class="flex justify-end gap-3">
          <button
            @click="$router.push({ name: 'evolucionDetalle', params: { id: pacienteId, evoId: evo.id } })"
            class="text-blue-600 hover:text-blue-800 text-sm flex items-center"
          >
            <i class="pi pi-eye mr-1"></i> Ver Detalle
          </button>
          <button
            @click="descargarEvolucionPDF(evo.id)"
            class="text-red-600 hover:text-red-800 text-sm flex items-center"
          >
            <i class="pi pi-file-pdf mr-1"></i> Exportar PDF
          </button>
          <button
            @click="verificarEvolucion(evo.id)"
            class="text-purple-600 hover:text-blue-800 text-sm flex items-center"
          >
            <i class="pi pi-shield mr-1"></i> Verificar Integridad
          </button>

        </div>
      </div>
    </div>

    <!-- 📝 FORMULARIO NUEVA EVOLUCIÓN -->
    <div
      v-if="showForm"
      class="mt-6 border p-4 rounded-2xl bg-white shadow-sm animate-fade-in"
    >
      <h3 class="text-lg font-semibold text-gray-700 mb-4">Registrar nueva evolución</h3>

      <label for="fecha" class="block font-medium mb-2 text-gray-700">Fecha</label>
      <input type="date" v-model="fecha" class="p-2 border rounded w-full mb-4" />

      <label for="contenido" class="block font-medium mb-2 text-gray-700">Evolución</label>
      <textarea
        v-model="contenido"
        rows="5"
        class="p-2 border rounded w-full mb-4"
        placeholder="Escribí la evolución clínica..."
      ></textarea>

      <label class="block font-medium mb-2 text-gray-700">Archivos adjuntos</label>
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

      <button
        @click="guardarEvolucion"
        class="bg-blue-600 text-white px-5 py-2 rounded-lg shadow-sm hover:bg-blue-700 transition flex items-center"
      >
        <i class="pi pi-save mr-2"></i> Guardar Evolución
      </button>
    </div>
  </div>
</template>

<style scoped>
.line-clamp-3 {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.animate-fade-in {
  animation: fadeIn 0.4s ease-in-out;
}
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
