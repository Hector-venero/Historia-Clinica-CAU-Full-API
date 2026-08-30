<script setup>
/**
 * La pagina propia de una funcionalidad. **Una sola, para las diez.**
 *
 * La ruta es /funcionalidades/:slug y el contenido sale de `PAGINAS` en
 * datos.js. Diez archivos .vue casi identicos serian diez lugares donde
 * arreglar el mismo detalle de diseno, y a la tercera correccion uno queda
 * distinto del resto — que es justo lo que se nota en un sitio hecho a las
 * apuradas.
 *
 * Un slug desconocido no rompe: manda a la pagina general. Una URL vieja
 * compartida por alguien tiene que llevar a algun lado.
 */
import { computed } from 'vue';
import { useRoute } from 'vue-router';
import SitioLayout from './SitioLayout.vue';
import MockupAgenda from './MockupAgenda.vue';
import MockupBuzon from './MockupBuzon.vue';
import MockupEquipo from './MockupEquipo.vue';
import MockupReceta from './MockupReceta.vue';
import MockupRoles from './MockupRoles.vue';
import MockupSello from './MockupSello.vue';
import { AUDIENCIAS, CON_PAGINA, PAGINAS, funcionPorSlug } from './datos';

const MOCKUPS = {
    agenda: MockupAgenda,
    buzon: MockupBuzon,
    equipo: MockupEquipo,
    receta: MockupReceta,
    roles: MockupRoles,
    sello: MockupSello
};

const route = useRoute();

const funcion = computed(() => funcionPorSlug(route.params.slug));
const pagina = computed(() => PAGINAS[route.params.slug] || null);
const mockup = computed(() => MOCKUPS[pagina.value?.mockup] || MockupAgenda);
const audiencia = computed(() => AUDIENCIAS.find((a) => a.clave === funcion.value?.audiencia));

// El paciente no se registra en el mismo lugar que un consultorio.
const esDelPaciente = computed(() => funcion.value?.audiencia === 'paciente');

// Navegación entre páginas hermanas: quien terminó de leer una está listo para
// la siguiente, y dejarlo sin salida es desperdiciar el interés.
const hermanas = computed(() => CON_PAGINA.filter((f) => f.audiencia === funcion.value?.audiencia && f.slug !== funcion.value?.slug));
</script>

