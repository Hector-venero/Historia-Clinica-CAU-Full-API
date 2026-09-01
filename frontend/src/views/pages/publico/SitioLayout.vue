<script setup>
/**
 * El marco del sitio publico: barra de navegacion y pie.
 *
 * Vive aparte porque el sitio dejo de ser una sola pantalla. Con la barra
 * copiada en cada pagina, agregar un enlace obliga a tocarlas todas y la que se
 * olvida queda con un menu distinto — que es exactamente la sensacion de sitio
 * improvisado que hay que evitar en la carta de presentacion.
 */
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { useLayout } from '@/layout/composables/layout';
import logo from '@/assets/logo-ficha-salud.svg';
import { AUDIENCIAS, funcionesDe } from './datos';
import { PUBLICADO as LEGALES_PUBLICADOS } from './legales';

const { toggleDarkMode, isDarkTheme } = useLayout();
const route = useRoute();

// ⚠️ El dominio todavia no esta registrado. Cuando lo este, esta constante es
// el unico lugar donde cambiarlo.
const CORREO_CONTACTO = 'hola@fichasalud.com.ar';

// La barra se vuelve solida al bajar. Arriba compite con la portada; abajo, si
// es transparente, el texto de la pagina se le mezcla al pasar por encima.
const scrolleado = ref(false);
const alScrollear = () => (scrolleado.value = window.scrollY > 20);

onMounted(() => {
    alScrollear();
    window.addEventListener('scroll', alScrollear, { passive: true });
});
onUnmounted(() => window.removeEventListener('scroll', alScrollear));

// El desplegable de funcionalidades. Se abre al pasar el mouse, pero tambien
// con clic y con teclado: un menu que solo responde al hover no existe para
// quien navega con tab ni para quien entra desde el celular.
const menuAbierto = ref(false);
const menuMovil = ref(false);
let cierreDemorado = null;

function abrirMenu() {
    clearTimeout(cierreDemorado);
    menuAbierto.value = true;
}

function cerrarMenu(inmediato = false) {
    clearTimeout(cierreDemorado);
    // Una demora corta al salir: sin ella, el menu se cierra en el hueco que
    // queda entre el boton y el panel y se vuelve imposible de usar.
    if (inmediato) menuAbierto.value = false;
    else cierreDemorado = setTimeout(() => (menuAbierto.value = false), 150);
}

// Cada columna del desplegable son las funciones destacadas de una audiencia,
// tomadas de la misma lista que dibuja la pagina de funcionalidades.
const columnas = computed(() =>
    AUDIENCIAS.map((a) => ({
        ...a,
        funciones: funcionesDe(a.clave).filter((f) => f.destacada)
    }))
);

const enlaces = [
    { texto: 'Inicio', ruta: '/inicio' },
    { texto: 'Funcionalidades', ruta: '/funcionalidades', desplegable: true },
    { texto: 'Precios', ruta: '/precios' }
];

const esActual = (ruta) => route.path === ruta;
</script>

