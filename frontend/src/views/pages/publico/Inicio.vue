<script setup>
import { useLayout } from '@/layout/composables/layout';
import logo from '@/assets/logo-ficha-salud.svg';

const { toggleDarkMode, isDarkTheme } = useLayout();

// Lo que el sistema hace hoy, no lo que va a hacer. Prometer en la página de
// inicio lo que todavía no existe es la forma más rápida de que el primer
// cliente se sienta engañado en la primera semana.
const PARA_EL_PROFESIONAL = [
    { icono: 'pi-calendar', titulo: 'Agenda y turnos', detalle: 'Disponibilidad por día, bloqueos y recordatorios por mail.' },
    { icono: 'pi-book', titulo: 'Historia clínica', detalle: 'Evoluciones con archivos adjuntos y exportación a PDF.' },
    { icono: 'pi-file-edit', titulo: 'Recetas electrónicas', detalle: 'Medicamentos y estudios, con envío al paciente.' },
    { icono: 'pi-globe', titulo: 'Turnos online', detalle: 'Tus pacientes reservan solos los horarios que dejes libres.' },
    { icono: 'pi-users', titulo: 'Agendas grupales', detalle: 'Para centros con varios profesionales y secretaría.' },
    { icono: 'pi-shield', titulo: 'Integridad verificable', detalle: 'Sellado en Blockchain Federal Argentina, opcional.' }
];

const PARA_EL_PACIENTE = [
    { icono: 'pi-inbox', titulo: 'Todo en un lugar', detalle: 'Estudios y recetas de todos tus profesionales, juntos.' },
    { icono: 'pi-calendar-plus', titulo: 'Sacá turno solo', detalle: 'Sin llamar por teléfono ni esperar a que atiendan.' },
    { icono: 'pi-lock', titulo: 'Es tuyo', detalle: 'Tus documentos siguen siendo tuyos, pase lo que pase.' }
];
</script>

