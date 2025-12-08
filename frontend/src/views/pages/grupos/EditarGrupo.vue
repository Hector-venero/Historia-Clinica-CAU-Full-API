<template>
  <div class="p-8 max-w-3xl mx-auto bg-white shadow-xl rounded-2xl">
    
    <h1 class="text-3xl font-bold text-blue-700 mb-8">✏️ Editar Grupo Profesional</h1>
    
    <button
    class="px-4 py-2 text-sm rounded-lg bg-gray-200 hover:bg-gray-300 text-gray-700 mb-4"
    @click="router.push('/grupos')"
    >
    ⬅ Volver
    </button>

    <div v-if="cargando" class="text-gray-500">Cargando datos...</div>

    <form v-else @submit.prevent="guardarCambios" class="space-y-6">

      <!-- Nombre -->
      <div>
        <label class="block text-gray-700 font-semibold mb-2">Nombre del grupo</label>
        <input
          v-model="grupo.nombre"
          type="text"
          class="w-full border rounded-lg p-3 focus:ring-2 focus:ring-blue-500"
          placeholder="Ejemplo: Rehabilitación, Terapia..."
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
          placeholder="Describe el objetivo del grupo"
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
          <span class="text-gray-600 text-sm">Se usará para identificar el grupo en los calendarios</span>
        </div>
      </div>

      <!-- Miembros -->
      <div>
        <label class="block text-gray-700 font-semibold mb-2">Miembros del grupo</label>

        <div class="border rounded-lg p-3">
          <p v-if="miembros.length === 0" class="text-gray-500">No hay miembros asignados.</p>

          <div
            v-for="m in miembros"
            :key="m.id"
            class="flex justify-between items-center border-b py-2"
          >
            <span>{{ m.nombre }} — <span class="text-sm text-gray-500">{{ m.rol }}</span></span>

            <button
              type="button"
              class="text-red-600 hover:text-red-800 text-sm"
              @click="quitarMiembro(m)"
            >
              Quitar
            </button>
          </div>
        </div>

        <!-- Agregar miembro -->
        <div class="mt-4">
          <label class="block text-gray-700 font-semibold mb-2">Agregar miembro</label>
          <select
            v-model="nuevoMiembro"
            class="w-full border rounded-lg p-3"
          >
            <option disabled value="">Seleccione un profesional</option>
            <option
              v-for="u in usuariosDisponibles"
              :key="u.id"
              :value="u.id"
            >
              {{ u.nombre }} ({{ u.rol }})
            </option>
          </select>

          <button
            type="button"
            class="mt-3 bg-green-600 hover:bg-green-700 text-white w-full py-2 rounded-lg shadow"
            @click="agregarMiembro"
          >
            ➕ Agregar miembro
          </button>
        </div>
      </div>

      <!-- Botón Guardar -->
      <div class="flex justify-center">
        <button
          type="submit"
          class="bg-blue-600 hover:bg-blue-700 text-white font-semibold px-8 py-3 rounded-xl shadow-md"
        >
          Guardar Cambios
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
import api from "@/api/axios";
import { useRoute, useRouter } from "vue-router";

const route = useRoute();
const router = useRouter();

const grupoId = route.params.id;

const grupo = ref({
  nombre: "",
  descripcion: "",
  color: "#00936B"
});

const miembros = ref([]);
const usuariosDisponibles = ref([]);

const nuevoMiembro = ref("");

const cargando = ref(true);
const mensaje = ref("");
const error = ref("");

// ====================================
// CARGAR DATOS DEL GRUPO
// ====================================
onMounted(async () => {
  try {
    // 1️⃣ Obtener datos del grupo
    const resGrupo = await api.get(`/grupos/${grupoId}`, { withCredentials: true });
    grupo.value = resGrupo.data;

    // 2️⃣ Obtener miembros actuales
    const resMiembros = await api.get(`/grupos/${grupoId}/miembros`, { withCredentials: true });
    miembros.value = resMiembros.data;

    // 3️⃣ Usuarios disponibles para agregar
    const resUsuarios = await api.get("/usuarios", { withCredentials: true });
    usuariosDisponibles.value = resUsuarios.data.filter(u => u.rol === "profesional");
  } catch (err) {
    console.error("Error cargando grupo:", err);
    error.value = "No se pudieron cargar los datos del grupo.";
  } finally {
    cargando.value = false;
  }
});

// ====================================
// GUARDAR CAMBIOS DEL GRUPO
// ====================================
async function guardarCambios() {
  mensaje.value = "";
  error.value = "";

  try {
    await api.put(`/grupos/${grupoId}`, grupo.value, { withCredentials: true });
    mensaje.value = "Cambios guardados correctamente ✔️";
  } catch (err) {
    console.error("Error guardando cambios:", err);
    error.value = err.response?.data?.error || "Error al guardar cambios.";
  }
}

// ====================================
// QUITAR MIEMBRO
// ====================================
async function quitarMiembro(m) {
  if (!confirm(`¿Quitar a ${m.nombre} del grupo?`)) return;

  try {
    await api.delete(`/grupos/${grupoId}/miembros/${m.id}`, { withCredentials: true });
    miembros.value = miembros.value.filter(x => x.id !== m.id);
  } catch (err) {
    console.error("Error quitando miembro:", err);
    error.value = "No se pudo quitar el miembro.";
  }
}

// ====================================
// AGREGAR MIEMBRO
// ====================================
async function agregarMiembro() {
  if (!nuevoMiembro.value) return;

  // 🚫 Bloquear duplicados en frontend
  if (miembros.value.some(m => m.id === nuevoMiembro.value)) {
    error.value = "Este profesional ya pertenece al grupo.";
    return;
  }

  try {
    await api.post(
      `/grupos/${grupoId}/miembros`,
      { usuario_id: nuevoMiembro.value },
      { withCredentials: true }
    );

    const user = usuariosDisponibles.value.find(u => u.id === nuevoMiembro.value);
    if (user) miembros.value.push(user);

    nuevoMiembro.value = "";
    mensaje.value = "Miembro agregado correctamente ✔️";
  } catch (err) {
    console.error("Error agregando miembro:", err);
    error.value = "No se pudo agregar el miembro.";
  }
}

</script>