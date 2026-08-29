<script setup>
import { computed, ref } from 'vue';
import portalService from '@/service/portalService';
import logo from '@/assets/logo-ficha-salud.svg';

const email = ref('');
const enviando = ref(false);
const enviado = ref(false);

const puedeEnviar = computed(() => email.value.trim() && !enviando.value);

async function enviar() {
    enviando.value = true;
    try {
        await portalService.recuperar(email.value.trim());
    } catch {
        // El backend responde lo mismo exista o no la cuenta, así que un error
        // acá es de red. Igual se muestra la confirmación: decir "ese correo no
        // existe" delataría quién es paciente de la plataforma.
    } finally {
        enviando.value = false;
        enviado.value = true;
    }
}
</script>

<template>
    <div class="min-h-screen flex items-center justify-center p-4 bg-surface-50 dark:bg-surface-950">
        <div class="w-full max-w-md bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-2xl p-6 md:p-8">
            <div v-if="enviado" class="text-center">
                <i class="pi pi-envelope text-5xl text-primary-500 mb-4 block"></i>
                <h1 class="text-2xl font-bold text-surface-900 dark:text-surface-0 m-0 mb-3">Revisá tu correo</h1>
                <p class="text-surface-600 dark:text-surface-300 leading-relaxed m-0 mb-2">
                    Si <strong>{{ email }}</strong> tiene una cuenta, te mandamos el enlace para elegir una contraseña nueva.
                </p>
                <p class="text-sm text-surface-500 dark:text-surface-400 m-0 mb-6">El enlace vence en una hora.</p>
                <router-link to="/portal/login" class="text-primary-600 dark:text-primary-400 font-semibold hover:underline">Volver</router-link>
            </div>

            <div v-else>
                <header class="text-center mb-6">
                    <img :src="logo" alt="Ficha Salud" class="h-12 w-12 mx-auto mb-3" />
                    <h1 class="text-2xl font-bold text-surface-900 dark:text-surface-0 m-0">¿Olvidaste tu contraseña?</h1>
                    <p class="text-sm text-surface-500 dark:text-surface-400 mt-2 mb-0">Te mandamos un enlace para elegir una nueva.</p>
                </header>

                <form class="space-y-4" @submit.prevent="enviar">
                    <div class="flex flex-col gap-2">
                        <label class="text-sm font-semibold text-surface-700 dark:text-surface-200">Tu correo</label>
                        <input v-model="email" type="email" placeholder="vos@ejemplo.com" class="campo" autocomplete="username" />
                    </div>

                    <button type="submit" :disabled="!puedeEnviar" class="w-full inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl font-semibold text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-60 transition">
                        <i :class="enviando ? 'pi pi-spin pi-spinner' : 'pi pi-send'"></i>
                        {{ enviando ? 'Enviando…' : 'Mandarme el enlace' }}
                    </button>

                    <p class="text-center text-sm text-surface-500 dark:text-surface-400 m-0">
                        <router-link to="/portal/login" class="text-primary-600 dark:text-primary-400 font-semibold hover:underline">Volver a entrar</router-link>
                    </p>
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
