<script setup>
import { onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import registroService from '@/service/registroService';

const route = useRoute();

// 'creando' | 'listo' | 'error'
const estado = ref('creando');
const url = ref('');
const error = ref('');

onMounted(async () => {
    try {
        // Esta llamada es la que crea la base. Tarda unos segundos: aplica el
        // esquema, corre las migraciones y siembra el usuario.
        const { data } = await registroService.verificar(route.params.token);

        if (data.estado === 'listo') {
            estado.value = 'listo';
            url.value = data.url;
            return;
        }

        // Si otro pedido ya lo estaba creando, se espera a que termine en vez de
        // lanzar una segunda creación.
        await esperarAQueTermine();
    } catch (e) {
        estado.value = 'error';
        error.value = e?.response?.data?.error || 'No pudimos crear tu consultorio.';
    }
});

async function esperarAQueTermine() {
    for (let intento = 0; intento < 30; intento++) {
        await new Promise((r) => setTimeout(r, 2000));
        const { data } = await registroService.estado(route.params.token);
        if (data.estado === 'listo') {
            estado.value = 'listo';
            url.value = data.url;
            return;
        }
        if (data.estado === 'fallido') break;
    }
    estado.value = 'error';
    error.value = 'La creación está demorando más de lo normal. Escribinos y lo resolvemos.';
}
</script>

<template>
    <div class="min-h-screen flex items-center justify-center p-4 bg-surface-50 dark:bg-surface-950">
        <div class="w-full max-w-md bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-2xl p-8 text-center">
            <template v-if="estado === 'creando'">
                <i class="pi pi-spin pi-spinner text-5xl text-primary-500 mb-4 block"></i>
                <h1 class="text-2xl font-bold text-surface-900 dark:text-surface-0 m-0 mb-3">Preparando tu sistema</h1>
                <p class="text-surface-600 dark:text-surface-300 leading-relaxed m-0">Estamos creando tu consultorio. Tarda unos segundos, no cierres esta pantalla.</p>
            </template>

            <template v-else-if="estado === 'listo'">
                <i class="pi pi-check-circle text-5xl text-green-500 mb-4 block"></i>
                <h1 class="text-2xl font-bold text-surface-900 dark:text-surface-0 m-0 mb-3">Tu consultorio está listo</h1>
                <p class="text-surface-600 dark:text-surface-300 leading-relaxed m-0 mb-6">Entrá con el usuario <strong>admin</strong> y la contraseña que elegiste.</p>
                <a :href="url" class="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-semibold text-white bg-primary-600 hover:bg-primary-700 transition"> <i class="pi pi-arrow-right"></i> Entrar a mi consultorio </a>
                <p class="text-xs text-surface-500 dark:text-surface-400 mt-4 mb-0">{{ url }}</p>
            </template>

            <template v-else>
                <i class="pi pi-exclamation-triangle text-5xl text-red-500 mb-4 block"></i>
                <h1 class="text-2xl font-bold text-surface-900 dark:text-surface-0 m-0 mb-3">Algo salió mal</h1>
                <p class="text-surface-600 dark:text-surface-300 leading-relaxed m-0">{{ error }}</p>
            </template>
        </div>
    </div>
</template>
