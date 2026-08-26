<script setup>
import { ref, computed, onMounted } from 'vue';
import { useUserStore } from '@/stores/user';
import comunicadoService from '@/service/comunicadoService';

import Button from 'primevue/button';
import Card from 'primevue/card';
import InputText from 'primevue/inputtext';
import Textarea from 'primevue/textarea';
import Toast from 'primevue/toast';
import { useToast } from 'primevue/usetoast';
import { emit } from '@/utils/eventBus';

const toast = useToast();
const userStore = useUserStore();

const loading = ref(true);
const guardando = ref(false);
const comunicados = ref([]);
const form = ref({ titulo: '', contenido: '', prioridad: 'normal' });

// Un `importante` ademas manda un mail a todo el equipo, asi que conviene que
// al publicar quede claro cual de los dos se esta eligiendo.
const PRIORIDADES = [
    { valor: 'normal', etiqueta: 'Normal', ayuda: 'Aparece en la campana' },
    { valor: 'importante', etiqueta: 'Importante', ayuda: 'Campana y mail a todo el equipo' }
];

const puedePublicar = computed(() => {
    const rol = (userStore.rol || '').toLowerCase().trim();
    return rol === 'director' || rol === 'administrativo';
});

function formatearFecha(value) {
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return value || '';
    return d.toLocaleString('es-AR', { dateStyle: 'medium', timeStyle: 'short' });
}

async function cargarComunicados() {
    loading.value = true;
    try {
        const res = await comunicadoService.listar();
        comunicados.value = res.data || [];
    } catch (err) {
        console.error('Error cargando comunicados:', err);
        toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudieron cargar los comunicados.', life: 4000 });
    } finally {
        loading.value = false;
    }
}

async function publicarComunicado() {
    if (!puedePublicar.value) return;
    const titulo = (form.value.titulo || '').trim();
    const contenido = (form.value.contenido || '').trim();

    if (!titulo || !contenido) {
        toast.add({ severity: 'warn', summary: 'Campos incompletos', detail: 'Ingrese titulo y contenido.', life: 3500 });
        return;
    }

    guardando.value = true;
    try {
        const { data } = await comunicadoService.crear({ titulo, contenido, prioridad: form.value.prioridad });
        form.value = { titulo: '', contenido: '', prioridad: 'normal' };

        // Se informa a cuantos se les mando el mail: publicar un importante
        // notifica a todo el equipo y conviene que quede a la vista.
        const detail = data?.avisados ? `Publicado. Se avisó por mail a ${data.avisados} persona(s).` : 'Comunicado publicado correctamente.';
        toast.add({ severity: 'success', summary: 'Publicado', detail, life: 4000 });

        emit('comunicados:actualizados');
        await cargarComunicados();
    } catch (err) {
        console.error('Error publicando comunicado:', err);
        const detail = err?.response?.data?.error || 'No se pudo publicar el comunicado.';
        toast.add({ severity: 'error', summary: 'Error', detail, life: 4200 });
    } finally {
        guardando.value = false;
    }
}

async function eliminarComunicado(comunicado) {
    if (!comunicado?.id) return;
    if (!confirm('Eliminar este comunicado?')) return;

    try {
        await comunicadoService.eliminar(comunicado.id);
        toast.add({ severity: 'success', summary: 'Eliminado', detail: 'Comunicado eliminado.', life: 2800 });
        await cargarComunicados();
    } catch (err) {
        console.error('Error eliminando comunicado:', err);
        const detail = err?.response?.data?.error || 'No se pudo eliminar el comunicado.';
        toast.add({ severity: 'error', summary: 'Error', detail, life: 4200 });
    }
}

onMounted(async () => {
    await cargarComunicados();

    // Entrar a la pantalla cuenta como haberlos leido: quedan todos a la vista.
    // Se hace despues de cargar para que el resaltado de no leidos alcance a
    // verse en esta visita y no desaparezca antes de que la persona los mire.
    if (comunicados.value.some((c) => !c.leido)) {
        try {
            await comunicadoService.marcarTodosLeidos();
            emit('comunicados:actualizados');
        } catch (err) {
            console.error('No se pudieron marcar como leidos:', err);
        }
    }
});
</script>

