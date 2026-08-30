<script setup>
/**
 * El detalle del producto, dividido por audiencia.
 *
 * Una sola lista de veinte funciones no la lee nadie: la mitad no le habla a
 * quien esta mirando. Cada seccion tiene su ancla (#profesional, #equipo,
 * #paciente) porque el menu desplegable y el pie entran directo al bloque que
 * corresponde.
 *
 * Todo sale de `datos.js`: esta pantalla no tiene una lista propia, asi que no
 * puede quedar desincronizada de la portada ni de la tabla de precios.
 */
import SitioLayout from './SitioLayout.vue';
import MockupAgenda from './MockupAgenda.vue';
import MockupBuzon from './MockupBuzon.vue';
import MockupEquipo from './MockupEquipo.vue';
import { AUDIENCIAS, FUNCIONES, funcionesDe } from './datos';

const MOCKUPS = { profesional: MockupAgenda, equipo: MockupEquipo, paciente: MockupBuzon };

// `encabezado` y no `titulo`: el titulo de la audiencia ("Para el profesional")
// se usa como antetitulo y en el menu, y pisarlo desde aca dejaria las dos
// lineas diciendo lo mismo.
const TITULOS = {
    profesional: {
        encabezado: 'Tu consultorio, completo',
        texto: 'Todo lo que necesitás para atender por tu cuenta: la agenda, la historia clínica y las recetas, sin saltar entre programas.'
    },
    equipo: {
        encabezado: 'El centro, coordinado',
        texto: 'Varios profesionales sobre la misma historia clínica, cada uno con su agenda y su nivel de acceso.'
    },
    paciente: {
        encabezado: 'El paciente, del otro lado',
        texto: 'Una cuenta gratuita donde recibe lo que le enviaron sus profesionales y saca turno sin llamar.'
    }
};

const secciones = AUDIENCIAS.map((a) => ({
    ...a,
    ...TITULOS[a.clave],
    mockup: MOCKUPS[a.clave],
    funciones: funcionesDe(a.clave)
}));

// Lo que todavía no está, dicho de frente. Ocultarlo no evita la pregunta: la
// adelanta al primer mes de uso, cuando ya pagó.
const enCamino = FUNCIONES.filter((f) => f.enCamino);
</script>

