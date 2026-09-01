<script setup>
/**
 * El perfil del paciente.
 *
 * La barra del portal enlazaba a /portal/perfil desde el avatar, pero la ruta y
 * la pantalla no existian: el clic caia en el 404. El endpoint del backend
 * (`POST /api/portal/perfil`) ya estaba escrito, asi que faltaba solo esto.
 *
 * Lo que se puede cambiar es lo que decide `portal.actualizar_perfil()`:
 * telefono y cobertura. El **documento no**, y no es un olvido — es la llave con
 * la que dos consultorios le envian a la misma persona, asi que cambiarlo lo
 * desconectaria de todo lo que ya le mandaron. Se dice en pantalla, porque si no
 * la ausencia del campo parece un error.
 */
import { onMounted, reactive, ref } from 'vue';
import portalService from '@/service/portalService';
import { usePacienteStore } from '@/stores/paciente';

const paciente = usePacienteStore();

const form = reactive({
    telefono: '',
    fecha_nacimiento: '',
    sexo: '',
    cobertura: '',
    plan_cobertura: '',
    nro_afiliado: '',
    // Preferencias de aviso. Van en el mismo formulario y no en una pantalla
    // aparte: es una casilla, no una sección.
    avisar_documentos: true,
    avisar_turnos: true
});

const SEXOS = [
    { valor: '', texto: 'Prefiero no decirlo' },
    { valor: 'F', texto: 'Femenino' },
    { valor: 'M', texto: 'Masculino' },
    { valor: 'X', texto: 'No binario' },
    { valor: 'O', texto: 'Otro' }
];

const guardando = ref(false);
const mensaje = ref('');
const error = ref('');

function volcarDesdeStore() {
    form.telefono = paciente.telefono || '';
    form.cobertura = paciente.cobertura || '';
    form.plan_cobertura = paciente.planCobertura || '';
    form.nro_afiliado = paciente.nroAfiliado || '';
    form.fecha_nacimiento = (paciente.fechaNacimiento || '').slice(0, 10);
    form.sexo = paciente.sexo || '';
    form.avisar_documentos = paciente.avisarDocumentos !== false;
    form.avisar_turnos = paciente.avisarTurnos !== false;
}

onMounted(async () => {
    if (!paciente.autenticado) {
        try {
            await paciente.cargar();
        } catch {
            // El guard del router se encarga de redirigir.
        }
    }
    volcarDesdeStore();
});

async function guardar() {
    guardando.value = true;
    mensaje.value = '';
    error.value = '';
    try {
        const { data } = await portalService.actualizarPerfil({ ...form });
        // El backend devuelve la cuenta ya actualizada: se refresca el store con
        // eso y no con lo que se escribio en el formulario, que es lo que el
        // servidor decidio guardar.
        paciente.setPaciente(data);
        volcarDesdeStore();
        mensaje.value = 'Listo, guardamos tus datos.';
    } catch (e) {
        error.value = e?.response?.data?.error || 'No pudimos guardar los cambios.';
    } finally {
        guardando.value = false;
    }
}
</script>

