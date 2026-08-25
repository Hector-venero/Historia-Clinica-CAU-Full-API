<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import api from '@/api/axios';
import { useUserStore } from '@/stores/user';
import { buildFotoURL } from '@/utils/fotoUrl.js';

const userStore = useUserStore();

// Campos del formulario
const nombre = ref('');
const email = ref('');

// Datos que la receta electrónica exige del profesional que la firma.
// Los edita cada uno: es quien conoce su matrícula y dónde atiende.
const CAMPOS_PROFESIONALES = ['apellido', 'dni', 'sexo', 'telefono', 'matricula_tipo', 'matricula_numero', 'matricula_provincia', 'lugar_atencion_nombre', 'lugar_atencion_direccion', 'lugar_atencion_contacto', 'lugar_atencion_email'];

const perfil = reactive(Object.fromEntries(CAMPOS_PROFESIONALES.map((c) => [c, ''])));

const SEXOS = [
    { label: 'Femenino', value: 'F' },
    { label: 'Masculino', value: 'M' },
    { label: 'No binario / X', value: 'X' },
    { label: 'Otro', value: 'O' }
];
const TIPOS_MATRICULA = ['MN', 'MP', 'OP'];

const puedePrescribir = computed(() => ['profesional', 'director'].includes((userStore.rol || '').toLowerCase()));
const archivoFoto = ref(null);
const previewFoto = ref(null);
const mensaje = ref('');
const error = ref('');

// Variable reactiva para forzar la recarga de la imagen
const imgVersion = ref(Date.now());

// Cargar datos iniciales
onMounted(async () => {
    if (!userStore.id) {
        await userStore.fetchUser();
    }
    nombre.value = userStore.nombre || '';
    email.value = userStore.email || '';

    // Los campos profesionales se piden al backend: el store no los tiene.
    try {
        const { data } = await api.get('/usuario/perfil', { withCredentials: true });
        CAMPOS_PROFESIONALES.forEach((campo) => {
            perfil[campo] = data?.[campo] ?? '';
        });
    } catch (err) {
        console.error('No se pudieron cargar los datos profesionales:', err);
    }
});

/**
 * PROPIEDAD COMPUTADA INTELIGENTE:
 * 1. Si hay preview (usuario subió archivo pero no guardó), muestra eso.
 * 2. Si hay foto en BD, construye la URL con un timestamp (imgVersion) para evitar caché.
 * 3. Si no hay nada, devuelve null (para activar el v-else del avatar con letra).
 */
const imagenA_Mostrar = computed(() => {
    if (previewFoto.value) return previewFoto.value;
    if (userStore.foto) return buildFotoURL(userStore.foto, imgVersion.value);
    return null;
});

/* Selección de archivo */
const onFileChange = (e) => {
    const file = e.target.files[0];
    if (!file) {
        archivoFoto.value = null;
        previewFoto.value = null;
        return;
    }
    archivoFoto.value = file;
    previewFoto.value = URL.createObjectURL(file);
};

/* Guardar perfil */
const actualizarPerfil = async () => {
    mensaje.value = '';
    error.value = '';

    try {
        const form = new FormData();
        form.append('nombre', nombre.value);
        form.append('email', email.value);

        // Solo se mandan si el rol prescribe; el backend actualiza únicamente
        // las claves que llegan, así que no se pisa nada de los demás roles.
        if (puedePrescribir.value) {
            CAMPOS_PROFESIONALES.forEach((campo) => form.append(campo, perfil[campo] ?? ''));
        }

        if (archivoFoto.value) {
            form.append('foto', archivoFoto.value);
        }

        await api.post('/usuario/perfil', form, {
            withCredentials: true,
            headers: { 'Content-Type': 'multipart/form-data' }
        });

        mensaje.value = 'Perfil actualizado correctamente ✅';

        // 1. Recargar datos del usuario
        await userStore.fetchUser();
        userStore.recargarImagen();
        // 2. Limpiar preview local
        previewFoto.value = null;
        archivoFoto.value = null;

        // 3. ¡TRUCO! Actualizamos esta variable para que la URL cambie (ej: user_1.jpg?t=12345)
        // Esto obliga al navegador a bajar la imagen nueva
        imgVersion.value = Date.now();
    } catch (err) {
        console.error(err);
        error.value = 'Error al actualizar el perfil.';
    }
};

/* ELIMINAR FOTO */
const eliminarFoto = async () => {
    if (!confirm('¿Estás seguro de eliminar tu foto?')) return;

    try {
        await api.delete('/usuario/foto', { withCredentials: true });

        await userStore.fetchUser();
        userStore.recargarImagen();
        // Limpiar todo para que se muestre la letra inicial
        previewFoto.value = null;
        archivoFoto.value = null;
        imgVersion.value = Date.now();

        mensaje.value = 'Foto eliminada correctamente.';
    } catch (err) {
        console.error(err);
        error.value = 'No se pudo eliminar la foto.';
    }
};
</script>

