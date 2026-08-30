<script setup>
/**
 * Precios y comparacion de planes.
 *
 * La tabla no es una matriz escrita a mano: sale de `datos.js`, donde cada
 * funcion declara en que planes entra. Una tabla comparativa mantenida aparte
 * es de las cosas que primero quedan viejas, y una que miente sobre lo que
 * incluye el plan que alguien acaba de pagar es peor que no tenerla.
 */
import { computed, ref } from 'vue';
import SitioLayout from './SitioLayout.vue';
import { FUNCIONES, PLANES } from './datos';

// Como en la referencia del rubro: primero preguntar como trabaja, y mostrarle
// solo lo suyo. Un medico solo no tiene por que leer la fila de "usuario de
// secretaria" para descubrir que no le aplica.
const caso = ref('profesional');

const CASOS = [
    { clave: 'profesional', titulo: 'Soy profesional', bajada: 'Atiendo de forma independiente', icono: 'pi-user' },
    { clave: 'equipo', titulo: 'Somos un equipo', bajada: 'Clínica, centro o consultorio grupal', icono: 'pi-users' }
];

// Con "soy profesional" se muestra el plan individual; con "somos un equipo",
// los dos, porque un centro chico puede arrancar con el plan individual.
const planesVisibles = computed(() => (caso.value === 'profesional' ? PLANES.filter((p) => p.clave === 'profesional') : PLANES));

// La tabla compara los dos planes pagos. Las funciones del paciente quedan
// afuera a propósito: no son parte de lo que se contrata, son gratis siempre.
const filas = computed(() => FUNCIONES.filter((f) => !f.enCamino && f.audiencia !== 'paciente'));

const PREGUNTAS = [
    {
        q: '¿Qué pasa cuando terminan los 30 días?',
        a: 'Te avisamos antes. Si no seguís, la cuenta queda suspendida y podés exportar todo lo que cargaste. No borramos nada de un día para el otro.'
    },
    {
        q: '¿Puedo llevarme mis datos?',
        a: 'Sí, cuando quieras. La historia clínica de cada paciente se exporta en PDF con sus adjuntos, y el listado de pacientes en un archivo que abre cualquier planilla.'
    },
    {
        q: '¿Hay permanencia?',
        a: 'No. Es mes a mes y se da de baja cuando quieras.'
    },
    {
        q: '¿Mis datos están separados de los de otros consultorios?',
        a: 'Sí. Cada consultorio tiene su propia base de datos, no una tabla compartida con un filtro. Es la razón por la que un consultorio no puede ver los pacientes de otro ni por error de programación.'
    },
    {
        q: '¿El paciente paga algo?',
        a: 'No. La cuenta del paciente es gratis y siempre lo va a ser: es lo que hace que te reserve turno y reciba sus estudios.'
    },
    {
        q: '¿Necesito instalar algo o contratar un servidor?',
        a: 'No. Funciona desde el navegador y tu consultorio tiene su propia dirección web desde el primer día.'
    }
];

const abierta = ref(null);
const alternar = (i) => (abierta.value = abierta.value === i ? null : i);
</script>

