<script setup>
import { computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { usePacienteStore } from '@/stores/paciente';
import { useLayout } from '@/layout/composables/layout';
import logo from '@/assets/logo-ficha-salud.svg';

const route = useRoute();
const router = useRouter();
const paciente = usePacienteStore();
const { toggleDarkMode, isDarkTheme } = useLayout();

// El portal NO usa AppLayout: ese trae el menú del consultorio (agenda,
// pacientes, recetas, comunicados), que a un paciente no le sirve y le daría
// 401 o 403 en cada clic. La barra de acá tiene solo lo suyo.
const iniciales = computed(() => {
    const n = paciente.nombre?.[0] || '';
    const a = paciente.apellido?.[0] || '';
    return (n + a).toUpperCase() || 'P';
});

// Buscar profesional y elegir horario se ven SIN cuenta, y desde el 31/08/2026
// tambien van adentro de este layout: antes quedaban afuera y se veian como
// paginas huerfanas, sin logo y sin forma de volver. Por eso la barra tiene que
// funcionar con y sin sesion.
const SUBTITULOS = {
    PortalDocumentos: 'Mis documentos',
    PortalMisTurnos: 'Mis turnos',
    PortalPerfil: 'Mi perfil',
    PortalBuscar: 'Sacar un turno',
    PortalReservar: 'Sacar un turno'
};

// Decia "Mis documentos" siempre, incluso parado en Mis turnos.
const subtitulo = computed(() => SUBTITULOS[route.name] || 'Tu salud, en un solo lugar');

onMounted(async () => {
    if (!paciente.autenticado) {
        try {
            await paciente.cargar();
        } catch {
            // Sin sesion no se rompe nada: en las rutas publicas la barra
            // muestra "Entrar", y en las privadas el guard ya redirigio.
        }
    }
});

async function salir() {
    await paciente.logout();
    router.replace('/portal/login');
}
</script>

<template>
    <div class="min-h-screen bg-surface-50 dark:bg-surface-950 flex flex-col">
        <header class="bg-surface-0 dark:bg-surface-900 border-b border-surface-200 dark:border-surface-700">
            <div class="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between gap-4">
                <router-link :to="paciente.autenticado ? '/portal' : '/portal/buscar'" class="flex items-center gap-2 no-underline">
                    <img :src="logo" alt="Ficha Salud" class="h-9 w-9" />
                    <div class="leading-tight">
                        <div class="font-bold text-surface-900 dark:text-surface-0">Ficha Salud</div>
                        <div class="text-xs text-surface-500 dark:text-surface-400">{{ subtitulo }}</div>
                    </div>
                </router-link>

                <div class="flex items-center gap-2">
                    <router-link
                        v-if="paciente.autenticado"
                        to="/portal/turnos"
                        class="inline-flex items-center gap-2 px-2.5 sm:px-3 py-2 rounded-lg text-sm font-medium text-surface-600 dark:text-surface-300 hover:bg-surface-100 dark:hover:bg-surface-800 transition no-underline"
                        title="Mis turnos"
                    >
                        <i class="pi pi-calendar"></i>
                        <span class="hidden sm:inline">Mis turnos</span>
                    </router-link>

                    <router-link to="/portal/buscar" class="inline-flex items-center gap-2 px-3 md:px-4 py-2 rounded-lg text-sm font-semibold text-white bg-primary-600 hover:bg-primary-700 transition no-underline">
                        <i class="pi pi-calendar-plus"></i>
                        <span class="hidden sm:inline">Sacar turno</span>
                    </router-link>

                    <button
                        type="button"
                        class="w-9 h-9 rounded-lg flex items-center justify-center text-surface-600 dark:text-surface-300 hover:bg-surface-100 dark:hover:bg-surface-800 transition"
                        :title="isDarkTheme ? 'Modo claro' : 'Modo oscuro'"
                        @click="toggleDarkMode"
                    >
                        <i :class="isDarkTheme ? 'pi pi-sun' : 'pi pi-moon'"></i>
                    </button>

                    <template v-if="paciente.autenticado">
                        <router-link
                            to="/portal/perfil"
                            class="w-9 h-9 rounded-full bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300 flex items-center justify-center font-semibold text-sm no-underline"
                            :title="paciente.nombreCompleto"
                        >
                            {{ iniciales }}
                        </router-link>

                        <button type="button" class="w-9 h-9 rounded-lg flex items-center justify-center text-surface-600 dark:text-surface-300 hover:bg-surface-100 dark:hover:bg-surface-800 transition" title="Cerrar sesión" @click="salir">
                            <i class="pi pi-sign-out"></i>
                        </button>
                    </template>

                    <!-- Se lleva de dónde salió: quien está eligiendo un horario y
                         entra tiene que volver a ese turno, no al buzón. -->
                    <router-link
                        v-else
                        :to="{ path: '/portal/login', query: { volver: route.fullPath } }"
                        class="inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-semibold text-surface-700 dark:text-surface-200 ring-1 ring-surface-300 dark:ring-surface-600 hover:bg-surface-100 dark:hover:bg-surface-800 transition no-underline"
                    >
                        <i class="pi pi-sign-in"></i>
                        <span class="hidden sm:inline">Entrar</span>
                    </router-link>
                </div>
            </div>
        </header>

        <main class="flex-1">
            <router-view />
        </main>

        <footer class="py-4 text-center text-xs text-surface-500 dark:text-surface-400">© {{ new Date().getFullYear() }} Ficha Salud</footer>
    </div>
</template>
