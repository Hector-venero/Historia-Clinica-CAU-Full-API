<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import api from '@/api/axios';
import { useUserStore } from '@/stores/user';
import { useMarcaStore } from '@/stores/marca';
import { buildFotoURL } from '@/utils/fotoUrl.js';

import Toast from 'primevue/toast';
import { useToast } from 'primevue/usetoast';

const toast = useToast();
const userStore = useUserStore();

// Campos del formulario
const nombre = ref('');
const email = ref('');

// Datos que la receta electrónica exige del profesional que la firma.
// Los edita cada uno: es quien conoce su matrícula y dónde atiende.
// La lista tiene que coincidir con PROFESSIONAL_FIELDS del backend.
const CAMPOS_PROFESIONALES = ['apellido', 'dni', 'sexo', 'telefono', 'matricula_tipo', 'matricula_numero', 'matricula_provincia', 'lugar_atencion_nombre', 'lugar_atencion_direccion', 'lugar_atencion_contacto', 'lugar_atencion_email'];

const perfil = reactive(Object.fromEntries(CAMPOS_PROFESIONALES.map((c) => [c, ''])));

const SEXOS = [
    { label: 'Femenino', value: 'F' },
    { label: 'Masculino', value: 'M' },
    { label: 'No binario / X', value: 'X' },
    { label: 'Otro', value: 'O' }
];
const TIPOS_MATRICULA = ['MN', 'MP', 'OP'];

// Lo que _validar_payload() del backend exige para que el proveedor acepte una
// receta. Se listan acá para poder decir qué falta antes de que la persona
// llegue a la pantalla de emisión y se choque con un error del proveedor.
const REQUERIDOS_RECETA = [
    { campo: 'nombre', etiqueta: 'Nombre completo', valor: () => nombre.value },
    { campo: 'apellido', etiqueta: 'Apellido', valor: () => perfil.apellido },
    { campo: 'dni', etiqueta: 'DNI', valor: () => perfil.dni },
    { campo: 'matricula_numero', etiqueta: 'N° de matrícula', valor: () => perfil.matricula_numero },
    { campo: 'lugar_atencion_direccion', etiqueta: 'Dirección de atención', valor: () => perfil.lugar_atencion_direccion }
];

const puedePrescribir = computed(() => ['profesional', 'director'].includes((userStore.rol || '').toLowerCase()));

// El logo es del CONSULTORIO, no de la persona: por eso solo lo toca la
// dirección. Va en esta pantalla porque es donde ya se editan los datos que
// salen impresos, y abrir una pantalla aparte para un solo campo era peor.
const esDirector = computed(() => (userStore.rol || '').toLowerCase() === 'director');
const marcaStore = useMarcaStore();
const subiendoLogo = ref(false);
const errorLogo = ref('');

async function subirLogo(evento) {
    const archivo = evento.target.files?.[0];
    if (!archivo) return;

    errorLogo.value = '';
    subiendoLogo.value = true;
    try {
        const datos = new FormData();
        datos.append('logo', archivo);
        const { data } = await api.post('/marca/logo', datos, { headers: { 'Content-Type': 'multipart/form-data' } });
        // Se refresca la marca entera y no solo esta pantalla: el logo se ve en
        // la barra superior, que lee del mismo store.
        marcaStore.logo = data.logo;
        toast.add({ severity: 'success', summary: 'Logo actualizado', life: 3000 });
    } catch (e) {
        errorLogo.value = e?.response?.data?.error || 'No pudimos subir el logo.';
    } finally {
        subiendoLogo.value = false;
        evento.target.value = '';
    }
}

async function quitarLogo() {
    errorLogo.value = '';
    subiendoLogo.value = true;
    try {
        await api.delete('/marca/logo');
        marcaStore.logo = null;
        toast.add({ severity: 'success', summary: 'Logo eliminado', life: 3000 });
    } catch (e) {
        errorLogo.value = e?.response?.data?.error || 'No pudimos eliminar el logo.';
    } finally {
        subiendoLogo.value = false;
    }
}
const faltantes = computed(() => REQUERIDOS_RECETA.filter((r) => !String(r.valor() || '').trim()).map((r) => r.etiqueta));
const listoParaRecetar = computed(() => faltantes.value.length === 0);

