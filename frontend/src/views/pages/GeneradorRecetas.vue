<script setup>
import { ref, onMounted } from 'vue';
import AutoComplete from 'primevue/autocomplete';
import InputNumber from 'primevue/inputnumber';
import Textarea from 'primevue/textarea';
import Select from 'primevue/select';
import DatePicker from 'primevue/datepicker';
import Button from 'primevue/button';
import api from '@/api/axios';

// Búsqueda de paciente en BD local
const pacienteBuscado = ref(null);
const sugerenciasPacientes = ref([]);
const pacienteId = ref(null);
const emailPaciente = ref('');

// Datos del paciente (se autocompletan al seleccionar o se ingresan manual)
const nombre = ref('');
const apellido = ref('');
const nroDni = ref('');
const sexo = ref(null);
const fechaNacimiento = ref(null);
const opcionesSexo = [
    { label: 'Masculino', value: 'M' },
    { label: 'Femenino', value: 'F' },
    { label: 'X', value: 'X' }
];

// Financiadores / cobertura
const financiadores = ref([]);
const financiadorSeleccionado = ref(null);
const nroAfiliado = ref('');

// Medicamento
const medicamentoSeleccionado = ref(null);
const sugerenciasMed = ref([]);
const cantidad = ref(1);
const posologia = ref('');

// Diagnóstico
const diagnosticoSeleccionado = ref(null);
const sugerenciasDiag = ref([]);

// Estado
const emitiendo = ref(false);
const errorEmision = ref('');
const mensajeExito = ref('');
const recetaEmitidaHash = ref('');
const recetaLink = ref('');

// Mapa de sexo de BD (Masculino/Femenino/Otro) al valor del Select (M/F/X)
const SEXO_MAP = { Masculino: 'M', Femenino: 'F', Otro: 'X' };

onMounted(async () => {
    try {
        const { data } = await api.get('/recetas/financiadores');
        financiadores.value = data.financiadores || [];
    } catch {
        financiadores.value = [];
    }
});

// ---------------------------------------------------------------------------
// Búsqueda y selección de paciente
// ---------------------------------------------------------------------------

async function buscarPacientesBD(event) {
    if (!event.query.trim()) {
        sugerenciasPacientes.value = [];
        return;
    }
    try {
        const { data } = await api.get('/recetas/buscar_paciente', { params: { q: event.query } });
        sugerenciasPacientes.value = data;
    } catch {
        sugerenciasPacientes.value = [];
    }
}

function seleccionarPaciente(event) {
    const p = event.value;
    // Limpiar receta previa al cambiar de paciente
    recetaEmitidaHash.value = '';
    recetaLink.value = '';
    errorEmision.value = '';
    mensajeExito.value = '';

    nombre.value = p.nombre;
    apellido.value = p.apellido;
    nroDni.value = p.dni;
    sexo.value = SEXO_MAP[p.sexo] || null;
    pacienteId.value = p.id;
    emailPaciente.value = p.email || '';

    if (p.fecha_nacimiento) {
        const [y, m, d] = p.fecha_nacimiento.split('-');
        fechaNacimiento.value = new Date(Number(y), Number(m) - 1, Number(d));
    } else {
        fechaNacimiento.value = null;
    }
}

// ---------------------------------------------------------------------------
// Búsquedas QBI2
// ---------------------------------------------------------------------------

async function buscarMedicamento(event) {
    // El backend exige 2 caracteres y devuelve 400 con menos: se corta acá
    // para no mostrar un error mientras el usuario todavía está tipeando.
    if (event.query.trim().length < 2) {
        sugerenciasMed.value = [];
        return;
    }
    try {
        const { data } = await api.get('/recetas/buscar_medicamento', { params: { q: event.query } });
        sugerenciasMed.value = data.medicamentos || [];
    } catch {
        sugerenciasMed.value = [];
    }
}

async function buscarDiagnostico(event) {
    // El backend exige 3 caracteres para diagnósticos.
    if (event.query.trim().length < 3) {
        sugerenciasDiag.value = [];
        return;
    }
    try {
        const { data } = await api.get('/recetas/buscar_diagnostico', { params: { q: event.query } });
        sugerenciasDiag.value = data.diagnosticos || [];
    } catch {
        sugerenciasDiag.value = [];
    }
}

// ---------------------------------------------------------------------------
// Emisión y acciones
// ---------------------------------------------------------------------------

