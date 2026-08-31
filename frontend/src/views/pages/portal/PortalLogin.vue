<script setup>
import { computed, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { usePacienteStore } from '@/stores/paciente';
import logo from '@/assets/logo-ficha-salud.svg';

const route = useRoute();
const router = useRouter();
const paciente = usePacienteStore();

/**
 * A dónde volver después de entrar.
 *
 * Quien eligió un horario sin cuenta va a la pantalla de registro, pero si ya
 * tenía cuenta hace clic en "Iniciá sesión" — y hasta ahora eso lo dejaba en el
 * buzón, con el turno elegido abandonado en sessionStorage y sin ninguna señal
 * de que había quedado algo a medias.
 *
 * Solo se aceptan rutas internas del portal: `volver` viene de la URL, y
 * redirigir a cualquier cosa que llegue por ahí es un redirect abierto —
 * alguien manda un enlace de Ficha Salud que termina en otro sitio.
 */
const destino = computed(() => {
    const pedido = String(route.query.volver || sessionStorage.getItem('ficha-salud:volver') || '');
    return pedido.startsWith('/portal/') ? pedido : '/portal';
});

const email = ref('');
const password = ref('');
const entrando = ref(false);
const error = ref('');

const puedeEntrar = computed(() => email.value.trim() && password.value && !entrando.value);

async function entrar() {
    error.value = '';
    entrando.value = true;
    try {
        await paciente.login(email.value.trim(), password.value);
        sessionStorage.removeItem('ficha-salud:volver');
        router.replace(destino.value);
    } catch (e) {
        // El backend devuelve el mismo mensaje para "no existe" y "clave
        // incorrecta": distinguirlos deja averiguar qué correos están
        // registrados. Acá se muestra tal cual.
        error.value = e?.response?.data?.error || 'No pudimos iniciar sesión.';
    } finally {
        entrando.value = false;
    }
}
</script>

<template>
    <div class="min-h-screen flex items-center justify-center p-4 bg-surface-50 dark:bg-surface-950">
        <div class="w-full max-w-md bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-2xl p-6 md:p-8">
            <header class="text-center mb-6">
                <img :src="logo" alt="Ficha Salud" class="h-12 w-12 mx-auto mb-3" />
                <h1 class="text-2xl font-bold text-surface-900 dark:text-surface-0 m-0">Ficha Salud</h1>
                <p class="text-sm text-surface-500 dark:text-surface-400 mt-1 mb-0">Tus estudios y recetas, en un solo lugar.</p>
            </header>

            <form class="space-y-4" @submit.prevent="entrar">
                <div class="flex flex-col gap-2">
                    <label class="text-sm font-semibold text-surface-700 dark:text-surface-200">Correo</label>
                    <input v-model="email" type="email" placeholder="vos@ejemplo.com" class="campo" autocomplete="username" />
                </div>

                <div class="flex flex-col gap-2">
                    <label class="text-sm font-semibold text-surface-700 dark:text-surface-200">Contraseña</label>
                    <input v-model="password" type="password" class="campo" autocomplete="current-password" />
                </div>

                <div v-if="error" class="p-3 rounded-xl bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-300 text-sm border border-red-200 dark:border-red-900">
                    {{ error }}
                </div>

                <button
                    type="submit"
                    :disabled="!puedeEntrar"
                    class="w-full inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl font-semibold text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-60 disabled:cursor-not-allowed transition"
                >
                    <i :class="entrando ? 'pi pi-spin pi-spinner' : 'pi pi-sign-in'"></i>
                    {{ entrando ? 'Entrando…' : 'Entrar' }}
                </button>

                <p class="text-center text-sm m-0">
                    <router-link to="/portal/recuperar" class="text-surface-500 dark:text-surface-400 hover:underline">¿Olvidaste tu contraseña?</router-link>
                </p>

                <p class="text-center text-sm text-surface-500 dark:text-surface-400 m-0">
                    ¿No tenés cuenta?
                    <router-link to="/portal/registro" class="text-primary-600 dark:text-primary-400 font-semibold hover:underline">Creá una</router-link>
                </p>
            </form>
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
