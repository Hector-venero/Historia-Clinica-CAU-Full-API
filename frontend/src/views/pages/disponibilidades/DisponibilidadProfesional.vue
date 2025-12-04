<template>
  <div class="p-10 max-w-6xl mx-auto">
    <div class="rounded-2xl shadow-xl border border-gray-200 bg-white dark:bg-[#1b1b1b] p-10">

      <!-- ENCABEZADO -->
      <div class="flex items-center justify-between mb-8">
        <div>
          <h1 class="text-4xl font-bold text-gray-800 dark:text-gray-100">
            Disponibilidad del Profesional
          </h1>
          <p class="text-gray-500 dark:text-gray-400 text-lg">
            Configurá tus días y horarios de atención.
          </p>
        </div>

        <div
          v-if="usuario && usuario.nombre"
          class="bg-blue-50 dark:bg-[#00bfa51a] px-5 py-3 rounded-xl border border-blue-100 
                 dark:border-[#00bfa533] flex items-center gap-2 shadow-sm"
        >
          <i class="pi pi-user text-blue-500 dark:text-[#00bfa5]"></i>
          <p class="text-gray-700 dark:text-gray-100 font-medium">{{ usuario.nombre }}</p>
        </div>
      </div>

      <!-- RESUMEN -->
      <div v-if="resumen.length > 0" class="mb-8">
        <h2 class="text-xl font-semibold text-gray-700 dark:text-gray-200 mb-3">Resumen</h2>

        <div class="flex flex-col gap-1">
          <p
            v-for="item in resumen"
            :key="item.dia"
            class="text-blue-600 dark:text-blue-400 font-medium flex items-center gap-2"
          >
            <span class="w-3 h-3 bg-blue-500 rounded-sm"></span>
            Atendés <strong>{{ item.dia }}</strong> de 
            <strong>{{ item.inicio }}</strong> a <strong>{{ item.fin }}</strong>
          </p>
        </div>
      </div>

      <!-- TABLA -->
      <div class="overflow-x-auto">
        <table
          class="min-w-full border border-gray-200 dark:border-gray-700 rounded-2xl shadow-sm text-base overflow-hidden"
        >
          <thead
            class="bg-gradient-to-r from-blue-50 to-blue-100 dark:from-[#242424] dark:to-[#2a2a2a] 
                   text-gray-700 dark:text-gray-100"
          >
            <tr>
              <th class="px-6 py-4 text-left">Día</th>
              <th class="px-6 py-4 text-center">Activo</th>
              <th class="px-6 py-4 text-center">Hora inicio</th>
              <th class="px-6 py-4 text-center">Hora fin</th>
            </tr>
          </thead>

          <tbody>
            <tr
              v-for="dia in diasSemana"
              :key="dia.nombre"
              class="transition-all hover:bg-blue-50 dark:hover:bg-[#2a2a2a]"
            >
              <td class="px-6 py-4 font-medium text-lg">
                {{ dia.nombre }}
              </td>

              <!-- SWITCH -->
              <td class="text-center">
                <label class="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    v-model="dia.activo"
                    class="sr-only peer"
                  />

                  <!-- FONDO -->
                  <div
                    class="w-12 h-6 rounded-full
                    bg-gray-300 dark:bg-gray-600
                    peer-checked:bg-blue-500
                    transition duration-300"
                  ></div>

                  <!-- BOLITA -->
                  <div
                    class="absolute top-1 left-1 w-4 h-4 rounded-full bg-white dark:bg-gray-200 shadow
                    transition-transform duration-300 peer-checked:translate-x-6"
                  ></div>
                </label>
              </td>

              <!-- HORA INICIO -->
              <td class="text-center">
                <input
                  type="time"
                  v-model="dia.hora_inicio"
                  :disabled="!dia.activo"
                  class="border dark:bg-[#2a2a2a] px-3 py-2 rounded-lg w-32 disabled:opacity-50"
                />
              </td>

              <!-- HORA FIN -->
              <td class="text-center">
                <input
                  type="time"
                  v-model="dia.hora_fin"
                  :disabled="!dia.activo"
                  class="border dark:bg-[#2a2a2a] px-3 py-2 rounded-lg w-32 disabled:opacity-50"
                />
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- BOTONES -->
      <div class="flex justify-between mt-10">

        <!-- SALIR -->
        <button
          @click="irAlDashboard"
          class="bg-gray-100 hover:bg-gray-200 text-gray-800 px-6 py-3 rounded-lg border 
                shadow-sm transition flex items-center gap-2"
        >
          <i class="pi pi-chevron-left"></i> Salir
        </button>

        <!-- GUARDAR -->
        <button
          @click="guardarDisponibilidades"
          :disabled="guardando"
          class="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-lg shadow 
                 disabled:opacity-50 transition flex items-center gap-2"
        >
          <i class="pi pi-save"></i>
          {{ guardando ? "Guardando..." : "Guardar cambios" }}
        </button>
      </div>

      <!-- MENSAJES -->
      <div class="mt-6">
        <p v-if="mensaje" class="text-green-600 font-semibold text-lg">
          ✅ {{ mensaje }}
        </p>
        <p v-if="error" class="text-red-500 font-semibold text-lg">
          ⚠️ {{ error }}
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from "vue";
import { useRouter } from "vue-router";
import axios from "axios";
import { useUserStore } from "@/stores/user";

const router = useRouter();
const userStore = useUserStore();
const usuario = ref(userStore);

const irAlDashboard = () => {
  router.push({ name: "dashboard" });   // o router.push('/')
};

// ░░ DIAS BASE ░░
const diasSemana = ref([
  { nombre: "Lunes", id: null, activo: false, hora_inicio: "09:00", hora_fin: "17:00" },
  { nombre: "Martes", id: null, activo: false, hora_inicio: "09:00", hora_fin: "17:00" },
  { nombre: "Miercoles", id: null, activo: false, hora_inicio: "09:00", hora_fin: "17:00" },
  { nombre: "Jueves", id: null, activo: false, hora_inicio: "09:00", hora_fin: "17:00" },
  { nombre: "Viernes", id: null, activo: false, hora_inicio: "09:00", hora_fin: "17:00" },
  { nombre: "Sabado", id: null, activo: false, hora_inicio: "09:00", hora_fin: "13:00" }
]);

const mensaje = ref("");
const error = ref("");
const guardando = ref(false);

// ░░ RESUMEN COMPUTADO ░░
const resumen = computed(() =>
  diasSemana.value
    .filter(d => d.activo)
    .map(d => ({
      dia: d.nombre,
      inicio: d.hora_inicio,
      fin: d.hora_fin
    }))
);

// ░░ CARGA DE DISPONIBILIDADES ░░
async function cargarDisponibilidades() {
  mensaje.value = "";
  error.value = "";
  try {
    const res = await axios.get("/api/disponibilidades");
    const datos = res.data;

    diasSemana.value.forEach((dia) => {
      const encontrado = datos.find((d) => d.dia_semana === dia.nombre);
      if (encontrado) {
        dia.id = encontrado.id;
        dia.activo = encontrado.activo;
        dia.hora_inicio = encontrado.hora_inicio.slice(0, 5);
        dia.hora_fin = encontrado.hora_fin.slice(0, 5);
      }
    });
  } catch (err) {
    console.error(err);
    error.value = "No se pudieron cargar las disponibilidades";
  }
}

// ░░ GUARDAR CAMBIOS ░░
async function guardarDisponibilidades() {
  guardando.value = true;
  mensaje.value = "";
  error.value = "";

  try {
    for (const dia of diasSemana.value) {
      if (dia.activo) {
        if (dia.id) {
          await axios.put(`/api/disponibilidades/${dia.id}`, {
            hora_inicio: dia.hora_inicio,
            hora_fin: dia.hora_fin,
            activo: true
          });
        } else {
          const res = await axios.post("/api/disponibilidades", {
            dia_semana: dia.nombre,
            hora_inicio: dia.hora_inicio,
            hora_fin: dia.hora_fin,
            activo: true
          });
          dia.id = res.data.id;
        }
      } else if (dia.id) {
        await axios.put(`/api/disponibilidades/${dia.id}`, {
          hora_inicio: dia.hora_inicio,
          hora_fin: dia.hora_fin,
          activo: false
        });
      }
    }
    mensaje.value = "Disponibilidades actualizadas correctamente.";
  } catch (err) {
    console.error(err);
    error.value = "Error al guardar los cambios.";
  } finally {
    guardando.value = false;
  }
}

onMounted(cargarDisponibilidades);
</script>
