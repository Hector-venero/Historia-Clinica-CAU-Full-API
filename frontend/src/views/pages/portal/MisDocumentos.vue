<script setup>
import { computed, onMounted, ref } from 'vue';
import portalService from '@/service/portalService';
import { usePacienteStore } from '@/stores/paciente';
import { descargarBlob } from '@/utils/descargas';

const paciente = usePacienteStore();

const documentos = ref([]);
const cargando = ref(true);
const error = ref('');
const descargando = ref(null);
const filtro = ref('todos');

// El icono y el color salen del tipo. Son los cuatro que valida el backend, así
// que no puede llegar uno desconocido; igual hay respaldo por las dudas.
const ESTILOS = {
    estudio: { icono: 'pi-image', etiqueta: 'Estudio', clase: 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/40' },
    receta: { icono: 'pi-file-edit', etiqueta: 'Receta', clase: 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-950/40' },
    informe: { icono: 'pi-file', etiqueta: 'Informe', clase: 'text-purple-600 dark:text-purple-400 bg-purple-50 dark:bg-purple-950/40' },
    indicacion: { icono: 'pi-list-check', etiqueta: 'Indicación', clase: 'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/40' }
};

const estilo = (tipo) => ESTILOS[tipo] || { icono: 'pi-file', etiqueta: tipo, clase: 'text-surface-600 dark:text-surface-300 bg-surface-100 dark:bg-surface-800' };

const filtrados = computed(() => (filtro.value === 'todos' ? documentos.value : documentos.value.filter((d) => d.tipo === filtro.value)));

const sinLeer = computed(() => documentos.value.filter((d) => !d.leido_en).length);

// Los consultorios que le enviaron algo. Es la prueba visible de lo que hace el
// portal: ver junto lo que viene de lugares distintos.
const consultorios = computed(() => [...new Set(documentos.value.map((d) => d.consultorio_nombre))]);

function fecha(valor) {
    if (!valor) return '';
    return new Date(valor).toLocaleDateString('es-AR', { day: '2-digit', month: 'short', year: 'numeric' });
}

async function cargar() {
    cargando.value = true;
    error.value = '';
    try {
        const { data } = await portalService.documentos();
        documentos.value = data;
    } catch {
        error.value = 'No pudimos cargar tus documentos. Probá de nuevo en un momento.';
    } finally {
        cargando.value = false;
    }
}

async function abrir(doc) {
    if (!doc.leido_en) {
        // Optimista: si falla el marcado, no vale la pena molestar al paciente.
        doc.leido_en = new Date().toISOString();
        portalService.marcarLeido(doc.id).catch(() => {});
    }
}

async function descargar(doc) {
    descargando.value = doc.id;
    error.value = '';
    try {
        const { data } = await portalService.descargarArchivo(doc.id);
        descargarBlob(data, doc.archivo_nombre || `${doc.titulo}.pdf`);
        await abrir(doc);
    } catch {
        error.value = 'No pudimos descargar el archivo.';
    } finally {
        descargando.value = null;
    }
}

onMounted(cargar);
</script>

<template>
    <div class="max-w-4xl mx-auto p-4 md:p-6 space-y-5">
        <header>
            <h1 class="text-2xl md:text-3xl font-bold text-surface-900 dark:text-surface-0 m-0">Hola, {{ paciente.nombre }}</h1>
            <p class="text-sm text-surface-500 dark:text-surface-400 mt-1 mb-0">
                <template v-if="consultorios.length > 1"> Tenés documentos de {{ consultorios.length }} consultorios, todos acá. </template>
                <template v-else-if="documentos.length"> Lo que te enviaron tus profesionales. </template>
                <template v-else> Acá vas a ver lo que te envíen tus profesionales. </template>
            </p>
        </header>

        <!-- Filtros. Solo aparecen si hay algo que filtrar: con tres documentos
             una barra de filtros es ruido. -->
        <div v-if="documentos.length > 3" class="flex flex-wrap gap-2">
            <button
                v-for="op in ['todos', 'estudio', 'receta', 'informe', 'indicacion']"
                :key="op"
                type="button"
                class="px-3 py-1.5 rounded-lg text-sm font-medium transition"
                :class="filtro === op ? 'bg-primary-600 text-white' : 'bg-surface-100 dark:bg-surface-800 text-surface-600 dark:text-surface-300 hover:bg-surface-200 dark:hover:bg-surface-700'"
                @click="filtro = op"
            >
                {{ op === 'todos' ? 'Todos' : estilo(op).etiqueta }}
            </button>
        </div>

        <div v-if="error" class="p-3 rounded-xl bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-300 text-sm border border-red-200 dark:border-red-900">
            {{ error }}
        </div>

        <div v-if="cargando" class="text-center py-16 text-surface-500 dark:text-surface-400"><i class="pi pi-spin pi-spinner text-3xl mb-3 block"></i> Cargando…</div>

        <!-- Vacío. Se explica por qué está vacío en vez de dejar la pantalla
             muda: un paciente recién registrado no tiene forma de saber que
             depende de que un profesional le envíe algo. -->
        <div v-else-if="!documentos.length" class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-2xl p-10 text-center">
            <i class="pi pi-inbox text-5xl text-surface-300 dark:text-surface-600 mb-4 block"></i>
            <h2 class="text-lg font-semibold text-surface-900 dark:text-surface-0 m-0 mb-2">Todavía no tenés documentos</h2>
            <p class="text-sm text-surface-500 dark:text-surface-400 leading-relaxed max-w-md mx-auto m-0">
                Cuando un profesional te envíe un estudio, una receta o un informe, lo vas a ver acá. Si ya te atendiste, pedile que te lo mande a tu documento
                <strong>{{ paciente.numeroDocumento }}</strong
                >.
            </p>
        </div>

        <div v-else class="space-y-3">
            <p v-if="sinLeer" class="text-sm text-primary-700 dark:text-primary-400 font-medium m-0"><i class="pi pi-circle-fill text-[8px] mr-1"></i> {{ sinLeer }} sin abrir</p>

            <article
                v-for="doc in filtrados"
                :key="doc.id"
                class="bg-surface-0 dark:bg-surface-900 border rounded-2xl p-4 md:p-5 transition"
                :class="doc.leido_en ? 'border-surface-200 dark:border-surface-700' : 'border-primary-300 dark:border-primary-800'"
            >
                <div class="flex items-start gap-4">
                    <div class="w-11 h-11 rounded-xl flex items-center justify-center shrink-0" :class="estilo(doc.tipo).clase">
                        <i class="pi text-lg" :class="estilo(doc.tipo).icono"></i>
                    </div>

                    <div class="flex-1 min-w-0">
                        <div class="flex items-start justify-between gap-3">
                            <h3 class="font-semibold text-surface-900 dark:text-surface-0 m-0 break-words">
                                {{ doc.titulo }}
                            </h3>
                            <span v-if="!doc.leido_en" class="shrink-0 w-2 h-2 rounded-full bg-primary-500 mt-2" title="Sin abrir"></span>
                        </div>

                        <p v-if="doc.descripcion" class="text-sm text-surface-600 dark:text-surface-300 leading-relaxed mt-1 mb-0">
                            {{ doc.descripcion }}
                        </p>

                        <!-- De dónde vino. Es el dato que hace útil el portal
                             cuando alguien se atiende en más de un lugar. -->
                        <div class="flex flex-wrap items-center gap-x-3 gap-y-1 mt-2 text-xs text-surface-500 dark:text-surface-400">
                            <span><i class="pi pi-building mr-1"></i>{{ doc.consultorio_nombre }}</span>
                            <span v-if="doc.profesional_nombre"><i class="pi pi-user mr-1"></i>{{ doc.profesional_nombre }}</span>
                            <span><i class="pi pi-calendar mr-1"></i>{{ fecha(doc.enviado_en) }}</span>
                        </div>

                        <div v-if="doc.tiene_archivo" class="mt-3">
                            <button
                                type="button"
                                :disabled="descargando === doc.id"
                                class="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-60 transition"
                                @click="descargar(doc)"
                            >
                                <i :class="descargando === doc.id ? 'pi pi-spin pi-spinner' : 'pi pi-download'"></i>
                                {{ descargando === doc.id ? 'Descargando…' : 'Descargar' }}
                            </button>
                        </div>
                        <button v-else-if="!doc.leido_en" type="button" class="mt-3 text-sm text-primary-600 dark:text-primary-400 font-medium hover:underline" @click="abrir(doc)">Marcar como leído</button>
                    </div>
                </div>
            </article>
        </div>
    </div>
</template>