<template>
    <div class="max-w-lg mx-auto bg-white p-8 rounded-2xl shadow-lg mt-6 border border-gray-100">
        <h1 class="text-2xl font-bold mb-8 text-gray-800 text-center">Editar mi Perfil</h1>

        <div class="flex flex-col items-center mb-8">
            <div v-if="imagenA_Mostrar" class="mb-4 relative group">
                <img :src="imagenA_Mostrar" class="w-32 h-32 rounded-full object-cover border-4 border-blue-50 shadow-md" alt="Foto de perfil" />
            </div>

            <div v-else class="mb-4 w-32 h-32 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 text-5xl font-bold border-4 border-white shadow-md select-none">
                {{ nombre ? nombre.charAt(0).toUpperCase() : 'U' }}
            </div>

            <label class="cursor-pointer bg-gray-50 hover:bg-gray-100 text-gray-700 px-4 py-2 rounded-lg transition border border-gray-200 text-sm font-medium flex items-center gap-2">
                <i class="pi pi-camera text-lg"></i>
                <span>{{ userStore.foto || previewFoto ? 'Cambiar foto' : 'Subir foto' }}</span>
                <input type="file" class="hidden" accept="image/*" @change="onFileChange" />
            </label>
        </div>

        <div class="space-y-5">
            <div>
                <label class="block mb-2 font-semibold text-gray-700 text-sm">Nombre completo</label>
                <input v-model="nombre" type="text" class="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition bg-gray-50" />
            </div>

            <div>
                <label class="block mb-2 font-semibold text-gray-700 text-sm">Correo electrónico</label>
                <input v-model="email" type="email" class="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition bg-gray-50" />
            </div>

            <!-- Sin estos datos no se puede emitir ninguna receta. Los completa
                 el propio profesional: es quien conoce su matrícula y su consultorio. -->
            <section v-if="puedePrescribir" class="p-4 bg-amber-50 border border-amber-200 rounded-xl space-y-3">
                <h3 class="font-semibold text-gray-700 text-sm">Datos para recetas electrónicas</h3>
                <p class="text-xs text-gray-500">Necesarios para emitir recetas: apellido, DNI, matrícula y dirección de atención.</p>

                <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <div>
                        <label class="block mb-1 text-sm text-gray-600">Apellido</label>
                        <input v-model.trim="perfil.apellido" type="text" class="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition bg-gray-50" />
                    </div>
                    <div>
                        <label class="block mb-1 text-sm text-gray-600">DNI</label>
                        <input v-model.trim="perfil.dni" type="text" class="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition bg-gray-50" />
                    </div>
                    <div>
                        <label class="block mb-1 text-sm text-gray-600">Sexo</label>
                        <select v-model="perfil.sexo" class="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition bg-gray-50">
                            <option value="">—</option>
                            <option v-for="s in SEXOS" :key="s.value" :value="s.value">{{ s.label }}</option>
                        </select>
                    </div>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <div>
                        <label class="block mb-1 text-sm text-gray-600">Tipo de matrícula</label>
                        <select v-model="perfil.matricula_tipo" class="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition bg-gray-50">
                            <option value="">—</option>
                            <option v-for="t in TIPOS_MATRICULA" :key="t" :value="t">{{ t }}</option>
                        </select>
                    </div>
                    <div>
                        <label class="block mb-1 text-sm text-gray-600">N° de matrícula</label>
                        <input v-model.trim="perfil.matricula_numero" type="text" class="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition bg-gray-50" />
                    </div>
                    <div>
                        <label class="block mb-1 text-sm text-gray-600">Provincia</label>
                        <input v-model.trim="perfil.matricula_provincia" type="text" class="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition bg-gray-50" />
                    </div>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                        <label class="block mb-1 text-sm text-gray-600">Lugar de atención</label>
                        <input v-model.trim="perfil.lugar_atencion_nombre" type="text" class="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition bg-gray-50" />
                    </div>
                    <div>
                        <label class="block mb-1 text-sm text-gray-600">Dirección de atención</label>
                        <input
                            v-model.trim="perfil.lugar_atencion_direccion"
                            type="text"
                            placeholder="Calle y número"
                            class="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition bg-gray-50"
                        />
                    </div>
                    <div>
                        <label class="block mb-1 text-sm text-gray-600">Teléfono</label>
                        <input v-model.trim="perfil.telefono" type="text" class="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition bg-gray-50" />
                    </div>
                    <div>
                        <label class="block mb-1 text-sm text-gray-600">Email de contacto</label>
                        <input v-model.trim="perfil.lugar_atencion_email" type="text" class="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition bg-gray-50" />
                    </div>
                </div>
            </section>
        </div>

        <div class="flex justify-between items-center mt-8 pt-6 border-t border-gray-100">
            <button v-if="userStore.foto" class="text-red-500 hover:text-red-700 text-sm font-semibold flex items-center gap-1 transition px-2 py-1 rounded hover:bg-red-50" @click="eliminarFoto"><i class="pi pi-trash"></i> Eliminar foto</button>

            <div v-else></div>

            <button class="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-xl shadow-md transition font-semibold flex items-center gap-2" @click="actualizarPerfil"><i class="pi pi-check"></i> Guardar cambios</button>
        </div>

        <div v-if="mensaje" class="mt-4 p-3 bg-green-50 text-green-700 rounded-lg text-center text-sm font-medium border border-green-200 animate-fade-in">
            {{ mensaje }}
        </div>

        <div v-if="error" class="mt-4 p-3 bg-red-50 text-red-700 rounded-lg text-center text-sm font-medium border border-red-200 animate-fade-in">
            {{ error }}
        </div>
    </div>
</template>

<style scoped>
.animate-fade-in {
    animation: fadeIn 0.3s ease-in-out;
}
@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(-5px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}
</style>
