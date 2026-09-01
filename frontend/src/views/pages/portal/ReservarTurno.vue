<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import portalService from '@/service/portalService';
import { usePacienteStore } from '@/stores/paciente';

const route = useRoute();
const router = useRouter();
const paciente = usePacienteStore();

const clienteId = Number(route.params.clienteId);
const usuarioId = Number(route.params.usuarioId);

const profesional = ref(null);
const fecha = ref('');
const horarios = ref([]);
const elegido = ref('');
const motivo = ref('');

// Prestaciones del profesional. Lista vacía en un consultorio que no las use, y
// entonces la reserva es como siempre: solo día y horario.
const servicios = ref([]);
const servicioId = ref(null);
const servicioElegido = computed(() => servicios.value.find((s) => s.id === servicioId.value) || null);

const cargandoHorarios = ref(false);
const confirmando = ref(false);
const error = ref('');
const confirmado = ref(null);

// Sesión pendiente: si alguien eligió horario sin cuenta, se guarda para
// retomarlo después de registrarse. Perder la selección justo en ese punto es
// lo que hace abandonar el trámite.
const CLAVE_PENDIENTE = 'ficha-salud:turno-pendiente';

const hoy = new Date().toISOString().slice(0, 10);
const maximo = new Date(Date.now() + 60 * 86400000).toISOString().slice(0, 10);

const nombreProfesional = computed(() => (profesional.value ? `${profesional.value.nombre} ${profesional.value.apellido || ''}`.trim() : ''));

function horaDe(iso) {
    return iso.slice(11, 16);
}

// Mañana y tarde, en vez de una grilla corrida de veinte botones. Es como la
// gente piensa el día cuando elige un turno: primero el rato, después la hora.
const franjas = computed(() => {
    const manana = horarios.value.filter((h) => Number(h.slice(11, 13)) < 13);
    const tarde = horarios.value.filter((h) => Number(h.slice(11, 13)) >= 13);
    return [
        { nombre: 'Mañana', icono: 'pi-sun', horas: manana },
        { nombre: 'Tarde', icono: 'pi-moon', horas: tarde }
    ].filter((f) => f.horas.length);
});

// Los próximos días con lugar, para elegir sin abrir el calendario. Sale de la
// misma consulta que ya se hacía cuando un día quedaba vacío.
const sugeridos = ref([]);

async function cargarServicios() {
    try {
        const { data } = await portalService.servicios(clienteId, usuarioId);
        servicios.value = data.servicios || [];
    } catch {
        // Sin la lista se reserva como siempre. No vale cortar la pantalla.
        servicios.value = [];
    }
}

function precioTexto(valor) {
    if (valor === null || valor === undefined) return '';
    return valor.toLocaleString('es-AR', { style: 'currency', currency: 'ARS', maximumFractionDigits: 0 });
}

async function cargarSugeridos() {
    try {
        const { data } = await portalService.proximoDia(clienteId, usuarioId, hoy, servicioId.value);
        sugeridos.value = data.dia ? [data.dia] : [];
    } catch {
        sugeridos.value = [];
    }
}

function fechaLarga(valor) {
    if (!valor) return '';
    // Se agrega la hora para que el navegador no lo interprete como UTC y
    // muestre el día anterior.
    return new Date(`${valor}T12:00:00`).toLocaleDateString('es-AR', { weekday: 'long', day: 'numeric', month: 'long' });
}

// El día vacío no puede terminar en "probá con otro": se busca el próximo con
// lugar y se ofrece de un clic. Importa sobre todo el mismo día a la tarde,
// cuando no hay horarios porque ya pasó el mínimo de anticipación y nada en
// pantalla lo explica.
const proximoConLugar = ref(null);
const buscandoProximo = ref(false);

