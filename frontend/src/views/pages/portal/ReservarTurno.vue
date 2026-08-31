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
        const { data } = await portalService.proximoDia(clienteId, usuarioId, fecha.value);
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
        const { data } = await portalService.horarios(clienteId, usuarioId, fecha.value);
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

async function confirmar() {
    if (!elegido.value) return;

    // Sin cuenta: se guarda la elección y se manda a registrarse.
    if (!paciente.autenticado) {
        sessionStorage.setItem(CLAVE_PENDIENTE, JSON.stringify({ clienteId, usuarioId, fechaInicio: elegido.value, motivo: motivo.value }));
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
            motivo: motivo.value
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
});
</script>

<template>
    <div class="max-w-2xl mx-auto p-4 md:p-6 space-y-5">
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
            </header>

            <section class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-2xl p-5 space-y-4">
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

                <div v-else-if="horarios.length" class="space-y-2">
                    <label class="text-sm font-semibold text-surface-700 dark:text-surface-200 block">{{ horarios.length }} horarios el {{ fechaLarga(fecha) }}</label>
                    <div class="grid grid-cols-3 sm:grid-cols-4 gap-2">
                        <button
                            v-for="h in horarios"
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
