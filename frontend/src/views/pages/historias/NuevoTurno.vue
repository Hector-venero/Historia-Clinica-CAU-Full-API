<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { useUserStore } from '@/stores/user';
import api from '@/api/axios';
import ausenciasService from '@/service/ausenciasService';
import servicioService from '@/service/servicioService';
import DatePicker from 'primevue/datepicker';
import Button from 'primevue/button';

const userStore = useUserStore();
const searchPaciente = ref('');
const pacientes = ref([]);
const pacienteId = ref('');
const pacienteSeleccionado = ref('');
const usuarioId = ref('');
const fecha = ref(null);
const motivo = ref('');
// Videoconsulta. El enlace lo pone el profesional con la herramienta que ya usa
// (Meet, Zoom, la que sea): el sistema no genera ni aloja la videollamada.
const modalidad = ref('presencial');
const enlaceVideo = ref('');
const mensaje = ref('');
const error = ref('');
const guardando = ref(false);
// Aviso cuando el backend movió el turno al siguiente slot disponible.
const avisoAjuste = ref('');
// Horarios que el backend ofrece cuando el pedido está ocupado.
const horariosSugeridos = ref([]);
const profesionales = ref([]);
// Bloqueos de agenda del profesional elegido, para no ofrecer días que no atiende.
const ausenciasProfesional = ref([]);
// Prestaciones que puede dar el profesional elegido. Vacío en un consultorio
// que no las use, y ahí el selector no se muestra: no tiene sentido pedir que
// elija de una lista que no existe.
const servicios = ref([]);
const servicioId = ref(null);

// 🔹 Campos nuevos para tanda
const esTanda = ref(false);
const cantidad = ref(10);
const diasSemana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];
const diasSeleccionados = ref([]);

const servicioElegido = computed(() => servicios.value.find((s) => s.id === servicioId.value) || null);

// La duración sale del servicio cuando hay uno. Sin servicio, de la
// configuración —el mismo orden que aplica el backend, para que lo que muestra
// la pantalla y lo que se guarda no puedan discrepar.
const duracion = computed(() => servicioElegido.value?.duracion_minutos || userStore.duracion_turno || 30);

onMounted(async () => {
    try {
        // La instancia `api` y no fetch crudo: así pasa por el interceptor de
        // 401 y por la resolución de baseURL, como el resto de la aplicación.
        const { data } = await api.get('/profesionales');
        profesionales.value = data || [];
    } catch (e) {
        console.error('Error cargando profesionales', e);
        error.value = 'No se pudieron cargar los profesionales';
    }
});

// ---------------------------------------------- bloqueos de agenda

watch(usuarioId, async (id) => {
    await cargarAusenciasProfesional(id);
    await cargarServicios(id);

    // Si ya había una fecha elegida y el profesional nuevo no atiende ese día,
    // se limpia: dejarla puesta terminaría en un rechazo del backend.
    if (fecha.value && estaBloqueada(fecha.value)) {
        fecha.value = null;
        error.value = 'Ese día el profesional tiene la agenda bloqueada.';
    }
});

async function cargarServicios(profesionalId) {
    servicioId.value = null;
    if (!profesionalId) {
        servicios.value = [];
        return;
    }
    try {
        const { data } = await servicioService.listar({ usuarioId: profesionalId, soloActivos: true });
        servicios.value = data || [];
    } catch (e) {
        console.error('Error cargando servicios', e);
        // Sin la lista se agenda como siempre, con la duración configurada.
        servicios.value = [];
    }
}

async function cargarAusenciasProfesional(profesionalId) {
    if (!profesionalId) {
        ausenciasProfesional.value = [];
        return;
    }
    try {
        const { data } = await ausenciasService.listar();
        ausenciasProfesional.value = (data || []).filter((a) => Number(a.usuario_id) === Number(profesionalId));
    } catch (e) {
        console.error('Error cargando ausencias', e);
        ausenciasProfesional.value = [];
    }
}

function aFecha(valor) {
    const d = new Date(valor);
    return Number.isNaN(d.getTime()) ? null : d;
}