const archivoFoto = ref(null);
const previewFoto = ref(null);
const guardando = ref(false);

// Variable reactiva para forzar la recarga de la imagen
const imgVersion = ref(Date.now());

const inicial = computed(() => (nombre.value ? nombre.value.charAt(0).toUpperCase() : 'U'));

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
        toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudieron cargar los datos profesionales.', life: 4500 });
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
    guardando.value = true;

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

        toast.add({ severity: 'success', summary: 'Guardado', detail: 'Perfil actualizado correctamente.', life: 3200 });

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
        const detail = err?.response?.data?.error || 'Error al actualizar el perfil.';
        toast.add({ severity: 'error', summary: 'Error', detail, life: 4500 });
    } finally {
        guardando.value = false;
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

        toast.add({ severity: 'success', summary: 'Listo', detail: 'Foto eliminada correctamente.', life: 3000 });
    } catch (err) {
        console.error(err);
        toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo eliminar la foto.', life: 4500 });
    }
};
</script>

<template>
    <!-- Todos los colores van con su variante dark:. La pantalla no tenia
         ninguna, asi que en tema oscuro quedaba una tarjeta blanca con campos
         claros, peleada con el resto de la aplicacion. -->
    <div class="max-w-5xl mx-auto p-4 md:p-6 space-y-6">
        <Toast />

        <!-- Un solo boton de guardar, al pie del formulario. Habia tambien uno
             aca arriba, pensando en que no se perdiera de vista al scrollear,
             pero en pantallas normales entran los dos a la vez y dos botones
             identicos hacen dudar de si hacen lo mismo. -->
        <header>
            <h1 class="text-2xl md:text-3xl font-bold text-surface-900 dark:text-surface-0 m-0">Mi perfil</h1>
            <p class="text-sm text-surface-500 dark:text-surface-400 mt-1 mb-0">Tus datos personales y los que se imprimen en las recetas.</p>
        </header>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
            <!-- Identidad -->
            <section class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-2xl p-6 flex flex-col items-center text-center">
                <img v-if="imagenA_Mostrar" :src="imagenA_Mostrar" class="w-28 h-28 rounded-full object-cover ring-4 ring-surface-100 dark:ring-surface-800" alt="Foto de perfil" />

                <div v-else class="w-28 h-28 rounded-full bg-primary-100 dark:bg-primary-900 text-primary-700 dark:text-primary-200 flex items-center justify-center text-4xl font-bold ring-4 ring-surface-100 dark:ring-surface-800 select-none">
                    {{ inicial }}
                </div>

                <p class="mt-4 mb-0 font-semibold text-surface-900 dark:text-surface-0 break-words">{{ nombre || 'Sin nombre' }}</p>
                <span v-if="userStore.rol" class="mt-1 inline-block text-[11px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full bg-surface-100 dark:bg-surface-800 text-surface-600 dark:text-surface-300">
                    {{ userStore.rol }}
                </span>

                <label
                    class="mt-5 w-full cursor-pointer inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl text-sm font-medium border border-surface-300 dark:border-surface-600 text-surface-700 dark:text-surface-200 hover:bg-surface-100 dark:hover:bg-surface-800 transition"
                >
                    <i class="pi pi-camera"></i>
                    <span>{{ userStore.foto || previewFoto ? 'Cambiar foto' : 'Subir foto' }}</span>
                    <input type="file" class="hidden" accept="image/*" @change="onFileChange" />
                </label>

                <p v-if="previewFoto" class="text-xs text-amber-600 dark:text-amber-400 mt-2 mb-0">Vista previa. Guardá los cambios para aplicarla.</p>

                <button v-if="userStore.foto" type="button" class="mt-2 text-sm text-red-600 dark:text-red-400 hover:underline inline-flex items-center gap-1" @click="eliminarFoto"><i class="pi pi-trash"></i> Eliminar foto</button>
            </section>

            <!-- Formularios -->
            <div class="lg:col-span-2 space-y-6">
                <section class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-2xl p-6">
                    <h2 class="text-base font-semibold text-surface-900 dark:text-surface-0 m-0 mb-4">Datos de la cuenta</h2>

                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label class="block mb-1.5 text-sm font-medium text-surface-700 dark:text-surface-300">Nombre completo</label>
                            <input v-model="nombre" type="text" class="campo" />
                        </div>
                        <div>
                            <label class="block mb-1.5 text-sm font-medium text-surface-700 dark:text-surface-300">Correo electrónico</label>
                            <input v-model="email" type="email" class="campo" />
                        </div>
                    </div>
                </section>

                <!-- Sin estos datos no se puede emitir ninguna receta. Los completa
                     el propio profesional: es quien conoce su matrícula y su consultorio. -->
                <section v-if="puedePrescribir" class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-2xl p-6">
                    <div class="flex items-start justify-between gap-3 mb-1">
                        <h2 class="text-base font-semibold text-surface-900 dark:text-surface-0 m-0">Datos para recetas electrónicas</h2>
                        <span
                            :class="[
                                'shrink-0 text-[11px] font-bold uppercase tracking-wide px-2 py-1 rounded-full',
                                listoParaRecetar ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200'
                            ]"
                        >
                            {{ listoParaRecetar ? 'Completo' : 'Incompleto' }}
                        </span>
                    </div>
                    <p class="text-sm text-surface-500 dark:text-surface-400 mt-0 mb-4">Se imprimen en cada receta que emitís.</p>

                    <!-- Decir exactamente que falta evita que la persona lo
                         descubra recien al emitir, con un codigo de error del
                         proveedor que no dice donde se carga el dato. -->
                    <div v-if="faltantes.length" class="mb-5 p-3 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800">
                        <p class="text-sm text-amber-900 dark:text-amber-200 m-0">
                            <i class="pi pi-exclamation-circle mr-1"></i>
                            Sin estos datos no vas a poder emitir recetas: <strong>{{ faltantes.join(', ') }}</strong>
                        </p>
                    </div>

                    <div class="space-y-4">
                        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div>
                                <label class="etiqueta">Apellido</label>
                                <input v-model.trim="perfil.apellido" type="text" class="campo" />
                            </div>
                            <div>
                                <label class="etiqueta">DNI</label>
                                <input v-model.trim="perfil.dni" type="text" class="campo" />
                            </div>
                            <div>
                                <label class="etiqueta">Sexo</label>
                                <select v-model="perfil.sexo" class="campo">
                                    <option value="">—</option>
                                    <option v-for="s in SEXOS" :key="s.value" :value="s.value">{{ s.label }}</option>
                                </select>
                            </div>
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div>
                                <label class="etiqueta">Tipo de matrícula</label>
                                <select v-model="perfil.matricula_tipo" class="campo">
                                    <option value="">—</option>
                                    <option v-for="t in TIPOS_MATRICULA" :key="t" :value="t">{{ t }}</option>
                                </select>
                            </div>
                            <div>
                                <label class="etiqueta">N° de matrícula</label>
                                <input v-model.trim="perfil.matricula_numero" type="text" class="campo" />
                            </div>
                            <div>
                                <label class="etiqueta">Provincia</label>
                                <input v-model.trim="perfil.matricula_provincia" type="text" class="campo" />
                            </div>
                        </div>

                        <hr class="border-surface-200 dark:border-surface-700" />

                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label class="etiqueta">Lugar de atención</label>
                                <input v-model.trim="perfil.lugar_atencion_nombre" type="text" placeholder="Nombre del consultorio" class="campo" />
                            </div>
                            <div>
                                <label class="etiqueta">Dirección de atención</label>
                                <input v-model.trim="perfil.lugar_atencion_direccion" type="text" placeholder="Calle y número" class="campo" />
                            </div>
                            <div>
                                <label class="etiqueta">Teléfono</label>
                                <input v-model.trim="perfil.telefono" type="text" class="campo" />
                            </div>
                            <div>
                                <label class="etiqueta">Email de contacto</label>
                                <input v-model.trim="perfil.lugar_atencion_email" type="text" class="campo" />
                            </div>
                        </div>
                    </div>
                </section>

                <!-- Logo del consultorio. Es lo que sale impreso en las historias
                     clínicas: sin uno propio va el nombre en texto. -->
                <section v-if="esDirector" class="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-2xl p-5">
                    <h2 class="text-base font-semibold text-surface-900 dark:text-surface-0 m-0 mb-1">Logo del consultorio</h2>
                    <p class="text-sm text-surface-500 dark:text-surface-400 mt-0 mb-4">Se muestra en la barra superior y en el encabezado de las historias clínicas en PDF.</p>

                    <div class="flex flex-wrap items-center gap-5">
                        <div class="w-32 h-20 rounded-xl border border-surface-200 dark:border-surface-700 bg-surface-50 dark:bg-surface-800 flex items-center justify-center overflow-hidden shrink-0">
                            <img v-if="marcaStore.logo" :src="marcaStore.logo" alt="Logo del consultorio" class="max-h-full max-w-full object-contain" />
                            <span v-else class="text-xs text-surface-400 dark:text-surface-500 px-2 text-center">Sin logo</span>
                        </div>

                        <div class="flex flex-col gap-2">
                            <label class="inline-flex items-center gap-2 px-4 py-2 rounded-xl font-semibold text-sm text-white bg-primary-600 hover:bg-primary-700 cursor-pointer transition">
                                <i :class="subiendoLogo ? 'pi pi-spin pi-spinner' : 'pi pi-upload'"></i>
                                {{ marcaStore.logo ? 'Cambiar logo' : 'Subir logo' }}
                                <input type="file" accept=".png,.jpg,.jpeg,.webp" class="hidden" :disabled="subiendoLogo" @change="subirLogo" />
                            </label>
                            <button v-if="marcaStore.logo" type="button" class="text-sm text-red-600 dark:text-red-400 hover:underline text-left" :disabled="subiendoLogo" @click="quitarLogo">Quitar logo</button>
                            <span class="text-xs text-surface-500 dark:text-surface-400"
                                >PNG o WEBP con fondo transparente, hasta 2 MB. Un JPG no tiene transparencia: el fondo blanco se ve como un recuadro sobre la barra, sobre todo en modo oscuro. Se muestra a 40 px de alto, así que un logo apaisado se
                                lee mejor que uno cuadrado.</span
                            >
                        </div>
                    </div>

                    <div v-if="errorLogo" class="mt-4 p-3 rounded-xl bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-300 text-sm border border-red-200 dark:border-red-900">
                        {{ errorLogo }}
                    </div>
                </section>

                <div class="flex justify-end">
                    <button
                        type="button"
                        :disabled="guardando"
                        class="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-60 disabled:cursor-not-allowed shadow-sm transition"
                        @click="actualizarPerfil"
                    >
                        <i :class="guardando ? 'pi pi-spin pi-spinner' : 'pi pi-check'"></i>
                        {{ guardando ? 'Guardando...' : 'Guardar cambios' }}
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
/* Los campos repetian la misma cadena de doce clases de Tailwind en cada input,
   lo que hacia imposible ver que ninguno tenia variante oscura. Con @apply la
   definicion queda en un solo lugar. */
.campo {
    @apply w-full px-3 py-2.5 rounded-xl outline-none transition
           bg-surface-50 dark:bg-surface-800
           border border-surface-300 dark:border-surface-600
           text-surface-900 dark:text-surface-0
           placeholder:text-surface-400 dark:placeholder:text-surface-500
           focus:ring-2 focus:ring-primary-500 focus:border-primary-500;
}

.etiqueta {
    @apply block mb-1.5 text-sm font-medium text-surface-700 dark:text-surface-300;
}
</style>
