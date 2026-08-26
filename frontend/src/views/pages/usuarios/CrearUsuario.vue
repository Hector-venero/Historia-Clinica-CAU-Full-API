<script setup>
import { computed, reactive, ref } from 'vue';
import usuarioService from '@/service/usuarioService';
import { validarPasswordFuerte, validarEmail } from '@/utils/validators';

// Imports de PrimeVue
import InputText from 'primevue/inputtext';
import Password from 'primevue/password';
import Dropdown from 'primevue/dropdown'; // ✅ Corregido: Usamos Dropdown en vez de Select
import Button from 'primevue/button';

const form = reactive({
    nombre: '',
    username: '',
    email: '',
    password: '',
    rol: '',
    especialidad: '',
    // Datos que la receta electrónica necesita del profesional que la firma.
    apellido: '',
    dni: '',
    sexo: 'X',
    telefono: '',
    matricula_tipo: 'MN',
    matricula_numero: '',
    matricula_provincia: '',
    lugar_atencion_nombre: 'CAU - UNSAM',
    lugar_atencion_direccion: '',
    lugar_atencion_contacto: '',
    lugar_atencion_email: ''
});

const ESTADO_INICIAL = { ...form };

// Los cuatro valores del ENUM de la base. 'Otro' existe en el esquema y sin él
// se perdería al guardar.
const sexos = ref([
    { label: 'Femenino', value: 'F' },
    { label: 'Masculino', value: 'M' },
    { label: 'No binario / X', value: 'X' },
    { label: 'Otro', value: 'O' }
]);
const tiposMatricula = ref(['MN', 'MP', 'OP']);

// Solo estos roles firman recetas, así que solo a ellos se les piden los datos.
const rolPrescribe = () => ['Profesional', 'Director'].includes(form.rol);

const loading = ref(false);
const error = ref('');
const ok = ref('');

// ✅ Lista de roles corregida (incluye Área)
const roles = ref(['Director', 'Profesional', 'Administrativo', 'Área']);

// Los nombres de los roles no dicen qué puede hacer cada uno, y 'Área' no es
// una persona sino un módulo: sin explicarlo se elige por intuición.
const DESCRIPCION_ROL = {
    Director: 'Acceso total: usuarios, auditoría y todos los datos.',
    Profesional: 'Su agenda, sus pacientes y emisión de recetas.',
    Administrativo: 'Operación diaria: pacientes y turnos.',
    Área: 'No es una persona: representa una especialidad o módulo (ej. Kinesiología) para las agendas grupales.'
};

const ayudaRol = computed(() => DESCRIPCION_ROL[form.rol] || 'Define a qué pantallas y datos accede.');

function validate() {
    if (!form.nombre || !form.username || !form.email || !form.password || !form.rol) {
        return 'Todos los campos son obligatorios';
    }

    if (!validarEmail(form.email)) {
        return 'Email inválido';
    }

    const errPw = validarPasswordFuerte(form.password);
    if (errPw) return errPw;

    if (!roles.value.includes(form.rol)) {
        return 'Rol inválido';
    }

    // Validar especialidad solo si es Profesional
    if (form.rol === 'Profesional' && !form.especialidad) {
        return 'La especialidad es obligatoria para profesionales';
    }

    // Sin estos datos el profesional no va a poder emitir ninguna receta.
    if (rolPrescribe() && (!form.apellido || !form.dni || !form.matricula_numero || !form.lugar_atencion_direccion)) {
        return 'Para emitir recetas hacen falta apellido, DNI, número de matrícula y dirección del lugar de atención';
    }

    return '';
}

async function onSubmit() {
    error.value = '';
    ok.value = '';

    const v = validate();
    if (v) {
        error.value = v;
        return;
    }

    loading.value = true;
    try {
        // 1. Clonamos el formulario para no modificar la vista
        const payload = { ...form };

        // 2. Mapeo de roles para el Backend
        // El backend espera: 'director', 'profesional', 'administrativo', 'area'
        if (payload.rol === 'Área') {
            payload.rol = 'area';
        } else {
            payload.rol = payload.rol.toLowerCase();
        }

        // 3. La especialidad solo aplica a quienes prescriben
        if (!['profesional', 'director'].includes(payload.rol)) {
            payload.especialidad = null;
        }

        // 4. Enviamos el payload transformado
        const resp = await usuarioService.createUsuario(payload);
        ok.value = resp.data?.message || 'Usuario creado correctamente ✅';

        Object.assign(form, ESTADO_INICIAL);
    } catch (e) {
        error.value = e.response?.data?.error || e.message || 'Error al crear usuario';
    } finally {
        loading.value = false;
    }
}
</script>

