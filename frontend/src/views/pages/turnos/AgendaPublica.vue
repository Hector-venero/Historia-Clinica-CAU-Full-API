<script setup>
import { computed, onMounted, ref } from 'vue';
import api from '@/api/axios';

const cargando = ref(true);
const guardando = ref(false);
const error = ref('');
const mensaje = ref('');

const activa = ref(false);
const presentacion = ref('');
const especialidad = ref('');
const lugarDireccion = ref('');
const duracionTurno = ref(20);
const vistaPrevia = ref({ nombre: '', consultorio: '' });

// Lo que falta para poder publicarse. Viene del backend y no se calcula acá:
// que las dos puntas decidan por separado qué es indispensable garantiza que
// tarde o temprano difieran.
const faltantes = ref([]);

const puedeActivar = computed(() => especialidad.value.trim() && lugarDireccion.value.trim());

const iniciales = computed(() =>
    (vistaPrevia.value.nombre || '')
        .split(' ')
        .filter(Boolean)
        .slice(0, 2)
        .map((p) => p[0])
        .join('')
        .toUpperCase()
);

async function cargar() {
    cargando.value = true;
    try {
        const { data } = await api.get('/agenda-publica');
        activa.value = data.activa;
        presentacion.value = data.presentacion;
        especialidad.value = data.especialidad;
        lugarDireccion.value = data.lugar_direccion;
        duracionTurno.value = data.duracion_turno;
        vistaPrevia.value = data.vista_previa || {};
        faltantes.value = data.faltantes || [];
    } catch (e) {
        error.value = e?.response?.data?.error || 'No pudimos cargar tu configuración.';
    } finally {
        cargando.value = false;
    }
}

async function guardar(nuevoEstado) {
    guardando.value = true;
    error.value = '';
    mensaje.value = '';
    try {
        const { data } = await api.post('/agenda-publica', {
            activa: nuevoEstado,
            presentacion: presentacion.value,
            especialidad: especialidad.value,
            lugar_atencion_direccion: lugarDireccion.value
        });
        activa.value = data.activa;
        mensaje.value = data.mensaje;
        faltantes.value = [];
    } catch (e) {
        error.value = e?.response?.data?.error || 'No pudimos guardar los cambios.';
        faltantes.value = e?.response?.data?.faltantes || [];
    } finally {
        guardando.value = false;
    }
}

onMounted(cargar);
</script>

