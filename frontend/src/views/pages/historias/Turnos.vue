<template>
  <div class="p-6">
    <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
      <div>
        <h1 class="text-2xl font-bold text-gray-800 dark:text-gray-100">
          📅 Agenda del Profesional
        </h1>
      </div>

      <div class="flex flex-wrap items-center gap-4 text-sm">
        <div class="flex items-center gap-2">
          <span class="w-3 h-3 rounded-full bg-blue-600 border border-blue-800"></span>
          <span class="text-gray-600 dark:text-gray-300">Individuales</span>
        </div>

        <div
          v-for="g in leyendaGrupos"
          :key="g.nombre"
          class="flex items-center gap-2"
        >
          <span
            class="w-3 h-3 rounded-full border border-dashed"
            :style="{ backgroundColor: g.colorTransparente, borderColor: g.colorOriginal }"
          ></span>
          <span class="text-gray-600 dark:text-gray-300">
             {{ g.nombre }}
          </span>
        </div>
      </div>
    </div>

    <div class="bg-white dark:bg-[#1b1b1b] rounded-2xl shadow border border-gray-200 dark:border-gray-700 p-4">
      <FullCalendar :options="calendarOptions" />
    </div>

    <div
      v-if="turnoSeleccionado"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    >
      <div class="bg-white dark:bg-[#1f1f1f] rounded-lg shadow-lg p-6 w-full max-w-md">
        <h2 class="text-xl font-bold mb-4 text-gray-800 dark:text-gray-100">
          Detalles del Turno
        </h2>

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

        <div v-else>
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
                class="text-xs text-blue-500 font-semibold"
              >
                 👥 {{ turnoSeleccionado.grupoNombre || 'Turno grupal' }}
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
              class="text-xs text-blue-500 mt-1 font-semibold"
            >
              👥 Grupo: {{ turnoSeleccionado.grupoNombre || 'Grupal' }}
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
              
              <span v-else class="text-xs text-gray-400 self-center mr-auto">
                (Gestionado por grupo)
              </span>

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

/* -------------------------------------------------------------------------- */
/* VARIABLES PRINCIPALES                                                     */
/* -------------------------------------------------------------------------- */
const eventos = ref([])
const leyendaGrupos = ref([])
const turnoSeleccionado = ref(null)
const editando = ref(false)
const fechaEdit = ref('')
const horaEdit = ref('')
const duracionTurno = ref(30)
const nombreProfesionalLogueado = ref('') // Para saber quién soy

/* -------------------------------------------------------------------------- */
/* CONFIGURACIÓN FULLCALENDAR                                                */
/* -------------------------------------------------------------------------- */
const calendarOptions = ref({
  plugins: [dayGridPlugin, timeGridPlugin, interactionPlugin],
  initialView: 'timeGridWeek',
  locale: 'es',
  slotMinTime: '08:00:00',
  slotMaxTime: '21:00:00',
  allDaySlot: false,
  slotEventOverlap: true, 
  eventOverlap: true,     
  eventOrder: 'order',    // Ordenar visualmente (mis turnos arriba)
  
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
      editable: e.extendedProps.editable, // Respetamos lo que calculamos nosotros
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
    const esGrupal = info.event.extendedProps.tipo === 'grupal'
    
    // Si es grupal, mostramos el nombre del colega en negrita
    const tituloTooltip = esGrupal 
        ? `<strong>${profesional}</strong><br>Paciente: ${paciente}`
        : `${paciente}`

    tippy(info.el, {
      content: `${tituloTooltip}<br><em>${desc}</em>`,
      allowHTML: true,
      placement: "top",
      theme: "light-border",
    })
  }
})

/* -------------------------------------------------------------------------- */
/* HELPERS VISUALES                                                          */
/* -------------------------------------------------------------------------- */

// Genera un color consistente a partir de un texto (Hash)
function stringToColor(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  const c = (hash & 0x00ffffff).toString(16).toUpperCase();
  return '#' + "00000".substring(0, 6 - c.length) + c;
}

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

function hexToRgba(hex, alpha) {
  if (!hex) return 'rgba(59, 130, 246, 1)';
  let c;
  if(/^#([A-Fa-f0-9]{3}){1,2}$/.test(hex)){
      c= hex.substring(1).split('');
      if(c.length== 3) c= [c[0], c[0], c[1], c[1], c[2], c[2]];
      c= '0x'+c.join('');
      return 'rgba('+[(c>>16)&255, (c>>8)&255, c&255].join(',')+','+alpha+')';
  }
  return hex;
}

