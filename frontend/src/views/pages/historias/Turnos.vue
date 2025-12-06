<template>
  <div class="p-6">
    <!-- ENCABEZADO + LEYENDA -->
    <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
      <div>
        <h1 class="text-2xl font-bold text-gray-800 dark:text-gray-100">
          📅 Agenda del Profesional
        </h1>
      </div>

      <!-- LEYENDA -->
      <div class="flex flex-wrap items-center gap-4 text-sm">
        <!-- INDIVIDUALES -->
        <div class="flex items-center gap-2">
          <span class="w-3 h-3 rounded-full bg-blue-600 border border-blue-800"></span>
          <span class="text-gray-600 dark:text-gray-300">Turnos individuales</span>
        </div>

        <!-- GRUPALES -->
        <div
          v-for="g in leyendaGrupos"
          :key="g.nombre"
          class="flex items-center gap-2"
        >
          <span
            class="w-3 h-3 rounded-full border"
            :style="{ backgroundColor: g.color, borderColor: g.color }"
          ></span>
          <span class="text-gray-600 dark:text-gray-300">
            Grupo {{ g.nombre }}
          </span>
        </div>

        <!-- QUITADO: AUSENCIAS -->
      </div>
    </div>

    <!-- CALENDARIO -->
    <div class="bg-white dark:bg-[#1b1b1b] rounded-2xl shadow border border-gray-200 dark:border-gray-700 p-4">
      <FullCalendar :options="calendarOptions" />
    </div>

    <!-- MODAL DETALLE / EDICIÓN -->
    <div
      v-if="turnoSeleccionado"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    >
      <div class="bg-white dark:bg-[#1f1f1f] rounded-lg shadow-lg p-6 w-full max-w-md">
        <h2 class="text-xl font-bold mb-4 text-gray-800 dark:text-gray-100">
          Detalles del Turno
        </h2>

        <!-- AUSENCIA (queda por si el backend las habilita) -->
        <div v-if="turnoSeleccionado.tipo === 'ausencia'">
          <p class="mb-2 text-gray-700 dark:text-gray-200">
            <strong>Día bloqueado:</strong>
            {{ turnoSeleccionado.fechaLegible }}
          </p>
          <p class="mb-4 text-gray-600 dark:text-gray-300">
            {{ turnoSeleccionado.motivo }}
          </p>

          <div class="flex justify-end gap-2 mt-4">
            <button
              @click="cerrarModal"
              class="bg-gray-400 text-white px-3 py-1 rounded hover:bg-gray-500"
            >
              Cerrar
            </button>
          </div>
        </div>

        <!-- TURNOS NORMALES -->
        <div v-else>
          <!-- MODO EDICIÓN -->
          <div v-if="editando">
            <label class="block mb-2 text-sm text-gray-700 dark:text-gray-300">
              Motivo:
              <input
                v-model="turnoSeleccionado.description"
                class="w-full border border-gray-300 dark:border-gray-600 bg-white dark:bg-[#2a2a2a] text-gray-800 dark:text-gray-100 p-2 rounded mt-1 text-sm"
              />
            </label>

            <div class="flex gap-2 mb-2">
              <label class="flex-1 text-sm text-gray-700 dark:text-gray-300">
                Fecha:
                <input
                  type="date"
                  v-model="fechaEdit"
                  class="w-full border border-gray-300 dark:border-gray-600 bg-white dark:bg-[#2a2a2a] text-gray-800 dark:text-gray-100 p-2 rounded mt-1 text-sm"
                />
              </label>
              <label class="flex-1 text-sm text-gray-700 dark:text-gray-300">
                Hora:
                <input
                  type="time"
                  v-model="horaEdit"
                  class="w-full border border-gray-300 dark:border-gray-600 bg-white dark:bg-[#2a2a2a] text-gray-800 dark:text-gray-100 p-2 rounded mt-1 text-sm"
                />
              </label>
            </div>

            <div class="flex justify-between items-center mt-4">
              <span
                v-if="turnoSeleccionado.tipo === 'grupal'"
                class="text-xs text-blue-500"
              >
                {{ turnoSeleccionado.grupoNombre || 'Turno grupal' }}
              </span>

              <div class="flex gap-2 ml-auto">
                <button
                  @click="guardarEdicion"
                  class="bg-green-600 text-white px-3 py-1 rounded hover:bg-green-700 text-sm"
                >
                  Guardar
                </button>
                <button
                  @click="editando = false"
                  class="bg-gray-400 text-white px-3 py-1 rounded hover:bg-gray-500 text-sm"
                >
                  Cancelar
                </button>
              </div>
            </div>
          </div>

          <!-- MODO LECTURA -->
          <div v-else>
            <p class="text-gray-700 dark:text-gray-200 mb-1">
              <strong>Paciente:</strong> {{ turnoSeleccionado.paciente }}
            </p>
            <p class="text-gray-700 dark:text-gray-200 mb-1">
              <strong>DNI:</strong> {{ turnoSeleccionado.dni }}
            </p>
            <p class="text-gray-700 dark:text-gray-200 mb-1">
              <strong>Profesional:</strong> {{ turnoSeleccionado.profesional }}
            </p>

            <p class="text-gray-700 dark:text-gray-200 mb-1">
              <strong>Fecha:</strong> {{ turnoSeleccionado.fechaLegible }}
            </p>
            <p class="text-gray-700 dark:text-gray-200 mb-1">
              <strong>Hora:</strong> {{ turnoSeleccionado.horaLegible }}
            </p>

            <p class="text-gray-700 dark:text-gray-200 mb-2">
              <strong>Motivo:</strong> {{ turnoSeleccionado.description }}
            </p>

            <p
              v-if="turnoSeleccionado.tipo === 'grupal'"
              class="text-xs text-blue-500 mt-1"
            >
              Grupo: {{ turnoSeleccionado.grupoNombre || 'Grupal' }}
            </p>

            <div class="flex justify-end gap-2 mt-4">
              <template v-if="turnoSeleccionado.editable">
                <button
                  @click="editarTurno"
                  class="bg-yellow-500 text-white px-3 py-1 rounded hover:bg-yellow-600 text-sm"
                >
                  Editar
                </button>
                <button
                  @click="eliminarTurno(turnoSeleccionado.turnoId)"
                  class="bg-red-600 text-white px-3 py-1 rounded hover:bg-red-700 text-sm"
                >
                  Eliminar
                </button>
              </template>

              <button
                @click="cerrarModal"
                class="bg-gray-400 text-white px-3 py-1 rounded hover:bg-gray-500 text-sm"
              >
                Cerrar
              </button>
            </div>
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

