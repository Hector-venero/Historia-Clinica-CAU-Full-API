<template>
  <div class="p-4">
    <h1 class="text-2xl font-bold mb-4">
      🗓️ Agenda grupal: {{ grupo?.nombre || 'Cargando...' }}
    </h1>

    <FullCalendar :options="calendarOptions" />

    <!-- Modal Detalle Turno -->
    <div
      v-if="turnoSeleccionado"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    >
      <div class="bg-white rounded-lg shadow-lg p-6 w-96">
        <h2 class="text-xl font-bold mb-4">Detalles del Turno</h2>

        <div>
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
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import FullCalendar from '@fullcalendar/vue3'
import dayGridPlugin from '@fullcalendar/daygrid'
import timeGridPlugin from '@fullcalendar/timegrid'
import interactionPlugin from '@fullcalendar/interaction'
import tippy from 'tippy.js'
import 'tippy.js/dist/tippy.css'

import '@fullcalendar/common/main.css'
import '@fullcalendar/daygrid/main.css'
import '@fullcalendar/timegrid/main.css'

const route = useRoute()
const grupoId = route.params.grupoId
const grupo = ref(null)
const eventos = ref([])
const turnoSeleccionado = ref(null)

const calendarOptions = ref({
  plugins: [dayGridPlugin, timeGridPlugin, interactionPlugin],
  initialView: 'dayGridMonth', // 👈 para ver los turnos del mes completo
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
      content: `${info.event.extendedProps.profesional} — ${info.event.extendedProps.description}`,
      placement: 'top',
      theme: 'light-border'
    })
  }
})

// 🔹 Cargar turnos de todos los miembros del grupo
async function cargarTurnosGrupo() {
  try {
    const [resGrupo, resTurnos] = await Promise.all([
      fetch(`/api/grupos/${grupoId}`, { credentials: 'include' }),
      fetch(`/api/turnos/grupo/${grupoId}`, { credentials: 'include' })
    ])

    if (!resGrupo.ok || !resTurnos.ok) throw new Error('Error al cargar datos del grupo')

    grupo.value = await resGrupo.json()
    const dataTurnos = await resTurnos.json()
    console.log('📅 Datos del backend:', dataTurnos)

    // 🔹 Convertir formato GMT → ISO válido para FullCalendar
    eventos.value = dataTurnos.map(t => {
      const fechaISO = new Date(t.fecha).toISOString().slice(0, 19)
      return {
        id: t.id,
        title: `${t.paciente} (${t.profesional})`,
        start: fechaISO,
        paciente: t.paciente,
        dni: t.dni || '',
        profesional: t.profesional,
        description: t.motivo || 'Sin motivo',
        backgroundColor: grupo.value?.color || '#00936B'
      }
    })

    calendarOptions.value.events = eventos.value
  } catch (err) {
    console.error('Error cargando turnos grupales:', err)
  }
}

onMounted(() => {
  cargarTurnosGrupo()
})
</script>

<style scoped>
.fc {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
  padding: 1rem;
}
</style>
