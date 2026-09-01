<script setup>
/**
 * Servicios (prestaciones) del consultorio.
 *
 * Hasta ahora todos los turnos de un profesional duraban lo mismo y el "de qué
 * es" iba en un texto libre. Acá se define el catálogo: una primera consulta de
 * 40 minutos y un control de 15 dejan de tener que durar igual.
 *
 * **Es opcional.** Sin ningún servicio cargado, el consultorio agenda como
 * siempre — por eso la pantalla vacía explica qué son en vez de mostrar una
 * tabla vacía y dejar a la persona adivinando si le falta configurar algo.
 *
 * Un servicio puede ser del consultorio entero o de un profesional. Un
 * `profesional` solo administra los suyos, y eso lo decide el backend: acá el
 * selector directamente no se muestra, que es presentación, no permiso.
 */
import { computed, onMounted, ref } from 'vue';
import { useToast } from 'primevue/usetoast';

import Button from 'primevue/button';
import Column from 'primevue/column';
import DataTable from 'primevue/datatable';
import Dialog from 'primevue/dialog';
import Dropdown from 'primevue/dropdown';
import InputNumber from 'primevue/inputnumber';
import InputText from 'primevue/inputtext';
import Tag from 'primevue/tag';
import InputSwitch from 'primevue/inputswitch';

import servicioService from '@/service/servicioService';
import usuarioService from '@/service/usuarioService';
import { useUserStore } from '@/stores/user';

const toast = useToast();
const userStore = useUserStore();

const servicios = ref([]);
const profesionales = ref([]);
const cargando = ref(true);
const guardando = ref(false);

const dialogoAbierto = ref(false);
const editandoId = ref(null);
const form = ref(vacio());

const esProfesional = computed(() => userStore.rol === 'profesional');

// El profesional no elige de quién es: siempre suyo. La lista solo hace falta
// para quien administra el consultorio.
const opcionesProfesional = computed(() => [{ label: 'Todo el consultorio', value: null }, ...profesionales.value.map((p) => ({ label: [p.nombre, p.apellido].filter(Boolean).join(' '), value: p.id }))]);

function vacio() {
    return {
        nombre: '',
        descripcion: '',
        duracion_minutos: 30,
        precio: null,
        usuario_id: null,
        activo: true
    };
}

async function cargar() {
    cargando.value = true;
    try {
        const { data } = await servicioService.listar();
        servicios.value = data;
    } catch {
        toast.add({ severity: 'error', summary: 'No pudimos cargar los servicios', life: 4000 });
    } finally {
        cargando.value = false;
    }
}

async function cargarProfesionales() {
    if (esProfesional.value) return;
    try {
        const { data } = await usuarioService.getUsuarios();
        const filas = Array.isArray(data) ? data : data?.usuarios || [];
        profesionales.value = filas.filter((u) => ['profesional', 'director'].includes((u.rol || '').toLowerCase()));
    } catch {
        // Sin la lista, el servicio queda como del consultorio entero. Es un
        // valor razonable: no vale cortar la pantalla por esto.
    }
}

function abrirNuevo() {
    editandoId.value = null;
    form.value = vacio();
    dialogoAbierto.value = true;
}

function abrirEdicion(servicio) {
    editandoId.value = servicio.id;
    form.value = {
        nombre: servicio.nombre,
        descripcion: servicio.descripcion || '',
        duracion_minutos: servicio.duracion_minutos,
        precio: servicio.precio,
        usuario_id: servicio.usuario_id,
        activo: servicio.activo
    };
    dialogoAbierto.value = true;
}

async function guardar() {
    if (!form.value.nombre?.trim()) {
        toast.add({ severity: 'warn', summary: 'Falta el nombre del servicio', life: 3000 });
        return;
    }
    guardando.value = true;
    try {
        if (editandoId.value) {
            await servicioService.actualizar(editandoId.value, form.value);
        } else {
            await servicioService.crear(form.value);
        }
        dialogoAbierto.value = false;
        await cargar();
        toast.add({ severity: 'success', summary: 'Servicio guardado', life: 3000 });
    } catch (e) {
        toast.add({
            severity: 'error',
            summary: 'No se pudo guardar',
            detail: e?.response?.data?.error,
            life: 5000
        });
    } finally {
        guardando.value = false;
    }
}

// La confirmacion es un Dialog propio y no `useConfirm`: la app no monta
// <ConfirmDialog> en ningun lado, asi que confirm.require() no dibujaria nada y
// la baja pasaria sin preguntar.
const aDarDeBaja = ref(null);

function pedirBaja(servicio) {
    aDarDeBaja.value = servicio;
}

async function confirmarBaja() {
    const servicio = aDarDeBaja.value;
    if (!servicio) return;
    try {
        await servicioService.darDeBaja(servicio.id);
        aDarDeBaja.value = null;
        await cargar();
        toast.add({ severity: 'success', summary: 'Servicio dado de baja', life: 3000 });
    } catch {
        toast.add({ severity: 'error', summary: 'No se pudo dar de baja', life: 4000 });
    }
}

function precioTexto(valor) {
    if (valor === null || valor === undefined) return '—';
    return valor.toLocaleString('es-AR', { style: 'currency', currency: 'ARS', maximumFractionDigits: 0 });
}

onMounted(() => {
    cargar();
    cargarProfesionales();
});
</script>

