<script setup>
import { computed, ref } from 'vue';
import { useRoute } from 'vue-router';
import portalService from '@/service/portalService';
import logo from '@/assets/logo-ficha-salud.svg';
import { PUBLICADO as LEGALES_PUBLICADOS, VERSION as TERMINOS_VERSION } from '@/views/pages/publico/legales';

const route = useRoute();

// A dónde volver después de verificar el correo. Lo pone la pantalla de reserva
// cuando alguien eligió horario sin tener cuenta.
if (route.query.volver) {
    sessionStorage.setItem('ficha-salud:volver', String(route.query.volver));
}

const form = ref({
    nombre: '',
    apellido: '',
    tipo_documento: 'DNI',
    numero_documento: '',
    email: '',
    password: '',
    telefono: ''
});

const TIPOS = ['DNI', 'CI', 'LC', 'LE', 'PASAPORTE'];

// Consentimiento. `TERMINOS_VERSION` viaja al servidor junto con la aceptacion:
// sin saber QUE version acepto cada uno, el dato no sirve el dia que el texto
// cambie. Con los textos sin publicar arranca en true, porque todavia no hay
// nada que aceptar.
const aceptaTerminos = ref(!LEGALES_PUBLICADOS);

const enviando = ref(false);
const enviado = ref(false);
const error = ref('');

const puedeEnviar = computed(() => form.value.nombre.trim() && form.value.apellido.trim() && form.value.numero_documento.trim() && form.value.email.trim() && form.value.password.length >= 8 && aceptaTerminos.value && !enviando.value);

async function enviar() {
    error.value = '';
    enviando.value = true;
    try {
        await portalService.registrar({ ...form.value, terminos_version: TERMINOS_VERSION });
        enviado.value = true;
    } catch (e) {
        error.value = e?.response?.data?.error || 'No pudimos completar el registro. Probá de nuevo.';
    } finally {
        enviando.value = false;
    }
}
</script>

