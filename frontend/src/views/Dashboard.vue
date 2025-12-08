<script setup>
import { ref, onMounted, computed } from 'vue'
import api from "@/api/axios";
import Chart from 'primevue/chart'
import { useUserStore } from '../stores/user'
import { reactive, watch } from 'vue'
import { fechaBonitaDashboard, fechaBonitaCompleta, fechaRangoBonito } from '@/utils/formatDate'


// ===============================
//  Usuario actual
// ===============================
const user = useUserStore()
const esDirector = computed(() => user.rol?.toLowerCase().trim() === 'director')
// ===============================
//  Variables reactivas
// ===============================
const loading = ref(true)
const error = ref(null)
const dashboard = ref(null)
const disponibilidades = ref([])

//  Datos del gráfico (solo turnos)
const chartData = ref({ labels: [], datasets: [] })
const chartOptions = ref({})

// ===============================
//  Cargar datos del backend
// ===============================
const fetchDashboard = async () => {
  try {
    loading.value = true
    const [resDashboard, resSemanal, resDisponibilidad] = await Promise.all([
      api.get('/dashboard', { withCredentials: true }),
      api.get('/dashboard/semanal', { withCredentials: true }),
      api.get('/disponibilidades', { withCredentials: true })
    ])

    dashboard.value = resDashboard.data

    // 🔹 Si es director → ver todas las disponibilidades
    // 🔹 Si es profesional → ver solo las propias (backend ya filtra)
    disponibilidades.value = resDisponibilidad.data

    //  Configurar gráfico de turnos
    const { labels, turnos } = resSemanal.data
    const colores = turnos.map(v => (v > 5 ? '#00936B' : '#3DB5E6'))

    chartData.value = {
      labels,
      datasets: [
        {
          label: 'Turnos programados',
          data: turnos,
          backgroundColor: colores,
          borderRadius: 8,
          hoverBackgroundColor: '#0073A7',
          borderWidth: 0
        }
      ]
    }

    chartOptions.value = {
      responsive: true,
      animation: { duration: 1000, easing: 'easeOutQuart' },
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: '#374151', font: { size: 13 } }
        },
        tooltip: {
          backgroundColor: '#111827',
          titleFont: { size: 14, weight: 'bold' },
          bodyFont: { size: 13 },
          callbacks: { label: (context) => `Turnos: ${context.parsed.y}` }
        },
        title: {
          display: true,
          text: 'Turnos programados — próximos 7 días',
          font: { size: 16, weight: 'bold' },
          color: '#1E3A8A'
        }
      },
      scales: {
        x: {
          title: { display: true, text: 'Día', color: '#374151', font: { weight: 'bold' } },
          ticks: { color: '#6B7280' },
          grid: { display: false }
        },
        y: {
          title: { display: true, text: 'Cantidad de turnos', color: '#374151', font: { weight: 'bold' } },
          beginAtZero: true,
          ticks: { stepSize: 1, color: '#6B7280' },
          grid: { color: '#E5E7EB' }
        }
      }
    }
  } catch (err) {
    console.error('Error cargando dashboard:', err)
    error.value = 'Error al cargar el panel.'
  } finally {
    loading.value = false
  }
}

// 🔹 Agrupar disponibilidades por profesional
const profesionalesAgrupados = reactive([])

// Cada vez que cambia la lista de disponibilidades, reconstruimos el agrupado
watch(disponibilidades, (nuevas) => {
  profesionalesAgrupados.length = 0
  const mapa = {}

  for (const d of nuevas) {
    if (!mapa[d.profesional]) {
      mapa[d.profesional] = { nombre: d.profesional, disponibilidades: [], mostrar: false }
    }
    mapa[d.profesional].disponibilidades.push(d)
  }

  for (const key in mapa) {
    profesionalesAgrupados.push(mapa[key])
  }
}, { immediate: true })

//  Inicialización
onMounted(fetchDashboard)
</script>

