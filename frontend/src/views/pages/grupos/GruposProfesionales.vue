<template>
  <div class="p-8 max-w-6xl mx-auto">
    
    <!-- TÍTULO -->
    <div class="flex justify-between items-center mb-8">
      <h1 class="text-3xl font-bold text-blue-700">👥 Agendas Grupales</h1>

      <button
        class="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg shadow"
        @click="crearGrupo"
      >
        ➕ Nuevo Grupo
      </button>
    </div>

    <!-- MENSAJES -->
    <div v-if="loading" class="text-gray-500">Cargando grupos...</div>
    <div v-else-if="grupos.length === 0" class="text-gray-500">
      No hay grupos registrados.
    </div>

    <!-- LISTADO DE GRUPOS -->
    <div v-else class="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
      <div
        v-for="grupo in grupos"
        :key="grupo.id"
        class="border border-gray-200 rounded-xl p-5 bg-white shadow-sm hover:shadow-md transition"
      >
        <!-- HEADER TARJETA -->
        <div class="flex justify-between items-center">
          <h2 class="text-xl font-semibold text-gray-800">{{ grupo.nombre }}</h2>
          <span
            class="w-4 h-4 rounded-full border"
            :style="{ backgroundColor: grupo.color, borderColor: grupo.color }"
          ></span>
        </div>

        <p class="text-gray-600 text-sm mt-1 line-clamp-2">{{ grupo.descripcion }}</p>

        <!-- ACCIONES -->
        <div class="mt-4 flex justify-between text-sm">

          <button
            class="text-blue-600 hover:text-blue-800 underline"
            @click="verMiembros(grupo)"
          >
            👥 Miembros
          </button>

          <button
            class="text-yellow-600 hover:text-yellow-700 underline"
            @click="editarGrupo(grupo)"
          >
            ✏️ Editar
          </button>

          <button
            class="text-red-600 hover:text-red-800 underline"
            @click="eliminar(grupo)"
          >
            🗑️ Eliminar
          </button>
        </div>

        <!-- BOTÓN VER CALENDARIO -->
        <button
          class="mt-5 w-full bg-blue-600 hover:bg-blue-700 text-white py-2 rounded-lg shadow"
          @click="verCalendario(grupo)"
        >
          🗓️ Ver Calendario
        </button>
      </div>
    </div>

    <!-- MODAL MIEMBROS DEL GRUPO -->
    <div
      v-if="modalMiembros"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    >
      <div class="bg-white rounded-xl p-6 w-full max-w-lg shadow-lg">

        <div class="flex justify-between items-center mb-4">
          <h2 class="text-2xl font-bold text-gray-800">
            Miembros de {{ grupoActual?.nombre }}
          </h2>
          <button @click="cerrarModal" class="text-gray-500 hover:text-gray-700">✖</button>
        </div>

        <div v-if="cargandoMiembros" class="text-gray-500">Cargando...</div>
        
        <div v-else>
          <ul class="space-y-2 text-gray-700">
            <li
              v-for="m in miembros"
              :key="m.id"
              class="flex justify-between items-center border-b pb-1"
            >
              <span>• {{ m.nombre }} ({{ m.rol }})</span>

              <button
                class="text-red-600 hover:text-red-800"
                @click="quitarMiembro(m)"
              >
                Quitar
              </button>
            </li>
          </ul>

          <!-- AGREGAR MIEMBRO -->
          <div class="mt-5">
            <label class="text-sm font-semibold">Agregar profesional:</label>
            <select
              v-model="nuevoMiembro"
              class="w-full border rounded p-2 mt-1"
            >
              <option disabled value="">Seleccione un profesional</option>
              <option v-for="u in usuarios" :key="u.id" :value="u.id">
                {{ u.nombre }} ({{ u.rol }})
              </option>
            </select>

            <button
              class="mt-3 bg-green-600 hover:bg-green-700 text-white w-full py-2 rounded-lg shadow"
              @click="agregarMiembro"
            >
              Agregar
            </button>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import api from "@/api/axios";
import { useRouter } from "vue-router";

const grupos = ref([]);
const loading = ref(true);

const router = useRouter();

// Modal estado
const modalMiembros = ref(false);
const grupoActual = ref(null);
const miembros = ref([]);
const cargandoMiembros = ref(false);

// Agregar miembros
const usuarios = ref([]);
const nuevoMiembro = ref("");

// ================================
// Cargar grupos
// ================================
onMounted(async () => {
  try {
    const res = await api.get("/grupos", { withCredentials: true });
    grupos.value = res.data || [];
  } catch (err) {
    console.error("Error cargando grupos:", err);
  } finally {
    loading.value = false;
  }
});

// ================================
// Editar grupo
// ================================
function editarGrupo(grupo) {
  router.push({ name: "EditarGrupo", params: { id: grupo.id } });
}

// ================================
// Crear grupo
// ================================
function crearGrupo() {
  router.push({ name: "CrearGrupo" });
}

// ================================
// Eliminar grupo
// ================================
async function eliminar(grupo) {
  if (!confirm(`¿Eliminar el grupo "${grupo.nombre}"? Esta acción es permanente.`))
    return;

  try {
    await api.delete(`/grupos/${grupo.id}`, { withCredentials: true });
    grupos.value = grupos.value.filter((g) => g.id !== grupo.id);
  } catch (err) {
    console.error("Error eliminando grupo:", err);
    alert("No se pudo eliminar el grupo");
  }
}

// ================================
// Ver miembros (modal)
// ================================
async function verMiembros(grupo) {
  grupoActual.value = grupo;
  modalMiembros.value = true;
  cargandoMiembros.value = true;

  try {
    const res = await api.get(`/grupos/${grupo.id}/miembros`, {
      withCredentials: true,
    });
    miembros.value = res.data || [];

    const res2 = await api.get("/usuarios", { withCredentials: true });
    usuarios.value = res2.data.filter((u) => u.rol === "profesional");
  } catch (err) {
    console.error("Error cargando miembros:", err);
  } finally {
    cargandoMiembros.value = false;
  }
}

function cerrarModal() {
  modalMiembros.value = false;
  grupoActual.value = null;
  miembros.value = [];
  nuevoMiembro.value = "";
}

// ================================
// Agregar miembro
// ================================
async function agregarMiembro() {
  if (!nuevoMiembro.value) return;

  try {
    await api.post(
      `/grupos/${grupoActual.value.id}/miembros`,
      { usuario_id: nuevoMiembro.value },
      { withCredentials: true }
    );

    const user = usuarios.value.find((u) => u.id === nuevoMiembro.value);
    miembros.value.push(user);

    nuevoMiembro.value = "";
  } catch (err) {
    console.error("Error agregando miembro:", err);
  }
}

// ================================
// Quitar miembro
// ================================
async function quitarMiembro(m) {
  if (!confirm(`¿Quitar a ${m.nombre} del grupo?`)) return;

  try {
    await api.delete(
      `/grupos/${grupoActual.value.id}/miembros/${m.id}`,
      { withCredentials: true }
    );
    miembros.value = miembros.value.filter((x) => x.id !== m.id);
  } catch (err) {
    console.error("Error quitando miembro:", err);
  }
}

// ================================
// Ver calendario grupal
// ================================
function verCalendario(grupo) {
  router.push({ name: "CalendarioGrupo", params: { grupoId: grupo.id } });
}
</script>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
