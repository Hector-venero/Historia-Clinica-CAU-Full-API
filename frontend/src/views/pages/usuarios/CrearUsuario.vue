<template>
    <div class="flex justify-center items-start p-6 md:p-8">
        <div class="bg-white dark:bg-[#1e1e1e] shadow-xl rounded-2xl p-8 w-full max-w-2xl transition-colors">
            <div class="text-center mb-8">
                <h1 class="text-3xl font-bold text-gray-800 dark:text-white mb-2">Crear Usuario</h1>
                <p class="text-gray-500 dark:text-gray-400">Registrar un nuevo miembro del personal</p>
            </div>

            <form @submit.prevent="onSubmit" class="space-y-6">
                <div class="flex flex-col gap-2">
                    <label class="font-semibold text-gray-700 dark:text-gray-200"> <i class="pi pi-id-card mr-1 text-primary"></i> Nombre completo </label>
                    <InputText v-model.trim="form.nombre" placeholder="Ej: Ana Pérez (o Módulo Kinesiología)" class="w-full" :disabled="loading" />
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div class="flex flex-col gap-2">
                        <label class="font-semibold text-gray-700 dark:text-gray-200"> <i class="pi pi-user mr-1 text-primary"></i> Usuario </label>
                        <InputText v-model.trim="form.username" placeholder="Ej: aperez" class="w-full" :disabled="loading" />
                    </div>

                    <div class="flex flex-col gap-2">
                        <label class="font-semibold text-gray-700 dark:text-gray-200"> <i class="pi pi-envelope mr-1 text-primary"></i> Email </label>
                        <InputText v-model.trim="form.email" type="email" placeholder="ana@ejemplo.com" class="w-full" :disabled="loading" />
                    </div>
                </div>

                <div class="flex flex-col gap-2">
                    <label class="font-semibold text-gray-700 dark:text-gray-200"> <i class="pi pi-lock mr-1 text-primary"></i> Contraseña </label>
                    <Password v-model="form.password" :feedback="false" toggleMask placeholder="********" class="w-full" inputClass="w-full" :disabled="loading" />
                    <small class="text-gray-500 dark:text-gray-400"> Mínimo 8 caracteres, mayúscula, minúscula y número. </small>
                </div>

                <div class="flex flex-col gap-2">
                    <label class="font-semibold text-gray-700 dark:text-gray-200"> <i class="pi pi-briefcase mr-1 text-primary"></i> Rol </label>
                    <Dropdown v-model="form.rol" :options="roles" placeholder="Seleccioná un rol" class="w-full" :disabled="loading" />
                </div>

                <transition name="fade">
                    <div v-if="rolPrescribe()" class="flex flex-col gap-2 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-xl border border-blue-100 dark:border-blue-800">
                        <label class="font-semibold text-gray-700 dark:text-gray-200"> <i class="pi pi-heart mr-1 text-primary"></i> Especialidad </label>
                        <InputText v-model.trim="form.especialidad" placeholder="Ej: Cardiología, Pediatría..." class="w-full" :disabled="loading" />
                    </div>
                </transition>

                <!-- Datos que la receta electrónica exige del profesional que la firma.
                     Sin apellido, DNI, matrícula y dirección de atención, el proveedor
                     rechaza la emisión. -->
                <transition name="fade">
                    <div v-if="rolPrescribe()" class="flex flex-col gap-4 p-4 bg-amber-50 dark:bg-amber-900/20 rounded-xl border border-amber-100 dark:border-amber-800">
                        <h3 class="font-semibold text-gray-700 dark:text-gray-200"><i class="pi pi-id-card mr-1 text-primary"></i> Datos para recetas electrónicas</h3>

                        <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                            <div class="flex flex-col gap-1">
                                <label class="text-sm text-gray-600 dark:text-gray-300">Apellido</label>
                                <InputText v-model.trim="form.apellido" placeholder="Apellido" class="w-full" :disabled="loading" />
                            </div>
                            <div class="flex flex-col gap-1">
                                <label class="text-sm text-gray-600 dark:text-gray-300">DNI</label>
                                <InputText v-model.trim="form.dni" placeholder="Sin puntos" class="w-full" :disabled="loading" />
                            </div>
                            <div class="flex flex-col gap-1">
                                <label class="text-sm text-gray-600 dark:text-gray-300">Sexo</label>
                                <Dropdown v-model="form.sexo" :options="sexos" optionLabel="label" optionValue="value" class="w-full" :disabled="loading" />
                            </div>
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                            <div class="flex flex-col gap-1">
                                <label class="text-sm text-gray-600 dark:text-gray-300">Tipo de matrícula</label>
                                <Dropdown v-model="form.matricula_tipo" :options="tiposMatricula" class="w-full" :disabled="loading" />
                            </div>
                            <div class="flex flex-col gap-1">
                                <label class="text-sm text-gray-600 dark:text-gray-300">N° de matrícula</label>
                                <InputText v-model.trim="form.matricula_numero" class="w-full" :disabled="loading" />
                            </div>
                            <div class="flex flex-col gap-1">
                                <label class="text-sm text-gray-600 dark:text-gray-300">Provincia</label>
                                <InputText v-model.trim="form.matricula_provincia" placeholder="Ej: Buenos Aires" class="w-full" :disabled="loading" />
                            </div>
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                            <div class="flex flex-col gap-1">
                                <label class="text-sm text-gray-600 dark:text-gray-300">Lugar de atención</label>
                                <InputText v-model.trim="form.lugar_atencion_nombre" class="w-full" :disabled="loading" />
                            </div>
                            <div class="flex flex-col gap-1">
                                <label class="text-sm text-gray-600 dark:text-gray-300">Dirección de atención</label>
                                <InputText v-model.trim="form.lugar_atencion_direccion" placeholder="Calle y número" class="w-full" :disabled="loading" />
                            </div>
                            <div class="flex flex-col gap-1">
                                <label class="text-sm text-gray-600 dark:text-gray-300">Teléfono</label>
                                <InputText v-model.trim="form.telefono" class="w-full" :disabled="loading" />
                            </div>
                            <div class="flex flex-col gap-1">
                                <label class="text-sm text-gray-600 dark:text-gray-300">Email de contacto</label>
                                <InputText v-model.trim="form.lugar_atencion_email" class="w-full" :disabled="loading" />
                            </div>
                        </div>
                    </div>
                </transition>

                <div v-if="error" class="p-3 rounded-lg bg-red-100 text-red-700 text-center font-medium border border-red-200"><i class="pi pi-times-circle mr-2"></i> {{ error }}</div>

                <div v-if="ok" class="p-3 rounded-lg bg-green-100 text-green-700 text-center font-medium border border-green-200"><i class="pi pi-check-circle mr-2"></i> {{ ok }}</div>

                <div class="flex justify-center pt-4">
                    <Button type="submit" label="Crear Usuario" icon="pi pi-user-plus" class="w-full md:w-auto px-8 py-3 font-bold shadow-lg" :loading="loading" />
                </div>
            </form>
        </div>
    </div>
</template>

<script setup>
import { reactive, ref } from 'vue';
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

<style scoped>
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