<template>
    <SitioLayout>
        <!-- ══════════════ Encabezado ══════════════ -->
        <section class="relative overflow-hidden py-16 md:py-20 border-b border-slate-200 dark:border-slate-800">
            <div class="absolute inset-0 -z-10 bg-gradient-to-b from-primary-50/60 to-white dark:from-primary-950/20 dark:to-slate-950" aria-hidden="true"></div>

            <div class="max-w-3xl mx-auto px-5 text-center">
                <span class="inline-block px-3 py-1.5 rounded-full text-xs font-semibold bg-primary-100 dark:bg-primary-950/60 text-primary-800 dark:text-primary-300 ring-1 ring-primary-200 dark:ring-primary-900"> Planes y precios </span>
                <h1 class="mt-6 text-4xl md:text-5xl font-extrabold tracking-tight text-slate-900 dark:text-white">Un precio, todas las funciones</h1>
                <p class="mt-5 text-lg leading-relaxed text-slate-600 dark:text-slate-300">Sin módulos que se cobran aparte ni sorpresas en la factura. Empezás con 30 días gratis y sin tarjeta.</p>
            </div>
        </section>

        <!-- ══════════════ Cómo trabajás ══════════════ -->
        <section class="py-14 md:py-16">
            <div class="max-w-5xl mx-auto px-5">
                <p class="text-center text-slate-600 dark:text-slate-300 m-0">¿Cómo trabajás? Elegí tu caso y te mostramos solo los planes que aplican.</p>

                <div class="mt-6 flex flex-col sm:flex-row justify-center gap-3">
                    <button
                        v-for="c in CASOS"
                        :key="c.clave"
                        type="button"
                        class="flex-1 sm:flex-none sm:w-64 px-6 py-4 rounded-2xl text-center transition ring-1"
                        :class="caso === c.clave ? 'bg-primary-50 dark:bg-primary-950/40 ring-primary-400 dark:ring-primary-700' : 'bg-white dark:bg-slate-900 ring-slate-200 dark:ring-slate-800 hover:ring-slate-300 dark:hover:ring-slate-700'"
                        @click="caso = c.clave"
                    >
                        <i class="pi text-xl" :class="[c.icono, caso === c.clave ? 'text-primary-600 dark:text-primary-400' : 'text-slate-400']"></i>
                        <span class="block mt-2 font-semibold" :class="caso === c.clave ? 'text-primary-800 dark:text-primary-300' : 'text-slate-800 dark:text-slate-100'">{{ c.titulo }}</span>
                        <span class="block text-xs mt-0.5 text-slate-500 dark:text-slate-400">{{ c.bajada }}</span>
                    </button>
                </div>

                <!-- ══════════════ Los planes ══════════════ -->
                <div class="mt-12 grid gap-6" :class="planesVisibles.length > 1 ? 'md:grid-cols-2 max-w-3xl mx-auto' : 'max-w-md mx-auto'">
                    <article
                        v-for="p in planesVisibles"
                        :key="p.clave"
                        class="relative flex flex-col rounded-2xl p-7 transition"
                        :class="p.destacado ? 'bg-white dark:bg-slate-900 ring-2 ring-primary-500 shadow-xl shadow-primary-600/10' : 'bg-white dark:bg-slate-900 ring-1 ring-slate-200 dark:ring-slate-800'"
                    >
                        <span v-if="p.destacado" class="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider text-white bg-primary-600"> Más elegido </span>

                        <p class="text-xs font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 m-0">{{ p.rotulo }}</p>
                        <h2 class="mt-2 text-2xl font-bold text-slate-900 dark:text-white m-0">{{ p.nombre }}</h2>
                        <p class="mt-2 text-sm text-slate-600 dark:text-slate-400 m-0">{{ p.bajada }}</p>

                        <div class="mt-6 pb-6 border-b border-slate-200 dark:border-slate-800">
                            <template v-if="p.precio">
                                <span class="text-4xl font-extrabold text-slate-900 dark:text-white">${{ p.precio.toLocaleString('es-AR') }}</span>
                                <span class="block text-sm text-slate-500 dark:text-slate-400 mt-1">por mes · IVA incluido</span>
                            </template>
                            <template v-else>
                                <span class="text-3xl font-extrabold text-slate-900 dark:text-white">Consultanos</span>
                                <span class="block text-sm text-slate-500 dark:text-slate-400 mt-1">Los 30 días de prueba son gratis igual</span>
                            </template>
                        </div>

                        <ul class="mt-6 space-y-3 list-none p-0 m-0 flex-1">
                            <li v-for="f in filas.filter((x) => x.planes.includes(p.clave) && x.destacada)" :key="f.titulo" class="flex items-start gap-2.5 text-sm text-slate-700 dark:text-slate-300">
                                <i class="pi pi-check text-primary-500 text-xs mt-1 shrink-0"></i>
                                <span>{{ f.titulo }}</span>
                            </li>
                            <li class="flex items-start gap-2.5 text-sm text-slate-500 dark:text-slate-400">
                                <i class="pi pi-plus text-slate-400 text-xs mt-1 shrink-0"></i>
                                <span>y todo lo de la tabla de abajo</span>
                            </li>
                        </ul>

                        <router-link
                            :to="p.ruta"
                            class="mt-7 block text-center px-5 py-3 rounded-xl font-semibold transition no-underline"
                            :class="p.destacado ? 'text-white bg-primary-600 hover:bg-primary-700' : 'text-slate-800 dark:text-slate-100 ring-1 ring-slate-300 dark:ring-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800'"
                        >
                            {{ p.cta }}
                        </router-link>
                    </article>
                </div>

                <p class="mt-8 text-center text-sm text-slate-500 dark:text-slate-400">
                    La cuenta del paciente es <strong class="text-slate-700 dark:text-slate-200">gratis</strong> y no cuenta para ningún plan.
                    <router-link to="/funcionalidades#paciente" class="text-primary-600 dark:text-primary-400 hover:underline">Ver qué incluye</router-link>
                </p>
            </div>
        </section>

        <!-- ══════════════ Comparación ══════════════ -->
        <section class="py-16 md:py-20 bg-slate-50 dark:bg-slate-900/40 border-y border-slate-200 dark:border-slate-800">
            <div class="max-w-4xl mx-auto px-5">
                <h2 class="text-2xl md:text-3xl font-bold tracking-tight text-slate-900 dark:text-white text-center">Qué incluye cada plan</h2>

                <!-- La tabla se desborda en horizontal dentro de su caja: en un
                     celular, dejar que empuje el ancho de la página rompe todo
                     lo demás. -->
                <div class="mt-10 overflow-x-auto rounded-2xl ring-1 ring-slate-200 dark:ring-slate-800 bg-white dark:bg-slate-900">
                    <table class="w-full text-sm border-collapse min-w-[34rem]">
                        <thead>
                            <tr class="border-b border-slate-200 dark:border-slate-800">
                                <th class="text-left font-semibold text-slate-500 dark:text-slate-400 px-5 py-4">Función</th>
                                <th v-for="p in PLANES" :key="p.clave" class="text-center font-semibold text-slate-900 dark:text-white px-5 py-4 w-32">
                                    {{ p.nombre }}
                                </th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="f in filas" :key="f.titulo" class="border-b border-slate-100 dark:border-slate-800/70 last:border-0">
                                <td class="px-5 py-4">
                                    <span class="block font-medium text-slate-900 dark:text-white">{{ f.titulo }}</span>
                                    <span class="block text-xs text-slate-500 dark:text-slate-400 mt-0.5">{{ f.detalle }}</span>
                                </td>
                                <td v-for="p in PLANES" :key="p.clave" class="text-center px-5 py-4">
                                    <i v-if="f.planes.includes(p.clave)" class="pi pi-check text-primary-500" :title="`Incluido en ${p.nombre}`"></i>
                                    <i v-else class="pi pi-minus text-slate-300 dark:text-slate-700" :title="`No incluido en ${p.nombre}`"></i>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </section>

        <!-- ══════════════ Preguntas ══════════════ -->
        <section class="py-16 md:py-24">
            <div class="max-w-3xl mx-auto px-5">
                <h2 class="text-2xl md:text-3xl font-bold tracking-tight text-slate-900 dark:text-white text-center">Preguntas que nos hacen siempre</h2>

                <div class="mt-10 space-y-3">
                    <div v-for="(p, i) in PREGUNTAS" :key="p.q" class="rounded-2xl ring-1 ring-slate-200 dark:ring-slate-800 bg-white dark:bg-slate-900 overflow-hidden">
                        <button type="button" class="w-full flex items-center justify-between gap-4 text-left px-5 py-4 hover:bg-slate-50 dark:hover:bg-slate-800/60 transition" :aria-expanded="abierta === i" @click="alternar(i)">
                            <span class="font-semibold text-slate-900 dark:text-white">{{ p.q }}</span>
                            <i class="pi pi-chevron-down text-xs text-slate-400 transition-transform shrink-0" :class="abierta === i ? 'rotate-180' : ''"></i>
                        </button>
                        <div v-if="abierta === i" class="px-5 pb-5 -mt-1 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
                            {{ p.a }}
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <!-- ══════════════ Cierre ══════════════ -->
        <section class="pb-24">
            <div class="max-w-4xl mx-auto px-5">
                <div class="relative overflow-hidden rounded-3xl px-8 py-14 md:px-14 text-center ring-1 ring-primary-200 dark:ring-primary-900 bg-gradient-to-br from-primary-50 to-white dark:from-primary-950/40 dark:to-slate-900">
                    <div class="absolute -top-24 left-1/2 -translate-x-1/2 w-96 h-96 rounded-full bg-primary-300/25 dark:bg-primary-500/10 blur-3xl" aria-hidden="true"></div>
                    <div class="relative">
                        <h2 class="text-3xl md:text-4xl font-bold tracking-tight text-slate-900 dark:text-white">¿Dudas? Escribinos</h2>
                        <p class="mt-5 text-lg text-slate-600 dark:text-slate-300 max-w-xl mx-auto">Si tenés un equipo o venís de otro sistema, contanos cómo trabajás y te decimos si te sirve.</p>
                        <div class="mt-9 flex flex-col sm:flex-row items-center justify-center gap-3">
                            <router-link
                                to="/registro/medico"
                                class="inline-flex items-center gap-2 px-7 py-4 rounded-xl font-semibold text-white bg-primary-600 hover:bg-primary-700 shadow-lg shadow-primary-600/25 hover:-translate-y-0.5 transition-all no-underline"
                            >
                                Empezar 30 días gratis
                                <i class="pi pi-arrow-right text-sm"></i>
                            </router-link>
                            <router-link to="/registro/institucion" class="px-7 py-4 rounded-xl font-semibold text-slate-700 dark:text-slate-200 hover:bg-white/60 dark:hover:bg-slate-800 transition no-underline"> Somos un centro médico </router-link>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    </SitioLayout>
</template>
