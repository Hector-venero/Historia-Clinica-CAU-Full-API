<script setup>
/**
 * Términos y política de privacidad, con un solo componente para los dos.
 *
 * Mismo criterio que `Funcionalidad.vue`: son dos textos con la misma forma, así
 * que dos `.vue` casi idénticos serían dos lugares donde arreglar el mismo
 * detalle.
 *
 * ⚠️ Mientras `PUBLICADO` sea false, la página avisa que el texto está en
 * revisión en lugar de mostrarlo como si rigiera. Un texto legal sin revisar
 * puesto como vigente es peor que no tener ninguno: compromete a algo que nadie
 * leyó.
 */
import { computed } from 'vue';
import { useRoute } from 'vue-router';
import SitioLayout from './SitioLayout.vue';
import { ACTUALIZADO, DOCUMENTOS, PUBLICADO, VERSION } from './legales';

const route = useRoute();

const documento = computed(() => DOCUMENTOS[route.params.documento] || DOCUMENTOS.terminos);

// Las negritas del texto van en markdown mínimo, para no escribir HTML dentro
// de los datos: lo que se guarda ahí es texto, no marcado.
function conNegritas(texto) {
    return texto.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
}
</script>

<template>
    <SitioLayout>
        <section class="relative overflow-hidden py-14 md:py-20 border-b border-slate-200 dark:border-slate-800">
            <div class="absolute inset-0 -z-10 bg-gradient-to-b from-primary-50/60 to-white dark:from-primary-950/20 dark:to-slate-950" aria-hidden="true"></div>
            <div class="max-w-3xl mx-auto px-5">
                <h1 class="text-3xl md:text-4xl font-extrabold tracking-tight text-slate-900 dark:text-white">{{ documento.titulo }}</h1>
                <p class="mt-4 text-lg text-slate-600 dark:text-slate-300">{{ documento.bajada }}</p>
                <p class="mt-4 text-sm text-slate-500 dark:text-slate-400">Versión {{ VERSION }} · actualizado el {{ ACTUALIZADO }}</p>
            </div>
        </section>

        <section class="py-14 md:py-16">
            <div class="max-w-3xl mx-auto px-5">
                <!-- Sin revisar, se dice. No se muestra el texto como si rigiera. -->
                <div v-if="!PUBLICADO" class="mb-10 p-5 rounded-2xl border border-amber-300 dark:border-amber-900 bg-amber-50 dark:bg-amber-950/30">
                    <p class="font-semibold text-amber-900 dark:text-amber-200 m-0"><i class="pi pi-exclamation-triangle mr-2"></i>Este texto todavía no rige</p>
                    <p class="text-sm text-amber-800 dark:text-amber-300/90 mt-2 mb-0">
                        Es un borrador pendiente de revisión legal. Lo que sigue describe cómo funciona el sistema, pero no constituye todavía un acuerdo. Cuando esté revisado, esta advertencia desaparece.
                    </p>
                </div>

                <article class="space-y-10">
                    <div v-for="seccion in documento.secciones" :key="seccion.titulo">
                        <h2 class="text-xl md:text-2xl font-bold text-slate-900 dark:text-white">{{ seccion.titulo }}</h2>
                        <!-- eslint-disable-next-line vue/no-v-html -->
                        <p v-for="(parrafo, i) in seccion.cuerpo" :key="i" class="mt-3 leading-relaxed text-slate-600 dark:text-slate-300" v-html="conNegritas(parrafo)"></p>
                    </div>
                </article>

                <div class="mt-14 pt-8 border-t border-slate-200 dark:border-slate-800 flex flex-wrap gap-4 text-sm">
                    <router-link to="/legales/terminos" class="text-primary-600 dark:text-primary-400 hover:underline">Términos y condiciones</router-link>
                    <router-link to="/legales/privacidad" class="text-primary-600 dark:text-primary-400 hover:underline">Política de privacidad</router-link>
                </div>
            </div>
        </section>
    </SitioLayout>
</template>