<template>
  <div class="p-4">
    <h1 class="text-3xl font-semibold mb-6 text-[#003B70]">Panel de Control</h1>

    <div v-if="loading" class="text-gray-500">Cargando información...</div>
    <div v-if="error" class="text-red-500">{{ error }}</div>

    <div v-if="dashboard && !loading" class="grid grid-cols-12 gap-6">
      <!-- TARJETAS -->
      <div
        class="col-span-12 sm:col-span-6 lg:col-span-3 transition-all duration-300 hover:scale-[1.02]"
        v-for="(value, key) in dashboard.estadisticas"
        :key="key"
      >
        <div class="card shadow-md border border-gray-100 bg-white rounded-xl p-4">
          <div class="flex justify-between mb-3">
            <div>
              <span class="block text-gray-500 capitalize text-sm">{{ key }}</span>
              <div class="text-2xl font-semibold text-[#00936B]">{{ value }}</div>
            </div>
            <div class="flex items-center justify-center bg-[#E0F7FA] rounded-full w-10 h-10">
              <i class="pi pi-chart-bar text-[#0073A7] text-lg"></i>
            </div>
          </div>
        </div>
      </div>

      <!-- TURNOS DEL DÍA -->
      <div class="col-span-12 lg:col-span-6">
        <div class="card shadow-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 rounded-xl p-5 transition">
          <h2 class="text-xl font-semibold mb-4 text-[#003B70]">📅 Turnos de Hoy</h2>
          <p v-if="dashboard.turnos.length === 0" class="text-gray-500">No hay turnos programados para hoy.</p>
          <DataTable
            v-else
            :value="dashboard.turnos"
            paginator
            :rows="5"
            responsiveLayout="scroll"
            class="p-datatable-sm dark:bg-gray-800 dark:text-gray-200 rounded-xl"
          >
            <Column field="fecha" header="Fecha/Hora" :body="(r) => fechaBonitaDashboard(r.fecha)" />
            <Column field="paciente" header="Paciente" />
            <Column field="profesional" header="Profesional" />
            <Column field="motivo" header="Motivo" />
          </DataTable>
        </div>
      </div>

      <!-- PRÓXIMO TURNO 
      <div class="col-span-12 lg:col-span-6">
        <div class="card shadow-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 rounded-xl p-5 transition">
          <h2 class="text-xl font-semibold mb-4 text-[#003B70]">🕒 Próximo Turno</h2>
          <div v-if="dashboard.proximo_turno" class="space-y-2 text-gray-700">
            <p><strong>Paciente:</strong> {{ dashboard.proximo_turno.paciente }} {{ dashboard.proximo_turno.apellido }}</p>
            <p><strong>Fecha:</strong> {{ new Date(dashboard.proximo_turno.fecha).toLocaleString() }}</p>
            <p><strong>Motivo:</strong> {{ dashboard.proximo_turno.motivo }}</p>
          </div>
          <p v-else class="text-gray-500">No hay próximos turnos.</p>
        </div>
      </div>