import ausenciasService from '@/service/ausenciasService'

/* -------------------------------------------------------------------------- */
/*  VARIABLES PRINCIPALES                                                     */
/* -------------------------------------------------------------------------- */
const eventos = ref([])
const eventosTurnos = ref([])
const eventosAusencias = ref([]) // ya no se usan pero mantenidas por compatibilidad
const leyendaGrupos = ref([])

const turnoSeleccionado = ref(null)
const editando = ref(false)
const fechaEdit = ref('')
const horaEdit = ref('')
const duracionTurno = ref(30)

/* -------------------------------------------------------------------------- */
/*  FULLCALENDAR                                                              */
/* -------------------------------------------------------------------------- */
const calendarOptions = ref({
  plugins: [dayGridPlugin, timeGridPlugin, interactionPlugin],
  initialView: 'timeGridWeek',
  locale: 'es',
  slotMinTime: '08:00:00',
  slotMaxTime: '21:00:00',
  allDaySlot: false,
  editable: false,
  selectable: false,
  eventOverlap: true,
  headerToolbar: {
    left: 'prev,next today',
    center: 'title',
    right: 'dayGridMonth,timeGridWeek,timeGridDay'
  },
  events: eventos.value,

  eventClick(info) {
    const e = info.event

    turnoSeleccionado.value = {
      tipo: e.extendedProps.tipo,
      editable: e.extendedProps.editable,
      turnoId: e.extendedProps.turnoId,
      paciente: e.extendedProps.paciente,
      dni: e.extendedProps.dni,
      profesional: e.extendedProps.profesional,
      description: e.extendedProps.description,
      grupoNombre: e.extendedProps.grupoNombre,
      start: e.start,
      fechaLegible: e.start.toLocaleDateString(),
      horaLegible: e.start.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
    editando.value = false
  },

  eventDidMount(info) {
    if (info.event.extendedProps.tipo === 'ausencia') return

    const desc = info.event.extendedProps.description || "Sin motivo"
    const paciente = info.event.extendedProps.paciente
    const profesional = info.event.extendedProps.profesional
    const grupo = info.event.extendedProps.grupoNombre ? ` · ${info.event.extendedProps.grupoNombre}` : ""

    tippy(info.el, {
      content: `${paciente} — ${profesional}${grupo}<br>${desc}`,
      allowHTML: true,
      placement: "top",
      theme: "light-border",
    })
  }
})

/* -------------------------------------------------------------------------- */
/*  HELPERS                                                                   */
/* -------------------------------------------------------------------------- */
function toLocalISO(dateObj) {
  return (
    dateObj.getFullYear() +
    "-" +
    String(dateObj.getMonth() + 1).padStart(2, "0") +
    "-" +
    String(dateObj.getDate()).padStart(2, "0") +
    "T" +
    String(dateObj.getHours()).padStart(2, "0") +
    ":" +
    String(dateObj.getMinutes()).padStart(2, "0") +
    ":00"
  )
}

/* -------------------------------------------------------------------------- */
/*  CARGA DE DATOS                                                            */
/* -------------------------------------------------------------------------- */
async function cargarDuracionProfesional() {
  const resp = await fetch("/api/user", { credentials: "include" })
  if (!resp.ok) return
  const data = await resp.json()
  duracionTurno.value = data.duracion_turno || 30
}

async function cargarTurnosProfesional() {
  const resp = await fetch("/api/turnos/profesional/completo", {
    credentials: "include"
  })
  const data = await resp.json()

  const mapaTurnos = new Map()
  const grupos = {}

  data.forEach(t => {
    if (!mapaTurnos.has(t.id)) {
      mapaTurnos.set(t.id, {
        id: t.id,
        title: `${t.paciente}`,
        start: t.start,   // ← SIN UTC
        end: t.end,
        backgroundColor: t.color || t.grupoColor,
        borderColor: t.color || t.grupoColor,
        textColor: "#fff",
        extendedProps: {
          tipo: t.editable ? "individual" : "grupal",
          editable: t.editable,
          turnoId: t.id,
          paciente: t.paciente,
          dni: t.dni,
          profesional: t.profesional,
          description: t.description,
          grupoNombre: t.grupoNombre
        }
      })
    }

    if (t.grupoNombre) grupos[t.grupoNombre] = t.color || t.grupoColor
  })

  eventosTurnos.value = Array.from(mapaTurnos.values())
  leyendaGrupos.value = Object.keys(grupos).map(nombre => ({
    nombre,
    color: grupos[nombre]
  }))
}

async function cargarAgendaCompleta() {
  await cargarTurnosProfesional()

  // Ausencias removidas del render (a pedido)
  eventos.value = [...eventosTurnos.value]

  calendarOptions.value.events = eventos.value
}

/* -------------------------------------------------------------------------- */
/*  EDITAR / ACTUALIZAR / ELIMINAR                                            */
/* -------------------------------------------------------------------------- */
function editarTurno() {
  if (!turnoSeleccionado.value.editable) return

  editando.value = true
  const f = new Date(turnoSeleccionado.value.start)
  fechaEdit.value = f.toISOString().split("T")[0]
  horaEdit.value = f.toTimeString().slice(0, 5)
}

async function guardarEdicion() {
  const inicio = new Date(`${fechaEdit.value}T${horaEdit.value}:00`)
  const inicioISO = toLocalISO(inicio)
  const finISO = toLocalISO(new Date(inicio.getTime() + duracionTurno.value * 60000))

  await fetch(`/api/turnos/${turnoSeleccionado.value.turnoId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({
      motivo: turnoSeleccionado.value.description,
      fecha_inicio: inicioISO,
      fecha_fin: finISO
    })
  })

  await cargarAgendaCompleta()
  turnoSeleccionado.value = null
  editando.value = false
}

async function eliminarTurno(turnoId) {
  if (!confirm("¿Seguro que desea eliminar este turno?")) return

  await fetch(`/api/turnos/${turnoId}`, {
    method: "DELETE",
    credentials: "include"
  })

  turnoSeleccionado.value = null
  await cargarAgendaCompleta()
}

function cerrarModal() {
  turnoSeleccionado.value = null
  editando.value = false
}

/* -------------------------------------------------------------------------- */
/*  CICLO DE VIDA                                                             */
/* -------------------------------------------------------------------------- */
let intervalo = null

onMounted(async () => {
  await cargarDuracionProfesional()
  await cargarAgendaCompleta()

  intervalo = setInterval(cargarAgendaCompleta, 60000)
})

onUnmounted(() => {
  clearInterval(intervalo)
})
</script>
