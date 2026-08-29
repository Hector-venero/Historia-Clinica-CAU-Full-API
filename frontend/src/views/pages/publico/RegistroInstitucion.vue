<script setup>
import { computed, ref, watch } from 'vue';
import registroService from '@/service/registroService';
import logo from '@/assets/logo-ficha-salud.svg';

const form = ref({
    tipo: 'institucion',
    nombre: '',
    slug: '',
    email: '',
    password: '',
    contacto_nombre: '',
    contacto_telefono: '',
    direccion: '',
    localidad: '',
    cantidad_profesionales: '',
    cantidad_consultorios: '',
    atencion_online: 0,
    sitio_web: '',
    como_nos_conocio: '',
    comentarios: ''
});

// Se pide poco y obligatorio menos: cada campo obligatorio de más es gente que
// abandona el formulario a mitad. Lo que no se pregunta acá se conversa después,
// que es lo que va a pasar igual.
const CANALES = ['Búsqueda en Google', 'Redes sociales', 'Recomendación de otro profesional', 'Ya lo usaba en otro lugar', 'Otro'];

const enviando = ref(false);
const enviado = ref(false);
const error = ref('');

const slugLibre = ref(null);
const slugMotivo = ref('');
const slugNormalizado = ref('');
let temporizador = null;

const dominio = computed(() => window.location.host.replace(/^www\./, ''));

watch(
    () => form.value.slug,
    (valor) => {
        slugLibre.value = null;
        clearTimeout(temporizador);
        if (!valor || valor.trim().length < 3) return;

        temporizador = setTimeout(async () => {
            try {
                const { data } = await registroService.disponible(valor.trim());
                slugLibre.value = data.disponible;
                slugMotivo.value = data.motivo || '';
                slugNormalizado.value = data.slug || '';
            } catch {
                slugLibre.value = null;
            }
        }, 400);
    }
);

const puedeEnviar = computed(() => form.value.nombre.trim() && form.value.email.trim() && form.value.password.length >= 8 && form.value.contacto_nombre.trim() && form.value.contacto_telefono.trim() && slugLibre.value === true && !enviando.value);

async function enviar() {
    error.value = '';
    enviando.value = true;
    try {
        await registroService.registrar({ ...form.value });
        enviado.value = true;
    } catch (e) {
        error.value = e?.response?.data?.error || 'No pudimos enviar la solicitud. Probá de nuevo.';
    } finally {
        enviando.value = false;
    }
}
</script>