async function buscarProximoDia() {
    proximoConLugar.value = null;
    buscandoProximo.value = true;
    try {
        const { data } = await portalService.proximoDia(clienteId, usuarioId, fecha.value, servicioId.value);
        // El backend responde 200 con `dia: null` cuando no hay nada en las
        // próximas dos semanas: es una respuesta, no un error.
        proximoConLugar.value = data.dia || null;
    } catch {
        // Que falle esta ayuda no puede tapar la pantalla: el mensaje de "no hay
        // horarios" ya está, y la persona puede seguir eligiendo días a mano.
        proximoConLugar.value = null;
    } finally {
        buscandoProximo.value = false;
    }
}

async function cargarHorarios() {
    if (!fecha.value) return;
    cargandoHorarios.value = true;
    elegido.value = '';
    error.value = '';
    proximoConLugar.value = null;
    try {
        const { data } = await portalService.horarios(clienteId, usuarioId, fecha.value, servicioId.value);
        horarios.value = data.horarios || [];
        if (!horarios.value.length) await buscarProximoDia();
    } catch (e) {
        horarios.value = [];
        error.value = e?.response?.data?.error || 'No pudimos cargar los horarios.';
    } finally {
        cargandoHorarios.value = false;
    }
}

watch(fecha, cargarHorarios);

// Cambiar de servicio cambia la duración, y con ella la grilla entera: los
// horarios de 20 minutos no sirven para un turno de 40. Se recalcula todo, y
// también el atajo al primer día con lugar, que si no quedaría apuntando a un
// día que ya no lo tiene.
watch(servicioId, () => {
    elegido.value = '';
    cargarSugeridos();
    cargarHorarios();
});

async function confirmar() {
    if (!elegido.value) return;

    // Sin cuenta: se guarda la elección y se manda a registrarse.
    if (!paciente.autenticado) {
        sessionStorage.setItem(CLAVE_PENDIENTE, JSON.stringify({ clienteId, usuarioId, fechaInicio: elegido.value, motivo: motivo.value, servicioId: servicioId.value }));
        router.push({ path: '/portal/registro', query: { volver: route.fullPath } });
        return;
    }

    confirmando.value = true;
    error.value = '';
    try {
        const { data } = await portalService.reservar({
            cliente_id: clienteId,
            usuario_id: usuarioId,
            fecha_inicio: elegido.value,
            motivo: motivo.value,
            servicio_id: servicioId.value
        });
        confirmado.value = data;
        sessionStorage.removeItem(CLAVE_PENDIENTE);
    } catch (e) {
        // 409: alguien tomó ese horario mientras tanto. Se recargan los
        // horarios para que no vuelva a elegir el mismo.
        error.value = e?.response?.data?.error || 'No pudimos confirmar el turno.';
        if (e?.response?.status === 409) await cargarHorarios();
    } finally {
        confirmando.value = false;
    }
}

onMounted(async () => {
    // Antes que nada: los horarios se piden con el servicio puesto, así que la
    // lista tiene que estar antes de la primera consulta.
    await cargarServicios();

    try {
        const { data } = await portalService.profesionales({});
        profesional.value = data.find((p) => p.cliente_id === clienteId && p.usuario_id === usuarioId) || null;
    } catch {
        // El nombre es presentación; sin él la reserva funciona igual.
    }

    // Retomar una selección hecha antes de registrarse.
    const pendiente = sessionStorage.getItem(CLAVE_PENDIENTE);
    if (pendiente && paciente.autenticado) {
        try {
            const datos = JSON.parse(pendiente);
            if (datos.clienteId === clienteId && datos.usuarioId === usuarioId) {
                // El servicio se restaura antes que la fecha: sin él la grilla
                // se armaría con otra duración y el horario guardado no
                // aparecería en la lista.
                if (datos.servicioId && servicios.value.some((s) => s.id === datos.servicioId)) servicioId.value = datos.servicioId;
                fecha.value = datos.fechaInicio.slice(0, 10);
                motivo.value = datos.motivo || '';
                await cargarHorarios();
                if (horarios.value.includes(datos.fechaInicio)) elegido.value = datos.fechaInicio;
            }
        } catch {
            sessionStorage.removeItem(CLAVE_PENDIENTE);
        }
        return;
    }

    fecha.value = hoy;
    cargarSugeridos();
});
</script>