<template>
    <div class="min-h-screen flex items-center justify-center p-4 bg-surface-50 dark:bg-surface-950">
        <div class="w-full max-w-lg">
            <div v-if="enviado" class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-2xl p-8 text-center">
                <i class="pi pi-envelope text-5xl text-primary-500 mb-4 block"></i>
                <h1 class="text-2xl font-bold text-surface-900 dark:text-surface-0 m-0 mb-3">Revisá tu correo</h1>
                <p class="text-surface-600 dark:text-surface-300 leading-relaxed m-0 mb-2">
                    Te mandamos un mensaje a <strong>{{ form.email }}</strong
                    >.
                </p>
                <p class="text-sm text-surface-500 dark:text-surface-400 leading-relaxed m-0">Cuando lo abras, tu cuenta queda activa. El enlace vence en 48 horas.</p>
            </div>

            <div v-else class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-2xl p-6 md:p-8">
                <header class="text-center mb-6">
                    <img :src="logo" alt="Ficha Salud" class="h-12 w-12 mx-auto mb-3" />
                    <h1 class="text-2xl font-bold text-surface-900 dark:text-surface-0 m-0">Creá tu cuenta</h1>
                    <p class="text-sm text-surface-500 dark:text-surface-400 mt-1 mb-0">Para ver tus estudios y recetas en un solo lugar.</p>
                </header>

                <form class="space-y-4" autocomplete="off" @submit.prevent="enviar">
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div class="flex flex-col gap-2">
                            <label class="text-sm font-semibold text-surface-700 dark:text-surface-200">Nombre</label>
                            <input v-model="form.nombre" type="text" class="campo" />
                        </div>
                        <div class="flex flex-col gap-2">
                            <label class="text-sm font-semibold text-surface-700 dark:text-surface-200">Apellido</label>
                            <input v-model="form.apellido" type="text" class="campo" />
                        </div>
                    </div>

                    <div class="grid grid-cols-3 gap-3">
                        <div class="flex flex-col gap-2">
                            <label class="text-sm font-semibold text-surface-700 dark:text-surface-200">Tipo</label>
                            <select v-model="form.tipo_documento" class="campo">
                                <option v-for="t in TIPOS" :key="t" :value="t">{{ t }}</option>
                            </select>
                        </div>
                        <div class="col-span-2 flex flex-col gap-2">
                            <label class="text-sm font-semibold text-surface-700 dark:text-surface-200">Número de documento</label>
                            <input v-model="form.numero_documento" type="text" placeholder="30111222" class="campo" />
                        </div>
                    </div>
                    <!-- Es la clave del modelo, y el paciente no tiene por qué
                         saberlo. Se le explica en una línea. -->
                    <small class="block text-surface-500 dark:text-surface-400 -mt-2"> Es con este número que tus profesionales te envían los documentos. Podés escribirlo con o sin puntos. </small>

                    <div class="flex flex-col gap-2">
                        <label class="text-sm font-semibold text-surface-700 dark:text-surface-200">Correo</label>
                        <input v-model="form.email" type="email" placeholder="vos@ejemplo.com" class="campo" autocomplete="off" />
                    </div>

                    <div class="flex flex-col gap-2">
                        <label class="text-sm font-semibold text-surface-700 dark:text-surface-200">Contraseña</label>
                        <input v-model="form.password" type="password" class="campo" autocomplete="new-password" />
                        <small class="text-surface-500 dark:text-surface-400">Mínimo 8 caracteres, con mayúscula, minúscula, número y símbolo.</small>
                    </div>

                    <div class="flex flex-col gap-2">
                        <label class="text-sm font-semibold text-surface-700 dark:text-surface-200">Teléfono <span class="font-normal text-surface-400">(opcional)</span></label>
                        <input v-model="form.telefono" type="tel" placeholder="11 2345-6789" class="campo" />
                    </div>

                    <!-- Consentimiento. Solo aparece con los textos publicados:
                         pedir que alguien acepte un borrador no consiente nada.
                         La validacion que cuenta esta en el servidor. -->
                    <label v-if="LEGALES_PUBLICADOS" class="flex items-start gap-3 cursor-pointer text-sm text-surface-600 dark:text-surface-300">
                        <input v-model="aceptaTerminos" type="checkbox" class="mt-0.5 w-4 h-4 shrink-0 accent-primary-600" />
                        <span>
                            Leí y acepto los
                            <router-link to="/legales/terminos" target="_blank" class="text-primary-600 dark:text-primary-400 font-semibold hover:underline">términos y condiciones</router-link>
                            y la
                            <router-link to="/legales/privacidad" target="_blank" class="text-primary-600 dark:text-primary-400 font-semibold hover:underline">política de privacidad</router-link>.
                        </span>
                    </label>

                    <div v-if="error" class="p-3 rounded-xl bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-300 text-sm border border-red-200 dark:border-red-900">
                        {{ error }}
                    </div>

                    <button
                        type="submit"
                        :disabled="!puedeEnviar"
                        class="w-full inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl font-semibold text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-60 disabled:cursor-not-allowed transition"
                    >
                        <i :class="enviando ? 'pi pi-spin pi-spinner' : 'pi pi-user-plus'"></i>
                        {{ enviando ? 'Creando…' : 'Crear mi cuenta' }}
                    </button>

                    <p class="text-center text-sm text-surface-500 dark:text-surface-400 m-0">
                        ¿Ya tenés cuenta?
                        <!-- El `volver` viaja con el enlace: si eligió un horario y
                             resulta que ya tenía cuenta, entrar tiene que devolverlo
                             a ese turno y no al buzón. -->
                        <router-link :to="{ path: '/portal/login', query: route.query.volver ? { volver: route.query.volver } : {} }" class="text-primary-600 dark:text-primary-400 font-semibold hover:underline"> Iniciá sesión </router-link>
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
