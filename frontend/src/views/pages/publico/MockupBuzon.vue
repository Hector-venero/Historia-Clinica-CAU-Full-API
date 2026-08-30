<script setup>
/**
 * El buzon del paciente, dibujado.
 *
 * Estaba escrito dentro de la portada. Se saco a un componente cuando la pagina
 * de funcionalidades necesito mostrar lo mismo: dos copias del dibujo terminan
 * divergiendo y contando cosas distintas del mismo producto.
 *
 * Lo que tiene que entenderse de una mirada es que los documentos vienen de
 * **consultorios distintos**. Ese es el argumento entero del portal, y por eso
 * los ejemplos nombran tres lugares y no uno.
 */

defineProps({
    // En el fondo oscuro de la portada el dibujo va translucido; sobre fondo
    // claro necesita tarjetas propias o se pierde.
    oscuro: { type: Boolean, default: false }
});

const DOCUMENTOS = [
    { icono: 'pi-image', titulo: 'Radiografía panorámica', de: 'Consultorio Dental Sur', cuando: 'Ayer', color: 'text-blue-500 bg-blue-500/15' },
    { icono: 'pi-file-edit', titulo: 'Receta — Amoxicilina 500 mg', de: 'Dr. López · Clínica médica', cuando: 'Hace 3 días', color: 'text-green-500 bg-green-500/15' },
    { icono: 'pi-calendar', titulo: 'Turno confirmado — mié 14:00', de: 'Centro Kinésico Sur', cuando: 'Hace 1 semana', color: 'text-amber-500 bg-amber-500/15' },
    { icono: 'pi-file', titulo: 'Orden de laboratorio', de: 'Dra. Pereyra · Endocrinología', cuando: 'Hace 2 semanas', color: 'text-violet-500 bg-violet-500/15' }
];
</script>

<template>
    <div class="space-y-3">
        <div
            v-for="doc in DOCUMENTOS"
            :key="doc.titulo"
            class="flex items-center gap-4 p-4 rounded-xl transition"
            :class="oscuro ? 'bg-white/5 ring-1 ring-white/10 backdrop-blur-sm' : 'bg-white dark:bg-slate-900 ring-1 ring-slate-200 dark:ring-slate-800 shadow-sm'"
        >
            <div class="w-10 h-10 rounded-lg grid place-items-center shrink-0" :class="doc.color">
                <i class="pi" :class="doc.icono"></i>
            </div>
            <div class="min-w-0 flex-1">
                <p class="font-medium text-sm m-0 truncate" :class="oscuro ? 'text-white' : 'text-slate-900 dark:text-white'">{{ doc.titulo }}</p>
                <p class="text-xs m-0 mt-0.5 truncate" :class="oscuro ? 'text-slate-400' : 'text-slate-500 dark:text-slate-400'">{{ doc.de }}</p>
            </div>
            <span class="text-[11px] shrink-0" :class="oscuro ? 'text-slate-500' : 'text-slate-400 dark:text-slate-500'">{{ doc.cuando }}</span>
        </div>
    </div>
</template>
