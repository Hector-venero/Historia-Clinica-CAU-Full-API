<script setup>
import { onMounted, ref } from 'vue';
import api from '@/api/axios';
import { useMarcaStore } from '@/stores/marca';
import { descargarBlob } from '@/utils/descargas';

const marca = useMarcaStore();

const descargando = ref(false);
const error = ref('');

onMounted(() => marca.cargar());

/**
 * La descarga funciona con la cuenta suspendida: es el punto entero de esta
 * pantalla. Son datos de los pacientes, no del proveedor del software.
 */
async function exportar() {
    error.value = '';
    descargando.value = true;
    try {
        const { data, headers } = await api.get('/cuenta/exportar', { responseType: 'blob' });
        const nombre = headers['content-disposition']?.match(/filename=([^;]+)/)?.[1]?.trim() || 'datos.zip';
        descargarBlob(data, nombre);
    } catch {
        error.value = 'No pudimos preparar la descarga. Probá de nuevo en un momento.';
    } finally {
        descargando.value = false;
    }
}
</script>

<template>
    <div class="min-h-screen flex items-center justify-center p-4 bg-surface-50 dark:bg-surface-950">
        <div class="w-full max-w-lg bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-2xl p-8">
            <div class="text-center mb-6">
                <i class="pi pi-pause-circle text-5xl text-amber-500 mb-4 block"></i>
                <h1 class="text-2xl font-bold text-surface-900 dark:text-surface-0 m-0 mb-2">Se pausó el acceso</h1>
                <p class="text-surface-600 dark:text-surface-300 leading-relaxed m-0">
                    Terminó el período de prueba de <strong>{{ marca.nombreCorto }}</strong
                    >.
                </p>
            </div>

            <!-- Lo primero que tiene que leer alguien que entra acá: sus datos
                 están, y se los puede llevar. -->
            <div class="bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-900 rounded-xl p-4 mb-6">
                <p class="text-sm text-green-800 dark:text-green-300 leading-relaxed m-0">
                    <i class="pi pi-check-circle mr-1"></i>
                    <strong>Tus historias clínicas están intactas.</strong> No se borró nada, y podés descargarlas ahora mismo.
                </p>
            </div>

            <button :disabled="descargando" class="w-full inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl font-semibold text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-60 transition mb-3" @click="exportar">
                <i :class="descargando ? 'pi pi-spin pi-spinner' : 'pi pi-download'"></i>
                {{ descargando ? 'Preparando el archivo…' : 'Descargar todos mis datos' }}
            </button>

            <p class="text-xs text-surface-500 dark:text-surface-400 text-center leading-relaxed mb-6">Incluye pacientes, historias, turnos y los archivos adjuntos, en planillas que se abren con Excel.</p>

            <div v-if="error" class="p-3 rounded-xl bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-300 text-sm border border-red-200 dark:border-red-900 mb-4">
                {{ error }}
            </div>

            <div class="pt-5 border-t border-surface-200 dark:border-surface-700 text-center">
                <p class="text-sm text-surface-600 dark:text-surface-300 m-0 mb-3">¿Querés seguir usándolo?</p>
                <a href="mailto:hectorvenero29hv@gmail.com" class="text-primary-600 dark:text-primary-400 font-semibold hover:underline"> Escribinos para reactivar la cuenta </a>
            </div>
        </div>
    </div>
</template>
