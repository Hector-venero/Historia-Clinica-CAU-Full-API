<template>
    <div class="flex justify-center items-start p-8">
        <div class="bg-white shadow-xl rounded-2xl p-8 w-full max-w-2xl">
            <h1 class="text-3xl font-bold text-center mb-8 text-gray-800 dark:text-white">Nuevo Turno</h1>

            <form @submit.prevent="crearTurno" class="space-y-6">
                <!-- Paciente -->
                <div class="relative">
                    <label class="block mb-2 font-semibold text-gray-700">Paciente</label>
                    <input v-model="searchPaciente" @input="buscarPacientes" type="text" placeholder="Buscar por DNI o nombre" class="w-full p-3 border rounded-xl shadow-sm focus:ring-2 focus:ring-blue-500" autocomplete="off" />
                    <!-- Lista resultados -->
                    <ul v-if="pacientes.length > 0" class="absolute z-20 left-0 right-0 border rounded-lg mt-2 bg-white shadow-md divide-y max-h-48 overflow-y-auto">
                        <li v-for="p in pacientes" :key="p.id" @click="seleccionarPaciente(p)" class="px-3 py-2 hover:bg-blue-100 cursor-pointer">{{ p.apellido }} {{ p.nombre }} (DNI: {{ p.dni }})</li>
                    </ul>
                    <p v-if="pacienteId" class="mt-2 text-sm text-green-600 font-medium">✅ Seleccionado: {{ pacienteSeleccionado }}</p>
                </div>

                <!-- Profesional -->
                <div>
                    <label class="block mb-2 font-semibold text-gray-700">Profesional</label>
                    <select v-model="usuarioId" class="w-full p-3 border rounded-xl shadow-sm focus:ring-2 focus:ring-blue-500" required>
                        <option value="" disabled>Seleccione un profesional</option>
                        <option v-for="p in profesionales" :key="p.id" :value="p.id">{{ p.nombre }} ({{ p.especialidad || 'Sin especialidad' }})</option>
                    </select>
                </div>

                <!-- Fecha -->
                <div>
                    <label class="block mb-2 font-semibold text-gray-700">Fecha y hora</label>
                    <DatePicker v-model="fecha" showTime hourFormat="24" :stepMinute="5" iconDisplay="input" placeholder="Seleccionar fecha y hora" fluid class="w-full" inputClass="w-full p-3 border rounded-xl shadow-sm" required />
                </div>

                <!-- Motivo -->
                <div>
                    <label class="block mb-2 font-semibold text-gray-700">Motivo</label>
                    <textarea v-model="motivo" rows="3" placeholder="Motivo del turno" class="w-full p-3 border rounded-xl shadow-sm focus:ring-2 focus:ring-blue-500"></textarea>
                </div>

                <!-- 🔹 Tanda de turnos -->
                <div class="mt-6 border-t pt-4">
                    <label class="flex items-center gap-2 text-gray-700 font-semibold cursor-pointer">
                        <input type="checkbox" v-model="esTanda" class="accent-blue-600 w-5 h-5" />
                        Crear tanda de turnos (kinesiología, rehabilitación, etc.)
                    </label>

                    <transition name="fade">
                        <div v-if="esTanda" class="mt-4 space-y-4 bg-blue-50 p-4 rounded-xl border border-blue-100">
                            <div>
                                <label class="block mb-2 font-semibold text-gray-700">Cantidad de turnos</label>
                                <input v-model.number="cantidad" type="number" min="1" class="w-full p-3 border rounded-xl shadow-sm focus:ring-2 focus:ring-blue-500" placeholder="Ejemplo: 10" />
                            </div>

                            <div>
                                <label class="block mb-2 font-semibold text-gray-700">Días de la semana</label>
                                <div class="grid grid-cols-3 gap-2">
                                    <label v-for="(dia, idx) in diasSemana" :key="idx" class="flex items-center space-x-2">
                                        <input type="checkbox" v-model="diasSeleccionados" :value="dia" class="accent-blue-600 w-5 h-5" />
                                        <span>{{ dia }}</span>
                                    </label>
                                </div>
                                <p class="text-gray-500 text-sm mt-1">Seleccioná los días en que se repetirá el turno</p>
                            </div>
                        </div>
                    </transition>
                </div>

                <!-- Botón -->
                <div class="flex justify-center">
                    <Button type="submit" label="Guardar Turno" class="w-full md:w-auto px-6 py-3 font-semibold shadow-lg" />
                </div>
            </form>

            <!-- Mensajes -->
            <p v-if="mensaje" class="mt-6 text-green-600 font-semibold text-center">
                {{ mensaje }}
            </p>
            <!-- El backend puede correr el turno al siguiente slot libre.
                 Se avisa para que no se le confirme al paciente un horario distinto. -->
            <div v-if="avisoAjuste" class="mt-4 p-3 rounded-lg bg-amber-50 border border-amber-300 text-amber-800 text-sm text-center"><i class="pi pi-clock mr-1"></i> {{ avisoAjuste }}</div>
            <p v-if="error" class="mt-6 text-red-600 font-semibold text-center">
                {{ error }}
            </p>
            <!-- Alternativas del mismo día, para no tener que probar a ciegas -->
            <div v-if="horariosSugeridos.length" class="mt-3 text-center">
                <p class="text-sm text-gray-600 mb-2">Horarios disponibles ese día:</p>
                <div class="flex flex-wrap gap-2 justify-center">
                    <button v-for="h in horariosSugeridos" :key="h" type="button" class="px-3 py-1 rounded-lg border border-blue-300 bg-blue-50 text-blue-700 text-sm hover:bg-blue-100 transition" @click="usarHorario(h)">
                        {{ soloHora(h) }}
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useUserStore } from '@/stores/user';
import api from '@/api/axios';
import DatePicker from 'primevue/datepicker';
import Button from 'primevue/button';

