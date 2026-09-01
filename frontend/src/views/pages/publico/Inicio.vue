<script setup>
/**
 * La portada.
 *
 * Su trabajo no es enumerar todo el producto —para eso esta /funcionalidades—
 * sino que alguien entienda en diez segundos que es esto, para quien es y que
 * hacer despues. Por eso cada bloque termina en un camino: la audiencia que se
 * reconoce entra por su tarjeta, el que quiere el detalle va a funcionalidades y
 * el que ya se decidio tiene el boton de siempre a la vista.
 */
import SitioLayout from './SitioLayout.vue';
import MockupAgenda from './MockupAgenda.vue';
import MockupBuzon from './MockupBuzon.vue';
import MockupEquipo from './MockupEquipo.vue';
import { AUDIENCIAS, funcionesDe } from './datos';

// Solo las destacadas del profesional: la portada muestra la punta, no el
// inventario. Salen de la misma lista que la pagina de funcionalidades.
const destacadas = funcionesDe('profesional').filter((f) => f.destacada);

const audiencias = AUDIENCIAS.map((a) => ({
    ...a,
    // El texto de la tarjeta cambia segun a quien le habla; el resto lo aporta
    // la lista compartida.
    resumen: {
        profesional: 'Tu propio sistema, con tu dirección web, en dos minutos. Agenda, historia clínica y recetas.',
        equipo: 'Una cuenta para todo el equipo: agendas por profesional, secretaría y la misma historia clínica.',
        paciente: 'Gratis. Tus estudios y recetas de todos tus profesionales, y turnos sin llamar por teléfono.'
    }[a.clave],
    ruta: { profesional: '/registro/medico', equipo: '/registro/institucion', paciente: '/portal/registro' }[a.clave],
    accion: { profesional: 'Crear mi consultorio', equipo: 'Solicitar una cuenta', paciente: 'Crear mi cuenta' }[a.clave],
    color: {
        profesional: 'text-primary-600 dark:text-primary-400 bg-primary-50 dark:bg-primary-950/50 ring-primary-100 dark:ring-primary-900',
        equipo: 'text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-950/50 ring-indigo-100 dark:ring-indigo-900',
        paciente: 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/50 ring-blue-100 dark:ring-blue-900'
    }[a.clave]
}));

const PASOS = [
    { n: '1', titulo: 'Creá tu cuenta', detalle: 'Elegís tu dirección web y confirmás el correo. Dos minutos, sin tarjeta.' },
    { n: '2', titulo: 'Cargá tu agenda', detalle: 'Tus días y horarios de atención. El sistema calcula los turnos solo.' },
    { n: '3', titulo: 'Empezá a atender', detalle: 'Los pacientes reservan, vos cargás la historia y emitís las recetas.' }
];

const GARANTIAS = [
    { icono: 'pi-cloud', texto: 'Sin instalar nada' },
    { icono: 'pi-download', texto: 'Tus datos, siempre exportables' },
    { icono: 'pi-verified', texto: 'Historia sellada en Blockchain Federal Argentina' },
    { icono: 'pi-map-marker', texto: 'Hecho en Argentina' }
];
</script>

