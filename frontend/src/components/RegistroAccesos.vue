<script setup>
/**
 * Quién accedió a la historia de este paciente.
 *
 * No existía ningún registro: en un consultorio con dirección, varios
 * profesionales, secretaría y coordinación de área —todos con acceso a datos de
 * pacientes— nadie podía responder "¿quién miró esta historia?".
 *
 * **Solo la dirección lo ve.** Dice, sobre cada persona del equipo, a qué hora
 * abrió qué historia: es información sobre el personal, no solo sobre el
 * paciente. Acá se oculta el botón, pero quien decide es `@requiere_rol` en el
 * servidor — ocultar no es un permiso.
 *
 * Se carga **al abrirlo**, no al montar la pantalla: es una consulta que casi
 * nadie hace, y pedirla en cada apertura de historia sería una consulta más por
 * cada paciente que se atiende.
 */
import { computed, ref } from 'vue';
import api from '@/api/axios';
import { useUserStore } from '@/stores/user';

const props = defineProps({
    pacienteId: { type: [Number, String], required: true }
});

const userStore = useUserStore();
const puedeVer = computed(() => userStore.rol === 'director');

const abierto = ref(false);
const cargando = ref(false);
const error = ref('');
const accesos = ref([]);

async function alternar() {
    abierto.value = !abierto.value;
    if (!abierto.value || accesos.value.length) return;

    cargando.value = true;
    error.value = '';
    try {
        const { data } = await api.get(`/pacientes/${props.pacienteId}/accesos`);
        accesos.value = data.accesos || [];
    } catch (e) {
        error.value = e?.response?.data?.error || 'No pudimos cargar el registro.';
    } finally {
        cargando.value = false;
    }
}

function cuando(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    return d.toLocaleString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}
</script>

<template>
    <div v-if="puedeVer" class="mt-6">
        <button type="button" class="inline-flex items-center gap-2 text-sm font-medium text-surface-500 dark:text-surface-400 hover:text-surface-800 dark:hover:text-surface-100 transition" @click="alternar">
            <i class="pi" :class="abierto ? 'pi-chevron-down' : 'pi-chevron-right'"></i>
            <i class="pi pi-eye"></i>
            Quién accedió a esta historia
        </button>

        <div v-if="abierto" class="mt-3 rounded-xl border border-surface-200 dark:border-surface-700 overflow-hidden">
            <div v-if="cargando" class="p-6 text-center text-surface-500 dark:text-surface-400"><i class="pi pi-spin pi-spinner"></i></div>

            <p v-else-if="error" class="p-4 m-0 text-sm text-red-700 dark:text-red-300">{{ error }}</p>

            <p v-else-if="!accesos.length" class="p-4 m-0 text-sm text-surface-500 dark:text-surface-400">Todavía no hay accesos registrados. El registro empieza cuando se instaló esta versión: lo anterior no quedó anotado.</p>

            <div v-else class="max-h-96 overflow-y-auto">
                <div v-for="a in accesos" :key="a.id" class="flex flex-wrap items-baseline gap-x-3 gap-y-1 px-4 py-2.5 border-b last:border-b-0 border-surface-100 dark:border-surface-800">
                    <span class="text-sm font-semibold text-surface-900 dark:text-surface-0">{{ a.usuario }}</span>
                    <span v-if="a.rol" class="text-xs px-2 py-0.5 rounded-full bg-surface-100 dark:bg-surface-800 text-surface-500 dark:text-surface-400">{{ a.rol }}</span>
                    <span class="text-sm text-surface-600 dark:text-surface-300">{{ a.accion_nombre }}</span>
                    <span v-if="a.detalle" class="text-xs text-surface-400 dark:text-surface-500">({{ a.detalle }})</span>
                    <span class="ml-auto text-xs text-surface-400 dark:text-surface-500 tabular-nums">{{ cuando(a.cuando) }}</span>
                </div>
            </div>

            <!-- Se dice qué NO guarda. Un registro de accesos genera la
                 sospecha de que además se guarda lo que se leyó, y no es así. -->
            <p class="px-4 py-2.5 m-0 text-xs text-surface-400 dark:text-surface-500 bg-surface-50 dark:bg-surface-800/50 border-t border-surface-200 dark:border-surface-700">Queda registrado quién, qué y cuándo. Nunca lo que se leyó.</p>
        </div>
    </div>
</template>