const userStore = useUserStore();
const searchPaciente = ref('');
const pacientes = ref([]);
const pacienteId = ref('');
const pacienteSeleccionado = ref('');
const usuarioId = ref('');
const fecha = ref(null); // 👈 ahora es Date
const motivo = ref('');
const mensaje = ref('');
const error = ref('');
// Aviso cuando el backend movió el turno al siguiente slot disponible.
const avisoAjuste = ref('');
// Horarios que el backend ofrece cuando el pedido está ocupado.
const horariosSugeridos = ref([]);
const profesionales = ref([]);

// 🔹 Campos nuevos para tanda
const esTanda = ref(false);
const cantidad = ref(10);
const diasSemana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];
const diasSeleccionados = ref([]);

onMounted(async () => {
    try {
        const resp = await fetch('/api/profesionales', { credentials: 'include' });
        if (!resp.ok) throw new Error('Error al cargar profesionales');
        profesionales.value = await resp.json();
    } catch (e) {
        console.error('Error cargando profesionales', e);
        error.value = 'No se pudieron cargar los profesionales';
    }
});

async function buscarPacientes() {
    if (!searchPaciente.value || searchPaciente.value.length < 2) {
        pacientes.value = [];
        return;
    }
    try {
        const resp = await fetch(`/api/pacientes/buscar?q=${encodeURIComponent(searchPaciente.value)}`, {
            credentials: 'include'
        });
        if (!resp.ok) throw new Error('Error de búsqueda');
        const data = await resp.json();
        pacientes.value = data.pacientes || [];
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

function formatearFechaBackend(dateObj) {
    if (!dateObj) return null;

    const d = new Date(dateObj);
    const pad = (n) => String(n).padStart(2, '0');

    const year = d.getFullYear();
    const month = pad(d.getMonth() + 1);
    const day = pad(d.getDate());
    const hour = pad(d.getHours());
    const minute = pad(d.getMinutes());

    // Ej: 2025-12-05T16:20
    return `${year}-${month}-${day}T${hour}:${minute}`;
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

async function crearTurno() {
    mensaje.value = '';
    error.value = '';
    avisoAjuste.value = '';
    horariosSugeridos.value = [];

    if (!pacienteId.value) {
        error.value = 'Debe seleccionar un paciente';
        return;
    }

    if (!fecha.value) {
        error.value = 'Debe seleccionar fecha y hora';
        return;
    }

    // Rutas relativas a la instancia `api`, que ya resuelve el prefijo /api.
    const endpoint = esTanda.value ? '/turnos/tanda' : '/turnos';
    const duracion = userStore.duracion_turno || 30;
    const fechaInicioStr = formatearFechaBackend(fecha.value);
    const fechaFinStr = calcularFin(fecha.value, duracion);

    const payload = {
        paciente_id: pacienteId.value,
        usuario_id: usuarioId.value,
        fecha_inicio: fechaInicioStr,
        fecha_fin: fechaFinStr,
        motivo: motivo.value
    };

    if (esTanda.value) {
        payload.cantidad = cantidad.value;
        payload.dias_semana = diasSeleccionados.value;
        payload.fecha = fechaInicioStr;
    }

    try {
        // Se usa la instancia `api` y no fetch crudo: así pasa por el
        // interceptor de 401 y por la resolución de baseURL como el resto.
        const { data } = await api.post(endpoint, payload);

        mensaje.value = data.message || 'Turno creado correctamente ✅';

        // El backend alinea el turno al siguiente slot libre. Si lo movió, hay
        // que decirlo: sin este aviso se le informa al paciente un horario y el
        // sistema guarda otro.
        avisoAjuste.value = describirAjuste(data.ajuste_horario);

        // Resetear formulario
        pacienteId.value = '';
        usuarioId.value = '';
        fecha.value = null;
        motivo.value = '';
        searchPaciente.value = '';
        pacienteSeleccionado.value = '';
        esTanda.value = false;
        diasSeleccionados.value = [];
    } catch (e) {
        const datos = e.response?.data || {};
        error.value = datos.error || e.message || 'Error al crear turno';
        // El backend sugiere horarios libres del mismo día cuando el pedido
        // está ocupado; así se le puede ofrecer una alternativa al paciente.
        horariosSugeridos.value = datos.horarios_disponibles || [];
    }
}

/** Toma un horario sugerido y lo carga en el formulario. */
function usarHorario(iso) {
    fecha.value = new Date(iso);
    error.value = '';
    horariosSugeridos.value = [];
}

function soloHora(iso) {
    return new Date(iso).toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' });
}
</script>

<style scoped>
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