<template>
    <div class="min-h-screen flex flex-col bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 antialiased">
        <!-- ══════════════ Barra ══════════════ -->
        <header class="fixed top-0 inset-x-0 z-50 transition-all duration-300" :class="scrolleado || menuAbierto || menuMovil ? 'bg-white/85 dark:bg-slate-950/85 backdrop-blur-lg border-b border-slate-200/80 dark:border-slate-800' : ''">
            <div class="max-w-6xl mx-auto px-5 h-16 flex items-center justify-between gap-4">
                <router-link to="/inicio" class="flex items-center gap-2.5 no-underline shrink-0">
                    <img :src="logo" alt="" class="h-9 w-9" />
                    <span class="font-bold text-lg tracking-tight text-slate-900 dark:text-white">Ficha Salud</span>
                </router-link>

                <!-- Navegación de escritorio -->
                <nav class="hidden lg:flex items-center gap-1 text-sm font-medium">
                    <template v-for="e in enlaces" :key="e.ruta">
                        <div v-if="e.desplegable" class="relative" @mouseenter="abrirMenu" @mouseleave="cerrarMenu()">
                            <button
                                type="button"
                                class="flex items-center gap-1.5 px-3 py-2 rounded-lg transition"
                                :class="esActual(e.ruta) ? 'text-primary-600 dark:text-primary-400' : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white'"
                                :aria-expanded="menuAbierto"
                                @click="menuAbierto ? cerrarMenu(true) : abrirMenu()"
                            >
                                {{ e.texto }}
                                <i class="pi pi-chevron-down text-[10px] transition-transform" :class="menuAbierto ? 'rotate-180' : ''"></i>
                            </button>
                        </div>
                        <router-link
                            v-else
                            :to="e.ruta"
                            class="px-3 py-2 rounded-lg transition no-underline"
                            :class="esActual(e.ruta) ? 'text-primary-600 dark:text-primary-400' : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white'"
                        >
                            {{ e.texto }}
                        </router-link>
                    </template>
                </nav>

                <div class="flex items-center gap-2">
                    <button
                        type="button"
                        class="w-9 h-9 rounded-lg grid place-items-center text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                        :title="isDarkTheme ? 'Modo claro' : 'Modo oscuro'"
                        @click="toggleDarkMode"
                    >
                        <i :class="isDarkTheme ? 'pi pi-sun' : 'pi pi-moon'"></i>
                    </button>

                    <router-link
                        to="/ingresar"
                        class="hidden sm:inline-flex px-4 py-2 rounded-lg text-sm font-semibold text-slate-700 dark:text-slate-200 ring-1 ring-slate-200 dark:ring-slate-700 hover:ring-slate-300 dark:hover:ring-slate-600 transition no-underline"
                    >
                        Ingresar
                    </router-link>

                    <router-link to="/registro" class="px-4 py-2 rounded-lg text-sm font-semibold text-white bg-primary-600 hover:bg-primary-700 transition no-underline"> Registrarse </router-link>

                    <button type="button" class="lg:hidden w-9 h-9 rounded-lg grid place-items-center text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition" aria-label="Menú" @click="menuMovil = !menuMovil">
                        <i :class="menuMovil ? 'pi pi-times' : 'pi pi-bars'"></i>
                    </button>
                </div>
            </div>

            <!-- Desplegable de funcionalidades: las tres audiencias del producto.
                 Quien entra al sitio se reconoce en una de las tres columnas y
                 va directo a lo suyo, en vez de leer una lista de 20 funciones
                 donde la mitad no le habla a él. -->
            <transition enter-active-class="transition duration-150 ease-out" enter-from-class="opacity-0 -translate-y-1" leave-active-class="transition duration-100 ease-in" leave-to-class="opacity-0 -translate-y-1">
                <div v-if="menuAbierto" class="hidden lg:block absolute inset-x-0 top-16 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 shadow-xl shadow-slate-900/5" @mouseenter="abrirMenu" @mouseleave="cerrarMenu()">
                    <div class="max-w-6xl mx-auto px-5 py-8 grid grid-cols-3 gap-8">
                        <div v-for="col in columnas" :key="col.clave">
                            <p class="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-primary-600 dark:text-primary-400 m-0 mb-4">
                                <i class="pi text-sm" :class="col.icono"></i>
                                {{ col.titulo }}
                            </p>
                            <ul class="list-none p-0 m-0 space-y-1">
                                <li v-for="f in col.funciones" :key="f.titulo">
                                    <router-link
                                        :to="f.slug ? `/funcionalidades/${f.slug}` : `/funcionalidades#${col.clave}`"
                                        class="block px-3 py-2 -mx-3 rounded-lg no-underline hover:bg-slate-50 dark:hover:bg-slate-900 transition"
                                        @click="cerrarMenu(true)"
                                    >
                                        <span class="block text-sm font-semibold text-slate-900 dark:text-white">{{ f.titulo }}</span>
                                        <span class="block text-xs text-slate-500 dark:text-slate-400 mt-0.5 truncate">{{ f.detalle }}</span>
                                    </router-link>
                                </li>
                            </ul>
                        </div>
                    </div>
                </div>
            </transition>

            <!-- Menú de celular -->
            <transition enter-active-class="transition duration-150" enter-from-class="opacity-0" leave-active-class="transition duration-100" leave-to-class="opacity-0">
                <nav v-if="menuMovil" class="lg:hidden border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 px-5 py-4 space-y-1">
                    <router-link v-for="e in enlaces" :key="e.ruta" :to="e.ruta" class="block px-3 py-2.5 rounded-lg font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-900 no-underline" @click="menuMovil = false">
                        {{ e.texto }}
                    </router-link>
                    <router-link to="/ingresar" class="block px-3 py-2.5 rounded-lg font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-900 no-underline" @click="menuMovil = false"> Ingresar </router-link>
                </nav>
            </transition>
        </header>

        <main class="flex-1 pt-16">
            <slot />
        </main>

        <!-- ══════════════ Pie ══════════════ -->
        <footer class="bg-slate-900 dark:bg-slate-950 text-slate-300 border-t border-transparent dark:border-slate-800">
            <div class="max-w-6xl mx-auto px-5 py-14 grid gap-10 sm:grid-cols-2 lg:grid-cols-5">
                <div class="lg:col-span-1">
                    <div class="flex items-center gap-2.5">
                        <img :src="logo" alt="" class="h-8 w-8" />
                        <span class="font-bold text-white">Ficha Salud</span>
                    </div>
                    <p class="mt-4 text-sm leading-relaxed text-slate-400 m-0">Gestión para consultorios y centros médicos. Hecho en Argentina.</p>
                    <a :href="`mailto:${CORREO_CONTACTO}`" class="inline-flex items-center gap-2 mt-4 text-sm text-slate-300 hover:text-white no-underline transition">
                        <i class="pi pi-envelope text-xs"></i>
                        {{ CORREO_CONTACTO }}
                    </a>
                </div>

                <div>
                    <p class="text-sm font-semibold text-white m-0 mb-4">Plataforma</p>
                    <ul class="list-none p-0 m-0 space-y-2.5 text-sm">
                        <li><router-link to="/inicio" class="text-slate-400 hover:text-white no-underline transition">Inicio</router-link></li>
                        <li><router-link to="/funcionalidades" class="text-slate-400 hover:text-white no-underline transition">Funcionalidades</router-link></li>
                        <li><router-link to="/precios" class="text-slate-400 hover:text-white no-underline transition">Precios</router-link></li>
                        <li><router-link to="/ingresar" class="text-slate-400 hover:text-white no-underline transition">Ingresar</router-link></li>
                        <!-- Solo cuando los textos estén revisados. Enlazar a un
                             texto legal sin revisar es peor que no tenerlo. -->
                        <template v-if="LEGALES_PUBLICADOS">
                            <li><router-link to="/legales/terminos" class="text-slate-400 hover:text-white no-underline transition">Términos y condiciones</router-link></li>
                            <li><router-link to="/legales/privacidad" class="text-slate-400 hover:text-white no-underline transition">Privacidad</router-link></li>
                        </template>
                    </ul>
                </div>

                <div v-for="a in AUDIENCIAS" :key="a.clave">
                    <p class="text-sm font-semibold text-white m-0 mb-4">{{ a.titulo }}</p>
                    <ul class="list-none p-0 m-0 space-y-2.5 text-sm">
                        <li v-for="f in funcionesDe(a.clave).slice(0, 5)" :key="f.titulo">
                            <router-link :to="f.slug ? `/funcionalidades/${f.slug}` : `/funcionalidades#${a.clave}`" class="text-slate-400 hover:text-white no-underline transition">{{ f.titulo }}</router-link>
                        </li>
                    </ul>
                </div>
            </div>

            <div class="border-t border-white/10">
                <div class="max-w-6xl mx-auto px-5 py-6 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-500">
                    <p class="m-0">© {{ new Date().getFullYear() }} Ficha Salud. Todos los derechos reservados.</p>
                    <p class="m-0">Los datos de tu consultorio son tuyos y podés llevártelos cuando quieras.</p>
                </div>
            </div>
        </footer>
    </div>
</template>

<style scoped>
:global(html) {
    scroll-behavior: smooth;
}
</style>

<!-- Sin `scoped` a propósito: el contenido del slot se renderiza en el ámbito de
     la página, no en el de este componente, así que un estilo scoped de acá no
     lo alcanzaría. La clase es específica para que no afecte a nada más. -->
<style>
.seccion-anclada {
    scroll-margin-top: 5rem;
}
</style>