<template>
    <div class="p-6 md:p-8 max-w-5xl mx-auto space-y-6">
        <Toast />

        <div>
            <h1 class="text-3xl font-bold text-gray-800 dark:text-white">Comunicados</h1>
            <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">Avisos institucionales para todo el equipo.</p>
        </div>

        <Card v-if="puedePublicar" class="border border-cyan-100 dark:border-slate-700">
            <template #title>Nuevo comunicado</template>
            <template #content>
                <div class="space-y-3">
                    <InputText v-model="form.titulo" class="w-full" placeholder="Titulo" />
                    <Textarea v-model="form.contenido" rows="5" class="w-full" placeholder="Escriba el comunicado" autoResize />

                    <div class="flex flex-wrap gap-2">
                        <label
                            v-for="p in PRIORIDADES"
                            :key="p.valor"
                            :class="[
                                'flex-1 min-w-[180px] cursor-pointer rounded-lg border p-3 transition',
                                form.prioridad === p.valor ? 'border-primary-500 bg-primary-50 dark:bg-slate-800' : 'border-gray-200 dark:border-slate-700 hover:border-gray-300'
                            ]"
                        >
                            <input v-model="form.prioridad" type="radio" :value="p.valor" class="sr-only" />
                            <span class="block text-sm font-semibold text-gray-800 dark:text-gray-100">
                                <i :class="['pi mr-1', p.valor === 'importante' ? 'pi-exclamation-circle text-amber-500' : 'pi-bell text-gray-400']"></i>
                                {{ p.etiqueta }}
                            </span>
                            <span class="block text-xs text-gray-500 mt-0.5">{{ p.ayuda }}</span>
                        </label>
                    </div>

                    <div class="flex justify-end">
                        <Button label="Publicar" icon="pi pi-send" :loading="guardando" @click="publicarComunicado" />
                    </div>
                </div>
            </template>
        </Card>

        <div v-if="loading" class="text-sm text-gray-500">Cargando comunicados...</div>

        <div v-else-if="comunicados.length === 0" class="text-sm text-gray-500 dark:text-gray-400 bg-white dark:bg-slate-900 border border-dashed border-gray-300 dark:border-slate-700 rounded-xl p-6 text-center">
            No hay comunicados publicados por el momento.
        </div>

        <div v-else class="space-y-4">
            <Card
                v-for="c in comunicados"
                :key="c.id"
                :class="[
                    'border',
                    // El borde ambar distingue los importantes de un vistazo, sin
                    // depender de leer la etiqueta.
                    c.prioridad === 'importante' ? 'border-amber-300 dark:border-amber-700' : 'border-gray-100 dark:border-slate-700'
                ]"
            >
                <template #title>
                    <div class="flex items-start justify-between gap-3">
                        <div>
                            <div class="flex items-center gap-2 flex-wrap">
                                <span v-if="!c.leido" class="w-2 h-2 rounded-full bg-primary-500 shrink-0" title="Sin leer"></span>
                                <h2 class="text-lg font-semibold text-gray-800 dark:text-gray-100">{{ c.titulo }}</h2>
                                <span v-if="c.prioridad === 'importante'" class="text-[11px] font-bold tracking-wide uppercase px-2 py-0.5 rounded bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200"> Importante </span>
                            </div>
                            <p class="text-xs text-gray-500 mt-1">{{ c.autor_nombre }} ({{ c.autor_rol }}) - {{ formatearFecha(c.creado_en) }}</p>
                        </div>
                        <Button v-if="c.puede_eliminar" icon="pi pi-trash" text severity="danger" @click="eliminarComunicado(c)" />
                    </div>
                </template>
                <template #content>
                    <p class="whitespace-pre-line text-sm text-gray-700 dark:text-gray-200">{{ c.contenido }}</p>
                </template>
            </Card>
        </div>
    </div>
</template>
