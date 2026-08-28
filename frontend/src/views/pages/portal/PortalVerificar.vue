<script setup>
import { onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import portalService from '@/service/portalService';
import { usePacienteStore } from '@/stores/paciente';
import logo from '@/assets/logo-ficha-salud.svg';

const route = useRoute();
const router = useRouter();
const paciente = usePacienteStore();

// 'verificando' | 'listo' | 'error'
const estado = ref('verificando');
const error = ref('');

onMounted(async () => {
    try {
        // Esta llamada crea la cuenta e inicia sesión en un solo paso: quien
        // acaba de demostrar que tiene la casilla no tiene por qué escribir la
        // contraseña que eligió hace un minuto.
        const { data } = await portalService.verificar(route.params.token);
        paciente.setPaciente(data.paciente);
        estado.value = 'listo';

        // Si venía de elegir un horario, se lo devuelve ahí para que confirme
        // en vez de dejarlo en el buzón sin entender qué pasó con su turno.
        const volver = sessionStorage.getItem('ficha-salud:volver');
        sessionStorage.removeItem('ficha-salud:volver');
        setTimeout(() => router.replace(volver || '/portal'), 1500);
    } catch (e) {
        estado.value = 'error';
        error.value = e?.response?.data?.error || 'No pudimos activar tu cuenta.';
    }
});
</script>

<template>
    <div class="min-h-screen flex items-center justify-center p-4 bg-surface-50 dark:bg-surface-950">
        <div class="w-full max-w-md bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-2xl p-8 text-center">
            <img :src="logo" alt="Ficha Salud" class="h-12 w-12 mx-auto mb-4" />

            <template v-if="estado === 'verificando'">
                <i class="pi pi-spin pi-spinner text-4xl text-primary-500 mb-4 block"></i>
                <h1 class="text-xl font-bold text-surface-900 dark:text-surface-0 m-0">Activando tu cuenta…</h1>
            </template>

            <template v-else-if="estado === 'listo'">
                <i class="pi pi-check-circle text-5xl text-green-500 mb-4 block"></i>
                <h1 class="text-2xl font-bold text-surface-900 dark:text-surface-0 m-0 mb-2">¡Listo, {{ paciente.nombre }}!</h1>
                <p class="text-surface-600 dark:text-surface-300 leading-relaxed m-0">Te llevamos a tus documentos.</p>
            </template>

            <template v-else>
                <i class="pi pi-exclamation-triangle text-5xl text-red-500 mb-4 block"></i>
                <h1 class="text-xl font-bold text-surface-900 dark:text-surface-0 m-0 mb-3">No pudimos activarla</h1>
                <p class="text-surface-600 dark:text-surface-300 leading-relaxed m-0 mb-5">{{ error }}</p>
                <router-link to="/portal/registro" class="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-white bg-primary-600 hover:bg-primary-700 transition"> Registrarme de nuevo </router-link>
            </template>
        </div>
    </div>
</template>
