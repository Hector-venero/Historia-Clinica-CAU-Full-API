<template>
  <div class="p-8 max-w-6xl mx-auto">
    <h1 class="text-3xl font-bold text-blue-700 mb-6">👥 Agendas Grupales</h1>

    <!-- 🔹 Listado de grupos -->
    <div v-if="loading" class="text-gray-500">Cargando grupos...</div>
    <div v-else-if="grupos.length === 0" class="text-gray-500">No hay grupos registrados.</div>

    <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <div
        v-for="grupo in grupos"
        :key="grupo.id"
        class="border border-gray-200 rounded-xl p-5 shadow-sm hover:shadow-md transition cursor-pointer bg-white"
        @click="seleccionarGrupo(grupo)"
      >
        <div class="flex justify-between items-center">
          <h2 class="text-xl font-semibold text-gray-800">{{ grupo.nombre }}</h2>
          <span class="w-4 h-4 rounded-full" :style="{ backgroundColor: grupo.color }"></span>
        </div>
        <p class="text-gray-600 text-sm mt-1 line-clamp-2">{{ grupo.descripcion }}</p>
      </div>
    </div>

    <!-- 🔹 Detalle del grupo seleccionado -->
    <div v-if="grupoSeleccionado" class="mt-8 bg-blue-50 border border-blue-200 p-6 rounded-xl">
      <div class="flex justify-between items-center mb-4">
        <h2 class="text-2xl font-bold text-blue-800">
          Agenda grupal: {{ grupoSeleccionado.nombre }}
        </h2>
        <button
          class="text-sm text-gray-500 hover:text-blue-600"
          @click="grupoSeleccionado = null; miembros = []"
        >
          ← Volver
        </button>
      </div>

      <div v-if="cargandoMiembros" class="text-gray-500">Cargando miembros...</div>
      <div v-else-if="miembros.length === 0" class="text-gray-500">
        No hay miembros en este grupo.
      </div>

      <div v-else>
        <h3 class="font-semibold mb-3 text-gray-700">Miembros del grupo:</h3>
        <ul class="space-y-1 text-gray-700">
          <li v-for="m in miembros" :key="m.id">• {{ m.nombre }} ({{ m.rol }})</li>
        </ul>

        <div class="mt-6 text-center">
          <button
            @click="verCalendarioGrupo"
            class="bg-blue-600 hover:bg-blue-700 text-white font-semibold px-6 py-2 rounded-lg shadow-md"
          >
            🗓️ Ver calendario grupal
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import axios from "axios";
import { useRouter } from "vue-router";

const grupos = ref([]);
const grupoSeleccionado = ref(null);
const miembros = ref([]);
const loading = ref(true);
const cargandoMiembros = ref(false);
const router = useRouter();

// ✅ Cargar grupos al iniciar
onMounted(async () => {
  try {
    const res = await axios.get("/api/grupos", { withCredentials: true });
    grupos.value = res.data || [];
  } catch (err) {
    console.error("Error cargando grupos:", err);
  } finally {
    loading.value = false;
  }
});

// ✅ Seleccionar grupo
async function seleccionarGrupo(grupo) {
  grupoSeleccionado.value = grupo;
  cargandoMiembros.value = true;
  try {
    const res = await axios.get(`/api/grupos/${grupo.id}/miembros`, { withCredentials: true });
    miembros.value = res.data || [];
  } catch (err) {
    console.error("Error cargando miembros:", err);
  } finally {
    cargandoMiembros.value = false;
  }
}

// ✅ Ir al calendario de grupo
function verCalendarioGrupo() {
  router.push({ name: "CalendarioGrupo", params: { grupoId: grupoSeleccionado.value.id } });
}
</script>