/* -------------------------------------------------------------------------- */
/* CARGA DE DATOS                                                            */
/* -------------------------------------------------------------------------- */
async function cargarDatosUsuario() {
  try {
    // CORRECCIÓN: La ruta correcta es /api/usuarios/me
    const resp = await fetch("/api/usuarios/me", { credentials: "include" })
    
    if (!resp.ok) return
    const data = await resp.json()
    duracionTurno.value = data.duracion_turno || 30
    
    // Aquí usamos el nombre para identificar si los turnos son míos
    nombreProfesionalLogueado.value = data.nombre || data.email || "YO"; 
  } catch (e) {
    console.error("Error cargando usuario", e)
  }
}

async function cargarTurnosProfesional() {
  try {
    const resp = await fetch("/api/turnos/profesional/completo", {
      credentials: "include"
    })
    const data = await resp.json()

    const mapaTurnos = new Map()
    const gruposDetectados = {}

    // Obtenemos el nombre normalizado del usuario actual para comparar
    const miNombre = nombreProfesionalLogueado.value.toLowerCase().trim();

    data.forEach(t => {
      // 1. Detección Inteligente de Propiedad
      const profNombre = (t.profesional || "").toLowerCase().trim();
      
      // Es propio si el nombre coincide PARCIALMENTE o EXACTAMENTE
      // (Ajusta esta lógica según cuán exactos sean tus datos)
      const esPropio = miNombre && profNombre.includes(miNombre);
      
      const esGrupal = !esPropio; 

      // 2. Asignación de Color
      let colorFinal;
      if (esPropio) {
          colorFinal = '#1976D2'; // Azul oficial para MIS turnos
      } else {
          // Generamos un color único para ese colega si no viene del back
          colorFinal = stringToColor(t.profesional || "Desconocido");
      }

      if (!mapaTurnos.has(t.id)) {
        mapaTurnos.set(t.id, {
          id: t.id,
          // Si es grupal mostramos el nombre del profesional, si es mío, el del paciente
          title: esGrupal ? `Dr/a. ${t.profesional}` : t.paciente,
          start: t.start,
          end: t.end,

          // Estilos
          backgroundColor: esGrupal ? hexToRgba(colorFinal, 0.7) : colorFinal,
          borderColor: colorFinal,
          textColor: '#ffffff',
          classNames: esGrupal ? ['evento-grupal'] : ['evento-propio'],

          extendedProps: {
            order: esGrupal ? 0 : 10, // Mis turnos (10) siempre tapan a los grupales (0)
            tipo: esGrupal ? "grupal" : "individual",
            // Forzamos false si es grupal, aunque el back diga true
            editable: esPropio ? (t.editable === 1) : false, 
            turnoId: t.id,
            paciente: t.paciente,
            dni: t.dni,
            profesional: t.profesional,
            description: t.description,
            grupoNombre: t.grupoNombre || t.profesional // Usamos el nombre del colega como grupo
          }
        })
      }

      // Llenamos la leyenda dinámicamente
      if (esGrupal) {
        gruposDetectados[t.profesional] = colorFinal;
      }
    })

    eventos.value = Array.from(mapaTurnos.values())
    
    // Generamos la leyenda para la UI
    leyendaGrupos.value = Object.keys(gruposDetectados).map(nombre => ({
      nombre,
      colorOriginal: gruposDetectados[nombre],
      colorTransparente: hexToRgba(gruposDetectados[nombre], 0.7)
    }))
    
    calendarOptions.value.events = eventos.value

  } catch (error) {
    console.error("Error cargando turnos:", error);
  }
}

/* -------------------------------------------------------------------------- */
/* RESTO DE FUNCIONES (Igual que antes)                                      */
/* -------------------------------------------------------------------------- */
// ... editarTurno, guardarEdicion, eliminarTurno, cerrarModal ...
// Copia aquí las funciones que ya tenías para editar/eliminar
function cerrarModal() {
  turnoSeleccionado.value = null
  editando.value = false
}
// etc...

let intervalo = null

onMounted(async () => {
  await cargarDatosUsuario() // Primero cargamos quién soy
  await cargarTurnosProfesional() // Luego cargamos los turnos y comparamos

  intervalo = setInterval(cargarTurnosProfesional, 60000)
})

onUnmounted(() => {
  clearInterval(intervalo)
})
</script>

<style>
/* Clase para eventos grupales (Borde punteado, atrás visualmente) */
.evento-grupal {
  border-style: dashed !important;
  border-width: 2px !important;
  z-index: 1 !important; 
  opacity: 0.95; /* Leve ajuste adicional si se requiere */
}

/* Clase para eventos propios (Borde sólido, adelante, sombra) */
.evento-propio {
  border-style: solid !important;
  border-width: 1px !important;
  z-index: 5 !important; 
  box-shadow: 0 2px 5px rgba(0,0,0,0.25);
}

/* Ajuste de texto del evento */
.fc-event-title {
  font-weight: 600;
  font-size: 0.85rem;
}
</style>