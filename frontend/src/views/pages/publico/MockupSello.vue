<script setup>
/**
 * La verificacion de integridad, dibujada.
 *
 * Lo dificil de explicar del sellado en blockchain es que la verificacion tiene
 * **tres** estados y no dos: pendiente no es adulterado. El dibujo muestra los
 * tres, que es mas honesto que un tilde verde solo.
 */
const ESTADOS = [
    { icono: 'pi-check-circle', titulo: 'Historia verificada', detalle: 'Coincide con el sello del 12/08', clase: 'text-green-600 dark:text-green-400 bg-green-500/10' },
    { icono: 'pi-clock', titulo: 'Sellado pendiente', detalle: 'Esperando la confirmación del lote', clase: 'text-amber-600 dark:text-amber-400 bg-amber-500/10' },
    { icono: 'pi-check-circle', titulo: 'Evolución verificada', detalle: 'Acto médico del 03/07, sin cambios', clase: 'text-green-600 dark:text-green-400 bg-green-500/10' }
];
</script>

<template>
    <div class="relative">
        <div class="absolute -inset-8 bg-gradient-to-tr from-primary-400/20 via-primary-300/10 to-transparent blur-3xl rounded-full" aria-hidden="true"></div>

        <div class="relative rounded-2xl bg-white dark:bg-slate-900 shadow-2xl shadow-slate-900/10 dark:shadow-black/40 ring-1 ring-slate-900/5 dark:ring-white/10 overflow-hidden">
            <div class="px-5 py-4 border-b border-slate-200 dark:border-slate-700 flex items-center gap-3">
                <div class="w-9 h-9 rounded-xl grid place-items-center bg-primary-500/15 text-primary-600 dark:text-primary-400">
                    <i class="pi pi-verified"></i>
                </div>
                <div>
                    <p class="text-sm font-bold text-slate-900 dark:text-white m-0">Integridad</p>
                    <p class="text-[11px] text-slate-500 dark:text-slate-400 m-0">Blockchain Federal Argentina</p>
                </div>
            </div>

            <div class="p-5 space-y-2.5">
                <div v-for="e in ESTADOS" :key="e.titulo" class="flex items-center gap-3 p-3 rounded-xl" :class="e.clase">
                    <i class="pi shrink-0" :class="e.icono"></i>
                    <div class="min-w-0">
                        <p class="text-xs font-semibold m-0 truncate">{{ e.titulo }}</p>
                        <p class="text-[10px] opacity-80 m-0 mt-0.5 truncate">{{ e.detalle }}</p>
                    </div>
                </div>

                <!-- El hash: lo que realmente se compara -->
                <div class="mt-4 p-3 rounded-xl bg-slate-50 dark:bg-slate-800/70">
                    <p class="text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 m-0">Huella registrada</p>
                    <p class="mt-1.5 font-mono text-[10px] leading-relaxed text-slate-500 dark:text-slate-400 m-0 break-all">a3f9c1e0b7d4…2f8e6a91c05d</p>
                </div>
            </div>
        </div>
    </div>
</template>
