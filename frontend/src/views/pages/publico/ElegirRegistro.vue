<script setup>
import logo from '@/assets/logo-ficha-salud.svg';

// Las tres puertas de entrada. Cada una lleva a un circuito distinto, y la
// diferencia se explica acá y no después: alguien que elige mal completa un
// formulario entero para descubrir que no era el suyo.
const OPCIONES = [
    {
        clave: 'medico',
        titulo: 'Soy profesional',
        bajada: 'Atiendo por mi cuenta',
        icono: 'pi-user-plus',
        detalle: 'Tenés tu propio sistema con agenda, historia clínica y recetas, en tu propia dirección web. 30 días de prueba, sin tarjeta.',
        accion: 'Crear mi consultorio',
        ruta: '/registro/medico',
        clase: 'border-primary-200 dark:border-primary-900 hover:border-primary-400 dark:hover:border-primary-700',
        acento: 'text-primary-600 dark:text-primary-400 bg-primary-50 dark:bg-primary-950/40'
    },
    {
        clave: 'paciente',
        titulo: 'Soy paciente',
        bajada: 'Quiero ver mis estudios',
        icono: 'pi-heart',
        detalle: 'Vas a ver en un solo lugar los estudios y recetas que te envíen tus profesionales, y podés sacar turno sin llamar. Es gratis.',
        accion: 'Crear mi cuenta',
        ruta: '/portal/registro',
        clase: 'border-blue-200 dark:border-blue-900 hover:border-blue-400 dark:hover:border-blue-700',
        acento: 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/40'
    },
    {
        clave: 'institucion',
        titulo: 'Somos un centro',
        bajada: 'Varios profesionales',
        icono: 'pi-building',
        detalle: 'Una cuenta para todo el equipo, con agendas compartidas y secretaría. Nos ponemos en contacto para configurarlo con vos.',
        accion: 'Solicitar una cuenta',
        ruta: '/registro/institucion',
        clase: 'border-green-200 dark:border-green-900 hover:border-green-400 dark:hover:border-green-700',
        acento: 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-950/40'
    }
];
</script>

<template>
    <div class="min-h-screen bg-surface-50 dark:bg-surface-950 p-4 py-10 md:py-16">
        <div class="max-w-5xl mx-auto">
            <header class="text-center mb-10">
                <router-link to="/" class="inline-flex items-center gap-2 no-underline mb-6">
                    <img :src="logo" alt="Ficha Salud" class="h-10 w-10" />
                    <span class="font-bold text-xl text-surface-900 dark:text-surface-0">Ficha Salud</span>
                </router-link>
                <h1 class="text-2xl md:text-3xl font-bold text-surface-900 dark:text-surface-0 m-0">¿Cómo vas a usarlo?</h1>
                <p class="text-surface-500 dark:text-surface-400 mt-2 mb-0">Elegí la opción que te describa.</p>
            </header>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-5">
                <article v-for="op in OPCIONES" :key="op.clave" class="bg-surface-0 dark:bg-surface-900 border-2 rounded-2xl p-6 flex flex-col transition" :class="op.clase">
                    <div class="w-12 h-12 rounded-xl flex items-center justify-center mb-4" :class="op.acento">
                        <i class="pi text-xl" :class="op.icono"></i>
                    </div>

                    <h2 class="text-lg font-bold text-surface-900 dark:text-surface-0 m-0">{{ op.titulo }}</h2>
                    <p class="text-sm font-medium m-0 mb-3" :class="op.acento.split(' ')[0]">{{ op.bajada }}</p>

                    <p class="text-sm text-surface-600 dark:text-surface-300 leading-relaxed m-0 mb-6 flex-1">
                        {{ op.detalle }}
                    </p>

                    <router-link :to="op.ruta" class="block w-full text-center px-4 py-2.5 rounded-xl font-semibold text-white bg-primary-600 hover:bg-primary-700 transition no-underline">
                        {{ op.accion }}
                    </router-link>
                </article>
            </div>

            <p class="text-center text-sm text-surface-500 dark:text-surface-400 mt-8">
                ¿Ya tenés cuenta?
                <router-link to="/portal/login" class="text-primary-600 dark:text-primary-400 font-semibold hover:underline">Entrá como paciente</router-link>
                — si sos profesional, entrá por la dirección de tu consultorio.
            </p>
        </div>
    </div>
</template>
