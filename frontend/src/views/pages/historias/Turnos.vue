<template>
  <div class="p-4">
    <h1 class="text-2xl font-bold mb-4">Agenda de Turnos</h1>

    <!-- Renderizamos FullCalendar -->
    <FullCalendar :options="calendarOptions" />

    <!-- Modal Detalle Turno -->
    <div
      v-if="turnoSeleccionado"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    >
      <div class="bg-white rounded-lg shadow-lg p-6 w-96">
        <h2 class="text-xl font-bold mb-4">Detalles del Turno</h2>

        <!-- 👇 Modo edición -->
        <div v-if="editando">
          <label class="block mb-2">
            Motivo:
            <input v-model="turnoSeleccionado.description" class="w-full border p-1 rounded" />
          </label>
          <label class="block mb-2">
            Fecha:
            <input type="date" v-model="fechaEdit" class="w-full border p-1 rounded" />
          </label>
          <label class="block mb-2">
            Hora:
            <input type="time" v-model="horaEdit" class="w-full border p-1 rounded" />
          </label>

          <div class="flex justify-end gap-2 mt-4">
            <button
              @click="guardarEdicion"
              class="bg-green-600 text-white px-3 py-1 rounded hover:bg-green-700"
            >
              Guardar
            </button>
            <button
              @click="editando = false"
              class="bg-gray-400 text-white px-3 py-1 rounded hover:bg-gray-500"
            >
              Cancelar
            </button>
          </div>
        </div>

        <!-- 👇 Modo lectura -->
        <div v-else>
          <p><strong>Paciente:</strong> {{ turnoSeleccionado.paciente }}</p>
          <p><strong>DNI:</strong> {{ turnoSeleccionado.dni }}</p>
          <p><strong>Profesional:</strong> {{ turnoSeleccionado.profesional }}</p>
          <p>
            <strong>Fecha:</strong>
            {{ new Date(turnoSeleccionado.start).toLocaleDateString() }}
          </p>
          <p>
            <strong>Hora:</strong>
            {{ new Date(turnoSeleccionado.start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }}
          </p>
          <p><strong>Motivo:</strong> {{ turnoSeleccionado.description }}</p>

          <div class="flex justify-end gap-2 mt-4">
            <button
              @click="editarTurno"
              class="bg-yellow-500 text-white px-3 py-1 rounded hover:bg-yellow-600"
            >
              Editar
            </button>
            <button
              @click="eliminarTurno(turnoSeleccionado.id)"
              class="bg-red-600 text-white px-3 py-1 rounded hover:bg-red-700"
            >
              Eliminar
            </button>
            <button
              @click="turnoSeleccionado = null"
              class="bg-gray-400 text-white px-3 py-1 rounded hover:bg-gray-500"
            >
              Cerrar
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import FullCalendar from '@fullcalendar/vue3'
import dayGridPlugin from '@fullcalendar/daygrid'
import timeGridPlugin from '@fullcalendar/timegrid'
import interactionPlugin from '@fullcalendar/interaction'
import tippy from 'tippy.js'
import 'tippy.js/dist/tippy.css'

import '@fullcalendar/common/main.css'
import '@fullcalendar/daygrid/main.css'
import '@fullcalendar/timegrid/main.css'

const eventos = ref([])
const turnoSeleccionado = ref(null)
const editando = ref(false)
const fechaEdit = ref('')
const horaEdit = ref('')

const calendarOptions = ref({
  plugins: [dayGridPlugin, timeGridPlugin, interactionPlugin],
  initialView: 'timeGridWeek',
  locale: 'es',
  headerToolbar: {
    left: 'prev,next today',
    center: 'title',
    right: 'dayGridMonth,timeGridWeek,timeGridDay'
  },
  events: eventos.value,
  eventClick(info) {
    turnoSeleccionado.value = {
      id: info.event.id,
      paciente: info.event.extendedProps?.paciente,
      dni: info.event.extendedProps?.dni,
      profesional: info.event.extendedProps?.profesional,
      description: info.event.extendedProps?.description,
      start: info.event.start
    }
  },
  eventDidMount(info) {
    tippy(info.el, {
      content: info.event.extendedProps.description || 'Sin motivo',
      placement: 'top',
      theme: 'light-border'
    })
  }
})

async function cargarTurnos() {
  try {
    const resp = await fetch('/api/turnos', { credentials: 'include' })
    if (!resp.ok) throw new Error('Error al cargar turnos')
    const data = await resp.json()

    eventos.value = data.map(t => ({
      id: t.id,
      title: `${t.paciente} (${t.dni})`,
      start: t.start,
      paciente: t.paciente,
      dni: t.dni,
      profesional: t.profesional,
      description: t.description
    }))

    calendarOptions.value.events = eventos.value
  } catch (err) {
    console.error('Error cargando turnos:', err)
  }
}

// 👉 Eliminar turno
async function eliminarTurno(id) {
  if (!confirm('¿Seguro que desea eliminar este turno?')) return

  const resp = await fetch(`/api/turnos/${id}`, {
    method: 'DELETE',
    credentials: 'include'
  })
  if (resp.ok) {
    eventos.value = eventos.value.filter(e => e.id !== id)
    calendarOptions.value.events = eventos.value
    turnoSeleccionado.value = null
    alert('Turno eliminado ✅')
  } else {
    alert('Error al eliminar turno ❌')
  }
}

// 👉 Activar edición
function editarTurno() {
  editando.value = true
  const fechaObj = new Date(turnoSeleccionado.value.start)
  fechaEdit.value = fechaObj.toISOString().split('T')[0]
  horaEdit.value = fechaObj.toTimeString().slice(0, 5)
}

// 👉 Guardar cambios (PUT)
async function guardarEdicion() {
  const nuevaFecha = `${fechaEdit.value}T${horaEdit.value}:00`

  const resp = await fetch(`/api/turnos/${turnoSeleccionado.value.id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({
      motivo: turnoSeleccionado.value.description,
      fecha: nuevaFecha
    })
  })

  if (resp.ok) {
    alert('Turno actualizado ✅')
    editando.value = false
    turnoSeleccionado.value.start = nuevaFecha
    cargarTurnos() // refrescar calendario
  } else {
    alert('Error al actualizar ❌')
  }
}

let intervalo = null
onMounted(() => {
  cargarTurnos()
  intervalo = setInterval(cargarTurnos, 30000)
})
onUnmounted(() => {
  if (intervalo) clearInterval(intervalo)
})
</script>
