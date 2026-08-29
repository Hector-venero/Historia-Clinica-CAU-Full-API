<script setup>
import { computed, onMounted, ref } from 'vue';
import portalService from '@/service/portalService';

const turnos = ref([]);
const cargando = ref(true);
const error = ref('');
const cancelando = ref(null);
const confirmando = ref(null);

const proximos = computed(() => turnos.value.filter((t) => t.estado === 'reservado'));
const otros = computed(() => turnos.value.filter((t) => t.estado !== 'reservado'));

function cuando(valor) {
    if (!valor) return '';
    const d = new Date(valor);
    return d.toLocaleDateString('es-AR', { weekday: 'long', day: 'numeric', month: 'long' }) + ' a las ' + d.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' });
}

async function cargar() {
    cargando.value = true;
    error.value = '';
    try {
        const { data } = await portalService.misTurnos();
        turnos.value = data;
    } catch {
        error.value = 'No pudimos cargar tus turnos. Probá de nuevo en un momento.';
    } finally {
        cargando.value = false;
    }
}

async function cancelar(turno) {
    cancelando.value = turno.id;
    error.value = '';
    try {
        await portalService.cancelarTurno(turno.id);
        confirmando.value = null;
        await cargar();
    } catch (e) {
        error.value = e?.response?.data?.error || 'No pudimos cancelar el turno.';
    } finally {
        cancelando.value = null;
    }
}

onMounted(cargar);
</script>

<template>
    <div class="max-w-3xl mx-auto p-4 md:p-6 space-y-5">
        <header class="flex items-start justify-between gap-4">
            <div>
                <h1 class="text-2xl md:text-3xl font-bold text-surface-900 dark:text-surface-0 m-0">Mis turnos</h1>
                <p class="text-sm text-surface-500 dark:text-surface-400 mt-1 mb-0">Los que sacaste desde acá.</p>
            </div>
            <router-link to="/portal/buscar" class="shrink-0 inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold text-white bg-primary-600 hover:bg-primary-700 transition no-underline">
                <i class="pi pi-plus"></i> Sacar turno
            </router-link>
        </header>

        <div v-if="error" class="p-3 rounded-xl bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-300 text-sm border border-red-200 dark:border-red-900">
            {{ error }}
        </div>

        <div v-if="cargando" class="text-center py-16 text-surface-500 dark:text-surface-400"><i class="pi pi-spin pi-spinner text-3xl"></i></div>

        <template v-else>
            <div v-if="!turnos.length" class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-2xl p-10 text-center">
                <i class="pi pi-calendar text-5xl text-surface-300 dark:text-surface-600 mb-4 block"></i>
                <h2 class="text-lg font-semibold text-surface-900 dark:text-surface-0 m-0 mb-2">No tenés turnos</h2>
                <p class="text-sm text-surface-500 dark:text-surface-400 m-0">Los turnos que saques desde Ficha Salud aparecen acá.</p>
            </div>

            <section v-if="proximos.length" class="space-y-3">
                <article v-for="t in proximos" :key="t.id" class="bg-surface-0 dark:bg-surface-900 border border-primary-200 dark:border-primary-900 rounded-2xl p-5">
                    <div class="flex items-start gap-4">
                        <div class="w-11 h-11 rounded-xl bg-primary-50 dark:bg-primary-950/40 text-primary-600 dark:text-primary-400 flex items-center justify-center shrink-0">
                            <i class="pi pi-calendar-plus text-lg"></i>
                        </div>

                        <div class="flex-1 min-w-0">
                            <h3 class="font-semibold text-surface-900 dark:text-surface-0 m-0 first-letter:uppercase">{{ cuando(t.fecha_inicio) }}</h3>
                            <div class="flex flex-wrap gap-x-3 gap-y-1 mt-2 text-xs text-surface-500 dark:text-surface-400">
                                <span v-if="t.profesional_nombre"><i class="pi pi-user mr-1"></i>{{ t.profesional_nombre }}</span>
                                <span><i class="pi pi-building mr-1"></i>{{ t.consultorio_nombre }}</span>
                                <span v-if="t.lugar"><i class="pi pi-map-marker mr-1"></i>{{ t.lugar }}</span>
                            </div>
                            <p v-if="t.motivo" class="text-sm text-surface-600 dark:text-surface-300 mt-2 mb-0">{{ t.motivo }}</p>

                            <!-- Confirmación en dos pasos. Cancelar un turno no se
                                 deshace: el horario queda libre y otro paciente
                                 puede tomarlo en el acto. -->
                            <div v-if="confirmando === t.id" class="mt-4 p-3 rounded-xl bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900">
                                <p class="text-sm text-red-800 dark:text-red-300 m-0 mb-3">¿Seguro? El horario queda libre y puede tomarlo otra persona.</p>
                                <div class="flex flex-wrap gap-2">
                                    <button type="button" :disabled="cancelando === t.id" class="px-4 py-2 rounded-lg text-sm font-semibold text-white bg-red-600 hover:bg-red-700 disabled:opacity-60 transition" @click="cancelar(t)">
                                        <i :class="cancelando === t.id ? 'pi pi-spin pi-spinner' : 'pi pi-times'" class="mr-1"></i>
                                        Sí, cancelar
                                    </button>
                                    <button
                                        type="button"
                                        class="px-4 py-2 rounded-lg text-sm font-semibold text-surface-700 dark:text-surface-200 bg-surface-100 dark:bg-surface-800 hover:bg-surface-200 dark:hover:bg-surface-700 transition"
                                        @click="confirmando = null"
                                    >
                                        Mejor no
                                    </button>
                                </div>
                            </div>

                            <button v-else-if="t.puede_cancelar" type="button" class="mt-3 text-sm text-red-600 dark:text-red-400 font-medium hover:underline" @click="confirmando = t.id">Cancelar turno</button>

                            <!-- Se dice por qué no se puede y qué hacer, en vez
                                 de esconder el botón sin explicación. -->
                            <p v-else class="text-xs text-surface-500 dark:text-surface-400 mt-3 mb-0">
                                <i class="pi pi-info-circle mr-1"></i>
                                Falta poco para el turno. Si no podés ir, llamá al consultorio.
                            </p>
                        </div>
                    </div>
                </article>
            </section>

            <section v-if="otros.length" class="space-y-3">
                <h2 class="text-sm font-semibold text-surface-500 dark:text-surface-400 uppercase tracking-wide">Cancelados</h2>
                <article v-for="t in otros" :key="t.id" class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-2xl p-4 opacity-70">
                    <div class="flex items-start gap-3">
                        <i class="pi pi-times-circle text-surface-400 mt-1"></i>
                        <div class="min-w-0">
                            <p class="text-sm text-surface-700 dark:text-surface-200 m-0 first-letter:uppercase line-through">{{ cuando(t.fecha_inicio) }}</p>
                            <p class="text-xs text-surface-500 dark:text-surface-400 m-0 mt-1">
                                {{ t.consultorio_nombre }} ·
                                <!-- Quién lo canceló importa: si lo canceló el
                                     consultorio, el paciente necesita saber que no
                                     fue él y que quizá deba reprogramar. -->
                                {{ t.cancelado_por === 'consultorio' ? 'lo canceló el consultorio' : 'lo cancelaste vos' }}
                            </p>
                        </div>
                    </div>
                </article>
            </section>
        </template>
    </div>
</template>