async function emitirReceta() {
    errorEmision.value = '';
    mensajeExito.value = '';

    if (!pacienteId.value) {
        errorEmision.value = 'Seleccioná un paciente de la lista antes de emitir.';
        return;
    }

    emitiendo.value = true;
    try {
        // El backend toma los datos del paciente y del profesional de la base,
        // no del formulario: la receta tiene que declarar lo que figura en la
        // historia clínica, no lo que se haya tipeado en pantalla.
        const payload = {
            paciente_id: pacienteId.value,
            tipo: 'receta',
            email_paciente: emailPaciente.value,
            medicamentos: [
                {
                    regNo: medicamentoSeleccionado.value?.regNo,
                    nombreProducto: medicamentoSeleccionado.value?.nombreProducto,
                    cantidad: cantidad.value,
                    posologia: posologia.value
                }
            ]
        };

        if (diagnosticoSeleccionado.value?.coddiagnostico) {
            payload.codigoDiagnostico = diagnosticoSeleccionado.value.coddiagnostico;
            payload.diagnostico = diagnosticoSeleccionado.value.diagnostico || '';
        }

        if (financiadorSeleccionado.value && nroAfiliado.value) {
            payload.cobertura = {
                idFinanciador: String(financiadorSeleccionado.value),
                numero: String(nroAfiliado.value)
            };
        }

        const { data } = await api.post('/recetas/emitir', payload);
        recetaEmitidaHash.value = data.receta_hash || '';
        recetaLink.value = data.link_pdf || '';
    } catch (e) {
        errorEmision.value = e?.response?.data?.error || 'Error al emitir la receta.';
    } finally {
        emitiendo.value = false;
    }
}

function abrirPdf() {
    if (recetaLink.value) window.open(recetaLink.value, '_blank');
}

function enviarWhatsApp() {
    if (recetaLink.value) {
        const url = `https://api.whatsapp.com/send?text=Hola, aquí tienes tu receta electrónica: ${recetaLink.value}`;
        window.open(url, '_blank');
    }
}

async function enviarEmailManual() {
    errorEmision.value = '';
    mensajeExito.value = '';
    try {
        await api.post('/recetas/enviar_mail_manual', {
            email: emailPaciente.value,
            nombre_paciente: `${nombre.value} ${apellido.value}`.trim(),
            link_pdf: recetaLink.value,
            nombre_med: medicamentoSeleccionado.value?.nombreProducto || ''
        });
        mensajeExito.value = 'Receta enviada por email correctamente.';
    } catch (e) {
        errorEmision.value = e?.response?.data?.error || 'Error al enviar el email.';
    }
}

async function anularReceta() {
    errorEmision.value = '';
    mensajeExito.value = '';
    try {
        await api.delete(`/recetas/anular/${recetaEmitidaHash.value}`);
        mensajeExito.value = 'Receta anulada correctamente.';
        recetaEmitidaHash.value = '';
        recetaLink.value = '';
    } catch (e) {
        errorEmision.value = e?.response?.data?.error || 'Error al anular la receta.';
    }
}
</script>