const ausenciasNormalizadas = computed(() =>
    (ausenciasProfesional.value || [])
        .map((a) => {
            const inicio = aFecha(a.fecha_inicio);
            const fin = aFecha(a.fecha_fin);
            if (!inicio || !fin) return null;

            // Día completo = arranca a las 00:00 y termina a las 23:59 del mismo
            // día. Depende de que el backend mande la fecha en hora argentina:
            // /api/ausencias las etiquetaba como GMT y el corrimiento de tres
            // horas hacía que ningún bloqueo se reconociera como día completo.
            const esDiaCompleto = inicio.getHours() === 0 && inicio.getMinutes() === 0 && fin.getHours() === 23 && fin.getMinutes() >= 59 && inicio.toDateString() === fin.toDateString();

            return { ...a, inicio, fin, esDiaCompleto };
        })
        .filter(Boolean)
);

// Los que ocupan el día entero se deshabilitan en el calendario; los parciales
// no, porque el resto del día sigue siendo agendable.
const diasBloqueados = computed(() => {
    const vistos = new Map();
    for (const a of ausenciasNormalizadas.value) {
        if (!a.esDiaCompleto) continue;
        const dia = new Date(a.inicio);
        dia.setHours(0, 0, 0, 0);
        vistos.set(dia.toDateString(), dia);
    }
    return [...vistos.values()];
});

const bloqueosParciales = computed(() => ausenciasNormalizadas.value.filter((a) => !a.esDiaCompleto));

function estaBloqueada(valor) {
    const dia = new Date(valor);
    dia.setHours(0, 0, 0, 0);
    return diasBloqueados.value.some((d) => d.getTime() === dia.getTime());
}

function haySolapamiento(inicio, fin) {
    return ausenciasNormalizadas.value.some((a) => inicio < a.fin && fin > a.inicio);
}

// ---------------------------------------------- pacientes

async function buscarPacientes() {
    if (!searchPaciente.value || searchPaciente.value.length < 2) {
        pacientes.value = [];
        return;
    }
    try {
        const { data } = await api.get('/pacientes/buscar', { params: { q: searchPaciente.value } });
        pacientes.value = data?.pacientes || [];
    } catch (e) {
        console.error('Error buscando pacientes', e);
    }
}

function seleccionarPaciente(p) {
    pacienteId.value = p.id;
    pacienteSeleccionado.value = `${p.apellido} ${p.nombre} (DNI: ${p.dni})`;
    searchPaciente.value = pacienteSeleccionado.value;
    pacientes.value = []; // cerrar lista
}

function limpiarPaciente() {
    pacienteId.value = '';
    pacienteSeleccionado.value = '';
    searchPaciente.value = '';
    pacientes.value = [];
}

// ---------------------------------------------- fechas