<template>
    <div class="min-h-screen bg-surface-0 dark:bg-surface-950">
        <header class="border-b border-surface-200 dark:border-surface-800">
            <div class="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between gap-4">
                <div class="flex items-center gap-2">
                    <img :src="logo" alt="Ficha Salud" class="h-9 w-9" />
                    <span class="font-bold text-lg text-surface-900 dark:text-surface-0">Ficha Salud</span>
                </div>

                <div class="flex items-center gap-2">
                    <button
                        type="button"
                        class="w-9 h-9 rounded-lg flex items-center justify-center text-surface-600 dark:text-surface-300 hover:bg-surface-100 dark:hover:bg-surface-800 transition"
                        :title="isDarkTheme ? 'Modo claro' : 'Modo oscuro'"
                        @click="toggleDarkMode"
                    >
                        <i :class="isDarkTheme ? 'pi pi-sun' : 'pi pi-moon'"></i>
                    </button>
                    <router-link to="/registro" class="px-4 py-2 rounded-lg text-sm font-semibold text-white bg-primary-600 hover:bg-primary-700 transition no-underline"> Empezar </router-link>
                </div>
            </div>
        </header>

        <!-- Portada -->
        <section class="max-w-6xl mx-auto px-4 py-16 md:py-24">
            <div class="max-w-3xl">
                <h1 class="text-4xl md:text-5xl font-bold text-surface-900 dark:text-surface-0 leading-tight m-0">
                    El sistema de tu consultorio,<br />
                    <span class="text-primary-600 dark:text-primary-400">sin servidores ni informática.</span>
                </h1>
                <p class="text-lg text-surface-600 dark:text-surface-300 leading-relaxed mt-5 mb-8 max-w-2xl">
                    Turnos, historia clínica y recetas electrónicas para consultorios chicos. Funciona desde el navegador, se paga por mes y no hace falta instalar nada.
                </p>
                <div class="flex flex-wrap gap-3">
                    <router-link to="/registro" class="inline-flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-white bg-primary-600 hover:bg-primary-700 transition no-underline">
                        Probar 30 días gratis <i class="pi pi-arrow-right"></i>
                    </router-link>
                    <a
                        href="#funciones"
                        class="inline-flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-surface-700 dark:text-surface-200 bg-surface-100 dark:bg-surface-800 hover:bg-surface-200 dark:hover:bg-surface-700 transition no-underline"
                    >
                        Ver qué incluye
                    </a>
                </div>
                <p class="text-sm text-surface-500 dark:text-surface-400 mt-4 mb-0">Sin tarjeta de crédito. Podés llevarte tus datos cuando quieras.</p>
            </div>
        </section>

        <!-- Para el profesional -->
        <section id="funciones" class="bg-surface-50 dark:bg-surface-900 border-y border-surface-200 dark:border-surface-800">
            <div class="max-w-6xl mx-auto px-4 py-16">
                <h2 class="text-2xl md:text-3xl font-bold text-surface-900 dark:text-surface-0 m-0 mb-2">Para el profesional</h2>
                <p class="text-surface-600 dark:text-surface-300 m-0 mb-10">Todo lo que hace falta para atender, sin lo que no.</p>

                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                    <article v-for="f in PARA_EL_PROFESIONAL" :key="f.titulo" class="bg-surface-0 dark:bg-surface-950 border border-surface-200 dark:border-surface-800 rounded-2xl p-5">
                        <i class="pi text-2xl text-primary-600 dark:text-primary-400 mb-3 block" :class="f.icono"></i>
                        <h3 class="font-semibold text-surface-900 dark:text-surface-0 m-0 mb-1">{{ f.titulo }}</h3>
                        <p class="text-sm text-surface-600 dark:text-surface-300 leading-relaxed m-0">{{ f.detalle }}</p>
                    </article>
                </div>
            </div>
        </section>

        <!-- Para el paciente -->
        <section class="max-w-6xl mx-auto px-4 py-16">
            <h2 class="text-2xl md:text-3xl font-bold text-surface-900 dark:text-surface-0 m-0 mb-2">Para el paciente</h2>
            <p class="text-surface-600 dark:text-surface-300 m-0 mb-10">Gratis, y sirve aunque tus médicos estén en consultorios distintos.</p>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-5">
                <article v-for="f in PARA_EL_PACIENTE" :key="f.titulo" class="flex gap-4">
                    <i class="pi text-xl text-primary-600 dark:text-primary-400 mt-1" :class="f.icono"></i>
                    <div>
                        <h3 class="font-semibold text-surface-900 dark:text-surface-0 m-0 mb-1">{{ f.titulo }}</h3>
                        <p class="text-sm text-surface-600 dark:text-surface-300 leading-relaxed m-0">{{ f.detalle }}</p>
                    </div>
                </article>
            </div>
        </section>

        <!-- Precio.
             No se publican importes: los define Hector, y poner un número
             inventado en la página de inicio es comprometerlo con algo que no
             decidió. Lo que sí se dice es cómo funciona la prueba, que es lo que
             la persona necesita saber para empezar. -->
        <section class="bg-surface-50 dark:bg-surface-900 border-y border-surface-200 dark:border-surface-800">
            <div class="max-w-3xl mx-auto px-4 py-16 text-center">
                <h2 class="text-2xl md:text-3xl font-bold text-surface-900 dark:text-surface-0 m-0 mb-3">30 días para probarlo</h2>
                <p class="text-surface-600 dark:text-surface-300 leading-relaxed m-0 mb-8">
                    Te das de alta y en dos minutos tenés tu sistema funcionando, con todas las funciones. Sin tarjeta. Si al mes te sirve, lo seguimos; si no, te llevás tus datos y listo.
                </p>
                <router-link to="/registro" class="inline-flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-white bg-primary-600 hover:bg-primary-700 transition no-underline">
                    Crear mi consultorio <i class="pi pi-arrow-right"></i>
                </router-link>
            </div>
        </section>

        <footer class="max-w-6xl mx-auto px-4 py-10 text-center">
            <p class="text-sm text-surface-500 dark:text-surface-400 m-0">
                © {{ new Date().getFullYear() }} Ficha Salud ·
                <router-link to="/portal/login" class="text-primary-600 dark:text-primary-400 hover:underline">Soy paciente</router-link>
            </p>
        </footer>
    </div>
</template>
