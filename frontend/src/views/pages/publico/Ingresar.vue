<script setup>
/**
 * "Ingresar" desde el sitio publico.
 *
 * No puede ser un formulario de usuario y contrasena: la sesion del profesional
 * vive en el subdominio de **su** consultorio, no en el dominio raiz. Un login
 * aca autenticaria contra ninguna base.
 *
 * Asi que esta pantalla lo que hace es mandar a cada uno a su puerta: al
 * paciente al portal, y al profesional a la direccion de su consultorio. Es una
 * consecuencia directa de la arquitectura —una base por consultorio— y por eso
 * se explica en pantalla en vez de dejar a alguien probando su contrasena en el
 * lugar equivocado.
 */
import { computed, ref } from 'vue';
import SitioLayout from './SitioLayout.vue';
import { urlConsultorio } from '@/utils/dominio';

const slug = ref('');

// La misma normalización que acepta el alta: minúsculas, sin espacios y sin el
// resto de la dirección si la pegan entera.
const normalizado = computed(() =>
    slug.value
        .trim()
        .toLowerCase()
        .replace(/^https?:\/\//, '')
        .split('.')[0]
        .replace(/[^a-z0-9-]/g, '')
);

const destino = computed(() => (normalizado.value ? urlConsultorio(normalizado.value) : ''));

function ir() {
    if (destino.value) window.location.href = destino.value;
}
</script>

<template>
    <SitioLayout>
        <section class="relative overflow-hidden py-16 md:py-24">
            <div class="absolute inset-0 -z-10 bg-gradient-to-b from-primary-50/60 to-white dark:from-primary-950/20 dark:to-slate-950" aria-hidden="true"></div>

            <div class="max-w-4xl mx-auto px-5">
                <div class="text-center">
                    <h1 class="text-3xl md:text-4xl font-extrabold tracking-tight text-slate-900 dark:text-white">Ingresar</h1>
                    <p class="mt-4 text-lg text-slate-600 dark:text-slate-300">¿Entrás como paciente o como profesional?</p>
                </div>

                <div class="mt-12 grid md:grid-cols-2 gap-5 items-start">
                    <!-- ─── Paciente ─── -->
                    <article class="p-7 rounded-2xl bg-white dark:bg-slate-900 ring-1 ring-slate-200 dark:ring-slate-800">
                        <div class="w-11 h-11 rounded-xl grid place-items-center bg-blue-50 dark:bg-blue-950/50 text-blue-600 dark:text-blue-400 ring-1 ring-blue-100 dark:ring-blue-900">
                            <i class="pi pi-heart text-lg"></i>
                        </div>
                        <h2 class="mt-5 text-xl font-bold text-slate-900 dark:text-white m-0">Soy paciente</h2>
                        <p class="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-400">Para ver tus estudios y recetas, y sacar o cancelar turnos.</p>

                        <router-link to="/portal/login" class="mt-6 block text-center px-5 py-3 rounded-xl font-semibold text-white bg-primary-600 hover:bg-primary-700 transition no-underline"> Entrar al portal </router-link>

                        <p class="mt-4 text-center text-sm text-slate-500 dark:text-slate-400 m-0">
                            ¿No tenés cuenta?
                            <router-link to="/portal/registro" class="text-primary-600 dark:text-primary-400 font-semibold hover:underline">Creá una gratis</router-link>
                        </p>
                    </article>

                    <!-- ─── Profesional ─── -->
                    <article class="p-7 rounded-2xl bg-white dark:bg-slate-900 ring-1 ring-slate-200 dark:ring-slate-800">
                        <div class="w-11 h-11 rounded-xl grid place-items-center bg-primary-50 dark:bg-primary-950/50 text-primary-600 dark:text-primary-400 ring-1 ring-primary-100 dark:ring-primary-900">
                            <i class="pi pi-user text-lg"></i>
                        </div>
                        <h2 class="mt-5 text-xl font-bold text-slate-900 dark:text-white m-0">Soy profesional o secretaría</h2>
                        <p class="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-400">Tu consultorio tiene su propia dirección. Escribí su nombre y te llevamos.</p>

                        <form class="mt-6" @submit.prevent="ir">
                            <div class="flex items-stretch rounded-xl ring-1 ring-slate-300 dark:ring-slate-700 focus-within:ring-2 focus-within:ring-primary-500 overflow-hidden bg-white dark:bg-slate-800">
                                <input v-model="slug" type="text" placeholder="miconsultorio" class="flex-1 min-w-0 px-4 py-3 bg-transparent outline-none text-slate-900 dark:text-white" autocomplete="off" spellcheck="false" />
                                <span class="hidden sm:flex items-center px-3 text-sm text-slate-400 dark:text-slate-500 bg-slate-50 dark:bg-slate-900 border-l border-slate-200 dark:border-slate-700"> .fichasalud.com.ar </span>
                            </div>

                            <button
                                type="submit"
                                :disabled="!normalizado"
                                class="mt-4 w-full px-5 py-3 rounded-xl font-semibold text-white bg-slate-900 dark:bg-white dark:text-slate-900 hover:bg-slate-700 dark:hover:bg-slate-200 disabled:opacity-50 disabled:cursor-not-allowed transition"
                            >
                                Ir a mi consultorio
                            </button>
                        </form>

                        <p class="mt-4 text-center text-sm text-slate-500 dark:text-slate-400 m-0">
                            ¿Todavía no lo creaste?
                            <router-link to="/registro/medico" class="text-primary-600 dark:text-primary-400 font-semibold hover:underline">Empezá gratis</router-link>
                        </p>
                    </article>
                </div>

                <p class="mt-10 text-center text-sm text-slate-500 dark:text-slate-400">
                    <i class="pi pi-info-circle text-xs"></i>
                    Cada consultorio tiene su propia dirección y su propia base de datos. Por eso el ingreso del equipo no es acá.
                </p>
            </div>
        </section>
    </SitioLayout>
</template>
