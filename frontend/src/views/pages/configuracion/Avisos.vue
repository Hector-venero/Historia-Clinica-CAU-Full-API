<script setup>
/**
 * Los avisos por correo del consultorio.
 *
 * Hasta ahora el correo se mandaba **siempre** y no había forma de apagarlo:
 * un consultorio que ya avisa por WhatsApp le manda al paciente dos
 * confirmaciones del mismo turno, y nada en el sistema lo evita.
 *
 * ⚠️ La lista **no está escrita acá**: viene del servidor con su título y su
 * explicación (`ajustes.descripcion()`). Así sumar un aviso es un solo lugar y
 * no dos que se contradicen.
 *
 * Un administrativo los ve pero no los cambia — puede necesitar saber por qué
 * un paciente no recibió el correo, pero decidir que el consultorio deje de
 * avisar es de la dirección. Eso lo decide el backend; acá solo se refleja.
 */
import { computed, onMounted, ref } from 'vue';
import { useToast } from 'primevue/usetoast';
import Button from 'primevue/button';
import InputSwitch from 'primevue/inputswitch';
import api from '@/api/axios';
import { useUserStore } from '@/stores/user';

const toast = useToast();
const userStore = useUserStore();

const avisos = ref([]);
const cargando = ref(true);
const guardando = ref(false);

const puedeEditar = computed(() => userStore.rol === 'director');
const hayAlgunoApagado = computed(() => avisos.value.some((a) => !a.valor));

async function cargar() {
    cargando.value = true;
    try {
        const { data } = await api.get('/ajustes');
        avisos.value = data.ajustes || [];
    } catch {
        toast.add({ severity: 'error', summary: 'No pudimos cargar los avisos', life: 4000 });
    } finally {
        cargando.value = false;
    }
}

async function guardar() {
    guardando.value = true;
    try {
        const payload = Object.fromEntries(avisos.value.map((a) => [a.clave, a.valor]));
        const { data } = await api.put('/ajustes', { ajustes: payload });
        avisos.value = data.ajustes || avisos.value;
        toast.add({ severity: 'success', summary: 'Avisos guardados', life: 3000 });
    } catch (e) {
        toast.add({ severity: 'error', summary: 'No se pudo guardar', detail: e?.response?.data?.error, life: 5000 });
    } finally {
        guardando.value = false;
    }
}

onMounted(cargar);
</script>

<template>
    <div>
        <header class="mb-6">
            <h3 class="text-lg font-bold text-surface-900 dark:text-surface-0 m-0">Avisos por correo</h3>
            <p class="text-surface-600 dark:text-surface-300 mt-2 mb-0 max-w-2xl">Qué manda el sistema automáticamente. Apagá lo que ya estés avisando por otro lado.</p>
        </header>

        <div v-if="cargando" class="py-8 text-center text-surface-500 dark:text-surface-400"><i class="pi pi-spin pi-spinner text-2xl"></i></div>

        <div v-else class="space-y-3 max-w-3xl">
            <div v-for="aviso in avisos" :key="aviso.clave" class="flex items-start gap-4 p-4 rounded-xl border border-surface-200 dark:border-surface-700">
                <InputSwitch v-model="aviso.valor" :disabled="!puedeEditar" :inputId="`aviso-${aviso.clave}`" class="mt-0.5" />
                <label :for="`aviso-${aviso.clave}`" class="cursor-pointer">
                    <span class="block font-semibold text-surface-900 dark:text-surface-0">{{ aviso.titulo }}</span>
                    <span class="block text-sm text-surface-500 dark:text-surface-400 mt-0.5">{{ aviso.detalle }}</span>
                </label>
            </div>

            <!-- Apagar un aviso no es un ajuste inocuo: el paciente deja de
                 enterarse. Se dice, en vez de dejar que se descubra. -->
            <div v-if="hayAlgunoApagado" class="p-4 rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900">
                <p class="text-sm text-amber-900 dark:text-amber-200 m-0"><i class="pi pi-exclamation-triangle mr-2"></i>Con un aviso apagado, el sistema deja de mandarlo. Asegurate de que alguien lo esté haciendo por otro medio.</p>
            </div>

            <div v-if="puedeEditar" class="pt-2">
                <Button label="Guardar" icon="pi pi-save" :loading="guardando" @click="guardar" />
            </div>
            <p v-else class="text-sm text-surface-500 dark:text-surface-400">Solo la dirección puede cambiar estos avisos.</p>
        </div>
    </div>
</template>