<template>
    <div class="max-w-4xl mx-auto p-4 md:p-6 space-y-5">
        <header>
            <h1 class="text-2xl md:text-3xl font-bold text-surface-900 dark:text-surface-0 m-0">Mi perfil</h1>
            <p class="text-sm text-surface-500 dark:text-surface-400 mt-1 mb-0">Los datos que ven tus profesionales cuando les sacás un turno.</p>
        </header>

        <!-- Identidad: se muestra, no se edita. -->
        <section class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-2xl p-5">
            <div class="flex items-start gap-4">
                <div class="w-12 h-12 rounded-full bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300 flex items-center justify-center font-bold shrink-0">
                    {{ (paciente.nombre?.[0] || '') + (paciente.apellido?.[0] || '') }}
                </div>
                <div class="min-w-0">
                    <p class="font-semibold text-surface-900 dark:text-surface-0 m-0">{{ paciente.nombreCompleto }}</p>
                    <p class="text-sm text-surface-500 dark:text-surface-400 m-0 mt-0.5">{{ paciente.email }}</p>
                    <p class="text-sm text-surface-500 dark:text-surface-400 m-0 mt-0.5">{{ paciente.tipoDocumento }} {{ paciente.numeroDocumento }}</p>
                </div>
            </div>

            <p class="text-xs text-surface-500 dark:text-surface-400 mt-4 mb-0 pt-4 border-t border-surface-200 dark:border-surface-700">
                <i class="pi pi-info-circle mr-1"></i>
                Tu documento no se puede cambiar desde acá: es con lo que tus profesionales te reconocen, así que cambiarlo te dejaría sin los estudios que ya te enviaron. Si está mal cargado, escribinos.
            </p>
        </section>

        <!-- Lo editable -->
        <form class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-2xl p-5 space-y-4" @submit.prevent="guardar">
            <div class="grid sm:grid-cols-3 gap-4">
                <div class="flex flex-col gap-2">
                    <label class="text-sm font-semibold text-surface-700 dark:text-surface-200">Teléfono</label>
                    <input v-model="form.telefono" type="tel" placeholder="Ej: 11 5555 4444" class="campo" autocomplete="tel" />
                </div>
                <div class="flex flex-col gap-2">
                    <label class="text-sm font-semibold text-surface-700 dark:text-surface-200">Fecha de nacimiento</label>
                    <input v-model="form.fecha_nacimiento" type="date" class="campo" />
                </div>
                <div class="flex flex-col gap-2">
                    <label class="text-sm font-semibold text-surface-700 dark:text-surface-200">Sexo</label>
                    <select v-model="form.sexo" class="campo">
                        <option v-for="s in SEXOS" :key="s.valor" :value="s.valor">{{ s.texto }}</option>
                    </select>
                </div>
            </div>

            <div class="grid sm:grid-cols-2 gap-4">
                <div class="flex flex-col gap-2">
                    <label class="text-sm font-semibold text-surface-700 dark:text-surface-200">Obra social o prepaga</label>
                    <input v-model="form.cobertura" type="text" placeholder="Ej: OSDE" class="campo" />
                </div>
                <div class="flex flex-col gap-2">
                    <label class="text-sm font-semibold text-surface-700 dark:text-surface-200">Plan</label>
                    <input v-model="form.plan_cobertura" type="text" placeholder="Ej: 210" class="campo" />
                </div>
            </div>

            <div class="flex flex-col gap-2">
                <label class="text-sm font-semibold text-surface-700 dark:text-surface-200">Número de afiliado</label>
                <input v-model="form.nro_afiliado" type="text" class="campo" />
            </div>

            <!-- Avisos. Apagarlos no deja de guardar nada en el portal: lo que
                 se apaga es el correo, no el envío. -->
            <fieldset class="pt-4 border-t border-surface-200 dark:border-surface-700">
                <legend class="text-sm font-semibold text-surface-700 dark:text-surface-200 mb-1">Avisos por correo</legend>
                <p class="text-xs text-surface-500 dark:text-surface-400 mt-0 mb-3">Los documentos y los turnos te siguen apareciendo acá aunque apagues los correos.</p>

                <label class="flex items-start gap-3 cursor-pointer py-1.5">
                    <input v-model="form.avisar_documentos" type="checkbox" class="mt-0.5 w-4 h-4 shrink-0 accent-primary-600" />
                    <span class="text-sm text-surface-700 dark:text-surface-200">Avisarme cuando un profesional me envía un estudio o una receta</span>
                </label>
                <label class="flex items-start gap-3 cursor-pointer py-1.5">
                    <input v-model="form.avisar_turnos" type="checkbox" class="mt-0.5 w-4 h-4 shrink-0 accent-primary-600" />
                    <span class="text-sm text-surface-700 dark:text-surface-200">Avisarme cuando confirmo o cancelo un turno</span>
                </label>
            </fieldset>

            <div v-if="mensaje" class="p-3 rounded-xl bg-green-50 dark:bg-green-950/40 text-green-700 dark:text-green-300 text-sm border border-green-200 dark:border-green-900">
                {{ mensaje }}
            </div>

            <div v-if="error" class="p-3 rounded-xl bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-300 text-sm border border-red-200 dark:border-red-900">
                {{ error }}
            </div>

            <button type="submit" :disabled="guardando" class="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-semibold text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-60 transition">
                <i :class="guardando ? 'pi pi-spin pi-spinner' : 'pi pi-check'"></i>
                {{ guardando ? 'Guardando…' : 'Guardar cambios' }}
            </button>
        </form>
    </div>
</template>

<style scoped>
.campo {
    @apply w-full px-4 py-2.5 rounded-xl border border-surface-300 dark:border-surface-600 bg-surface-0 dark:bg-surface-800 text-surface-900 dark:text-surface-0 outline-none transition;
}
.campo:focus {
    @apply border-primary-500 ring-2 ring-primary-500/20;
}
</style>