<template>
    <SitioLayout>
        <template v-if="pagina">
            <!-- ══════════════ Banda del encabezado ══════════════ -->
            <section class="relative overflow-hidden py-16 md:py-20 border-b border-slate-200 dark:border-slate-800">
                <div class="absolute inset-0 -z-10 bg-gradient-to-b from-primary-50/70 to-white dark:from-primary-950/25 dark:to-slate-950" aria-hidden="true"></div>

                <div class="max-w-3xl mx-auto px-5 text-center">
                    <router-link
                        :to="`/funcionalidades#${funcion.audiencia}`"
                        class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold uppercase tracking-wider bg-primary-100 dark:bg-primary-950/60 text-primary-800 dark:text-primary-300 ring-1 ring-primary-200 dark:ring-primary-900 no-underline"
                    >
                        <i class="pi text-[10px]" :class="funcion.icono"></i>
                        {{ funcion.titulo }}
                    </router-link>

                    <h1 class="mt-6 text-3xl md:text-5xl font-extrabold tracking-tight text-slate-900 dark:text-white">{{ pagina.encabezado }}</h1>
                    <p class="mt-5 text-lg leading-relaxed text-slate-600 dark:text-slate-300">{{ pagina.promesa }}</p>
                </div>
            </section>

            <!-- ══════════════ El detalle, con el dibujo al lado ══════════════ -->
            <section class="py-16 md:py-24">
                <div class="max-w-6xl mx-auto px-5 grid lg:grid-cols-2 gap-12 lg:gap-14 items-center">
                    <div>
                        <h2 class="text-2xl md:text-4xl font-bold tracking-tight text-slate-900 dark:text-white">
                            {{ pagina.titulo }}
                        </h2>
                        <p class="mt-5 text-lg leading-relaxed text-slate-600 dark:text-slate-300">{{ pagina.intro }}</p>

                        <ul class="mt-8 space-y-3.5 list-none p-0">
                            <li v-for="p in pagina.puntos" :key="p" class="flex items-start gap-3 text-slate-700 dark:text-slate-300">
                                <span class="mt-0.5 w-5 h-5 shrink-0 rounded-full grid place-items-center bg-primary-500/15 text-primary-600 dark:text-primary-400">
                                    <i class="pi pi-check text-[10px]"></i>
                                </span>
                                <span class="leading-relaxed">{{ p }}</span>
                            </li>
                        </ul>
                    </div>

                    <div>
                        <component :is="mockup" v-bind="pagina.mockup === 'buzon' ? { oscuro: false } : {}" />
                    </div>
                </div>
            </section>

            <!-- ══════════════ Por qué sirve ══════════════ -->
            <section class="py-16 md:py-20 bg-slate-50 dark:bg-slate-900/40 border-y border-slate-200 dark:border-slate-800">
                <div class="max-w-6xl mx-auto px-5">
                    <h2 class="text-2xl md:text-3xl font-bold tracking-tight text-slate-900 dark:text-white text-center">Por qué te sirve</h2>

                    <div class="mt-12 grid md:grid-cols-3 gap-5">
                        <article v-for="b in pagina.beneficios" :key="b.titulo" class="p-6 rounded-2xl bg-white dark:bg-slate-900 ring-1 ring-slate-200 dark:ring-slate-800">
                            <div class="w-11 h-11 rounded-xl grid place-items-center bg-primary-50 dark:bg-primary-950/50 text-primary-600 dark:text-primary-400 ring-1 ring-primary-100 dark:ring-primary-900">
                                <i class="pi text-lg" :class="b.icono"></i>
                            </div>
                            <h3 class="mt-5 font-semibold text-lg text-slate-900 dark:text-white">{{ b.titulo }}</h3>
                            <p class="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-400">{{ b.detalle }}</p>
                        </article>
                    </div>
                </div>
            </section>

            <!-- ══════════════ Seguir leyendo ══════════════ -->
            <section v-if="hermanas.length" class="py-16 md:py-20">
                <div class="max-w-6xl mx-auto px-5">
                    <div class="flex flex-wrap items-end justify-between gap-4">
                        <h2 class="text-xl md:text-2xl font-bold tracking-tight text-slate-900 dark:text-white m-0">Más de {{ audiencia?.titulo.toLowerCase() }}</h2>
                        <router-link :to="`/funcionalidades#${funcion.audiencia}`" class="text-sm font-semibold text-primary-600 dark:text-primary-400 hover:underline no-underline"> Ver todo → </router-link>
                    </div>

                    <div class="mt-8 grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
                        <router-link
                            v-for="h in hermanas"
                            :key="h.slug"
                            :to="`/funcionalidades/${h.slug}`"
                            class="group p-5 rounded-2xl bg-white dark:bg-slate-900 ring-1 ring-slate-200 dark:ring-slate-800 hover:ring-primary-300 dark:hover:ring-primary-800 hover:-translate-y-1 transition-all no-underline"
                        >
                            <i class="pi text-primary-500" :class="h.icono"></i>
                            <p class="mt-3 font-semibold text-sm text-slate-900 dark:text-white m-0">{{ h.titulo }}</p>
                            <p class="mt-1 text-xs text-slate-500 dark:text-slate-400 m-0 leading-relaxed">{{ h.detalle }}</p>
                        </router-link>
                    </div>
                </div>
            </section>

            <!-- ══════════════ Cierre ══════════════ -->
            <section class="pb-24">
                <div class="max-w-4xl mx-auto px-5">
                    <div class="relative overflow-hidden rounded-3xl px-8 py-12 md:px-14 text-center ring-1 ring-primary-200 dark:ring-primary-900 bg-gradient-to-br from-primary-50 to-white dark:from-primary-950/40 dark:to-slate-900">
                        <div class="absolute -top-24 left-1/2 -translate-x-1/2 w-96 h-96 rounded-full bg-primary-300/25 dark:bg-primary-500/10 blur-3xl" aria-hidden="true"></div>
                        <div class="relative">
                            <h2 class="text-2xl md:text-3xl font-bold tracking-tight text-slate-900 dark:text-white">
                                {{ esDelPaciente ? 'Creá tu cuenta de paciente' : 'Probalo en tu consultorio' }}
                            </h2>
                            <p class="mt-4 text-slate-600 dark:text-slate-300">
                                {{ esDelPaciente ? 'Es gratis y te lleva dos minutos.' : '30 días con todas las funciones, sin tarjeta.' }}
                            </p>
                            <div class="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3">
                                <router-link
                                    :to="esDelPaciente ? '/portal/registro' : '/registro/medico'"
                                    class="inline-flex items-center gap-2 px-7 py-3.5 rounded-xl font-semibold text-white bg-primary-600 hover:bg-primary-700 shadow-lg shadow-primary-600/25 hover:-translate-y-0.5 transition-all no-underline"
                                >
                                    {{ esDelPaciente ? 'Crear mi cuenta' : 'Empezar gratis' }}
                                    <i class="pi pi-arrow-right text-sm"></i>
                                </router-link>
                                <router-link v-if="!esDelPaciente" to="/precios" class="px-7 py-3.5 rounded-xl font-semibold text-slate-700 dark:text-slate-200 hover:bg-white/60 dark:hover:bg-slate-800 transition no-underline">
                                    Ver precios
                                </router-link>
                            </div>
                        </div>
                    </div>
                </div>
            </section>
        </template>

        <!-- Slug desconocido: no se muestra un error, se ofrece la salida. -->
        <section v-else class="py-24 text-center">
            <div class="max-w-md mx-auto px-5">
                <i class="pi pi-compass text-4xl text-slate-300 dark:text-slate-700"></i>
                <h1 class="mt-5 text-2xl font-bold text-slate-900 dark:text-white">Esa funcionalidad no existe</h1>
                <p class="mt-3 text-slate-600 dark:text-slate-400">Puede que hayamos cambiado la dirección. Están todas juntas acá.</p>
                <router-link to="/funcionalidades" class="mt-7 inline-flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-white bg-primary-600 hover:bg-primary-700 transition no-underline">
                    Ver las funcionalidades
                    <i class="pi pi-arrow-right text-sm"></i>
                </router-link>
            </div>
        </section>
    </SitioLayout>
</template>
