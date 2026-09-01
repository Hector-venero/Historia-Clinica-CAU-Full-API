<script setup>
/**
 * Plantillas de texto clínico.
 *
 * Buena parte de lo que se escribe en una evolución se repite: el control de
 * una misma patología, las indicaciones post quirúrgicas, la pauta de alarma
 * que hay que dejar por escrito siempre. Se vuelve a tipear cada vez, y lo que
 * se tipea de nuevo sale distinto cada vez — que en una historia clínica no es
 * solo una pérdida de tiempo.
 *
 * Una plantilla del consultorio la usa todo el equipo; una de un profesional es
 * suya. Un `profesional` solo administra las suyas, y eso lo decide el backend.
 */
import { computed, onMounted, ref } from 'vue';
import { useToast } from 'primevue/usetoast';

import Button from 'primevue/button';
import Dialog from 'primevue/dialog';
import Dropdown from 'primevue/dropdown';
import InputText from 'primevue/inputtext';
import Tag from 'primevue/tag';
import Textarea from 'primevue/textarea';

import plantillaService from '@/service/plantillaService';
import { useUserStore } from '@/stores/user';

const toast = useToast();
const userStore = useUserStore();

const CAMPOS = [
    { label: 'Evolución', value: 'evolucion' },
    { label: 'Indicaciones', value: 'indicaciones' }
];

const plantillas = ref([]);
const cargando = ref(true);
const guardando = ref(false);
const dialogoAbierto = ref(false);
const editandoId = ref(null);
const aBorrar = ref(null);
const form = ref(vacio());

const esProfesional = computed(() => userStore.rol === 'profesional');
const porCampo = computed(() => CAMPOS.map((c) => ({ ...c, lista: plantillas.value.filter((p) => p.campo === c.value) })));

function vacio() {
    return { nombre: '', cuerpo: '', campo: 'evolucion', usuario_id: null, activo: true };
}

async function cargar() {
    cargando.value = true;
    try {
        const { data } = await plantillaService.listar({ todas: true });
        plantillas.value = data || [];
    } catch {
        toast.add({ severity: 'error', summary: 'No pudimos cargar las plantillas', life: 4000 });
    } finally {
        cargando.value = false;
    }
}

function abrirNueva(campo) {
    editandoId.value = null;
    form.value = { ...vacio(), campo };
    dialogoAbierto.value = true;
}

function abrirEdicion(p) {
    editandoId.value = p.id;
    form.value = { nombre: p.nombre, cuerpo: p.cuerpo, campo: p.campo, usuario_id: p.usuario_id, activo: p.activo };
    dialogoAbierto.value = true;
}

async function guardar() {
    if (!form.value.nombre?.trim() || !form.value.cuerpo?.trim()) {
        toast.add({ severity: 'warn', summary: 'Faltan el nombre y el texto', life: 3000 });
        return;
    }
    guardando.value = true;
    try {
        if (editandoId.value) await plantillaService.actualizar(editandoId.value, form.value);
        else await plantillaService.crear(form.value);
        dialogoAbierto.value = false;
        await cargar();
        toast.add({ severity: 'success', summary: 'Plantilla guardada', life: 3000 });
    } catch (e) {
        toast.add({ severity: 'error', summary: 'No se pudo guardar', detail: e?.response?.data?.error, life: 5000 });
    } finally {
        guardando.value = false;
    }
}

async function confirmarBorrado() {
    try {
        await plantillaService.borrar(aBorrar.value.id);
        aBorrar.value = null;
        await cargar();
        toast.add({ severity: 'success', summary: 'Plantilla eliminada', life: 3000 });
    } catch {
        toast.add({ severity: 'error', summary: 'No se pudo eliminar', life: 4000 });
    }
}

onMounted(cargar);
</script>