<template>
    <SitioLayout>
        <!-- ══════════════ Encabezado ══════════════ -->
        <section class="relative overflow-hidden py-16 md:py-24 border-b border-slate-200 dark:border-slate-800">
            <div class="absolute inset-0 -z-10 bg-gradient-to-b from-primary-50/60 to-white dark:from-primary-950/20 dark:to-slate-950" aria-hidden="true"></div>

            <div class="max-w-3xl mx-auto px-5 text-center">
                <span class="inline-block px-3 py-1.5 rounded-full text-xs font-semibold bg-primary-100 dark:bg-primary-950/60 text-primary-800 dark:text-primary-300 ring-1 ring-primary-200 dark:ring-primary-900"> Funcionalidades </span>
                <h1 class="mt-6 text-4xl md:text-5xl font-extrabold tracking-tight text-slate-900 dark:text-white">Lo que el sistema hace hoy</h1>
                <p class="mt-5 text-lg leading-relaxed text-slate-600 dark:text-slate-300">Nada de esto es una promesa: está funcionando y lo probás gratis por 30 días.</p>

                <nav class="mt-8 flex flex-wrap justify-center gap-2">
                    <a
                        v-for="s in secciones"
                        :key="s.clave"
                        :href="`#${s.clave}`"
                        class="inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium bg-white dark:bg-slate-900 ring-1 ring-slate-200 dark:ring-slate-800 text-slate-700 dark:text-slate-200 hover:ring-primary-300 dark:hover:ring-primary-800 transition no-underline"
                    >
                        <i class="pi text-xs text-primary-500" :class="s.icono"></i>
                        {{ s.titulo }}
                    </a>
                </nav>
            </div>
        </section>

        <!-- ══════════════ Una sección por audiencia ══════════════ -->
        <section v-for="(s, i) in secciones" :id="s.clave" :key="s.clave" class="seccion-anclada py-20 md:py-24" :class="i % 2 === 1 ? 'bg-slate-50 dark:bg-slate-900/40 border-y border-slate-200 dark:border-slate-800' : ''">
            <div class="max-w-6xl mx-auto px-5">
                <!-- Encabezado del bloque, con el dibujo al lado. Se alternan los
                     lados para que la página no sea una columna monótona. -->
                <div class="grid lg:grid-cols-2 gap-12 lg:gap-14 items-center">
                    <div :class="i % 2 === 1 ? 'lg:order-2' : ''">
                        <span class="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-primary-600 dark:text-primary-400">
                            <i class="pi text-sm" :class="s.icono"></i>
                            {{ s.titulo }}
                        </span>
                        <h2 class="mt-4 text-3xl md:text-4xl font-bold tracking-tight text-slate-900 dark:text-white">{{ s.encabezado }}</h2>
                        <p class="mt-5 text-lg leading-relaxed text-slate-600 dark:text-slate-300">{{ s.texto }}</p>

                        <router-link
                            :to="s.clave === 'paciente' ? '/portal/registro' : '/registro'"
                            class="mt-8 inline-flex items-center gap-2 px-6 py-3.5 rounded-xl font-semibold text-white bg-primary-600 hover:bg-primary-700 shadow-lg shadow-primary-600/20 hover:-translate-y-0.5 transition-all no-underline"
                        >
                            {{ s.clave === 'paciente' ? 'Crear mi cuenta gratis' : 'Probar 30 días gratis' }}
                            <i class="pi pi-arrow-right text-sm"></i>
                        </router-link>
                    </div>

                    <div :class="i % 2 === 1 ? 'lg:order-1' : ''">
                        <component :is="s.mockup" v-bind="s.clave === 'paciente' ? { oscuro: false } : {}" />
                    </div>
                </div>

                <!-- La lista completa de la audiencia -->
                <div class="mt-16 grid sm:grid-cols-2 lg:grid-cols-3 gap-x-8 gap-y-8">
                    <!-- La que tiene página propia es un enlace; la que no, texto.
                         Un enlace que no lleva a ningún lado se prueba una vez y
                         se deja de confiar en el resto del sitio. -->
                    <component :is="f.slug ? 'router-link' : 'article'" v-for="f in s.funciones" :key="f.titulo" :to="f.slug ? `/funcionalidades/${f.slug}` : undefined" class="group flex gap-4 no-underline">
                        <div
                            class="w-10 h-10 shrink-0 rounded-xl grid place-items-center bg-primary-50 dark:bg-primary-950/50 text-primary-600 dark:text-primary-400 ring-1 ring-primary-100 dark:ring-primary-900 group-hover:scale-105 transition-transform"
                        >
                            <i class="pi" :class="f.icono"></i>
                        </div>
                        <div>
                            <h3 class="font-semibold text-slate-900 dark:text-white m-0">
                                {{ f.titulo }}
                                <i v-if="f.slug" class="pi pi-arrow-right text-[10px] text-primary-500 opacity-0 group-hover:opacity-100 transition-opacity"></i>
                            </h3>
                            <p class="mt-1.5 text-sm leading-relaxed text-slate-600 dark:text-slate-400 m-0">{{ f.detalle }}</p>
                        </div>
                    </component>
                </div>
            </div>
        </section>

        <!-- ══════════════ En camino ══════════════ -->
        <section class="py-20 md:py-24">
            <div class="max-w-5xl mx-auto px-5">
                <div class="text-center max-w-2xl mx-auto">
                    <h2 class="text-2xl md:text-3xl font-bold tracking-tight text-slate-900 dark:text-white">En qué estamos trabajando</h2>
                    <p class="mt-4 text-slate-600 dark:text-slate-300">Todavía no está. Lo decimos acá y no en la letra chica.</p>
                </div>

                <div class="mt-10 grid sm:grid-cols-2 gap-4">
                    <div v-for="f in enCamino" :key="f.titulo" class="flex items-center gap-4 p-5 rounded-2xl border border-dashed border-slate-300 dark:border-slate-700">
                        <div class="w-10 h-10 shrink-0 rounded-xl grid place-items-center bg-slate-100 dark:bg-slate-800 text-slate-400 dark:text-slate-500">
                            <i class="pi" :class="f.icono"></i>
                        </div>
                        <div class="min-w-0">
                            <p class="font-semibold text-slate-700 dark:text-slate-200 m-0">
                                {{ f.titulo }}
                                <span class="ml-2 align-middle px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide bg-amber-100 dark:bg-amber-950/60 text-amber-700 dark:text-amber-400">En camino</span>
                            </p>
                            <p class="mt-1 text-sm text-slate-500 dark:text-slate-400 m-0">{{ f.detalle }}</p>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <!-- ══════════════ Cierre ══════════════ -->
        <section class="pb-24">
            <div class="max-w-4xl mx-auto px-5">
                <div class="rounded-3xl px-8 py-12 md:px-14 text-center ring-1 ring-slate-200 dark:ring-slate-800 bg-slate-50 dark:bg-slate-900/60">
                    <h2 class="text-2xl md:text-3xl font-bold tracking-tight text-slate-900 dark:text-white">¿Te sirve para tu consultorio?</h2>
                    <p class="mt-4 text-slate-600 dark:text-slate-300">Averiguarlo cuesta dos minutos y no pedimos tarjeta.</p>
                    <div class="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3">
                        <router-link
                            to="/registro/medico"
                            class="inline-flex items-center gap-2 px-7 py-3.5 rounded-xl font-semibold text-white bg-primary-600 hover:bg-primary-700 shadow-lg shadow-primary-600/25 hover:-translate-y-0.5 transition-all no-underline"
                        >
                            Crear mi consultorio
                            <i class="pi pi-arrow-right text-sm"></i>
                        </router-link>
                        <router-link to="/precios" class="px-7 py-3.5 rounded-xl font-semibold text-slate-700 dark:text-slate-200 hover:bg-white dark:hover:bg-slate-800 transition no-underline"> Ver precios </router-link>
                    </div>
                </div>
            </div>
        </section>
    </SitioLayout>
</template>
