<script setup>
/**
 * "Usar plantilla" arriba de un campo de texto clínico.
 *
 * Se dibuja **solo si hay plantillas** para ese campo. Un consultorio que no
 * cargó ninguna no ve nada nuevo: el formulario queda como estaba.
 *
 * ⚠️ Inserta, no reemplaza a ciegas. Con el campo vacío pone el texto; con algo
 * escrito lo agrega debajo, separado por una línea en blanco. Pisar lo que
 * alguien ya escribió en una historia clínica por un clic mal dado es
 * exactamente el tipo de pérdida que no se puede deshacer desde la pantalla.
 */
import { computed, onMounted, ref } from 'vue';
import plantillaService from '@/service/plantillaService';

const props = defineProps({
    // 'evolucion' o 'indicaciones'. Separadas para no tener que leer veinte
    // opciones buscando una: un texto de indicaciones no sirve como evolución.
    campo: { type: String, required: true },
    // El texto actual del campo. Se necesita para decidir entre poner y agregar.
    modelValue: { type: String, default: '' }
});
const emit = defineEmits(['update:modelValue']);

const plantillas = ref([]);
const abierto = ref(false);

const hay = computed(() => plantillas.value.length > 0);

function usar(plantilla) {
    const actual = (props.modelValue || '').trim();
    emit('update:modelValue', actual ? `${actual}\n\n${plantilla.cuerpo}` : plantilla.cuerpo);
    abierto.value = false;
}

onMounted(async () => {
    try {
        const { data } = await plantillaService.listar({ campo: props.campo });
        plantillas.value = data || [];
    } catch {
        // Sin plantillas el formulario funciona igual. No vale mostrar un error
        // por una ayuda que no se pidió.
        plantillas.value = [];
    }
});
</script>

<template>
    <div v-if="hay" class="relative inline-block">
        <button type="button" class="inline-flex items-center gap-1.5 text-sm font-medium text-primary-600 dark:text-primary-400 hover:underline" @click="abierto = !abierto">
            <i class="pi pi-bolt text-xs"></i>
            Usar plantilla
        </button>

        <!-- Se cierra al elegir o al hacer clic en el velo. Un `blur` cerraría
             el panel antes de que el clic de adentro llegara a registrarse. -->
        <template v-if="abierto">
            <div class="fixed inset-0 z-10" @click="abierto = false"></div>
            <div class="absolute z-20 mt-2 w-80 max-h-72 overflow-y-auto rounded-xl border border-surface-200 dark:border-surface-700 bg-surface-0 dark:bg-surface-900 shadow-lg p-1">
                <button v-for="p in plantillas" :key="p.id" type="button" class="w-full text-left px-3 py-2 rounded-lg hover:bg-surface-100 dark:hover:bg-surface-800 transition" @click="usar(p)">
                    <span class="block font-medium text-surface-900 dark:text-surface-0">{{ p.nombre }}</span>
                    <span class="block text-xs text-surface-500 dark:text-surface-400 line-clamp-2">{{ p.cuerpo }}</span>
                </button>
                <p class="px-3 py-2 text-xs text-surface-400 dark:text-surface-500 m-0 border-t border-surface-200 dark:border-surface-700 mt-1">Se agrega al final de lo que ya escribiste. Podés editarlo antes de guardar.</p>
            </div>
        </template>
    </div>
</template>