-->

      <!-- PRÓXIMO TURNO -->
      <div class="col-span-12 lg:col-span-6">
        <div class="card shadow-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 rounded-xl p-5 transition">
          <h2 class="text-xl font-semibold mb-4 text-[#003B70] dark:text-white">🕒 Próximo Turno</h2>

          <div v-if="dashboard.proximo_turno" class="space-y-2 text-gray-700 dark:text-gray-200">
            <p><strong>Paciente:</strong> {{ dashboard.proximo_turno.paciente }} {{ dashboard.proximo_turno.apellido }}</p>
            <p><strong>Fecha:</strong>{{ fechaRangoBonito(dashboard.proximo_turno.fecha_inicio, dashboard.proximo_turno.fecha_fin) }}</p>
            <p><strong>Motivo:</strong> {{ dashboard.proximo_turno.motivo }}</p>
          </div>

          <p v-else class="text-gray-500 dark:text-gray-400">
            No hay próximos turnos.
          </p>
        </div>
      </div>

      <!-- GRÁFICO -->
      <div class="col-span-12 lg:col-span-8">
        <div class="card shadow-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 rounded-xl p-5 transition">
          <h2 class="text-xl font-semibold mb-4 text-[#003B70]">📈 Turnos programados (próximos 7 días)</h2>
          <Chart
            v-if="chartData && chartData.labels.length > 0"
            type="bar"
            :data="chartData"
            :options="chartOptions"
            class="h-80"
          />
          <p v-else class="text-gray-500">Sin datos disponibles para el gráfico.</p>
        </div>
      </div>

      <!-- DISPONIBILIDAD -->
      <div class="col-span-12 lg:col-span-4">
        <div class="card shadow-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 rounded-xl p-5 transition">
          <h2 class="text-xl font-semibold mb-4 text-[#003B70] flex items-center gap-2">🩺 Disponibilidad</h2>

          <!-- 👨‍⚕️ PROFESIONAL -->
          <template v-if="!esDirector">
            <div v-if="disponibilidades.length > 0" class="space-y-2">
              <div
                v-for="(d, i) in disponibilidades"
                :key="i"
                class="flex justify-between text-gray-700 border-b border-gray-100 pb-1"
              >
                <span class="font-medium">{{ d.dia_semana }}</span>
                <span
                  :class="[
                    'text-sm',
                    d.activo ? 'text-gray-600' : 'text-red-500 font-semibold'
                  ]"
                >
                  {{ d.activo ? `${d.hora_inicio} – ${d.hora_fin}` : 'No disponible' }}
                </span>
              </div>
            </div>
            <p v-else class="text-gray-500 italic">No hay disponibilidades cargadas.</p>

            <div class="mt-4 text-right">
              <router-link
                to="/disponibilidad"
                class="text-blue-600 hover:text-blue-800 text-sm font-medium transition"
              >
                🔧 Editar disponibilidad
              </router-link>
            </div>
          </template>

        <!-- 🧑‍💼 DIRECTOR: vista agrupada -->
        <template v-else>
          <div v-if="disponibilidades.length > 0" class="space-y-4 overflow-y-auto max-h-96">
            <div
              v-for="(prof, index) in profesionalesAgrupados"
              :key="index"
              class="border rounded-lg shadow-sm bg-white"
            >
              <!-- Encabezado -->
              <div
                @click="prof.mostrar = !prof.mostrar"
                class="flex justify-between items-center cursor-pointer bg-blue-50 hover:bg-blue-100 px-4 py-3 rounded-t-lg transition-all"
              >
                <h3 class="font-semibold text-gray-800 text-lg">{{ prof.nombre }}</h3>
                <i
                  :class="[
                    'pi',
                    prof.mostrar ? 'pi-chevron-up' : 'pi-chevron-down',
                    'text-blue-700'
                  ]"
                ></i>
              </div>

              <!-- Detalle expandible -->
              <div v-if="prof.mostrar" class="p-4 border-t">
                <table class="w-full text-sm border-collapse">
                  <thead>
                    <tr class="bg-blue-50 text-gray-700">
                      <th class="px-2 py-1 text-left">Día</th>
                      <th class="px-2 py-1 text-center">Horario</th>
                      <th class="px-2 py-1 text-center">Estado</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="(d, i) in prof.disponibilidades"
                      :key="i"
                      :class="['hover:bg-gray-50 transition-all', !d.activo ? 'bg-red-50 text-red-600' : '']"
                    >
                      <td class="px-2 py-1">{{ d.dia_semana }}</td>
                      <td class="px-2 py-1 text-center">{{ d.hora_inicio }} – {{ d.hora_fin }}</td>
                      <td class="px-2 py-1 text-center font-semibold">
                        <span :class="d.activo ? 'text-green-600' : 'text-red-500'">
                          {{ d.activo ? 'Activo' : 'Inactivo' }}
                        </span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <p v-else class="text-gray-500 italic">No hay disponibilidades cargadas.</p>
        </template>
        </div>
      </div>
    </div>
  </div>
</template>
