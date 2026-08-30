<script setup>
/**
 * La ficha de un paciente vista por un equipo, dibujada.
 *
 * Lo que le vende a un centro medico no es "tiene historia clinica": es que la
 * historia sea **una sola** y que se vea quien escribio cada cosa. El dibujo
 * muestra tres profesionales distintos sobre el mismo paciente, que es
 * exactamente lo que no se puede hacer con una carpeta de papel por consultorio.
 *
 * Dibujado y no capturado: pesa nada, sigue el modo oscuro y no queda viejo
 * cuando cambie la pantalla real. Los datos son inventados.
 */

const EVOLUCIONES = [
    { autor: 'Dra. Pereyra', area: 'Clínica médica', color: 'bg-primary-500', cuando: 'Hoy 09:40', adjuntos: 1 },
    { autor: 'Lic. Gómez', area: 'Kinesiología', color: 'bg-indigo-500', cuando: 'Lun 15:10', adjuntos: 0 },
    { autor: 'Dr. López', area: 'Traumatología', color: 'bg-amber-500', cuando: '12 ago', adjuntos: 2 }
];
</script>

<template>
    <div class="relative">
        <div class="absolute -inset-8 bg-gradient-to-tr from-indigo-400/15 via-primary-300/10 to-transparent blur-3xl rounded-full" aria-hidden="true"></div>

        <div class="relative rounded-2xl bg-white dark:bg-slate-900 shadow-2xl shadow-slate-900/10 dark:shadow-black/40 ring-1 ring-slate-900/5 dark:ring-white/10 overflow-hidden">
            <div class="flex items-center gap-2 px-4 py-3 bg-slate-50 dark:bg-slate-800/80 border-b border-slate-200 dark:border-slate-700">
                <span class="w-2.5 h-2.5 rounded-full bg-red-400"></span>
                <span class="w-2.5 h-2.5 rounded-full bg-amber-400"></span>
                <span class="w-2.5 h-2.5 rounded-full bg-green-400"></span>
                <div class="ml-3 flex-1 max-w-xs px-3 py-1 rounded-md bg-white dark:bg-slate-900 text-[10px] text-slate-400 dark:text-slate-500 truncate">centro.fichasalud.com.ar</div>
            </div>

            <div class="p-4 md:p-5">
                <!-- Cabecera de la ficha -->
                <div class="flex items-center gap-3 pb-4 border-b border-slate-200 dark:border-slate-700">
                    <div class="w-10 h-10 rounded-full bg-slate-200 dark:bg-slate-700 grid place-items-center text-xs font-bold text-slate-500 dark:text-slate-300">MR</div>
                    <div class="flex-1 min-w-0">
                        <div class="h-2.5 w-32 rounded bg-slate-800 dark:bg-slate-200"></div>
                        <div class="h-2 w-20 rounded bg-slate-300 dark:bg-slate-600 mt-2"></div>
                    </div>
                    <div class="hidden sm:block px-2.5 py-1 rounded-md text-[10px] font-semibold bg-primary-500/15 text-primary-700 dark:text-primary-300">HC 1042</div>
                </div>

                <!-- Evoluciones de tres profesionales sobre el mismo paciente -->
                <div class="mt-4 space-y-3">
                    <div v-for="e in EVOLUCIONES" :key="e.autor" class="flex gap-3">
                        <div class="flex flex-col items-center pt-1">
                            <span class="w-2 h-2 rounded-full shrink-0" :class="e.color"></span>
                            <span class="w-px flex-1 bg-slate-200 dark:bg-slate-700 mt-1"></span>
                        </div>
                        <div class="flex-1 min-w-0 pb-1">
                            <div class="flex items-baseline gap-2 flex-wrap">
                                <span class="text-[11px] font-semibold text-slate-800 dark:text-slate-100">{{ e.autor }}</span>
                                <span class="text-[10px] text-slate-400 dark:text-slate-500">{{ e.area }}</span>
                                <span class="text-[10px] text-slate-400 dark:text-slate-500 ml-auto">{{ e.cuando }}</span>
                            </div>
                            <div class="mt-2 space-y-1.5">
                                <div class="h-1.5 rounded-full bg-slate-200 dark:bg-slate-700 w-full"></div>
                                <div class="h-1.5 rounded-full bg-slate-200 dark:bg-slate-700 w-4/5"></div>
                            </div>
                            <div v-if="e.adjuntos" class="mt-2 flex gap-1.5">
                                <span v-for="n in e.adjuntos" :key="n" class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400">
                                    <i class="pi pi-paperclip text-[8px]"></i> adjunto
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>
