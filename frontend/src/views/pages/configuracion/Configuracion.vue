<script setup>
/**
 * Toda la configuración del consultorio en un solo lugar.
 *
 * Estaba repartida en cuatro rutas sin relación entre sí —`/disponibilidad`,
 * `/turnos/configuracion`, `/turnos/agenda-publica`, `/turnos/servicios`—, cada
 * una colgada de una parte distinta del menú. Poner en marcha un consultorio
 * era ir a buscarlas de a una sin que nada dijera que existían.
 *
 * Cada pestaña es una **ruta hija de verdad** (`/configuracion/avisos`) y no un
 * estado interno: así se puede guardar el enlace, compartirlo y volver con el
 * botón de atrás. Las cuatro rutas viejas siguen vivas redirigiendo acá, para
 * no romper lo que alguien haya dejado guardado.
 *
 * ⚠️ Las pestañas se filtran por rol con la misma lista que declara cada ruta.
 * Es presentación: quien decide es el guard del router y, sobre todo,
 * @requiere_rol en el servidor.
 *
 * El logo del consultorio no está acá todavía: vive en Mi Perfil, que es donde
 * funciona hoy. Moverlo es un cambio aparte y no vale arrastrarlo en este.
 */
import { computed } from 'vue';
import { useUserStore } from '@/stores/user';

const userStore = useUserStore();

const SOLAPAS = [
    { to: '/configuracion/disponibilidad', titulo: 'Disponibilidad', icono: 'pi-clock', roles: ['director', 'profesional', 'area'] },
    { to: '/configuracion/turnos', titulo: 'Duración de turnos', icono: 'pi-sliders-h', roles: ['director', 'profesional', 'area'] },
    { to: '/configuracion/servicios', titulo: 'Servicios', icono: 'pi-list', roles: ['director', 'administrativo', 'profesional'] },
    { to: '/configuracion/online', titulo: 'Turnos online', icono: 'pi-globe', roles: ['director', 'profesional'] },
    { to: '/configuracion/plantillas', titulo: 'Plantillas', icono: 'pi-bolt', roles: ['director', 'profesional'] },
    { to: '/configuracion/avisos', titulo: 'Avisos', icono: 'pi-envelope', roles: ['director', 'administrativo'] }
];

const solapas = computed(() => {
    const rol = userStore.rol?.toLowerCase().trim();
    return SOLAPAS.filter((s) => s.roles.includes(rol));
});
</script>

<template>
    <div class="card">
        <header class="mb-6">
            <h2 class="text-2xl font-bold text-surface-900 dark:text-surface-0 m-0">Configuración</h2>
            <p class="text-surface-600 dark:text-surface-300 mt-2 mb-0">Cómo trabaja el consultorio: cuándo se atiende, qué se ofrece y qué avisa el sistema.</p>
        </header>

        <nav class="flex flex-wrap gap-1 border-b border-surface-200 dark:border-surface-700 mb-8 -mx-2 px-2 overflow-x-auto">
            <!-- El estado activo se resuelve con v-slot y no con `active-class`:
                 esa clase se SUMA a las del atributo, así que quedarían
                 `border-transparent` y `border-primary-500` juntas y cuál gana
                 lo decidiría el orden del CSS, no el del template. -->
            <router-link v-for="solapa in solapas" :key="solapa.to" v-slot="{ href, navigate, isExactActive }" :to="solapa.to" custom>
                <a
                    :href="href"
                    class="px-4 py-3 text-sm font-semibold whitespace-nowrap border-b-2 -mb-px transition no-underline"
                    :class="isExactActive ? 'border-primary-500 text-primary-600 dark:text-primary-400' : 'border-transparent text-surface-500 dark:text-surface-400 hover:text-surface-800 dark:hover:text-surface-100'"
                    @click="navigate"
                >
                    <i class="pi mr-2" :class="solapa.icono"></i>{{ solapa.titulo }}
                </a>
            </router-link>
        </nav>

        <router-view />
    </div>
</template>
