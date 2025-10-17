<template>
  <div class="p-8 max-w-3xl mx-auto bg-white shadow-xl rounded-2xl">
    <h1 class="text-3xl font-bold text-blue-700 mb-8">➕ Crear Nuevo Grupo Profesional</h1>

    <form @submit.prevent="crearGrupo" class="space-y-6">
      <!-- Nombre -->
      <div>
        <label class="block text-gray-700 font-semibold mb-2">Nombre del grupo</label>
        <input
          v-model="grupo.nombre"
          type="text"
          class="w-full border rounded-lg p-3 focus:ring-2 focus:ring-blue-500"
          placeholder="Ejemplo: Kinesiología, Pediatría..."
          required
        />
      </div>

      <!-- Descripción -->
      <div>
        <label class="block text-gray-700 font-semibold mb-2">Descripción</label>
        <textarea
          v-model="grupo.descripcion"
          rows="3"
          class="w-full border rounded-lg p-3 focus:ring-2 focus:ring-blue-500"
          placeholder="Describe brevemente el propósito del grupo"
        ></textarea>
      </div>

      <!-- Color -->
      <div>
        <label class="block text-gray-700 font-semibold mb-2">Color del grupo</label>
        <div class="flex items-center gap-3">
          <input
            v-model="grupo.color"
            type="color"
            class="w-12 h-12 border rounded-lg cursor-pointer"
          />
          <span class="text-gray-600 text-sm">Usado para identificar el grupo en los calendarios</span>
        </div>
      </div>

      <!-- Miembros -->
      <div>
        <label class="block text-gray-700 font-semibold mb-2">Seleccionar miembros</label>
        <div class="border rounded-lg p-3 max-h-60 overflow-y-auto">
          <div
            v-for="usuario in usuarios"
            :key="usuario.id"
            class="flex items-center mb-2"
          >
            <input
              type="checkbox"
              :id="'user-' + usuario.id"
              :value="usuario.id"
              v-model="miembrosSeleccionados"
              class="mr-2"
            />
            <label :for="'user-' + usuario.id" class="text-gray-700">
              {{ usuario.nombre }} — <span class="text-sm text-gray-500">{{ usuario.rol }}</span>
            </label>
          </div>
        </div>
      </div>

      <!-- Botón Guardar -->
      <div class="flex justify-center">
        <button
          type="submit"
          class="bg-blue-600 hover:bg-blue-700 text-white font-semibold px-8 py-3 rounded-xl shadow-md transition"
        >
          Guardar Grupo
        </button>
      </div>
    </form>

    <!-- Mensajes -->
    <p v-if="mensaje" class="mt-6 text-green-600 font-semibold text-center">{{ mensaje }}</p>
    <p v-if="error" class="mt-6 text-red-600 font-semibold text-center">{{ error }}</p>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import axios from "axios";

const grupo = ref({
  nombre: "",
  descripcion: "",
  color: "#00936B"
});
const usuarios = ref([]);
const miembrosSeleccionados = ref([]);
const mensaje = ref("");
const error = ref("");

// ✅ Cargar usuarios disponibles
onMounted(async () => {
  try {
    const res = await axios.get("/api/usuarios", { withCredentials: true });
    usuarios.value = res.data || [];
  } catch (err) {
    console.error("Error cargando usuarios:", err);
  }
});

async function crearGrupo() {
  mensaje.value = "";
  error.value = "";

  try {
    // 1️⃣ Crear grupo
    const resGrupo = await axios.post("/api/grupos", grupo.value, { withCredentials: true });
    const grupoId = resGrupo.data.id;

    // 2️⃣ Agregar miembros seleccionados
    for (const usuarioId of miembrosSeleccionados.value) {
      await axios.post(`/api/grupos/${grupoId}/miembros`, { usuario_id: usuarioId }, { withCredentials: true });
    }

    mensaje.value = "✅ Grupo creado y miembros asignados correctamente";
    grupo.value = { nombre: "", descripcion: "", color: "#00936B" };
    miembrosSeleccionados.value = [];
  } catch (err) {
    console.error("Error creando grupo:", err);
    error.value =
      err.response?.data?.error || "Error al crear el grupo. Verifique los datos o permisos.";
  }
}
</script>