<template>
    <SitioLayout>
        <!-- ══════════════ Portada ══════════════ -->
        <section class="relative overflow-hidden pt-16 pb-20 md:pt-24 md:pb-28">
            <!-- Fondo: un degradado suave y una grilla tenue. Sin esto la portada
                 es una pared blanca y no invita ni a leerla. -->
            <div class="absolute inset-0 -z-10" aria-hidden="true">
                <div class="absolute inset-0 bg-gradient-to-b from-primary-50/70 via-white to-white dark:from-primary-950/20 dark:via-slate-950 dark:to-slate-950"></div>
                <div class="absolute top-0 left-1/2 -translate-x-1/2 w-[52rem] h-[52rem] rounded-full bg-primary-300/20 dark:bg-primary-500/10 blur-3xl"></div>
                <div class="absolute inset-0 opacity-[0.035] dark:opacity-[0.06] fondo-grilla"></div>
            </div>

            <div class="max-w-6xl mx-auto px-5 grid lg:grid-cols-2 gap-14 lg:gap-10 items-center">
                <div>
                    <span class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold bg-primary-100 dark:bg-primary-950/60 text-primary-800 dark:text-primary-300 ring-1 ring-primary-200 dark:ring-primary-900">
                        <span class="w-1.5 h-1.5 rounded-full bg-primary-500 animate-pulse"></span>
                        30 días gratis · sin tarjeta
                    </span>

                    <h1 class="mt-6 text-[2.6rem] leading-[1.08] md:text-6xl md:leading-[1.05] font-extrabold tracking-tight text-slate-900 dark:text-white">
                        Tu consultorio,<br />
                        <span class="bg-gradient-to-r from-primary-600 to-primary-400 dark:from-primary-400 dark:to-primary-200 bg-clip-text text-transparent"> ordenado de una vez. </span>
                    </h1>

                    <p class="mt-6 text-lg leading-relaxed text-slate-600 dark:text-slate-300 max-w-lg">
                        Turnos online, historia clínica y recetas electrónicas en un solo lugar. Funciona desde el navegador: sin servidores, sin instalar nada y sin depender de nadie que lo mantenga.
                    </p>

                    <div class="mt-9 flex flex-wrap items-center gap-3">
                        <router-link
                            to="/registro/medico"
                            class="group inline-flex items-center gap-2 px-6 py-3.5 rounded-xl font-semibold text-white bg-primary-600 hover:bg-primary-700 shadow-lg shadow-primary-600/25 hover:shadow-primary-600/40 hover:-translate-y-0.5 transition-all no-underline"
                        >
                            Crear mi consultorio
                            <i class="pi pi-arrow-right text-sm group-hover:translate-x-0.5 transition-transform"></i>
                        </router-link>
                        <router-link
                            to="/funcionalidades"
                            class="inline-flex items-center gap-2 px-6 py-3.5 rounded-xl font-semibold text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-900 ring-1 ring-slate-200 dark:ring-slate-700 hover:ring-slate-300 dark:hover:ring-slate-600 transition no-underline"
                        >
                            Ver todo lo que incluye
                        </router-link>
                    </div>

                    <!-- Lo que más frena a alguien que evalúa: quedar atrapado. -->
                    <ul class="mt-8 flex flex-wrap gap-x-6 gap-y-2 text-sm text-slate-500 dark:text-slate-400 list-none p-0">
                        <li class="flex items-center gap-1.5"><i class="pi pi-check text-primary-500 text-xs"></i> Tus datos son tuyos</li>
                        <li class="flex items-center gap-1.5"><i class="pi pi-check text-primary-500 text-xs"></i> Te los llevás cuando quieras</li>
                        <li class="flex items-center gap-1.5"><i class="pi pi-check text-primary-500 text-xs"></i> Sin permanencia</li>
                    </ul>
                </div>

                <div class="lg:pl-4">
                    <MockupAgenda />
                </div>
            </div>
        </section>

        <!-- ══════════════ Franja de garantías ══════════════ -->
        <div class="border-y border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-900/40">
            <div class="max-w-6xl mx-auto px-5 py-6 grid grid-cols-2 lg:grid-cols-4 gap-5 text-sm">
                <div v-for="g in GARANTIAS" :key="g.texto" class="flex items-center gap-2.5 text-slate-600 dark:text-slate-400">
                    <i class="pi text-primary-500 shrink-0" :class="g.icono"></i>
                    <span>{{ g.texto }}</span>
                </div>
            </div>
        </div>

        <!-- ══════════════ ¿Quién sos? ══════════════ -->
        <section class="py-20 md:py-24">
            <div class="max-w-6xl mx-auto px-5">
                <div class="text-center max-w-2xl mx-auto">
                    <h2 class="text-3xl md:text-4xl font-bold tracking-tight text-slate-900 dark:text-white">Una plataforma, tres puertas</h2>
                    <p class="mt-4 text-lg text-slate-600 dark:text-slate-300">Elegí la que te describa y andá directo a lo tuyo.</p>
                </div>

                <div class="mt-12 grid md:grid-cols-3 gap-5">
                    <article
                        v-for="a in audiencias"
                        :key="a.clave"
                        class="group flex flex-col p-6 rounded-2xl bg-white dark:bg-slate-900 ring-1 ring-slate-200 dark:ring-slate-800 hover:-translate-y-1 hover:shadow-xl hover:shadow-slate-900/5 transition-all duration-300"
                    >
                        <div class="w-11 h-11 rounded-xl grid place-items-center ring-1 group-hover:scale-105 transition-transform" :class="a.color">
                            <i class="pi text-lg" :class="a.icono"></i>
                        </div>
                        <h3 class="mt-5 font-semibold text-lg text-slate-900 dark:text-white">{{ a.titulo }}</h3>
                        <p class="mt-1 text-sm font-medium text-slate-400 dark:text-slate-500">{{ a.bajada }}</p>
                        <p class="mt-3 text-sm leading-relaxed text-slate-600 dark:text-slate-400 flex-1">{{ a.resumen }}</p>

                        <div class="mt-6 flex items-center gap-4">
                            <router-link :to="a.ruta" class="text-sm font-semibold text-primary-600 dark:text-primary-400 hover:underline no-underline"> {{ a.accion }} → </router-link>
                            <router-link :to="`/funcionalidades#${a.clave}`" class="text-sm text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 no-underline transition"> Ver funciones </router-link>
                        </div>
                    </article>
                </div>
            </div>
        </section>

        <!-- ══════════════ Funciones destacadas ══════════════ -->
        <section class="py-20 md:py-24 bg-slate-50 dark:bg-slate-900/40 border-y border-slate-200 dark:border-slate-800">
            <div class="max-w-6xl mx-auto px-5">
                <div class="flex flex-wrap items-end justify-between gap-6">
                    <div class="max-w-2xl">
                        <h2 class="text-3xl md:text-4xl font-bold tracking-tight text-slate-900 dark:text-white">Todo lo que hace falta para atender</h2>
                        <p class="mt-4 text-lg text-slate-600 dark:text-slate-300">Y nada de lo que no. Pensado para consultorios chicos, no para hospitales.</p>
                    </div>
                    <router-link to="/funcionalidades" class="text-sm font-semibold text-primary-600 dark:text-primary-400 hover:underline no-underline"> Ver la lista completa → </router-link>
                </div>

                <div class="mt-12 grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
                    <article
                        v-for="f in destacadas"
                        :key="f.titulo"
                        class="group p-6 rounded-2xl bg-white dark:bg-slate-900 ring-1 ring-slate-200 dark:ring-slate-800 hover:ring-primary-300 dark:hover:ring-primary-800 hover:-translate-y-1 hover:shadow-xl hover:shadow-slate-900/5 transition-all duration-300"
                    >
                        <div class="w-11 h-11 rounded-xl grid place-items-center bg-primary-50 dark:bg-primary-950/50 text-primary-600 dark:text-primary-400 ring-1 ring-primary-100 dark:ring-primary-900 group-hover:scale-105 transition-transform">
                            <i class="pi text-lg" :class="f.icono"></i>
                        </div>
                        <h3 class="mt-5 font-semibold text-lg text-slate-900 dark:text-white">{{ f.titulo }}</h3>
                        <p class="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-400">{{ f.detalle }}</p>
                    </article>
                </div>
            </div>
        </section>

        <!-- ══════════════ El equipo ══════════════ -->
        <section class="py-20 md:py-28">
            <div class="max-w-6xl mx-auto px-5 grid lg:grid-cols-2 gap-14 items-center">
                <div class="order-2 lg:order-1">
                    <MockupEquipo />
                </div>
                <div class="order-1 lg:order-2">
                    <span class="inline-block px-3 py-1.5 rounded-full text-xs font-semibold bg-indigo-50 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300 ring-1 ring-indigo-100 dark:ring-indigo-900"> Para centros y equipos </span>
                    <h2 class="mt-6 text-3xl md:text-4xl font-bold tracking-tight text-slate-900 dark:text-white">Una historia clínica, todo el equipo</h2>
                    <p class="mt-5 text-lg leading-relaxed text-slate-600 dark:text-slate-300">
                        La ficha del paciente es <strong class="text-slate-900 dark:text-white">una sola</strong>: quien lo atienda ve lo que hicieron los demás, con la firma de cada uno. Cada profesional tiene su agenda y su duración de turno, y la
                        secretaría gestiona el mostrador sin entrar a la historia.
                    </p>
                    <router-link to="/funcionalidades#equipo" class="mt-8 inline-flex items-center gap-2 font-semibold text-primary-600 dark:text-primary-400 hover:underline no-underline">
                        Ver las funciones del equipo
                        <i class="pi pi-arrow-right text-sm"></i>
                    </router-link>
                </div>
            </div>
        </section>

        <!-- ══════════════ Cómo funciona ══════════════ -->
        <section class="py-20 md:py-24 bg-slate-50 dark:bg-slate-900/40 border-y border-slate-200 dark:border-slate-800">
            <div class="max-w-5xl mx-auto px-5">
                <div class="text-center max-w-2xl mx-auto">
                    <h2 class="text-3xl md:text-4xl font-bold tracking-tight text-slate-900 dark:text-white">Andando en una tarde</h2>
                    <p class="mt-4 text-lg text-slate-600 dark:text-slate-300">No hace falta migrar nada ni contratar a nadie.</p>
                </div>

                <div class="mt-14 grid md:grid-cols-3 gap-8 md:gap-6">
                    <div v-for="p in PASOS" :key="p.n" class="text-center md:text-left">
                        <div class="inline-grid md:flex w-12 h-12 rounded-xl place-items-center items-center justify-center font-bold text-lg bg-slate-900 dark:bg-white text-white dark:text-slate-900">
                            {{ p.n }}
                        </div>
                        <h3 class="mt-5 font-semibold text-lg text-slate-900 dark:text-white">{{ p.titulo }}</h3>
                        <p class="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-400">{{ p.detalle }}</p>
                    </div>
                </div>
            </div>
        </section>

        <!-- ══════════════ El paciente ══════════════ -->
        <section class="py-20 md:py-28 bg-slate-900 dark:bg-slate-900/60 text-white overflow-hidden relative">
            <div class="absolute top-0 right-0 w-96 h-96 bg-primary-500/20 blur-3xl rounded-full -translate-y-1/3 translate-x-1/3" aria-hidden="true"></div>

            <div class="relative max-w-6xl mx-auto px-5 grid lg:grid-cols-2 gap-14 items-center">
                <div>
                    <span class="inline-block px-3 py-1.5 rounded-full text-xs font-semibold bg-white/10 text-primary-300 ring-1 ring-white/15"> Gratis para el paciente </span>
                    <h2 class="mt-6 text-3xl md:text-4xl font-bold tracking-tight">Tus estudios, en un solo lugar</h2>
                    <p class="mt-5 text-lg leading-relaxed text-slate-300 max-w-lg">
                        El paciente ve las recetas y los estudios que le enviaron <strong class="text-white">todos sus profesionales</strong>, aunque se atienda en consultorios distintos. Y saca turno sin llamar por teléfono.
                    </p>
                    <!-- dark-ok: la seccion es oscura en los dos temas; el boton blanco es deliberado. -->
                    <router-link to="/portal/registro" class="mt-8 inline-flex items-center gap-2 px-6 py-3.5 rounded-xl font-semibold text-slate-900 bg-white hover:bg-slate-100 transition no-underline">
                        Crear mi cuenta de paciente
                        <i class="pi pi-arrow-right text-sm"></i>
                    </router-link>
                </div>

                <MockupBuzon oscuro />
            </div>
        </section>

        <!-- ══════════════ Cierre ══════════════ -->
        <section class="py-20 md:py-28">
            <div class="max-w-4xl mx-auto px-5">
                <div class="relative overflow-hidden rounded-3xl px-8 py-14 md:px-14 text-center ring-1 ring-primary-200 dark:ring-primary-900 bg-gradient-to-br from-primary-50 to-white dark:from-primary-950/40 dark:to-slate-900">
                    <div class="absolute -top-24 left-1/2 -translate-x-1/2 w-96 h-96 rounded-full bg-primary-300/25 dark:bg-primary-500/10 blur-3xl" aria-hidden="true"></div>

                    <div class="relative">
                        <h2 class="text-3xl md:text-4xl font-bold tracking-tight text-slate-900 dark:text-white">Probalo un mes entero</h2>
                        <p class="mt-5 text-lg leading-relaxed text-slate-600 dark:text-slate-300 max-w-xl mx-auto">Con todas las funciones y sin tarjeta. Si te sirve, seguimos. Si no, te llevás tus datos y listo.</p>

                        <div class="mt-9 flex flex-col sm:flex-row items-center justify-center gap-3">
                            <router-link
                                to="/registro/medico"
                                class="inline-flex items-center gap-2 px-7 py-4 rounded-xl font-semibold text-white bg-primary-600 hover:bg-primary-700 shadow-lg shadow-primary-600/25 hover:-translate-y-0.5 transition-all no-underline"
                            >
                                Empezar ahora
                                <i class="pi pi-arrow-right text-sm"></i>
                            </router-link>
                            <router-link to="/precios" class="px-7 py-4 rounded-xl font-semibold text-slate-700 dark:text-slate-200 hover:bg-white/60 dark:hover:bg-slate-800 transition no-underline"> Ver precios </router-link>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    </SitioLayout>
</template>

<style scoped>
/* Grilla tenue de fondo. Le da textura a la portada sin competir con el texto. */
.fondo-grilla {
    background-image: linear-gradient(to right, currentColor 1px, transparent 1px), linear-gradient(to bottom, currentColor 1px, transparent 1px);
    background-size: 56px 56px;
    color: theme('colors.slate.400');
    mask-image: radial-gradient(ellipse 80% 60% at 50% 0%, #000 40%, transparent 100%);
    -webkit-mask-image: radial-gradient(ellipse 80% 60% at 50% 0%, #000 40%, transparent 100%);
}
</style>