function formatearFechaBackend(dateObj) {
    if (!dateObj) return null;

    const d = new Date(dateObj);
    const pad = (n) => String(n).padStart(2, '0');

    // Ej: 2025-12-05T16:20
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function calcularFin(fechaInicio, minutos) {
    if (!fechaInicio) return null;
    const d = new Date(fechaInicio);
    d.setMinutes(d.getMinutes() + minutos);
    return formatearFechaBackend(d);
}

/**
 * Arma el aviso cuando el backend movió el turno de horario.
 * Devuelve '' si no hubo ajuste.
 */
function describirAjuste(ajuste) {
    if (!ajuste?.aplicado) return '';

    const hora = (iso) => new Date(iso).toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' });

    return `El horario se ajustó de ${hora(ajuste.inicio_original)} a ${hora(ajuste.inicio_ajustado)} para que coincida con la agenda del profesional. Confirmá este horario con el paciente.`;
}

function soloHora(iso) {
    return new Date(iso).toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' });
}

const resumenFecha = computed(() => {
    if (!fecha.value) return '';
    const fin = new Date(fecha.value);
    fin.setMinutes(fin.getMinutes() + duracion.value);

    const dia = fecha.value.toLocaleDateString('es-AR', { weekday: 'long', day: 'numeric', month: 'long' });
    const hora = (d) => d.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' });

    return `${dia}, de ${hora(fecha.value)} a ${hora(fin)}`;
});

// ---------------------------------------------- guardar

async function crearTurno() {
    mensaje.value = '';
    error.value = '';
    avisoAjuste.value = '';
    horariosSugeridos.value = [];

    if (!pacienteId.value) {
        error.value = 'Debe seleccionar un paciente';
        return;
    }
    if (!usuarioId.value) {
        error.value = 'Debe seleccionar un profesional';
        return;
    }
    if (!fecha.value) {
        error.value = 'Debe seleccionar fecha y hora';
        return;
    }

    // Se avisa acá en vez de esperar el rechazo del backend: el mensaje puede
    // decir por qué está bloqueado, y no se pierde lo cargado en el formulario.
    const fin = new Date(fecha.value);
    fin.setMinutes(fin.getMinutes() + duracion.value);
    if (haySolapamiento(fecha.value, fin)) {
        error.value = 'Ese horario cae dentro de un bloqueo de agenda del profesional.';
        return;
    }

    // Rutas relativas a la instancia `api`, que ya resuelve el prefijo /api.
    const endpoint = esTanda.value ? '/turnos/tanda' : '/turnos';
    const fechaInicioStr = formatearFechaBackend(fecha.value);

    const payload = {
        paciente_id: pacienteId.value,
        usuario_id: usuarioId.value,
        fecha_inicio: fechaInicioStr,
        fecha_fin: calcularFin(fecha.value, duracion.value),
        motivo: motivo.value,
        servicio_id: servicioId.value,
        modalidad: modalidad.value,
        // Se manda solo en virtual: el backend descarta el enlace de un turno
        // presencial, y mandarlo igual seria pedirle que limpie lo nuestro.
        enlace_video: modalidad.value === 'virtual' ? enlaceVideo.value.trim() : null
    };

    if (esTanda.value) {
        payload.cantidad = cantidad.value;
        payload.dias_semana = diasSeleccionados.value;
        payload.fecha = fechaInicioStr;
    }

    guardando.value = true;
    try {
        const { data } = await api.post(endpoint, payload);

        mensaje.value = data.message || 'Turno creado correctamente';

        // El backend alinea el turno al siguiente slot libre. Si lo movió, hay
        // que decirlo: sin este aviso se le informa al paciente un horario y el
        // sistema guarda otro.
        avisoAjuste.value = describirAjuste(data.ajuste_horario);

        limpiarPaciente();
        usuarioId.value = '';
        fecha.value = null;
        motivo.value = '';
        servicioId.value = null;
        modalidad.value = 'presencial';
        enlaceVideo.value = '';
        esTanda.value = false;
        diasSeleccionados.value = [];
    } catch (e) {
        const datos = e.response?.data || {};
        error.value = datos.error || e.message || 'Error al crear turno';
        // El backend sugiere horarios libres del mismo día cuando el pedido
        // está ocupado; así se le puede ofrecer una alternativa al paciente.
        horariosSugeridos.value = datos.horarios_disponibles || [];
    } finally {
        guardando.value = false;
    }
}

/** Toma un horario sugerido y lo carga en el formulario. */
function usarHorario(iso) {
    fecha.value = new Date(iso);
    error.value = '';
    horariosSugeridos.value = [];
}
</script>

<template>
    <!-- Todos los colores llevan su variante dark:. La pantalla tenia una sola,
         asi que en tema oscuro quedaba una tarjeta blanca con campos claros. -->
    <div class="max-w-3xl mx-auto p-4 md:p-6 space-y-6">
        <header>
            <h1 class="text-2xl md:text-3xl font-bold text-surface-900 dark:text-surface-0 m-0">Nuevo turno</h1>
            <p class="text-sm text-surface-500 dark:text-surface-400 mt-1 mb-0">Turnos de {{ duracion }} minutos<span v-if="servicioElegido">, según el servicio elegido</span><span v-else>, según la configuración del profesional</span>.</p>
        </header>

        <form class="space-y-6" @submit.prevent="crearTurno">
            <!-- Paciente -->
            <section class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-2xl p-5">
                <h2 class="seccion">
                    <span class="paso">1</span>
                    Paciente
                </h2>

                <div class="relative">
                    <input v-model="searchPaciente" type="text" placeholder="Buscar por DNI, nombre o apellido" class="campo" autocomplete="off" @input="buscarPacientes" />

                    <ul
                        v-if="pacientes.length > 0"
                        class="absolute z-20 left-0 right-0 mt-2 rounded-xl border border-surface-200 dark:border-surface-700 bg-surface-0 dark:bg-surface-900 shadow-lg divide-y divide-surface-100 dark:divide-surface-800 max-h-56 overflow-y-auto"
                    >
                        <li v-for="p in pacientes" :key="p.id" class="px-3 py-2.5 cursor-pointer hover:bg-surface-100 dark:hover:bg-surface-800 text-surface-800 dark:text-surface-100" @click="seleccionarPaciente(p)">
                            <span class="font-medium">{{ p.apellido }} {{ p.nombre }}</span>
                            <span class="text-sm text-surface-500 dark:text-surface-400"> · DNI {{ p.dni }}</span>
                        </li>
                    </ul>
                </div>

                <div v-if="pacienteId" class="mt-3 flex items-center justify-between gap-3 rounded-xl bg-green-50 dark:bg-green-950/40 border border-green-200 dark:border-green-800 px-3 py-2">
                    <span class="text-sm text-green-800 dark:text-green-200"> <i class="pi pi-check-circle mr-1"></i>{{ pacienteSeleccionado }} </span>
                    <button type="button" class="text-sm text-surface-500 dark:text-surface-400 hover:underline shrink-0" @click="limpiarPaciente">Cambiar</button>
                </div>
            </section>

            <!-- Profesional y fecha -->
            <section class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-2xl p-5">
                <h2 class="seccion">
                    <span class="paso">2</span>
                    Profesional y horario
                </h2>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label class="etiqueta">Profesional</label>
                        <select v-model="usuarioId" class="campo" required>
                            <option value="" disabled>Seleccione un profesional</option>
                            <option v-for="p in profesionales" :key="p.id" :value="p.id">{{ p.nombre }} ({{ p.especialidad || 'Sin especialidad' }})</option>
                        </select>
                    </div>

                    <div>
                        <label class="etiqueta">Fecha y hora</label>
                        <DatePicker v-model="fecha" showTime hourFormat="24" :stepMinute="5" :disabledDates="diasBloqueados" :minDate="new Date()" iconDisplay="input" showIcon placeholder="Seleccionar fecha y hora" fluid class="w-full" required />
                    </div>
                </div>

                <!-- Que se ve en el calendario no alcanza: un bloqueo de medio dia
                     no deshabilita la fecha, asi que conviene enumerarlos. -->
                <div v-if="usuarioId && (diasBloqueados.length || bloqueosParciales.length)" class="mt-4 rounded-xl bg-surface-50 dark:bg-surface-800 border border-surface-200 dark:border-surface-700 px-3 py-2.5">
                    <p class="text-xs font-semibold text-surface-600 dark:text-surface-300 m-0 mb-1"><i class="pi pi-ban mr-1"></i> Agenda bloqueada</p>
                    <p v-if="diasBloqueados.length" class="text-xs text-surface-500 dark:text-surface-400 m-0">{{ diasBloqueados.length }} día(s) completo(s), ya deshabilitados en el calendario.</p>
                    <ul v-if="bloqueosParciales.length" class="text-xs text-surface-500 dark:text-surface-400 mt-1 mb-0 list-disc list-inside">
                        <li v-for="b in bloqueosParciales" :key="b.id">{{ b.inicio.toLocaleDateString('es-AR') }} de {{ soloHora(b.fecha_inicio) }} a {{ soloHora(b.fecha_fin) }}{{ b.motivo ? ` — ${b.motivo}` : '' }}</li>
                    </ul>
                </div>

                <p v-if="resumenFecha" class="mt-4 text-sm text-surface-600 dark:text-surface-300 m-0"><i class="pi pi-calendar mr-1"></i> {{ resumenFecha }}</p>
            </section>

            <!-- Motivo y tanda -->
            <section class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-2xl p-5">
                <h2 class="seccion">
                    <span class="paso">3</span>
                    Detalle
                </h2>

                <!-- Solo si el consultorio cargó servicios: pedir que elija de
                     una lista vacía sería pedir algo que no se puede hacer. -->
                <template v-if="servicios.length">
                    <label class="etiqueta">Servicio</label>
                    <select v-model="servicioId" class="campo">
                        <option :value="null">Sin servicio — {{ userStore.duracion_turno || 30 }} min</option>
                        <option v-for="s in servicios" :key="s.id" :value="s.id">{{ s.nombre }} — {{ s.duracion_minutos }} min</option>
                    </select>
                    <p class="text-sm text-surface-500 dark:text-surface-400 mt-1 mb-4">El servicio define cuánto dura el turno.</p>
                </template>

                <label class="etiqueta">Motivo</label>
                <textarea v-model="motivo" rows="3" placeholder="Motivo del turno (opcional)" class="campo"></textarea>

                <label class="etiqueta mt-5">Modalidad</label>
                <div class="grid grid-cols-2 gap-3">
                    <button
                        v-for="m in [
                            { valor: 'presencial', titulo: 'Presencial', detalle: 'En el consultorio', icono: 'pi-map-marker' },
                            { valor: 'virtual', titulo: 'Videoconsulta', detalle: 'Por videollamada', icono: 'pi-video' }
                        ]"
                        :key="m.valor"
                        type="button"
                        class="text-left rounded-xl border p-3 transition"
                        :class="modalidad === m.valor ? 'border-primary-500 bg-primary-50 dark:bg-primary-950/40' : 'border-surface-200 dark:border-surface-700 hover:bg-surface-50 dark:hover:bg-surface-800'"
                        @click="modalidad = m.valor"
                    >
                        <i class="pi mb-1 block" :class="[m.icono, modalidad === m.valor ? 'text-primary-600 dark:text-primary-400' : 'text-surface-400']"></i>
                        <span class="block text-sm font-semibold text-surface-800 dark:text-surface-100">{{ m.titulo }}</span>
                        <span class="block text-xs text-surface-500 dark:text-surface-400">{{ m.detalle }}</span>
                    </button>
                </div>

                <div v-if="modalidad === 'virtual'" class="mt-3">
                    <label class="etiqueta">Enlace de la videollamada</label>
                    <input v-model="enlaceVideo" type="url" placeholder="https://meet.google.com/abc-defg-hij" class="campo" autocomplete="off" />
                    <p class="text-xs text-surface-500 dark:text-surface-400 mt-1 mb-0">Pegá el enlace de tu sala de Meet, Zoom o la herramienta que uses. Se lo mandamos al paciente por correo y lo ve en su portal.</p>
                </div>

                <label class="mt-5 flex items-start gap-3 cursor-pointer rounded-xl border border-surface-200 dark:border-surface-700 p-3 hover:bg-surface-50 dark:hover:bg-surface-800 transition">
                    <input v-model="esTanda" type="checkbox" class="mt-0.5 w-5 h-5 accent-primary-600 shrink-0" />
                    <span>
                        <span class="block text-sm font-semibold text-surface-800 dark:text-surface-100">Crear una tanda de turnos</span>
                        <span class="block text-xs text-surface-500 dark:text-surface-400">Repite el turno varias semanas. Para kinesiología, rehabilitación y tratamientos con sesiones.</span>
                    </span>
                </label>

                <transition name="fade">
                    <div v-if="esTanda" class="mt-4 space-y-4 rounded-xl bg-surface-50 dark:bg-surface-800 border border-surface-200 dark:border-surface-700 p-4">
                        <div>
                            <label class="etiqueta">Cantidad de turnos</label>
                            <input v-model.number="cantidad" type="number" min="1" placeholder="Ejemplo: 10" class="campo md:max-w-[200px]" />
                        </div>

                        <div>
                            <label class="etiqueta">Días de la semana</label>
                            <!-- Botones y no casillas: se eligen de un vistazo y
                                 ocupan menos en pantallas chicas. -->
                            <div class="flex flex-wrap gap-2">
                                <label
                                    v-for="dia in diasSemana"
                                    :key="dia"
                                    :class="[
                                        'cursor-pointer select-none rounded-lg border px-3 py-1.5 text-sm transition',
                                        diasSeleccionados.includes(dia)
                                            ? 'border-primary-500 bg-primary-500 text-white font-semibold'
                                            : 'border-surface-300 dark:border-surface-600 text-surface-700 dark:text-surface-300 hover:bg-surface-100 dark:hover:bg-surface-700'
                                    ]"
                                >
                                    <input v-model="diasSeleccionados" type="checkbox" :value="dia" class="sr-only" />
                                    {{ dia }}
                                </label>
                            </div>
                            <p v-if="!diasSeleccionados.length" class="text-xs text-surface-500 dark:text-surface-400 mt-2 mb-0">Elegí al menos un día.</p>
                        </div>
                    </div>
                </transition>
            </section>

            <div class="flex justify-end">
                <Button type="submit" :loading="guardando" :label="esTanda ? `Crear ${cantidad} turnos` : 'Crear turno'" icon="pi pi-check" class="px-6 py-3 font-semibold" />
            </div>
        </form>

        <!-- Resultado -->
        <div v-if="mensaje" class="rounded-xl bg-green-50 dark:bg-green-950/40 border border-green-200 dark:border-green-800 px-4 py-3 text-sm text-green-800 dark:text-green-200"><i class="pi pi-check-circle mr-1"></i> {{ mensaje }}</div>

        <!-- El backend puede correr el turno al siguiente slot libre. Se avisa
             para que no se le confirme al paciente un horario distinto. No se usa
             un toast: esto hay que leerlo, no verlo pasar. -->
        <div v-if="avisoAjuste" class="rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-800 px-4 py-3 text-sm text-amber-900 dark:text-amber-200"><i class="pi pi-clock mr-1"></i> {{ avisoAjuste }}</div>

        <div v-if="error" class="rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 px-4 py-3 text-sm text-red-800 dark:text-red-200"><i class="pi pi-exclamation-circle mr-1"></i> {{ error }}</div>

        <!-- Alternativas del mismo día, para no tener que probar a ciegas -->
        <div v-if="horariosSugeridos.length" class="rounded-xl border border-surface-200 dark:border-surface-700 bg-surface-0 dark:bg-surface-900 px-4 py-3">
            <p class="text-sm text-surface-600 dark:text-surface-300 m-0 mb-2">Horarios libres ese día:</p>
            <div class="flex flex-wrap gap-2">
                <button
                    v-for="h in horariosSugeridos"
                    :key="h"
                    type="button"
                    class="px-3 py-1.5 rounded-lg border border-primary-300 dark:border-primary-700 bg-primary-50 dark:bg-primary-950 text-primary-800 dark:text-primary-200 text-sm hover:bg-primary-100 dark:hover:bg-primary-900 transition"
                    @click="usarHorario(h)"
                >
                    {{ soloHora(h) }}
                </button>
            </div>
        </div>
    </div>
</template>

<style scoped>
/* La cadena de clases se repetia en cada input, lo que hacia imposible ver que
   a ninguno le faltaba la variante oscura. */
.campo {
    @apply w-full px-3 py-2.5 rounded-xl outline-none transition
           bg-surface-50 dark:bg-surface-800
           border border-surface-300 dark:border-surface-600
           text-surface-900 dark:text-surface-0
           placeholder:text-surface-400 dark:placeholder:text-surface-500
           focus:ring-2 focus:ring-primary-500 focus:border-primary-500;
}

.etiqueta {
    @apply block mb-1.5 text-sm font-medium text-surface-700 dark:text-surface-300;
}

.seccion {
    @apply flex items-center gap-2 text-base font-semibold text-surface-900 dark:text-surface-0 m-0 mb-4;
}

/* El numero de paso ordena la lectura sin necesidad de un componente de wizard. */
.paso {
    @apply inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold
           bg-primary-100 dark:bg-primary-900 text-primary-700 dark:text-primary-200;
}

.fade-enter-active,
.fade-leave-active {
    transition: all 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
    opacity: 0;
    transform: translateY(-5px);
}
</style>
