<template>
  <div class="p-10 max-w-6xl mx-auto">
    <div
      class="rounded-2xl shadow-xl border border-gray-200 dark:border-gray-700 transition-all bg-white dark:bg-[#1b1b1b] p-10"
    >
      <!-- ENCABEZADO -->
      <div class="flex items-center justify-between mb-10">
        <div>
          <h1
            class="text-4xl font-bold mb-2 flex items-center gap-3 text-gray-800 dark:text-gray-100"
          >
             Disponibilidad del Profesional
          </h1>
          <p class="text-gray-500 dark:text-gray-400 text-lg">
            Configurá tus días y horarios de atención. Podés activar o desactivar los días según tu
            agenda.
          </p>
        </div>

        <!-- 🔹 Campo del profesional (solo si hay usuario logueado) -->
        <div
          v-if="usuario && usuario.nombre"
          class="bg-blue-50 dark:bg-[#00bfa51a] px-5 py-3 rounded-xl border border-blue-100 dark:border-[#00bfa533] flex items-center gap-2"
        >
          <i class="pi pi-user text-blue-500 dark:text-[#00bfa5] text-lg"></i>
          <p class="text-gray-700 dark:text-gray-100 font-medium">
            {{ usuario.nombre }}
          </p>
        </div>
      </div>

      <!-- TABLA -->
      <div class="overflow-x-auto mt-6">
        <table
          class="min-w-full border border-gray-200 dark:border-gray-700 rounded-2xl shadow-sm text-base overflow-hidden"
        >
          <thead
            class="bg-gradient-to-r from-blue-50 to-blue-100 dark:from-[#242424] dark:to-[#2a2a2a] text-gray-700 dark:text-gray-100"
          >
            <tr>
              <th class="text-left px-6 py-4 border-b dark:border-gray-700 font-semibold">Día</th>
              <th class="text-center px-6 py-4 border-b dark:border-gray-700 font-semibold">Activo</th>
              <th class="text-center px-6 py-4 border-b dark:border-gray-700 font-semibold">Hora inicio</th>
              <th class="text-center px-6 py-4 border-b dark:border-gray-700 font-semibold">Hora fin</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(dia, index) in diasSemana"
              :key="dia.nombre"
              class="transition-all hover:bg-blue-50 dark:hover:bg-[#2a2a2a]"
            >
              <td class="px-6 py-4 border-b dark:border-gray-700 font-medium text-gray-800 dark:text-gray-100 text-lg">
                {{ dia.nombre }}
              </td>
              <td class="text-center border-b dark:border-gray-700">
                <label class="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" v-model="dia.activo" class="sr-only peer" />
                  <div
                    class="w-12 h-6 bg-gray-300 dark:bg-gray-600 rounded-full peer peer-checked:bg-blue-500 transition"
                  ></div>
                  <span
                    class="absolute left-1 top-1 bg-white dark:bg-gray-200 w-4 h-4 rounded-full shadow transform transition peer-checked:translate-x-6"
                  ></span>
                </label>
              </td>
              <td class="text-center border-b dark:border-gray-700">
                <input
                  type="time"
                  v-model="dia.hora_inicio"
                  :disabled="!dia.activo"
                  class="border border-gray-300 dark:border-gray-700 dark:bg-[#2a2a2a] dark:text-gray-100 rounded-lg px-3 py-2 text-base w-32 focus:ring-2 focus:ring-blue-400 disabled:opacity-50"
                />
              </td>
              <td class="text-center border-b dark:border-gray-700">
                <input
                  type="time"
                  v-model="dia.hora_fin"
                  :disabled="!dia.activo"
                  class="border border-gray-300 dark:border-gray-700 dark:bg-[#2a2a2a] dark:text-gray-100 rounded-lg px-3 py-2 text-base w-32 focus:ring-2 focus:ring-blue-400 disabled:opacity-50"
                />
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- BOTONES -->
      <div class="flex justify-end mt-10 space-x-4">
        <button
          @click="cargarDisponibilidades"
          class="bg-gray-100 hover:bg-gray-200 dark:bg-[#2a2a2a] dark:hover:bg-[#333] dark:text-gray-100 text-gray-800 font-medium px-6 py-3 rounded-lg border border-gray-300 dark:border-gray-600 shadow-sm transition text-base"
        >
          🔄 Recargar
        </button>
        <button
          @click="guardarDisponibilidades"
          :disabled="guardando"
          class="bg-blue-600 hover:bg-blue-700 text-white font-semibold px-8 py-3 rounded-lg shadow transition text-base disabled:opacity-50"
        >
          {{ guardando ? '💾 Guardando...' : 'Guardar cambios' }}
        </button>
      </div>

      <!-- MENSAJES -->
      <div class="mt-8">
        <p v-if="mensaje" class="text-green-600 font-semibold text-lg dark:text-green-400">
          ✅ {{ mensaje }}
        </p>
        <p v-if="error" class="text-red-500 font-semibold text-lg dark:text-red-400">
          ⚠️ {{ error }}
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import axios from "axios";

// 🔹 Si tenés un store de usuario global (por ejemplo con Pinia)
import { useUserStore } from "@/stores/user";

const userStore = useUserStore();
const usuario = ref(userStore.user || null); // Si no hay usuario, no se muestra nada

const diasSemana = ref([
  { nombre: "Lunes", activo: false, hora_inicio: "09:00", hora_fin: "17:00" },
  { nombre: "Martes", activo: false, hora_inicio: "09:00", hora_fin: "17:00" },
  { nombre: "Miercoles", activo: false, hora_inicio: "09:00", hora_fin: "17:00" },
  { nombre: "Jueves", activo: false, hora_inicio: "09:00", hora_fin: "17:00" },
  { nombre: "Viernes", activo: false, hora_inicio: "09:00", hora_fin: "17:00" },
  { nombre: "Sabado", activo: false, hora_inicio: "09:00", hora_fin: "13:00" }
]);

const mensaje = ref("");
const error = ref("");
const guardando = ref(false);

async function cargarDisponibilidades() {
  mensaje.value = "";
  error.value = "";
  try {
    const res = await axios.get("/api/disponibilidades");
    const datos = res.data;
    diasSemana.value.forEach((dia) => {
      const existente = datos.find((d) => d.dia_semana === dia.nombre);
      if (existente) {
        dia.activo = existente.activo;
        dia.hora_inicio = existente.hora_inicio.slice(0, 5);
        dia.hora_fin = existente.hora_fin.slice(0, 5);
      }
    });
  } catch (err) {
    console.error(err);
    error.value = "No se pudieron cargar las disponibilidades.";
  }
}

async function guardarDisponibilidades() {
  guardando.value = true;
  mensaje.value = "";
  error.value = "";
  try {
    const res = await axios.get("/api/disponibilidades");
    const existentes = res.data;
    for (const d of existentes) {
      await axios.delete(`/api/disponibilidades/${d.id}`);
    }
    for (const dia of diasSemana.value) {
      if (dia.activo) {
        await axios.post("/api/disponibilidades", {
          dia_semana: dia.nombre,
          hora_inicio: dia.hora_inicio,
          hora_fin: dia.hora_fin,
          activo: true,
        });
      }
    }
    mensaje.value = "Disponibilidades guardadas correctamente ✅";
  } catch (err) {
    console.error(err);
    error.value = "Ocurrió un error al guardar las disponibilidades.";
  } finally {
    guardando.value = false;
  }
}

onMounted(cargarDisponibilidades);
</script>