<template>
    <div class="max-w-3xl mx-auto p-4 md:p-6 space-y-6">
        <header>
            <h1 class="text-2xl md:text-3xl font-bold text-surface-900 dark:text-surface-0 m-0">Turnos online</h1>
            <p class="text-sm text-surface-500 dark:text-surface-400 mt-1 mb-0">Dejá que tus pacientes reserven solos, sin llamarte por teléfono.</p>
        </header>

        <div v-if="cargando" class="text-center py-16 text-surface-500 dark:text-surface-400"><i class="pi pi-spin pi-spinner text-3xl"></i></div>

        <template v-else>
            <!-- Estado. Es lo primero que tiene que quedar claro al entrar. -->
            <section class="rounded-2xl p-5 border" :class="activa ? 'bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-900' : 'bg-surface-0 dark:bg-surface-900 border-surface-200 dark:border-surface-700'">
                <div class="flex items-start gap-4">
                    <i class="pi text-2xl mt-0.5" :class="activa ? 'pi-check-circle text-green-600 dark:text-green-400' : 'pi-eye-slash text-surface-400'"></i>
                    <div class="flex-1">
                        <h2 class="font-semibold text-surface-900 dark:text-surface-0 m-0 mb-1">
                            {{ activa ? 'Tus pacientes pueden reservarte turnos' : 'No aparecés en la búsqueda' }}
                        </h2>
                        <p class="text-sm text-surface-600 dark:text-surface-300 leading-relaxed m-0">
                            <template v-if="activa"> Figurás en el buscador y cualquiera puede tomar un horario libre de tu agenda. Los turnos entran como cualquier otro. </template>
                            <template v-else> Nadie puede encontrarte ni reservarte. Tu agenda sigue siendo tuya y solo la cargás vos o tu equipo. </template>
                        </p>
                    </div>
                </div>
            </section>

            <div v-if="mensaje" class="p-3 rounded-xl bg-green-50 dark:bg-green-950/40 text-green-700 dark:text-green-300 text-sm border border-green-200 dark:border-green-900">
                {{ mensaje }}
            </div>
            <div v-if="error" class="p-3 rounded-xl bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-300 text-sm border border-red-200 dark:border-red-900">
                {{ error }}
            </div>

            <section class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-2xl p-5 md:p-6 space-y-5">
                <h2 class="font-semibold text-surface-900 dark:text-surface-0 m-0">Cómo te van a ver</h2>

                <div class="flex flex-col gap-2">
                    <label class="text-sm font-semibold text-surface-700 dark:text-surface-200">Especialidad</label>
                    <input v-model="especialidad" type="text" placeholder="Ej: Odontología, Kinesiología" class="campo" />
                    <small class="text-surface-500 dark:text-surface-400">Es por lo que te van a buscar.</small>
                </div>

                <div class="flex flex-col gap-2">
                    <label class="text-sm font-semibold text-surface-700 dark:text-surface-200">Dirección donde atendés</label>
                    <input v-model="lugarDireccion" type="text" placeholder="Calle y número" class="campo" />
                </div>

                <div class="flex flex-col gap-2">
                    <label class="text-sm font-semibold text-surface-700 dark:text-surface-200"> Presentación <span class="font-normal text-surface-400">(opcional)</span> </label>
                    <textarea v-model="presentacion" rows="3" maxlength="300" placeholder="Contale a tus pacientes qué atendés y cómo trabajás." class="campo resize-none"></textarea>
                    <small class="text-surface-500 dark:text-surface-400">{{ presentacion.length }}/300</small>
                </div>

                <!-- Vista previa. Que el profesional lea cómo va a aparecer antes
                     de publicarse evita la sorpresa de verse distinto de como
                     esperaba, cuando ya lo está viendo todo el mundo. -->
                <div>
                    <p class="text-sm font-semibold text-surface-700 dark:text-surface-200 mb-2">Así te ve un paciente</p>
                    <article class="bg-surface-50 dark:bg-surface-800 border border-surface-200 dark:border-surface-700 rounded-xl p-4">
                        <div class="flex items-start gap-3 mb-2">
                            <div class="w-11 h-11 rounded-full bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300 flex items-center justify-center font-bold shrink-0">
                                {{ iniciales || '—' }}
                            </div>
                            <div class="min-w-0">
                                <h3 class="font-semibold text-surface-900 dark:text-surface-0 m-0">{{ vistaPrevia.nombre || 'Tu nombre' }}</h3>
                                <p class="text-sm text-primary-600 dark:text-primary-400 m-0">
                                    {{ especialidad || 'Falta tu especialidad' }}
                                </p>
                            </div>
                        </div>
                        <p v-if="presentacion" class="text-sm text-surface-600 dark:text-surface-300 leading-relaxed m-0 mb-2">{{ presentacion }}</p>
                        <div class="space-y-1 text-xs text-surface-500 dark:text-surface-400">
                            <div><i class="pi pi-building mr-1"></i>{{ vistaPrevia.consultorio }}</div>
                            <div v-if="lugarDireccion"><i class="pi pi-map-marker mr-1"></i>{{ lugarDireccion }}</div>
                            <div><i class="pi pi-clock mr-1"></i>Turnos de {{ duracionTurno }} minutos</div>
                        </div>
                    </article>
                </div>

                <div class="pt-2 border-t border-surface-200 dark:border-surface-700">
                    <button
                        v-if="!activa"
                        type="button"
                        :disabled="!puedeActivar || guardando"
                        class="w-full inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl font-semibold text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-60 disabled:cursor-not-allowed transition"
                        @click="guardar(true)"
                    >
                        <i :class="guardando ? 'pi pi-spin pi-spinner' : 'pi pi-globe'"></i>
                        {{ guardando ? 'Publicando…' : 'Activar turnos online' }}
                    </button>

                    <div v-else class="flex flex-col sm:flex-row gap-3">
                        <button
                            type="button"
                            :disabled="guardando"
                            class="flex-1 inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl font-semibold text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-60 transition"
                            @click="guardar(true)"
                        >
                            <i :class="guardando ? 'pi pi-spin pi-spinner' : 'pi pi-check'"></i>
                            Guardar cambios
                        </button>
                        <button
                            type="button"
                            :disabled="guardando"
                            class="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl font-semibold text-surface-700 dark:text-surface-200 bg-surface-100 dark:bg-surface-800 hover:bg-surface-200 dark:hover:bg-surface-700 transition"
                            @click="guardar(false)"
                        >
                            <i class="pi pi-eye-slash"></i>
                            Dejar de publicarme
                        </button>
                    </div>

                    <p v-if="!activa && !puedeActivar" class="text-sm text-amber-700 dark:text-amber-400 mt-3 mb-0">
                        <i class="pi pi-info-circle mr-1"></i>
                        Completá la especialidad y la dirección para poder publicarte.
                    </p>
                </div>
            </section>

            <p class="text-xs text-surface-500 dark:text-surface-400 text-center">Solo se ofrecen los horarios que tengas libres según tu disponibilidad. Podés dejar de publicarte cuando quieras.</p>
        </template>
    </div>
</template>

<style scoped>
.campo {
    @apply w-full px-4 py-2.5 rounded-xl border border-surface-300 dark:border-surface-600 bg-surface-0 dark:bg-surface-800 text-surface-900 dark:text-surface-0 outline-none transition;
}
.campo:focus {
    @apply border-primary-500 ring-2 ring-primary-500/20;
}
</style>
