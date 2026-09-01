<script setup>
/**
 * El plan del consultorio: qué incluye y qué no.
 *
 * Hasta ahora `clientes.plan` no se traducía a módulos en ninguna parte y el
 * cliente no tenía forma de ver qué había contratado. Se pagaba algo que no
 * estaba escrito en ningún lado.
 *
 * Lo que no está incluido **se muestra igual**, con candado. Esconderlo le
 * ahorra una frustración a quien no paga y le cuesta la venta a quien sí
 * pagaría: nadie contrata lo que no sabe que existe.
 *
 * ⚠️ No hay contratación desde acá y no se finge que la hay. El botón abre un
 * correo, que es lo que realmente pasa hoy. Un "Contratar" que no cobra nada
 * es peor que no tenerlo.
 */
import { computed } from 'vue';
import { useUserStore } from '@/stores/user';
import { CORREO_CONTACTO } from '@/views/pages/publico/datos';

const userStore = useUserStore();

// El nombre y la explicación de cada módulo. El sistema los conoce por su clave
// (`recetas`, `grupos`), que no es lo que se le muestra a quien paga.
const CATALOGO = {
    turnos: { nombre: 'Agenda y turnos', detalle: 'Calendario, disponibilidad y turnos online.', icono: 'pi-calendar' },
    pacientes: { nombre: 'Pacientes', detalle: 'Ficha, búsqueda y datos de contacto.', icono: 'pi-users' },
    historias: { nombre: 'Historia clínica', detalle: 'Evoluciones, adjuntos y el resumen consolidado.', icono: 'pi-book' },
    recetas: { nombre: 'Recetas electrónicas', detalle: 'Medicamentos y estudios, con tus datos profesionales.', icono: 'pi-file-edit' },
    grupos: { nombre: 'Agendas grupales', detalle: 'Grupos de profesionales con calendario compartido.', icono: 'pi-sitemap' },
    comunicados: { nombre: 'Comunicados', detalle: 'Avisos para todo el equipo, con campana y correo.', icono: 'pi-megaphone' },
    blockchain: { nombre: 'Sellado en blockchain', detalle: 'Prueba de que una historia no se modificó después.', icono: 'pi-shield' }
};

function describir(clave) {
    return CATALOGO[clave] || { nombre: clave, detalle: '', icono: 'pi-box' };
}

const incluidos = computed(() => userStore.modulos.map(describir));
const faltantes = computed(() => userStore.modulosNoIncluidos.map(describir));

const asunto = computed(() => `Ampliar el plan de ${userStore.nombre || 'mi consultorio'}`);
</script>

<template>
    <div class="card">
        <header class="mb-8">
            <h2 class="text-2xl font-bold text-surface-900 dark:text-surface-0 m-0">Tu plan</h2>
            <p v-if="userStore.plan" class="text-surface-600 dark:text-surface-300 mt-2 mb-0">
                Estás en el plan <strong class="text-surface-900 dark:text-surface-0">{{ userStore.plan.nombre }}</strong
                >. Esto es lo que incluye.
            </p>
        </header>

        <section>
            <h3 class="text-sm font-semibold uppercase tracking-wide text-surface-400 dark:text-surface-500 mb-3">Incluido</h3>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div v-for="m in incluidos" :key="m.nombre" class="flex gap-3 p-4 rounded-xl border border-surface-200 dark:border-surface-700">
                    <i class="pi text-xl text-primary-600 dark:text-primary-400 mt-0.5" :class="m.icono"></i>
                    <div>
                        <p class="font-semibold text-surface-900 dark:text-surface-0 m-0">{{ m.nombre }}</p>
                        <p class="text-sm text-surface-500 dark:text-surface-400 m-0 mt-0.5">{{ m.detalle }}</p>
                    </div>
                </div>
            </div>
        </section>

        <!-- Lo que no está contratado. Se muestra, no se esconde. -->
        <section v-if="faltantes.length" class="mt-10">
            <h3 class="text-sm font-semibold uppercase tracking-wide text-surface-400 dark:text-surface-500 mb-3">No incluido en tu plan</h3>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div v-for="m in faltantes" :key="m.nombre" class="flex gap-3 p-4 rounded-xl border border-dashed border-surface-300 dark:border-surface-600 bg-surface-50 dark:bg-surface-800/50">
                    <i class="pi pi-lock text-xl text-surface-400 dark:text-surface-500 mt-0.5"></i>
                    <div>
                        <p class="font-semibold text-surface-700 dark:text-surface-200 m-0">{{ m.nombre }}</p>
                        <p class="text-sm text-surface-500 dark:text-surface-400 m-0 mt-0.5">{{ m.detalle }}</p>
                    </div>
                </div>
            </div>

            <!-- Un correo y no un botón de "Contratar": hoy no hay cobro
                 online, y un botón que no cobra nada promete algo que no pasa. -->
            <div class="mt-6 p-5 rounded-2xl bg-primary-50 dark:bg-primary-950/30 border border-primary-200 dark:border-primary-900">
                <p class="font-semibold text-surface-900 dark:text-surface-0 m-0">¿Te sirve algo de esto?</p>
                <p class="text-sm text-surface-600 dark:text-surface-300 mt-1 mb-4">Escribinos y lo vemos. Se activa sobre la misma cuenta, sin migrar nada ni volver a cargar tus pacientes.</p>
                <a :href="`mailto:${CORREO_CONTACTO}?subject=${encodeURIComponent(asunto)}`" class="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-white bg-primary-600 hover:bg-primary-700 transition no-underline">
                    <i class="pi pi-envelope"></i>
                    Escribir a {{ CORREO_CONTACTO }}
                </a>
            </div>
        </section>

        <p v-else class="mt-8 text-surface-500 dark:text-surface-400">Tu plan incluye todo lo que ofrecemos hoy.</p>
    </div>
</template>
