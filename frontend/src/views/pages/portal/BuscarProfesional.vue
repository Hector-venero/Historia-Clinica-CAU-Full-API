<script setup>
import { onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import portalService from '@/service/portalService';
import logo from '@/assets/logo-ficha-salud.svg';

const router = useRouter();

const texto = ref('');
const especialidad = ref('');
const especialidades = ref([]);
const profesionales = ref([]);
const cargando = ref(true);
const error = ref('');

let temporizador = null;

async function buscar() {
    cargando.value = true;
    error.value = '';
    try {
        const params = {};
        if (texto.value.trim()) params.q = texto.value.trim();
        if (especialidad.value) params.especialidad = especialidad.value;
        const { data } = await portalService.profesionales(params);
        profesionales.value = data;
    } catch {
        error.value = 'No pudimos cargar el directorio. Probá de nuevo.';
    } finally {
        cargando.value = false;
    }
}

// Con retraso: sin esto cada tecla sería una petición.
watch(texto, () => {
    clearTimeout(temporizador);
    temporizador = setTimeout(buscar, 400);
});
watch(especialidad, buscar);

function elegir(p) {
    router.push(`/portal/reservar/${p.cliente_id}/${p.usuario_id}`);
}

onMounted(async () => {
    try {
        const { data } = await portalService.especialidades();
        especialidades.value = data;
    } catch {
        // El filtro es opcional; sin él la búsqueda por texto sigue andando.
    }
    buscar();
});
</script>

<template>
    <div class="max-w-4xl mx-auto p-4 md:p-6 space-y-5">
        <header>
            <h1 class="text-2xl md:text-3xl font-bold text-surface-900 dark:text-surface-0 m-0">Sacar un turno</h1>
            <p class="text-sm text-surface-500 dark:text-surface-400 mt-1 mb-0">Elegí un profesional y reservá el horario que te sirva.</p>
        </header>

        <div class="flex flex-col md:flex-row gap-3">
            <div class="flex-1 relative">
                <i class="pi pi-search absolute left-3 top-1/2 -translate-y-1/2 text-surface-400"></i>
                <input
                    v-model="texto"
                    type="text"
                    placeholder="Nombre, especialidad o consultorio"
                    class="w-full pl-10 pr-4 py-2.5 rounded-xl border border-surface-300 dark:border-surface-600 bg-surface-0 dark:bg-surface-800 text-surface-900 dark:text-surface-0 outline-none transition"
                />
            </div>

            <select v-if="especialidades.length" v-model="especialidad" class="px-4 py-2.5 rounded-xl border border-surface-300 dark:border-surface-600 bg-surface-0 dark:bg-surface-800 text-surface-900 dark:text-surface-0 outline-none md:w-56">
                <option value="">Todas las especialidades</option>
                <option v-for="e in especialidades" :key="e.especialidad" :value="e.especialidad">{{ e.especialidad }} ({{ e.n }})</option>
            </select>
        </div>

        <div v-if="error" class="p-3 rounded-xl bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-300 text-sm border border-red-200 dark:border-red-900">
            {{ error }}
        </div>

        <div v-if="cargando" class="text-center py-16 text-surface-500 dark:text-surface-400"><i class="pi pi-spin pi-spinner text-3xl mb-3 block"></i> Buscando…</div>

        <!-- Vacío. Se distingue "no hay nadie todavía" de "tu búsqueda no dio
             resultados": son dos situaciones distintas y la respuesta también. -->
        <div v-else-if="!profesionales.length" class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-2xl p-10 text-center">
            <i class="pi pi-search text-5xl text-surface-300 dark:text-surface-600 mb-4 block"></i>
            <h2 class="text-lg font-semibold text-surface-900 dark:text-surface-0 m-0 mb-2">
                {{ texto || especialidad ? 'No encontramos profesionales' : 'Todavía no hay profesionales con turnos online' }}
            </h2>
            <p class="text-sm text-surface-500 dark:text-surface-400 leading-relaxed max-w-md mx-auto m-0">
                {{ texto || especialidad ? 'Probá con otro nombre o quitá los filtros.' : 'Los profesionales que activen la reserva online van a aparecer acá.' }}
            </p>
        </div>

        <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <article
                v-for="p in profesionales"
                :key="`${p.cliente_id}-${p.usuario_id}`"
                class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-2xl p-5 flex flex-col hover:border-primary-300 dark:hover:border-primary-800 transition cursor-pointer"
                @click="elegir(p)"
            >
                <div class="flex items-start gap-3 mb-3">
                    <div class="w-12 h-12 rounded-full bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300 flex items-center justify-center font-bold shrink-0">
                        {{ (p.nombre?.[0] || '') + (p.apellido?.[0] || '') }}
                    </div>
                    <div class="min-w-0">
                        <h3 class="font-semibold text-surface-900 dark:text-surface-0 m-0 truncate">{{ p.nombre }} {{ p.apellido || '' }}</h3>
                        <p v-if="p.especialidad" class="text-sm text-primary-600 dark:text-primary-400 m-0">{{ p.especialidad }}</p>
                    </div>
                </div>

                <p v-if="p.presentacion" class="text-sm text-surface-600 dark:text-surface-300 leading-relaxed m-0 mb-3">
                    {{ p.presentacion }}
                </p>

                <div class="mt-auto space-y-1 text-xs text-surface-500 dark:text-surface-400">
                    <div><i class="pi pi-building mr-1"></i>{{ p.consultorio_nombre }}</div>
                    <div v-if="p.lugar_direccion"><i class="pi pi-map-marker mr-1"></i>{{ p.lugar_direccion }}</div>
                    <div><i class="pi pi-clock mr-1"></i>Turnos de {{ p.duracion_turno }} minutos</div>
                </div>

                <button type="button" class="mt-4 w-full px-4 py-2.5 rounded-xl font-semibold text-white bg-primary-600 hover:bg-primary-700 transition">Ver horarios</button>
            </article>
        </div>

        <!-- Quien todavía no tiene cuenta puede mirar igual; se le dice cuándo
             la va a necesitar, en vez de sorprenderlo al final. -->
        <p class="text-center text-xs text-surface-500 dark:text-surface-400 pt-2">
            <img :src="logo" alt="" class="h-4 w-4 inline-block align-text-bottom mr-1" />
            Podés mirar sin cuenta. Te la vamos a pedir recién al confirmar el turno.
        </p>
    </div>
</template>
