<template>
  <div class="flex justify-center items-start p-8">
    <div class="bg-white shadow-xl rounded-2xl p-8 w-full max-w-2xl">
      <h1 class="text-3xl font-bold text-center mb-8 text-blue-700">
        Nuevo Turno
      </h1>

      <form @submit.prevent="crearTurno" class="space-y-6">
        <!-- Paciente -->
        <div class="relative">
          <label class="block mb-2 font-semibold text-gray-700">Paciente</label>
          <input
            v-model="searchPaciente"
            @input="buscarPacientes"
            type="text"
            placeholder="Buscar por DNI o nombre"
            class="w-full p-3 border rounded-xl shadow-sm focus:ring-2 focus:ring-blue-500"
            autocomplete="off"
          />
          <!-- Lista resultados -->
          <ul
            v-if="pacientes.length > 0"
            class="absolute z-20 left-0 right-0 border rounded-lg mt-2 bg-white shadow-md divide-y max-h-48 overflow-y-auto"
          >
            <li
              v-for="p in pacientes"
              :key="p.id"
              @click="seleccionarPaciente(p)"
              class="px-3 py-2 hover:bg-blue-100 cursor-pointer"
            >
              {{ p.apellido }} {{ p.nombre }} (DNI: {{ p.dni }})
            </li>
          </ul>
          <p v-if="pacienteId" class="mt-2 text-sm text-green-600 font-medium">
            ✅ Seleccionado: {{ pacienteSeleccionado }}
          </p>
        </div>

        <!-- Profesional -->
        <div>
          <label class="block mb-2 font-semibold text-gray-700">Profesional</label>
          <select
            v-model="usuarioId"
            class="w-full p-3 border rounded-xl shadow-sm focus:ring-2 focus:ring-blue-500"
            required
          >
            <option value="" disabled>Seleccione un profesional</option>
            <option v-for="p in profesionales" :key="p.id" :value="p.id">
              {{ p.nombre }} ({{ p.especialidad || "Sin especialidad" }})
            </option>
          </select>
        </div>

        <!-- Fecha -->
        <div>
          <label class="block mb-2 font-semibold text-gray-700">Fecha y hora</label>
          <input
            v-model="fecha"
            type="datetime-local"
            class="w-full p-3 border rounded-xl shadow-sm focus:ring-2 focus:ring-blue-500"
            required
          />
        </div>

        <!-- Motivo -->
        <div>
          <label class="block mb-2 font-semibold text-gray-700">Motivo</label>
          <textarea
            v-model="motivo"
            rows="3"
            placeholder="Motivo del turno"
            class="w-full p-3 border rounded-xl shadow-sm focus:ring-2 focus:ring-blue-500"
          ></textarea>
        </div>

        <!-- Botón -->
        <div class="flex justify-center">
          <button
            type="submit"
            class="bg-blue-600 hover:bg-blue-700 text-white font-semibold px-6 py-3 rounded-xl shadow-lg transition"
          >
            Guardar Turno
          </button>
        </div>
      </form>

      <!-- Mensajes -->
      <p v-if="mensaje" class="mt-6 text-green-600 font-semibold text-center">
        {{ mensaje }}
      </p>
      <p v-if="error" class="mt-6 text-red-600 font-semibold text-center">
        {{ error }}
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const searchPaciente = ref('')
const pacientes = ref([])
const pacienteId = ref('')
const pacienteSeleccionado = ref('')
const usuarioId = ref('')
const fecha = ref('')
const motivo = ref('')
const mensaje = ref('')
const error = ref('')
const profesionales = ref([])

onMounted(async () => {
  try {
    const resp = await fetch('/api/profesionales', { credentials: 'include' })
    if (!resp.ok) throw new Error('Error al cargar profesionales')
    profesionales.value = await resp.json()
  } catch (e) {
    console.error('Error cargando profesionales', e)
    error.value = 'No se pudieron cargar los profesionales'
  }
})

async function buscarPacientes() {
  if (!searchPaciente.value || searchPaciente.value.length < 2) {
    pacientes.value = []
    return
  }
  try {
    const resp = await fetch(`/api/pacientes/buscar?q=${encodeURIComponent(searchPaciente.value)}`, {
      credentials: 'include'
    })
    if (!resp.ok) throw new Error('Error de búsqueda')
    const data = await resp.json()
    pacientes.value = data.pacientes || []
  } catch (e) {
    console.error('Error buscando pacientes', e)
  }
}

function seleccionarPaciente(p) {
  pacienteId.value = p.id
  pacienteSeleccionado.value = `${p.apellido} ${p.nombre} (DNI: ${p.dni})`
  searchPaciente.value = pacienteSeleccionado.value
  pacientes.value = [] // cerrar lista
}

async function crearTurno() {
  mensaje.value = ''
  error.value = ''

  if (!pacienteId.value) {
    error.value = 'Debe seleccionar un paciente'
    return
  }

  try {
    const resp = await fetch('/api/turnos', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({
        paciente_id: pacienteId.value,
        usuario_id: usuarioId.value,
        fecha: fecha.value,
        motivo: motivo.value
      })
    })

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}))
      throw new Error(err.error || 'Error al crear turno')
    }

    const data = await resp.json()
    mensaje.value = data.message || 'Turno creado correctamente ✅'

    // Resetear formulario
    pacienteId.value = ''
    usuarioId.value = ''
    fecha.value = ''
    motivo.value = ''
    searchPaciente.value = ''
    pacienteSeleccionado.value = ''
  } catch (e) {
    error.value = e.message
  }
}
</script>