<template>
    <div class="min-h-screen p-6 md:p-10 app-bg transition-colors">
        <div class="max-w-3xl mx-auto space-y-8">
            <h1 class="text-2xl font-bold text-gray-800 dark:text-white flex items-center gap-2">
                <i class="pi pi-file-edit text-primary-500"></i>
                Generador de Recetas
            </h1>

            <!-- Datos del Paciente -->
            <div class="bg-white dark:bg-[#1e1e1e] rounded-xl shadow p-6 space-y-4">
                <h2 class="text-base font-semibold text-gray-700 dark:text-gray-200 flex items-center gap-2"><i class="pi pi-user text-primary-500"></i> Datos del Paciente</h2>

                <!-- Buscador por nombre, apellido o DNI -->
                <div class="flex flex-col gap-1">
                    <label class="text-sm text-gray-600 dark:text-gray-400">Buscar paciente (nombre, apellido o DNI)</label>
                    <AutoComplete
                        v-model="pacienteBuscado"
                        :suggestions="sugerenciasPacientes"
                        @complete="buscarPacientesBD"
                        @select="seleccionarPaciente"
                        :optionLabel="(p) => `${p.nombre} ${p.apellido} — DNI: ${p.dni}`"
                        :inputProps="{ placeholder: 'Escriba para buscar...' }"
                        forceSelection
                        class="w-full"
                        inputClass="w-full"
                    >
                        <template #option="{ option }">
                            <div class="flex flex-col">
                                <span class="font-medium">{{ option.nombre }} {{ option.apellido }}</span>
                                <span class="text-xs text-gray-500">DNI: {{ option.dni }}</span>
                            </div>
                        </template>
                    </AutoComplete>
                </div>

                <!-- Campos del paciente (se autocompletan al seleccionar) -->
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div class="flex flex-col gap-1">
                        <label class="text-sm text-gray-600 dark:text-gray-400">Nombre</label>
                        <InputText v-model="nombre" placeholder="Nombre" class="w-full" />
                    </div>
                    <div class="flex flex-col gap-1">
                        <label class="text-sm text-gray-600 dark:text-gray-400">Apellido</label>
                        <InputText v-model="apellido" placeholder="Apellido" class="w-full" />
                    </div>
                    <div class="flex flex-col gap-1">
                        <label class="text-sm text-gray-600 dark:text-gray-400">Nro DNI</label>
                        <InputText v-model="nroDni" placeholder="Ej: 30123456" class="w-full" />
                    </div>
                    <div class="flex flex-col gap-1">
                        <label class="text-sm text-gray-600 dark:text-gray-400">Sexo</label>
                        <Select v-model="sexo" :options="opcionesSexo" optionLabel="label" optionValue="value" placeholder="Seleccionar" class="w-full" />
                    </div>
                    <div class="flex flex-col gap-1 sm:col-span-2">
                        <label class="text-sm text-gray-600 dark:text-gray-400">Fecha de Nacimiento</label>
                        <DatePicker v-model="fechaNacimiento" dateFormat="dd/mm/yy" placeholder="DD/MM/AAAA" showIcon class="w-full" />
                    </div>
                    <div class="flex flex-col gap-1 sm:col-span-2">
                        <label class="text-sm text-gray-600 dark:text-gray-400">Email del paciente (para envío de receta)</label>
                        <InputText v-model="emailPaciente" placeholder="correo@ejemplo.com" class="w-full" />
                    </div>

                    <!-- Obra Social -->
                    <div class="flex flex-col gap-1 sm:col-span-2">
                        <label class="text-sm text-gray-600 dark:text-gray-400">Obra Social (opcional)</label>
                        <Select v-model="financiadorSeleccionado" :options="financiadores" optionLabel="nombreComercial" optionValue="idfinanciador" placeholder="Sin cobertura" :filter="true" class="w-full" />
                    </div>
                    <div v-if="financiadorSeleccionado" class="flex flex-col gap-1 sm:col-span-2">
                        <label class="text-sm text-gray-600 dark:text-gray-400">Nro de Afiliado</label>
                        <InputText v-model="nroAfiliado" placeholder="Nro de afiliado" class="w-full" />
                    </div>
                </div>
            </div>

            <!-- Medicamento -->
            <div class="bg-white dark:bg-[#1e1e1e] rounded-xl shadow p-6 space-y-4">
                <h2 class="text-base font-semibold text-gray-700 dark:text-gray-200 flex items-center gap-2"><i class="pi pi-heart text-primary-500"></i> Medicamento</h2>
                <AutoComplete
                    v-model="medicamentoSeleccionado"
                    :suggestions="sugerenciasMed"
                    @complete="buscarMedicamento"
                    :inputProps="{ placeholder: 'Buscar medicamento...' }"
                    optionLabel="nombreProducto"
                    forceSelection
                    class="w-full"
                    inputClass="w-full"
                />
                <div v-if="medicamentoSeleccionado" class="text-sm text-green-600 dark:text-green-400">
                    <i class="pi pi-check mr-1"></i>
                    <strong>{{ medicamentoSeleccionado.nombreProducto }}</strong>
                </div>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div class="flex flex-col gap-1">
                        <label class="text-sm text-gray-600 dark:text-gray-400">Cantidad</label>
                        <InputNumber v-model="cantidad" :min="1" :max="99" showButtons class="w-full" />
                    </div>
                    <div class="flex flex-col gap-1">
                        <label class="text-sm text-gray-600 dark:text-gray-400">Posología</label>
                        <Textarea v-model="posologia" placeholder="Ej: 1 comprimido cada 8 horas" rows="2" class="w-full" />
                    </div>
                </div>
            </div>

            <!-- Diagnóstico -->
            <div class="bg-white dark:bg-[#1e1e1e] rounded-xl shadow p-6 space-y-3">
                <h2 class="text-base font-semibold text-gray-700 dark:text-gray-200 flex items-center gap-2"><i class="pi pi-list text-primary-500"></i> Diagnóstico (CIE-10)</h2>
                <AutoComplete
                    v-model="diagnosticoSeleccionado"
                    :suggestions="sugerenciasDiag"
                    @complete="buscarDiagnostico"
                    :inputProps="{ placeholder: 'Buscar diagnóstico...' }"
                    optionLabel="descdiagnostico"
                    forceSelection
                    class="w-full"
                    inputClass="w-full"
                />
                <div v-if="diagnosticoSeleccionado" class="text-sm text-green-600 dark:text-green-400">
                    <i class="pi pi-check mr-1"></i>
                    <strong>{{ diagnosticoSeleccionado.descdiagnostico }}</strong>
                </div>
            </div>

            <!-- Mensajes -->
            <div v-if="errorEmision" class="text-red-500 text-sm font-medium flex items-center gap-2"><i class="pi pi-exclamation-triangle"></i> {{ errorEmision }}</div>
            <div v-if="mensajeExito" class="text-green-600 text-sm font-medium flex items-center gap-2"><i class="pi pi-check-circle"></i> {{ mensajeExito }}</div>

            <!-- Acciones -->
            <div class="flex flex-wrap justify-end gap-3">
                <Button v-if="recetaEmitidaHash" label="Anular Receta" icon="pi pi-times-circle" severity="danger" @click="anularReceta" />
                <Button v-if="recetaEmitidaHash" label="Ver PDF" icon="pi pi-file-pdf" severity="info" @click="abrirPdf" />
                <Button v-if="recetaEmitidaHash" label="Enviar por WhatsApp" icon="pi pi-whatsapp" severity="success" @click="enviarWhatsApp" />
                <Button v-if="recetaEmitidaHash" label="Enviar por Email" icon="pi pi-envelope" severity="help" @click="enviarEmailManual" />
                <Button label="Emitir Receta" icon="pi pi-send" :loading="emitiendo" @click="emitirReceta" class="px-6" />
            </div>
        </div>
    </div>
</template>