<template>
    <div>
        <header class="mb-6">
            <h3 class="text-lg font-bold text-surface-900 dark:text-surface-0 m-0">Plantillas de texto</h3>
            <p class="text-surface-600 dark:text-surface-300 mt-2 mb-0 max-w-2xl">Lo que escribís seguido, guardado una vez. Al cargar una evolución aparecen como “Usar plantilla”, y podés editarlas antes de guardar.</p>
        </header>

        <div v-if="cargando" class="py-8 text-center text-surface-500 dark:text-surface-400"><i class="pi pi-spin pi-spinner text-2xl"></i></div>

        <div v-else class="space-y-8">
            <section v-for="grupo in porCampo" :key="grupo.value">
                <div class="flex items-center justify-between mb-3">
                    <h4 class="text-sm font-semibold uppercase tracking-wide text-surface-400 dark:text-surface-500 m-0">{{ grupo.label }}</h4>
                    <Button label="Nueva" icon="pi pi-plus" text size="small" @click="abrirNueva(grupo.value)" />
                </div>

                <p v-if="!grupo.lista.length" class="text-sm text-surface-500 dark:text-surface-400 p-4 rounded-xl border border-dashed border-surface-300 dark:border-surface-600 m-0">
                    Todavía no hay ninguna. Es opcional: sin plantillas el formulario funciona igual.
                </p>

                <div v-else class="space-y-2">
                    <div v-for="p in grupo.lista" :key="p.id" class="flex items-start gap-3 p-4 rounded-xl border border-surface-200 dark:border-surface-700">
                        <div class="flex-1 min-w-0">
                            <p class="font-semibold text-surface-900 dark:text-surface-0 m-0">
                                {{ p.nombre }}
                                <Tag v-if="!p.activo" value="Inactiva" severity="secondary" class="ml-2" />
                                <Tag v-if="!p.usuario_id" value="Del consultorio" severity="info" class="ml-2" />
                            </p>
                            <p class="text-sm text-surface-500 dark:text-surface-400 m-0 mt-1 whitespace-pre-line line-clamp-3">{{ p.cuerpo }}</p>
                        </div>
                        <div class="shrink-0">
                            <Button icon="pi pi-pencil" text rounded aria-label="Editar" @click="abrirEdicion(p)" />
                            <Button icon="pi pi-trash" text rounded severity="danger" aria-label="Eliminar" @click="aBorrar = p" />
                        </div>
                    </div>
                </div>
            </section>
        </div>

        <Dialog v-model:visible="dialogoAbierto" modal :header="editandoId ? 'Editar plantilla' : 'Nueva plantilla'" :style="{ width: '38rem' }" :breakpoints="{ '640px': '95vw' }">
            <div class="flex flex-col gap-4">
                <div>
                    <label class="block mb-2 font-medium text-surface-700 dark:text-surface-200">Nombre</label>
                    <InputText v-model="form.nombre" class="w-full" placeholder="Control de hipertensión" maxlength="120" />
                    <small class="text-surface-500 dark:text-surface-400">Es lo que vas a ver en la lista al escribir. Que se reconozca de un vistazo.</small>
                </div>

                <div>
                    <label class="block mb-2 font-medium text-surface-700 dark:text-surface-200">Campo</label>
                    <Dropdown v-model="form.campo" :options="CAMPOS" optionLabel="label" optionValue="value" class="w-full" />
                </div>

                <div>
                    <label class="block mb-2 font-medium text-surface-700 dark:text-surface-200">Texto</label>
                    <Textarea v-model="form.cuerpo" rows="8" autoResize class="w-full" placeholder="El texto que querés reutilizar…" maxlength="5000" />
                </div>

                <!-- El profesional no elige de quién es: siempre suya. -->
                <div v-if="!esProfesional">
                    <label class="block mb-2 font-medium text-surface-700 dark:text-surface-200">Disponible para</label>
                    <p class="text-sm text-surface-500 dark:text-surface-400 m-0">Todo el consultorio.</p>
                </div>
            </div>

            <template #footer>
                <Button label="Cancelar" text @click="dialogoAbierto = false" />
                <Button label="Guardar" icon="pi pi-check" :loading="guardando" @click="guardar" />
            </template>
        </Dialog>

        <Dialog :visible="!!aBorrar" modal header="Eliminar plantilla" :style="{ width: '28rem' }" :breakpoints="{ '640px': '95vw' }" @update:visible="aBorrar = null">
            <p class="m-0 text-surface-700 dark:text-surface-200">
                Se elimina <strong>{{ aBorrar?.nombre }}</strong
                >. Las evoluciones que se escribieron con ella no se tocan: lo que quedó guardado es el texto, no un enlace a la plantilla.
            </p>
            <template #footer>
                <Button label="Cancelar" text @click="aBorrar = null" />
                <Button label="Eliminar" icon="pi pi-trash" severity="danger" @click="confirmarBorrado" />
            </template>
        </Dialog>
    </div>
</template>