<template>
    <div class="max-w-3xl mx-auto p-4 md:p-6 space-y-6">
        <header>
            <h1 class="text-2xl md:text-3xl font-bold text-surface-900 dark:text-surface-0 m-0">Crear usuario</h1>
            <p class="text-sm text-surface-500 dark:text-surface-400 mt-1 mb-0">Registrar un nuevo miembro del personal.</p>
        </header>

        <!-- autocomplete="off" en el formulario y campos con nombres que el
             navegador no reconoce como los de un login. Sin esto, el gestor de
             contraseñas rellenaba usuario y contraseña con las credenciales de
             quien estaba logueado: se llegaba a crear una cuenta nueva con la
             contraseña del director sin que nadie lo notara. -->
        <form class="space-y-6" autocomplete="off" @submit.prevent="onSubmit">
            <section class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-2xl p-5 md:p-6 space-y-5">
                <h2 class="seccion"><span class="paso">1</span> Datos de la cuenta</h2>

                <div class="flex flex-col gap-2">
                    <label class="etiqueta"><i class="pi pi-id-card mr-1 text-primary"></i> Nombre completo</label>
                    <InputText v-model.trim="form.nombre" placeholder="Ej: Ana Pérez (o Módulo Kinesiología)" class="w-full" autocomplete="off" :disabled="loading" />
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div class="flex flex-col gap-2">
                        <label class="etiqueta"><i class="pi pi-user mr-1 text-primary"></i> Usuario</label>
                        <InputText v-model.trim="form.username" name="usuario-nuevo" placeholder="Ej: aperez" class="w-full" autocomplete="off" :disabled="loading" />
                    </div>

                    <div class="flex flex-col gap-2">
                        <label class="etiqueta"><i class="pi pi-envelope mr-1 text-primary"></i> Email</label>
                        <InputText v-model.trim="form.email" type="email" placeholder="ana@ejemplo.com" class="w-full" autocomplete="off" :disabled="loading" />
                    </div>
                </div>

                <div class="flex flex-col gap-2">
                    <label class="etiqueta"><i class="pi pi-lock mr-1 text-primary"></i> Contraseña</label>
                    <!-- new-password y no off: es lo que respetan Chrome y Firefox
                         para no ofrecer la contraseña guardada del sitio. -->
                    <Password v-model="form.password" :feedback="false" toggleMask placeholder="Contraseña para el nuevo usuario" class="w-full" inputClass="w-full" autocomplete="new-password" :disabled="loading" />
                    <small class="text-surface-500 dark:text-surface-400">Mínimo 8 caracteres, con mayúscula, minúscula y número.</small>
                </div>

                <div class="flex flex-col gap-2">
                    <label class="etiqueta"><i class="pi pi-briefcase mr-1 text-primary"></i> Rol</label>
                    <Dropdown v-model="form.rol" :options="roles" placeholder="Seleccioná un rol" class="w-full" :disabled="loading" />
                    <small class="text-surface-500 dark:text-surface-400">{{ ayudaRol }}</small>
                </div>
            </section>

            <!-- Datos que la receta electrónica exige del profesional que la firma.
                 Sin apellido, DNI, matrícula y dirección de atención, el proveedor
                 rechaza la emisión. Por eso aparecen recién al elegir un rol que
                 prescribe: al resto no le hacen falta. -->
            <transition name="fade">
                <section v-if="rolPrescribe()" class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-2xl p-5 md:p-6 space-y-5">
                    <div>
                        <h2 class="seccion m-0"><span class="paso">2</span> Datos profesionales</h2>
                        <p class="text-sm text-surface-500 dark:text-surface-400 mt-1 mb-0">Se imprimen en cada receta. Sin ellos, {{ form.rol === 'Director' ? 'el director' : 'el profesional' }} no va a poder emitir.</p>
                    </div>

                    <div class="flex flex-col gap-2">
                        <label class="etiqueta"><i class="pi pi-heart mr-1 text-primary"></i> Especialidad</label>
                        <InputText v-model.trim="form.especialidad" placeholder="Ej: Cardiología, Pediatría..." class="w-full" autocomplete="off" :disabled="loading" />
                    </div>

                    <div class="space-y-4">
                        <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                            <div class="flex flex-col gap-1">
                                <label class="text-sm text-surface-600 dark:text-surface-300">Apellido</label>
                                <InputText v-model.trim="form.apellido" placeholder="Apellido" class="w-full" :disabled="loading" />
                            </div>
                            <div class="flex flex-col gap-1">
                                <label class="text-sm text-surface-600 dark:text-surface-300">DNI</label>
                                <InputText v-model.trim="form.dni" placeholder="Sin puntos" class="w-full" :disabled="loading" />
                            </div>
                            <div class="flex flex-col gap-1">
                                <label class="text-sm text-surface-600 dark:text-surface-300">Sexo</label>
                                <Dropdown v-model="form.sexo" :options="sexos" optionLabel="label" optionValue="value" class="w-full" :disabled="loading" />
                            </div>
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                            <div class="flex flex-col gap-1">
                                <label class="text-sm text-surface-600 dark:text-surface-300">Tipo de matrícula</label>
                                <Dropdown v-model="form.matricula_tipo" :options="tiposMatricula" class="w-full" :disabled="loading" />
                            </div>
                            <div class="flex flex-col gap-1">
                                <label class="text-sm text-surface-600 dark:text-surface-300">N° de matrícula</label>
                                <InputText v-model.trim="form.matricula_numero" class="w-full" :disabled="loading" />
                            </div>
                            <div class="flex flex-col gap-1">
                                <label class="text-sm text-surface-600 dark:text-surface-300">Provincia</label>
                                <InputText v-model.trim="form.matricula_provincia" placeholder="Ej: Buenos Aires" class="w-full" :disabled="loading" />
                            </div>
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                            <div class="flex flex-col gap-1">
                                <label class="text-sm text-surface-600 dark:text-surface-300">Lugar de atención</label>
                                <InputText v-model.trim="form.lugar_atencion_nombre" class="w-full" :disabled="loading" />
                            </div>
                            <div class="flex flex-col gap-1">
                                <label class="text-sm text-surface-600 dark:text-surface-300">Dirección de atención</label>
                                <InputText v-model.trim="form.lugar_atencion_direccion" placeholder="Calle y número" class="w-full" :disabled="loading" />
                            </div>
                            <div class="flex flex-col gap-1">
                                <label class="text-sm text-surface-600 dark:text-surface-300">Teléfono</label>
                                <InputText v-model.trim="form.telefono" class="w-full" :disabled="loading" />
                            </div>
                            <div class="flex flex-col gap-1">
                                <label class="text-sm text-surface-600 dark:text-surface-300">Email de contacto</label>
                                <InputText v-model.trim="form.lugar_atencion_email" class="w-full" :disabled="loading" />
                            </div>
                        </div>
                    </div>
                </section>
            </transition>

            <!-- Los mensajes no tenian variante oscura: quedaban con fondo claro
                 y texto oscuro sobre una pantalla oscura. -->
            <div v-if="error" class="rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 px-4 py-3 text-sm text-red-800 dark:text-red-200"><i class="pi pi-times-circle mr-2"></i> {{ error }}</div>

            <div v-if="ok" class="rounded-xl bg-green-50 dark:bg-green-950/40 border border-green-200 dark:border-green-800 px-4 py-3 text-sm text-green-800 dark:text-green-200"><i class="pi pi-check-circle mr-2"></i> {{ ok }}</div>

            <div class="flex justify-end">
                <Button type="submit" label="Crear usuario" icon="pi pi-user-plus" class="px-6 py-3 font-semibold" :loading="loading" />
            </div>
        </form>
    </div>
</template>

<style scoped>
.etiqueta {
    @apply font-semibold text-surface-700 dark:text-surface-200;
}

.seccion {
    @apply flex items-center gap-2 text-base font-semibold text-surface-900 dark:text-surface-0 m-0;
}

/* El numero de paso ordena la lectura sin necesidad de un componente de wizard. */
.paso {
    @apply inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold
           bg-primary-100 dark:bg-primary-900 text-primary-700 dark:text-primary-200;
}

.fade-enter-active,
.fade-leave-active {
    transition:
        opacity 0.3s ease,
        transform 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
    opacity: 0;
    transform: translateY(-10px);
}
</style>
