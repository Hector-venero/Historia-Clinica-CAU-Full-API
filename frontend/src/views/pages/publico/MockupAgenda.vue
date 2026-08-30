<script setup>
/**
 * Mockup de la agenda, dibujado con divs.
 *
 * Una portada de software de gestión sin una imagen del producto obliga a la
 * persona a imaginárselo, y nadie compra lo que no puede ver. Un médico
 * reconoce una grilla de turnos al instante: dice más que tres párrafos.
 *
 * Es un dibujo y no una captura: pesa nada, se ve nítido en cualquier pantalla,
 * acompaña el modo oscuro y no queda desactualizado cuando cambie una pantalla
 * real. Los datos son inventados y genéricos a propósito.
 */

const DIAS = ['LUN', 'MAR', 'MIÉ', 'JUE', 'VIE'];

// 'c' consultorio · 'g' grupal · 'o' reservado online · null hueco libre.
// Dibuja una semana creíble —llena pero con lugar— en vez de una grilla
// perfecta que se nota inventada.
const TURNOS = [
    ['c', null, 'c', 'o', 'c'],
    ['c', 'g', 'c', null, 'c'],
    [null, 'g', 'o', 'c', null],
    ['c', 'g', null, 'c', 'o'],
    ['o', null, 'c', 'c', 'c']
];

const CLASES = {
    c: 'bg-primary-500/25 text-primary-700 dark:text-primary-300',
    g: 'bg-indigo-500/25 text-indigo-700 dark:text-indigo-300',
    o: 'bg-amber-500/25 text-amber-700 dark:text-amber-300'
};
</script>

<template>
    <div class="relative">
        <!-- Resplandor detrás, para que la tarjeta no flote sobre la nada -->
        <div class="absolute -inset-8 bg-gradient-to-tr from-primary-400/20 via-primary-300/10 to-transparent blur-3xl rounded-full" aria-hidden="true"></div>

        <div class="relative rounded-2xl bg-white dark:bg-slate-900 shadow-2xl shadow-slate-900/10 dark:shadow-black/40 ring-1 ring-slate-900/5 dark:ring-white/10 overflow-hidden">
            <!-- Barra del navegador: ubica que esto vive en la web, sin instalar -->
            <div class="flex items-center gap-2 px-4 py-3 bg-slate-50 dark:bg-slate-800/80 border-b border-slate-200 dark:border-slate-700">
                <span class="w-2.5 h-2.5 rounded-full bg-red-400"></span>
                <span class="w-2.5 h-2.5 rounded-full bg-amber-400"></span>
                <span class="w-2.5 h-2.5 rounded-full bg-green-400"></span>
                <div class="ml-3 flex-1 max-w-xs px-3 py-1 rounded-md bg-white dark:bg-slate-900 text-[10px] text-slate-400 dark:text-slate-500 truncate">consultorio.fichasalud.com.ar</div>
            </div>

            <div class="p-4 md:p-5">
                <div class="flex items-center justify-between mb-4">
                    <div>
                        <div class="h-2.5 w-24 rounded bg-slate-800 dark:bg-slate-200"></div>
                        <div class="h-2 w-16 rounded bg-slate-300 dark:bg-slate-600 mt-2"></div>
                    </div>
                    <div class="h-7 w-20 rounded-lg bg-primary-500"></div>
                </div>

                <div class="grid grid-cols-5 gap-1.5 text-[9px]">
                    <div v-for="d in DIAS" :key="d" class="text-center font-semibold text-slate-400 dark:text-slate-500 pb-1">
                        {{ d }}
                    </div>

                    <template v-for="(fila, i) in TURNOS" :key="i">
                        <div v-for="(celda, j) in fila" :key="`${i}-${j}`" class="h-7 rounded" :class="celda ? CLASES[celda] : 'bg-slate-100 dark:bg-slate-800'">
                            <div v-if="celda" class="h-full flex items-center px-1.5">
                                <div class="h-1 rounded-full bg-current opacity-50" :style="{ width: celda === 'g' ? '80%' : '60%' }"></div>
                            </div>
                        </div>
                    </template>
                </div>

                <div class="flex flex-wrap items-center gap-3 mt-4 pt-3 border-t border-slate-200 dark:border-slate-700 text-[9px] text-slate-400 dark:text-slate-500">
                    <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-sm bg-primary-500/70"></span> Consultorio</span>
                    <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-sm bg-indigo-400/70"></span> Grupal</span>
                    <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-sm bg-amber-400/70"></span> Reservado online</span>
                </div>
            </div>
        </div>
    </div>
</template>