<template>
    <div class="min-h-screen bg-surface-50 dark:bg-surface-950 p-4 py-10">
        <div class="max-w-2xl mx-auto">
            <!-- Enviado. Se explica que sigue y cuándo, porque una solicitud que
                 espera aprobación sin decir nada se siente como un formulario
                 que se perdió. -->
            <div v-if="enviado" class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-2xl p-8 text-center">
                <i class="pi pi-send text-5xl text-primary-500 mb-4 block"></i>
                <h1 class="text-2xl font-bold text-surface-900 dark:text-surface-0 m-0 mb-3">Recibimos tu solicitud</h1>
                <p class="text-surface-600 dark:text-surface-300 leading-relaxed m-0 mb-4">
                    Primero confirmá tu correo: te mandamos un mensaje a <strong>{{ form.email }}</strong
                    >.
                </p>
                <div class="bg-surface-50 dark:bg-surface-800 rounded-xl p-4 text-left">
                    <p class="text-sm text-surface-600 dark:text-surface-300 leading-relaxed m-0">
                        Después revisamos la solicitud y nos comunicamos con <strong>{{ form.contacto_nombre }}</strong> para terminar de configurarlo. A diferencia de una cuenta individual, la de un centro la activamos a mano.
                    </p>
                </div>
            </div>

            <div v-else>
                <header class="text-center mb-8">
                    <router-link to="/registro" class="inline-flex items-center gap-2 no-underline mb-5">
                        <img :src="logo" alt="Ficha Salud" class="h-10 w-10" />
                        <span class="font-bold text-xl text-surface-900 dark:text-surface-0">Ficha Salud</span>
                    </router-link>
                    <h1 class="text-2xl font-bold text-surface-900 dark:text-surface-0 m-0">Cuenta para un centro</h1>
                    <p class="text-sm text-surface-500 dark:text-surface-400 mt-2 mb-0">Contanos de ustedes y nos ponemos en contacto.</p>
                </header>

                <form class="space-y-6" autocomplete="off" @submit.prevent="enviar">
                    <section class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-2xl p-5 md:p-6 space-y-4">
                        <h2 class="font-semibold text-surface-900 dark:text-surface-0 m-0">El centro</h2>

                        <div class="flex flex-col gap-2">
                            <label class="etiqueta">Nombre del centro *</label>
                            <input v-model="form.nombre" type="text" placeholder="Ej: Clínica San Rafael" class="campo" />
                        </div>

                        <div class="flex flex-col gap-2">
                            <label class="etiqueta">Dirección web *</label>
                            <div class="flex items-center">
                                <input v-model="form.slug" type="text" placeholder="clinicasanrafael" class="campo rounded-r-none" />
                                <span class="px-3 py-2.5 text-sm text-surface-500 dark:text-surface-400 bg-surface-100 dark:bg-surface-800 border border-l-0 border-surface-300 dark:border-surface-600 rounded-r-xl whitespace-nowrap">
                                    .{{ dominio }}
                                </span>
                            </div>
                            <small v-if="slugLibre === true" class="text-green-600 dark:text-green-400">
                                <i class="pi pi-check-circle mr-1"></i> Disponible: <strong>{{ slugNormalizado }}.{{ dominio }}</strong>
                            </small>
                            <small v-else-if="slugLibre === false" class="text-red-600 dark:text-red-400"> <i class="pi pi-times-circle mr-1"></i> {{ slugMotivo }} </small>
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div class="flex flex-col gap-2">
                                <label class="etiqueta">Dirección</label>
                                <input v-model="form.direccion" type="text" placeholder="Calle y número" class="campo" />
                            </div>
                            <div class="flex flex-col gap-2">
                                <label class="etiqueta">Localidad</label>
                                <input v-model="form.localidad" type="text" placeholder="Ej: Belgrano, CABA" class="campo" />
                            </div>
                        </div>

                        <div class="grid grid-cols-2 gap-4">
                            <div class="flex flex-col gap-2">
                                <label class="etiqueta">¿Cuántos profesionales?</label>
                                <input v-model="form.cantidad_profesionales" type="number" min="1" placeholder="6" class="campo" />
                            </div>
                            <div class="flex flex-col gap-2">
                                <label class="etiqueta">¿Cuántos consultorios?</label>
                                <input v-model="form.cantidad_consultorios" type="number" min="1" placeholder="3" class="campo" />
                            </div>
                        </div>

                        <label class="flex items-center gap-3 cursor-pointer">
                            <input v-model="form.atencion_online" type="checkbox" :true-value="1" :false-value="0" class="w-4 h-4 rounded" />
                            <span class="text-sm text-surface-700 dark:text-surface-200">También atendemos online</span>
                        </label>

                        <div class="flex flex-col gap-2">
                            <label class="etiqueta">Sitio web <span class="font-normal text-surface-400">(opcional)</span></label>
                            <input v-model="form.sitio_web" type="url" placeholder="https://" class="campo" />
                        </div>
                    </section>

                    <section class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-2xl p-5 md:p-6 space-y-4">
                        <h2 class="font-semibold text-surface-900 dark:text-surface-0 m-0">Con quién hablamos</h2>

                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div class="flex flex-col gap-2">
                                <label class="etiqueta">Tu nombre *</label>
                                <input v-model="form.contacto_nombre" type="text" class="campo" />
                            </div>
                            <div class="flex flex-col gap-2">
                                <label class="etiqueta">Teléfono *</label>
                                <input v-model="form.contacto_telefono" type="tel" placeholder="11 5555-1234" class="campo" />
                            </div>
                        </div>

                        <div class="flex flex-col gap-2">
                            <label class="etiqueta">Correo *</label>
                            <input v-model="form.email" type="email" placeholder="admin@clinica.com" class="campo" autocomplete="off" />
                            <small class="text-surface-500 dark:text-surface-400">Con este correo se entra al sistema.</small>
                        </div>

                        <div class="flex flex-col gap-2">
                            <label class="etiqueta">Contraseña *</label>
                            <input v-model="form.password" type="password" class="campo" autocomplete="new-password" />
                            <small class="text-surface-500 dark:text-surface-400">Mínimo 8 caracteres, con mayúscula, minúscula, número y símbolo.</small>
                        </div>

                        <div class="flex flex-col gap-2">
                            <label class="etiqueta">¿Cómo nos conociste?</label>
                            <select v-model="form.como_nos_conocio" class="campo">
                                <option value="">Prefiero no decir</option>
                                <option v-for="c in CANALES" :key="c" :value="c">{{ c }}</option>
                            </select>
                        </div>

                        <div class="flex flex-col gap-2">
                            <label class="etiqueta">Algo más que quieras contarnos</label>
                            <textarea v-model="form.comentarios" rows="3" class="campo resize-none"></textarea>
                        </div>
                    </section>

                    <div v-if="error" class="p-3 rounded-xl bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-300 text-sm border border-red-200 dark:border-red-900">
                        {{ error }}
                    </div>

                    <button
                        type="submit"
                        :disabled="!puedeEnviar"
                        class="w-full inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl font-semibold text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-60 disabled:cursor-not-allowed transition"
                    >
                        <i :class="enviando ? 'pi pi-spin pi-spinner' : 'pi pi-send'"></i>
                        {{ enviando ? 'Enviando…' : 'Enviar solicitud' }}
                    </button>

                    <p class="text-xs text-center text-surface-500 dark:text-surface-400 m-0">Los campos con * son los únicos obligatorios.</p>
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
.etiqueta {
    @apply text-sm font-semibold text-surface-700 dark:text-surface-200;
}
</style>
