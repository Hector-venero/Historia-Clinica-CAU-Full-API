<script setup>
import { computed, ref, watch } from 'vue';
import registroService from '@/service/registroService';

const form = ref({ nombre: '', slug: '', email: '', password: '' });

const enviando = ref(false);
const enviado = ref(false);
const error = ref('');

// Estado de la dirección: null = sin consultar, true/false = respuesta del backend.
const slugLibre = ref(null);
const slugMotivo = ref('');
const slugNormalizado = ref('');
const consultandoSlug = ref(false);

let temporizador = null;

// El dominio sale de la propia dirección del navegador: la pantalla se sirve
// desde el dominio raíz de la plataforma, así que no hace falta configurarlo.
const dominio = computed(() => window.location.host.replace(/^www\./, ''));

const direccionFinal = computed(() => (slugNormalizado.value ? `${slugNormalizado.value}.${dominio.value}` : ''));

/**
 * Se consulta con retraso mientras se escribe: sin esto, cada tecla sería una
 * petición al servidor.
 */
watch(
    () => form.value.slug,
    (valor) => {
        slugLibre.value = null;
        slugMotivo.value = '';
        slugNormalizado.value = '';
        clearTimeout(temporizador);

        if (!valor || valor.trim().length < 3) return;

        temporizador = setTimeout(async () => {
            consultandoSlug.value = true;
            try {
                const { data } = await registroService.disponible(valor.trim());
                slugLibre.value = data.disponible;
                slugMotivo.value = data.motivo || '';
                slugNormalizado.value = data.slug || '';
            } catch {
                // Sin respuesta no se afirma nada: el backend valida igual al enviar.
                slugLibre.value = null;
            } finally {
                consultandoSlug.value = false;
            }
        }, 400);
    }
);

const puedeEnviar = computed(() => form.value.nombre.trim().length >= 3 && form.value.email.trim() && form.value.password.length >= 8 && slugLibre.value === true && !enviando.value);

async function enviar() {
    error.value = '';
    enviando.value = true;
    try {
        await registroService.registrar({
            nombre: form.value.nombre.trim(),
            slug: form.value.slug.trim(),
            email: form.value.email.trim(),
            password: form.value.password
        });
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
            <!-- Confirmación: no se creó nada todavía, y se dice explícitamente
                 para que nadie se quede esperando un sistema que no existe. -->
            <div v-if="enviado" class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-2xl p-8 text-center">
                <i class="pi pi-envelope text-5xl text-primary-500 mb-4 block"></i>
                <h1 class="text-2xl font-bold text-surface-900 dark:text-surface-0 m-0 mb-3">Revisá tu correo</h1>
                <p class="text-surface-600 dark:text-surface-300 leading-relaxed m-0 mb-2">
                    Te mandamos un mensaje a <strong>{{ form.email }}</strong
                    >.
                </p>
                <p class="text-sm text-surface-500 dark:text-surface-400 leading-relaxed m-0">Cuando lo abras creamos tu consultorio. El enlace vence en 48 horas.</p>
            </div>

            <div v-else class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-2xl p-6 md:p-8">
                <header class="mb-6">
                    <h1 class="text-2xl md:text-3xl font-bold text-surface-900 dark:text-surface-0 m-0">Creá tu consultorio</h1>
                    <p class="text-sm text-surface-500 dark:text-surface-400 mt-1 mb-0">30 días de prueba. Sin tarjeta.</p>
                </header>

                <form class="space-y-5" autocomplete="off" @submit.prevent="enviar">
                    <div class="flex flex-col gap-2">
                        <label class="text-sm font-semibold text-surface-700 dark:text-surface-200">Nombre del consultorio</label>
                        <input v-model="form.nombre" type="text" placeholder="Ej: Consultorio Odontológico Sur" class="campo" />
                    </div>

                    <div class="flex flex-col gap-2">
                        <label class="text-sm font-semibold text-surface-700 dark:text-surface-200">Tu dirección web</label>
                        <div class="flex items-center">
                            <input v-model="form.slug" type="text" placeholder="consultoriosur" class="campo rounded-r-none" />
                            <span class="px-3 py-2.5 text-sm text-surface-500 dark:text-surface-400 bg-surface-100 dark:bg-surface-800 border border-l-0 border-surface-300 dark:border-surface-600 rounded-r-xl whitespace-nowrap">
                                .{{ dominio }}
                            </span>
                        </div>

                        <small v-if="consultandoSlug" class="text-surface-500 dark:text-surface-400"> <i class="pi pi-spin pi-spinner mr-1"></i> Comprobando… </small>
                        <!-- Se muestra la dirección normalizada, no la escrita:
                             "Consultorio-Sur" queda como "consultorio-sur". -->
                        <small v-else-if="slugLibre === true" class="text-green-600 dark:text-green-400">
                            <i class="pi pi-check-circle mr-1"></i> Disponible: <strong>{{ direccionFinal }}</strong>
                        </small>
                        <small v-else-if="slugLibre === false" class="text-red-600 dark:text-red-400"> <i class="pi pi-times-circle mr-1"></i> {{ slugMotivo }} </small>
                        <small v-else class="text-surface-500 dark:text-surface-400"> Letras minúsculas, números y guiones. Mínimo 3 caracteres. </small>
                    </div>

                    <div class="flex flex-col gap-2">
                        <label class="text-sm font-semibold text-surface-700 dark:text-surface-200">Tu correo</label>
                        <input v-model="form.email" type="email" placeholder="vos@ejemplo.com" class="campo" autocomplete="off" />
                        <small class="text-surface-500 dark:text-surface-400">Te mandamos ahí el enlace para activarlo.</small>
                    </div>

                    <div class="flex flex-col gap-2">
                        <label class="text-sm font-semibold text-surface-700 dark:text-surface-200">Contraseña</label>
                        <input v-model="form.password" type="password" placeholder="Con la que vas a entrar" class="campo" autocomplete="new-password" />
                        <small class="text-surface-500 dark:text-surface-400">Mínimo 8 caracteres, con mayúscula, minúscula, número y símbolo.</small>
                    </div>

                    <div v-if="error" class="p-3 rounded-xl bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-300 text-sm border border-red-200 dark:border-red-900">
                        {{ error }}
                    </div>

                    <button
                        type="submit"
                        :disabled="!puedeEnviar"
                        class="w-full inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl font-semibold text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-60 disabled:cursor-not-allowed transition"
                    >
                        <i :class="enviando ? 'pi pi-spin pi-spinner' : 'pi pi-arrow-right'"></i>
                        {{ enviando ? 'Creando…' : 'Crear mi consultorio' }}
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
