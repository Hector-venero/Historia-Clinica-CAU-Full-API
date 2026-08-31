<script setup>
// Campana de comunicados en la barra superior.
//
// Los comunicados eran una pantalla a la que habia que entrar: no avisaban
// nada, asi que un aviso publicado el martes lo leia quien pasara por ahi. La
// campana los trae al unico lugar que todos ven siempre.
//
// Los `importante` ademas llegan por mail (lo decide el backend). Aca la
// prioridad solo cambia como se muestran.

import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import comunicadoService from '@/service/comunicadoService';
import { on } from '@/utils/eventBus';

// Se relee cada 2 minutos. Es un aviso interno, no un chat: un intervalo mas
// corto multiplicaria los pedidos sin que nadie note la diferencia.
const INTERVALO_MS = 120000;
const MAX_EN_PANEL = 5;

const router = useRouter();
const abierto = ref(false);
const cargando = ref(false);
const noLeidos = ref(0);
const comunicados = ref([]);

let temporizador = null;
let desuscribir = null;

const pendientes = computed(() => comunicados.value.filter((c) => !c.leido));
const visibles = computed(() => (pendientes.value.length ? pendientes.value : comunicados.value).slice(0, MAX_EN_PANEL));

// Arriba de 9 el globo se deforma y el numero exacto deja de importar.
const globo = computed(() => (noLeidos.value > 9 ? '9+' : String(noLeidos.value)));

function formatearFecha(valor) {
    const fecha = new Date(valor);
    if (Number.isNaN(fecha.getTime())) return valor || '';
    return fecha.toLocaleString('es-AR', { dateStyle: 'short', timeStyle: 'short' });
}

async function actualizarContador() {
    try {
        const { data } = await comunicadoService.contarNoLeidos();
        noLeidos.value = data?.cantidad ?? 0;
    } catch {
        // Silencio a proposito: un 401 tras cerrar sesion, o la red caida, no
        // justifican un cartel de error sobre una pantalla que el usuario
        // podria estar usando para otra cosa.
        noLeidos.value = 0;
    }
}

async function cargarLista() {
    cargando.value = true;
    try {
        const { data } = await comunicadoService.listar();
        comunicados.value = data || [];
    } catch {
        comunicados.value = [];
    } finally {
        cargando.value = false;
    }
}

async function alternarPanel() {
    abierto.value = !abierto.value;
    if (abierto.value) await cargarLista();
}

async function abrirComunicado(comunicado) {
    abierto.value = false;
    if (!comunicado.leido) {
        try {
            await comunicadoService.marcarLeido(comunicado.id);
            comunicado.leido = true;
            noLeidos.value = Math.max(0, noLeidos.value - 1);
        } catch {
            // Si falla el marcado, igual se navega: la pantalla es lo que el
            // usuario pidio, y el contador se corrige en la proxima lectura.
        }
    }
    router.push('/comunicados');
}

async function marcarTodos() {
    try {
        await comunicadoService.marcarTodosLeidos();
        comunicados.value = comunicados.value.map((c) => ({ ...c, leido: true }));
        noLeidos.value = 0;
    } catch {
        await actualizarContador();
    }
}

function cerrarSiEsAfuera(evento) {
    if (!evento.target.closest?.('[data-campana]')) abierto.value = false;
}

onMounted(() => {
    actualizarContador();
    temporizador = setInterval(actualizarContador, INTERVALO_MS);
    document.addEventListener('click', cerrarSiEsAfuera);
    // Al publicar desde la pantalla de comunicados el contador quedaria viejo
    // hasta el siguiente intervalo.
    desuscribir = on('comunicados:actualizados', actualizarContador);
});

onUnmounted(() => {
    if (temporizador) clearInterval(temporizador);
    document.removeEventListener('click', cerrarSiEsAfuera);
    if (desuscribir) desuscribir();
});
</script>

<template>
    <div data-campana class="relative">
        <button type="button" class="layout-topbar-action relative" :aria-label="`Comunicados, ${noLeidos} sin leer`" @click.stop="alternarPanel">
            <i class="pi pi-bell"></i>
            <span v-if="noLeidos > 0" class="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 rounded-full bg-red-500 text-white text-[11px] font-bold leading-[18px] text-center">
                {{ globo }}
            </span>
        </button>

        <div v-if="abierto" class="absolute right-0 mt-2 w-80 max-w-[90vw] bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-700 rounded-xl shadow-xl z-50 overflow-hidden" @click.stop>
            <div class="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-slate-700">
                <span class="font-semibold text-sm text-gray-800 dark:text-gray-100">Comunicados</span>
                <button v-if="noLeidos > 0" type="button" class="text-xs text-primary-600 hover:underline" @click="marcarTodos">Marcar todo como leído</button>
            </div>

            <div v-if="cargando" class="px-4 py-6 text-sm text-surface-500 dark:text-surface-400 text-center">Cargando...</div>

            <div v-else-if="visibles.length === 0" class="px-4 py-6 text-sm text-surface-500 dark:text-surface-400 text-center">No hay comunicados.</div>

            <ul v-else class="max-h-80 overflow-y-auto divide-y divide-gray-100 dark:divide-slate-700">
                <li v-for="c in visibles" :key="c.id">
                    <button type="button" class="w-full text-left px-4 py-3 hover:bg-gray-50 dark:hover:bg-slate-800 transition" @click="abrirComunicado(c)">
                        <div class="flex items-start gap-2">
                            <!-- El punto marca lo no leido sin depender del color,
                                 que en el tema oscuro pierde contraste. -->
                            <span :class="['mt-1.5 w-2 h-2 rounded-full shrink-0', c.leido ? 'bg-transparent' : 'bg-primary-500']"></span>
                            <div class="min-w-0">
                                <p :class="['text-sm truncate', c.leido ? 'text-gray-600 dark:text-gray-400' : 'font-semibold text-gray-900 dark:text-gray-100']">
                                    <span v-if="c.prioridad === 'importante'" class="text-amber-600 dark:text-amber-400 mr-1">●</span>
                                    {{ c.titulo }}
                                </p>
                                <p class="text-xs text-surface-500 dark:text-surface-400 truncate">{{ c.autor_nombre }} · {{ formatearFecha(c.creado_en) }}</p>
                            </div>
                        </div>
                    </button>
                </li>
            </ul>

            <button
                type="button"
                class="w-full px-4 py-2.5 text-sm text-primary-600 hover:bg-gray-50 dark:hover:bg-slate-800 border-t border-gray-100 dark:border-slate-700"
                @click="
                    abierto = false;
                    router.push('/comunicados');
                "
            >
                Ver todos
            </button>
        </div>
    </div>
</template>
