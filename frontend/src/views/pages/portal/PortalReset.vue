<script setup>
import { computed, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import portalService from '@/service/portalService';
import logo from '@/assets/logo-ficha-salud.svg';

const route = useRoute();
const router = useRouter();

const password = ref('');
const repetida = ref('');
const guardando = ref(false);
const listo = ref(false);
const error = ref('');

const coinciden = computed(() => !repetida.value || password.value === repetida.value);
const puedeGuardar = computed(() => password.value.length >= 8 && coinciden.value && repetida.value && !guardando.value);

async function guardar() {
    error.value = '';
    guardando.value = true;
    try {
        await portalService.resetear(route.params.token, password.value, repetida.value);
        listo.value = true;
        setTimeout(() => router.replace('/portal/login'), 2000);
    } catch (e) {
        error.value = e?.response?.data?.error || 'No pudimos cambiar tu contraseña.';
    } finally {
        guardando.value = false;
    }
}
</script>

<template>
    <div class="min-h-screen flex items-center justify-center p-4 bg-surface-50 dark:bg-surface-950">
        <div class="w-full max-w-md bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-2xl p-6 md:p-8">
            <div v-if="listo" class="text-center">
                <i class="pi pi-check-circle text-5xl text-green-500 mb-4 block"></i>
                <h1 class="text-2xl font-bold text-surface-900 dark:text-surface-0 m-0 mb-2">Listo</h1>
                <p class="text-surface-600 dark:text-surface-300 m-0">Ya podés entrar con tu contraseña nueva.</p>
            </div>

            <div v-else>
                <header class="text-center mb-6">
                    <img :src="logo" alt="Ficha Salud" class="h-12 w-12 mx-auto mb-3" />
                    <h1 class="text-2xl font-bold text-surface-900 dark:text-surface-0 m-0">Elegí una contraseña nueva</h1>
                </header>

                <form class="space-y-4" @submit.prevent="guardar">
                    <div class="flex flex-col gap-2">
                        <label class="text-sm font-semibold text-surface-700 dark:text-surface-200">Contraseña</label>
                        <input v-model="password" type="password" class="campo" autocomplete="new-password" />
                        <small class="text-surface-500 dark:text-surface-400">Mínimo 8 caracteres, con mayúscula, minúscula, número y símbolo.</small>
                    </div>

                    <div class="flex flex-col gap-2">
                        <label class="text-sm font-semibold text-surface-700 dark:text-surface-200">Repetila</label>
                        <input v-model="repetida" type="password" class="campo" autocomplete="new-password" />
                        <!-- Se avisa mientras escribe, no al enviar: descubrir que
                             no coinciden después de mandar obliga a reescribir las dos. -->
                        <small v-if="!coinciden" class="text-red-600 dark:text-red-400">No coinciden.</small>
                    </div>

                    <div v-if="error" class="p-3 rounded-xl bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-300 text-sm border border-red-200 dark:border-red-900">
                        {{ error }}
                    </div>

                    <button type="submit" :disabled="!puedeGuardar" class="w-full inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl font-semibold text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-60 transition">
                        <i :class="guardando ? 'pi pi-spin pi-spinner' : 'pi pi-check'"></i>
                        {{ guardando ? 'Guardando…' : 'Guardar' }}
                    </button>
                </form>
            </div>
        </div>
    </div>
</template>

<style scoped>
.campo {
    @apply w-full px-4 py-2.5 rounded-xl border border-surface-300 dark:border-surface-600 bg-surface-0 dark:bg-surface-800 text-surface-900 dark:text-surface-0 outline-none transition;
}
.campo:focus {
    @apply border-primary-500 ring-2 ring-primary-500/20;
}
</style>