<template>
    <div class="card">
        <div class="flex flex-wrap items-start justify-between gap-4 mb-6">
            <div>
                <h2 class="text-2xl font-bold text-surface-900 dark:text-surface-0 m-0">Servicios</h2>
                <p class="text-surface-600 dark:text-surface-300 mt-2 mb-0 max-w-2xl">Las prestaciones que ofrece el consultorio, cada una con su duración. Al agendar, el turno toma la duración del servicio elegido.</p>
            </div>
            <Button label="Nuevo servicio" icon="pi pi-plus" @click="abrirNuevo" />
        </div>

        <!-- La pantalla vacía explica qué son. Una tabla vacía deja a la persona
             sin saber si le falta configurar algo o si esto no le sirve. -->
        <div v-if="!cargando && !servicios.length" class="text-center py-12 px-6 rounded-2xl border border-dashed border-surface-300 dark:border-surface-700">
            <i class="pi pi-list text-4xl text-surface-400 dark:text-surface-500"></i>
            <p class="mt-4 font-semibold text-surface-800 dark:text-surface-100">Todavía no hay servicios cargados</p>
            <p class="mt-2 text-surface-600 dark:text-surface-300 max-w-xl mx-auto">
                No hacen falta para trabajar: sin servicios, todos los turnos duran lo que diga la configuración del profesional. Cargalos si querés que una primera consulta y un control tengan duraciones distintas, o si querés publicar precios en la
                reserva online.
            </p>
            <Button class="mt-5" label="Cargar el primero" icon="pi pi-plus" outlined @click="abrirNuevo" />
        </div>

        <DataTable v-else :value="servicios" :loading="cargando" dataKey="id" responsiveLayout="scroll" class="p-datatable-sm">
            <Column field="nombre" header="Servicio">
                <template #body="{ data }">
                    <div class="font-semibold text-surface-900 dark:text-surface-0">{{ data.nombre }}</div>
                    <div v-if="data.descripcion" class="text-sm text-surface-500 dark:text-surface-400">{{ data.descripcion }}</div>
                </template>
            </Column>
            <Column header="Quién lo da">
                <template #body="{ data }">
                    <span v-if="data.usuario_id">{{ data.profesional }}</span>
                    <span v-else class="text-surface-500 dark:text-surface-400">Todo el consultorio</span>
                </template>
            </Column>
            <Column header="Duración">
                <template #body="{ data }">{{ data.duracion_minutos }} min</template>
            </Column>
            <Column header="Precio">
                <template #body="{ data }">{{ precioTexto(data.precio) }}</template>
            </Column>
            <Column header="Estado">
                <template #body="{ data }">
                    <Tag :value="data.activo ? 'Activo' : 'De baja'" :severity="data.activo ? 'success' : 'secondary'" />
                </template>
            </Column>
            <Column style="width: 8rem">
                <template #body="{ data }">
                    <Button icon="pi pi-pencil" text rounded aria-label="Editar" @click="abrirEdicion(data)" />
                    <Button v-if="data.activo" icon="pi pi-times" text rounded severity="danger" aria-label="Dar de baja" @click="pedirBaja(data)" />
                </template>
            </Column>
        </DataTable>

        <Dialog v-model:visible="dialogoAbierto" modal :header="editandoId ? 'Editar servicio' : 'Nuevo servicio'" :style="{ width: '32rem' }" :breakpoints="{ '640px': '95vw' }">
            <div class="flex flex-col gap-4">
                <div>
                    <label class="block mb-2 font-medium text-surface-700 dark:text-surface-200">Nombre</label>
                    <InputText v-model="form.nombre" class="w-full" placeholder="Primera consulta" maxlength="120" />
                </div>

                <div>
                    <label class="block mb-2 font-medium text-surface-700 dark:text-surface-200">Descripción <span class="font-normal text-surface-500">(opcional)</span></label>
                    <InputText v-model="form.descripcion" class="w-full" placeholder="Incluye historia clínica y examen físico" maxlength="255" />
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                        <label class="block mb-2 font-medium text-surface-700 dark:text-surface-200">Duración</label>
                        <InputNumber v-model="form.duracion_minutos" class="w-full" suffix=" min" :min="5" :max="480" :step="5" showButtons />
                    </div>
                    <div>
                        <label class="block mb-2 font-medium text-surface-700 dark:text-surface-200">Precio <span class="font-normal text-surface-500">(opcional)</span></label>
                        <InputNumber v-model="form.precio" class="w-full" mode="currency" currency="ARS" locale="es-AR" :maxFractionDigits="0" placeholder="Sin precio" />
                    </div>
                </div>

                <div v-if="!esProfesional">
                    <label class="block mb-2 font-medium text-surface-700 dark:text-surface-200">Quién lo da</label>
                    <Dropdown v-model="form.usuario_id" :options="opcionesProfesional" optionLabel="label" optionValue="value" class="w-full" />
                    <small class="text-surface-500 dark:text-surface-400">"Todo el consultorio" lo deja disponible para cualquier profesional.</small>
                </div>

                <div class="flex items-center gap-3">
                    <InputSwitch v-model="form.activo" inputId="servicio-activo" />
                    <label for="servicio-activo" class="text-surface-700 dark:text-surface-200">Se puede elegir al agendar</label>
                </div>
            </div>

            <template #footer>
                <Button label="Cancelar" text @click="dialogoAbierto = false" />
                <Button label="Guardar" icon="pi pi-check" :loading="guardando" @click="guardar" />
            </template>
        </Dialog>

        <Dialog :visible="!!aDarDeBaja" modal header="Dar de baja" :style="{ width: '28rem' }" :breakpoints="{ '640px': '95vw' }" @update:visible="aDarDeBaja = null">
            <p class="m-0 text-surface-700 dark:text-surface-200">
                <strong>{{ aDarDeBaja?.nombre }}</strong> deja de ofrecerse al agendar. Los turnos que ya se dieron con este servicio no se tocan.
            </p>
            <template #footer>
                <Button label="Cancelar" text @click="aDarDeBaja = null" />
                <Button label="Dar de baja" icon="pi pi-times" severity="danger" @click="confirmarBaja" />
            </template>
        </Dialog>
    </div>
</template>
