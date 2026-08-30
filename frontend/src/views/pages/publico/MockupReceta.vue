<script setup>
/**
 * Una receta emitida, dibujada.
 *
 * En la pagina de recetas el argumento es que sale **con tus datos**: tu
 * matricula, tu lugar de atencion, tu firma. Un dibujo de la receta lo muestra
 * de una; el texto tendria que explicarlo en tres oraciones.
 *
 * Los datos son inventados, y la matricula es deliberadamente ficticia.
 */
const MEDICAMENTOS = [
    { nombre: 'Amoxicilina 500 mg', presentacion: 'comprimidos · 21 unidades', cantidad: 1 },
    { nombre: 'Ibuprofeno 400 mg', presentacion: 'comprimidos · 20 unidades', cantidad: 2 }
];
</script>

<template>
    <div class="relative">
        <div class="absolute -inset-8 bg-gradient-to-tr from-primary-400/20 via-primary-300/10 to-transparent blur-3xl rounded-full" aria-hidden="true"></div>

        <div class="relative rounded-2xl bg-white dark:bg-slate-900 shadow-2xl shadow-slate-900/10 dark:shadow-black/40 ring-1 ring-slate-900/5 dark:ring-white/10 overflow-hidden">
            <!-- Encabezado: el bloque que sale de tu perfil profesional -->
            <div class="px-5 py-4 border-b border-slate-200 dark:border-slate-700 flex items-start justify-between gap-4">
                <div>
                    <p class="text-sm font-bold text-slate-900 dark:text-white m-0">Dra. Laura Pereyra</p>
                    <p class="text-[11px] text-slate-500 dark:text-slate-400 m-0 mt-0.5">Clínica médica · MN 00000</p>
                    <p class="text-[11px] text-slate-400 dark:text-slate-500 m-0">Av. Siempreviva 742 · San Martín</p>
                </div>
                <span class="shrink-0 px-2.5 py-1 rounded-md text-[10px] font-bold uppercase tracking-wide bg-primary-500/15 text-primary-700 dark:text-primary-300"> Emitida </span>
            </div>

            <div class="p-5">
                <p class="text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 m-0">Paciente</p>
                <div class="mt-2 flex items-center gap-3">
                    <div class="h-2.5 w-28 rounded bg-slate-800 dark:bg-slate-200"></div>
                    <div class="h-2 w-16 rounded bg-slate-300 dark:bg-slate-600"></div>
                </div>

                <p class="mt-5 text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 m-0">Prescripción</p>
                <div class="mt-2 space-y-2">
                    <div v-for="m in MEDICAMENTOS" :key="m.nombre" class="flex items-center gap-3 p-3 rounded-xl bg-slate-50 dark:bg-slate-800/70">
                        <div class="w-8 h-8 rounded-lg grid place-items-center bg-primary-500/15 text-primary-600 dark:text-primary-400 shrink-0">
                            <i class="pi pi-plus-circle text-sm"></i>
                        </div>
                        <div class="min-w-0 flex-1">
                            <p class="text-xs font-semibold text-slate-900 dark:text-white m-0 truncate">{{ m.nombre }}</p>
                            <p class="text-[10px] text-slate-500 dark:text-slate-400 m-0 mt-0.5 truncate">{{ m.presentacion }}</p>
                        </div>
                        <span class="text-[10px] font-bold text-slate-400 dark:text-slate-500 shrink-0">x{{ m.cantidad }}</span>
                    </div>
                </div>

                <div class="mt-4 flex items-center gap-2 text-[10px] text-slate-500 dark:text-slate-400">
                    <i class="pi pi-tag text-[9px]"></i>
                    <span>Diagnóstico J03.9 · Amigdalitis aguda</span>
                </div>

                <!-- Lo que se puede hacer después de emitir -->
                <div class="mt-5 pt-4 border-t border-slate-200 dark:border-slate-700 flex flex-wrap gap-2">
                    <span class="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[10px] font-semibold bg-slate-900 dark:bg-white text-white dark:text-slate-900"> <i class="pi pi-file-pdf text-[9px]"></i> Ver PDF </span>
                    <span class="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[10px] font-semibold bg-green-500/15 text-green-700 dark:text-green-400"> <i class="pi pi-whatsapp text-[9px]"></i> WhatsApp </span>
                    <span class="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[10px] font-semibold bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300"> <i class="pi pi-envelope text-[9px]"></i> Enviar por mail </span>
                </div>
            </div>
        </div>
    </div>
</template>