<template>
    <div class="max-w-4xl mx-auto p-4 md:p-6 space-y-5">
        <!-- Confirmado -->
        <div v-if="confirmado" class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-2xl p-8 text-center">
            <i class="pi pi-check-circle text-5xl text-green-500 mb-4 block"></i>
            <h1 class="text-2xl font-bold text-surface-900 dark:text-surface-0 m-0 mb-3">Turno confirmado</h1>

            <div class="bg-surface-50 dark:bg-surface-800 rounded-xl p-4 text-left space-y-2 mb-6">
                <div class="flex justify-between gap-4 text-sm">
                    <span class="text-surface-500 dark:text-surface-400">Profesional</span>
                    <strong class="text-surface-900 dark:text-surface-0 text-right">{{ confirmado.profesional }}</strong>
                </div>
                <div class="flex justify-between gap-4 text-sm">
                    <span class="text-surface-500 dark:text-surface-400">Cuándo</span>
                    <strong class="text-surface-900 dark:text-surface-0 text-right">{{ confirmado.fecha_inicio?.slice(8, 10) }}/{{ confirmado.fecha_inicio?.slice(5, 7) }} a las {{ confirmado.fecha_inicio?.slice(11, 16) }}</strong>
                </div>
                <div class="flex justify-between gap-4 text-sm">
                    <span class="text-surface-500 dark:text-surface-400">Dónde</span>
                    <strong class="text-surface-900 dark:text-surface-0 text-right">{{ confirmado.lugar || confirmado.consultorio }}</strong>
                </div>
            </div>

            <p class="text-sm text-surface-500 dark:text-surface-400 mb-6">
                <i class="pi pi-envelope mr-1"></i>
                Te mandamos un correo con los datos del turno.
            </p>

            <!-- Acaba de sacar un turno: lo que quiere ver es el turno. El botón
                 llevaba al buzón de documentos, que no tiene nada que ver con lo
                 que acaba de hacer. -->
            <div class="flex flex-col sm:flex-row items-center justify-center gap-3">
                <router-link to="/portal/turnos" class="inline-flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-white bg-primary-600 hover:bg-primary-700 transition no-underline">
                    <i class="pi pi-calendar"></i>
                    Ver mis turnos
                </router-link>
                <router-link to="/portal" class="px-6 py-3 rounded-xl font-semibold text-surface-600 dark:text-surface-300 hover:bg-surface-100 dark:hover:bg-surface-800 transition no-underline"> Ir a mis documentos </router-link>
            </div>
        </div>

        <template v-else>
            <header>
                <router-link to="/portal/buscar" class="text-sm text-primary-600 dark:text-primary-400 hover:underline"> <i class="pi pi-arrow-left mr-1"></i>Volver </router-link>
                <h1 class="text-2xl font-bold text-surface-900 dark:text-surface-0 m-0 mt-2">
                    {{ nombreProfesional || 'Elegí un horario' }}
                </h1>
                <p v-if="profesional" class="text-sm text-surface-500 dark:text-surface-400 mt-1 mb-0">{{ profesional.especialidad }} · {{ profesional.consultorio_nombre }}</p>

                <!-- Lo que hace falta para decidir, sin tener que volver atrás:
                     cuánto dura y dónde es. -->
                <div v-if="profesional" class="flex flex-wrap gap-x-5 gap-y-1 mt-3 text-sm text-surface-500 dark:text-surface-400">
                    <span v-if="servicioElegido"><i class="pi pi-clock mr-1.5"></i>{{ servicioElegido.nombre }} · {{ servicioElegido.duracion_minutos }} minutos</span>
                    <span v-else-if="profesional.duracion_turno"><i class="pi pi-clock mr-1.5"></i>Turnos de {{ profesional.duracion_turno }} minutos</span>
                    <span v-if="profesional.lugar_direccion"><i class="pi pi-map-marker mr-1.5"></i>{{ profesional.lugar_direccion }}</span>
                </div>
            </header>

            <section class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-2xl p-5 space-y-4">
                <!-- Un atajo al primer día con lugar. El calendario nativo no
                     sabe qué días tienen horarios, así que sin esto hay que ir
                     probando de a uno. -->
                <div v-if="sugeridos.length && fecha !== sugeridos[0].fecha" class="flex flex-wrap items-center gap-2 -mt-1">
                    <span class="text-sm text-surface-500 dark:text-surface-400">Primer día con lugar:</span>
                    <button
                        type="button"
                        class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-semibold bg-primary-50 dark:bg-primary-950/40 text-primary-700 dark:text-primary-300 hover:bg-primary-100 dark:hover:bg-primary-950/70 transition"
                        @click="fecha = sugeridos[0].fecha"
                    >
                        <i class="pi pi-bolt text-xs"></i>
                        {{ fechaLarga(sugeridos[0].fecha) }}
                    </button>
                </div>

                <!-- Primero qué necesita, después cuándo: la prestación decide
                     cuánto dura el turno y por lo tanto qué horarios existen.
                     Solo aparece si el consultorio cargó servicios. -->
                <div v-if="servicios.length" class="flex flex-col gap-2">
                    <label class="text-sm font-semibold text-surface-700 dark:text-surface-200">¿Qué necesitás?</label>
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        <button
                            v-for="s in servicios"
                            :key="s.id"
                            type="button"
                            class="text-left px-4 py-3 rounded-xl border transition"
                            :class="servicioId === s.id ? 'border-primary-500 bg-primary-50 dark:bg-primary-950/40' : 'border-surface-200 dark:border-surface-700 hover:bg-surface-50 dark:hover:bg-surface-800'"
                            @click="servicioId = servicioId === s.id ? null : s.id"
                        >
                            <span class="block font-semibold text-surface-900 dark:text-surface-0">{{ s.nombre }}</span>
                            <span v-if="s.descripcion" class="block text-xs text-surface-500 dark:text-surface-400 mt-0.5">{{ s.descripcion }}</span>
                            <span class="block text-sm text-surface-500 dark:text-surface-400 mt-1">
                                {{ s.duracion_minutos }} min<span v-if="s.precio !== null"> · {{ precioTexto(s.precio) }}</span>
                            </span>
                        </button>
                    </div>
                    <p class="text-xs text-surface-400 dark:text-surface-500 m-0">Si no estás seguro, dejalo sin elegir y contalo en el motivo.</p>
                </div>

                <div class="flex flex-col gap-2">
                    <label class="text-sm font-semibold text-surface-700 dark:text-surface-200">¿Qué día?</label>
                    <input
                        v-model="fecha"
                        type="date"
                        :min="hoy"
                        :max="maximo"
                        class="w-full px-4 py-2.5 rounded-xl border border-surface-300 dark:border-surface-600 bg-surface-0 dark:bg-surface-800 text-surface-900 dark:text-surface-0 outline-none"
                    />
                </div>

                <div v-if="cargandoHorarios" class="text-center py-8 text-surface-500 dark:text-surface-400"><i class="pi pi-spin pi-spinner text-2xl"></i></div>

                <div v-else-if="fecha && !horarios.length" class="text-center py-8">
                    <p class="text-surface-600 dark:text-surface-300 m-0 mb-1">No hay horarios para el {{ fechaLarga(fecha) }}.</p>

                    <p v-if="buscandoProximo" class="text-sm text-surface-500 dark:text-surface-400 m-0"><i class="pi pi-spin pi-spinner mr-1"></i> Buscando el próximo día con lugar…</p>

                    <template v-else-if="proximoConLugar">
                        <p class="text-sm text-surface-500 dark:text-surface-400 m-0 mb-3">El próximo con lugar es el {{ fechaLarga(proximoConLugar.fecha) }}.</p>
                        <button type="button" class="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-white bg-primary-600 hover:bg-primary-700 transition" @click="fecha = proximoConLugar.fecha">
                            <i class="pi pi-arrow-right"></i>
                            Ver esos {{ proximoConLugar.horarios.length }} horarios
                        </button>
                    </template>

                    <p v-else class="text-sm text-surface-500 dark:text-surface-400 m-0">No encontramos horarios en las próximas dos semanas. Probá más adelante o comunicate con el consultorio.</p>
                </div>

                <div v-else-if="horarios.length" class="space-y-4">
                    <label class="text-sm font-semibold text-surface-700 dark:text-surface-200 block">{{ horarios.length }} horarios el {{ fechaLarga(fecha) }}</label>

                    <div v-for="franja in franjas" :key="franja.nombre" class="space-y-2">
                        <p class="text-xs font-semibold uppercase tracking-wide text-surface-400 dark:text-surface-500 m-0"><i class="pi mr-1" :class="franja.icono"></i>{{ franja.nombre }}</p>
                        <!-- Más columnas en pantalla ancha: el portal usa todo el
                             ancho del layout y estirar la página hacia abajo con
                             tres botones por fila era desaprovecharlo. -->
                        <div class="grid grid-cols-3 sm:grid-cols-5 lg:grid-cols-6 gap-2">
                            <button
                                v-for="h in franja.horas"
                                :key="h"
                                type="button"
                                class="px-3 py-2.5 rounded-lg text-sm font-semibold transition"
                                :class="elegido === h ? 'bg-primary-600 text-white' : 'bg-surface-100 dark:bg-surface-800 text-surface-700 dark:text-surface-200 hover:bg-surface-200 dark:hover:bg-surface-700'"
                                @click="elegido = h"
                            >
                                {{ horaDe(h) }}
                            </button>
                        </div>
                    </div>
                </div>

                <div v-if="elegido" class="flex flex-col gap-2 pt-2 border-t border-surface-200 dark:border-surface-700">
                    <label class="text-sm font-semibold text-surface-700 dark:text-surface-200">Motivo <span class="font-normal text-surface-400">(opcional)</span></label>
                    <input
                        v-model="motivo"
                        type="text"
                        placeholder="Ej: control, dolor de muela"
                        class="w-full px-4 py-2.5 rounded-xl border border-surface-300 dark:border-surface-600 bg-surface-0 dark:bg-surface-800 text-surface-900 dark:text-surface-0 outline-none"
                    />
                </div>

                <div v-if="error" class="p-3 rounded-xl bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-300 text-sm border border-red-200 dark:border-red-900">
                    {{ error }}
                </div>

                <button
                    v-if="elegido"
                    type="button"
                    :disabled="confirmando"
                    class="w-full inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl font-semibold text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-60 transition"
                    @click="confirmar"
                >
                    <i :class="confirmando ? 'pi pi-spin pi-spinner' : 'pi pi-check'"></i>
                    {{ confirmando ? 'Confirmando…' : paciente.autenticado ? `Confirmar turno ${horaDe(elegido)}` : 'Continuar y crear mi cuenta' }}
                </button>

                <!-- Se dice que la elección se recuerda, NO que el horario queda
                     reservado: no lo está, y alguien puede tomarlo mientras
                     tanto. Prometerlo haría que el 409 se sintiera una falla del
                     sistema en vez de lo que es. -->
                <p v-if="elegido && !paciente.autenticado" class="text-xs text-center text-surface-500 dark:text-surface-400 m-0">Al volver retomamos este horario, si todavía está libre.</p>
            </section>
        </template>
    </div>
</template>
