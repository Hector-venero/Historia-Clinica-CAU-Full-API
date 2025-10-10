<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import Chart from 'primevue/chart'

// ------------------------------
// 📦 Variables reactivas
// ------------------------------
const loading = ref(true)
const error = ref(null)
const dashboard = ref(null)

// Datos del gráfico
const chartData = ref({ labels: [], datasets: [] })
const chartOptions = ref({})

// ------------------------------
// 📊 Cargar datos desde el backend
// ------------------------------
const fetchDashboard = async () => {
  try {
    loading.value = true
    const [resDashboard, resSemanal] = await Promise.all([
      axios.get('/api/dashboard', { withCredentials: true }),
      axios.get('/api/dashboard/semanal', { withCredentials: true })
    ])

    dashboard.value = resDashboard.data
    const { labels, turnos, ausencias } = resSemanal.data

    // Colores institucionales UNSAM
    const colores = turnos.map(v => (v > 5 ? '#00936B' : '#3DB5E6')) // verde UNSAM si >5 turnos, celeste si no

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
        },
        {
          label: 'Ausencias / bloqueos',
          data: ausencias,
          backgroundColor: '#B0BEC5',
          borderRadius: 8,
          borderWidth: 0
        }
      ]
    }

    chartOptions.value = {
      responsive: true,
      animation: {
        duration: 1000,
        easing: 'easeOutQuart'
      },
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            color: '#374151',
            font: { size: 13 }
          }
        },
        tooltip: {
          backgroundColor: '#111827',
          titleFont: { size: 14, weight: 'bold' },
          bodyFont: { size: 13 },
          callbacks: {
            label: (context) => {
              const tipo = context.dataset.label
              const valor = context.parsed.y
              return `${tipo}: ${valor}`
            },
            afterBody: (context) => {
              if (context.length === 2) {
                return `Total día: ${context[0].parsed.y + context[1].parsed.y}`
              }
            }
          }
        },
        title: {
          display: true,
          text: 'Turnos y ausencias — próximos 7 días',
          font: { size: 16, weight: 'bold' },
          color: '#1E3A8A'
        }
      },
      scales: {
        x: {
          title: {
            display: true,
            text: 'Día',
            color: '#374151',
            font: { weight: 'bold' }
          },
          ticks: { color: '#6B7280' },
          grid: { display: false }
        },
        y: {
          title: {
            display: true,
            text: 'Cantidad',
            color: '#374151',
            font: { weight: 'bold' }
          },
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

// ------------------------------
// 🚀 Inicialización
// ------------------------------
onMounted(fetchDashboard)
</script>

<template>
  <div class="p-4">
    <h1 class="text-3xl font-semibold mb-6 text-[#003B70]">
      Panel de Control
    </h1>

    <div v-if="loading" class="text-gray-500">Cargando información...</div>
    <div v-if="error" class="text-red-500">{{ error }}</div>

    <div v-if="dashboard && !loading" class="grid grid-cols-12 gap-6">
      <!-- ===============================
           TARJETAS PRINCIPALES
      ================================== -->
      <div
        class="col-span-12 sm:col-span-6 lg:col-span-3 transition-all duration-300 hover:scale-[1.02]"
        v-for="(value, key) in dashboard.estadisticas"
        :key="key"
      >
        <div class="card shadow-md border border-gray-100 bg-white rounded-xl p-4">
          <div class="flex justify-between mb-3">
            <div>
              <span class="block text-gray-500 capitalize text-sm">{{ key }}</span>
              <div class="text-2xl font-semibold text-[#00936B]">
                {{ value }}
              </div>
            </div>
            <div
              class="flex items-center justify-center bg-[#E0F7FA] rounded-full w-10 h-10"
            >
              <i class="pi pi-chart-bar text-[#0073A7] text-lg"></i>
            </div>
          </div>
        </div>
      </div>

      <!-- ===============================
           TURNOS DEL DÍA
      ================================== -->
      <div class="col-span-12 lg:col-span-6">
        <div class="card shadow-md border border-gray-100 bg-white rounded-xl p-5">
          <h2 class="text-xl font-semibold mb-4 text-[#003B70]">📅 Turnos de Hoy</h2>
          <p v-if="dashboard.turnos.length === 0" class="text-gray-500">
            No hay turnos programados para hoy.
          </p>
          <DataTable
            v-else
            :value="dashboard.turnos"
            paginator
            :rows="5"
            responsiveLayout="scroll"
          >
            <Column
              field="fecha"
              header="Fecha/Hora"
              :body="(r) => new Date(r.fecha).toLocaleString()"
            />
            <Column field="paciente" header="Paciente" />
            <Column field="profesional" header="Profesional" />
            <Column field="motivo" header="Motivo" />
          </DataTable>
        </div>
      </div>

      <!-- ===============================
           PRÓXIMO TURNO
      ================================== -->
      <div class="col-span-12 lg:col-span-6">
        <div class="card shadow-md border border-gray-100 bg-white rounded-xl p-5">
          <h2 class="text-xl font-semibold mb-4 text-[#003B70]">🕒 Próximo Turno</h2>
          <div v-if="dashboard.proximo_turno" class="space-y-2 text-gray-700">
            <p>
              <strong>Paciente:</strong>
              {{ dashboard.proximo_turno.paciente }}
              {{ dashboard.proximo_turno.apellido }}
            </p>
            <p>
              <strong>Fecha:</strong>
              {{ new Date(dashboard.proximo_turno.fecha).toLocaleString() }}
            </p>
            <p><strong>Motivo:</strong> {{ dashboard.proximo_turno.motivo }}</p>
          </div>
          <p v-else class="text-gray-500">No hay próximos turnos.</p>
        </div>
      </div>

      <!-- ===============================
           GRÁFICO UNSAM PRO (PRÓXIMOS 7 DÍAS)
      ================================== -->
      <div class="col-span-12 lg:col-span-8">
        <div class="card shadow-md border border-gray-100 bg-white rounded-xl p-5">
          <h2 class="text-xl font-semibold mb-4 text-[#003B70]">
            📈 Actividad médica (próximos 7 días)
          </h2>
          <Chart type="bar" :data="chartData" :options="chartOptions" class="h-80" />
        </div>
      </div>

      <!-- ===============================
           AUSENCIAS
      ================================== -->
      <div class="col-span-12 lg:col-span-4">
        <div class="card shadow-md border border-gray-100 bg-white rounded-xl p-5">
          <h2 class="text-xl font-semibold mb-4 text-[#003B70]">🚫 Ausencias</h2>
          <p v-if="dashboard.ausencias.length === 0" class="text-gray-500">
            No hay ausencias registradas.
          </p>
          <ul v-else class="divide-y divide-gray-200">
            <li
              v-for="a in dashboard.ausencias"
              :key="a.id"
              class="py-2 hover:bg-gray-50 transition-all rounded-md p-2"
            >
              <p class="font-semibold text-[#0073A7]">
                {{ a.motivo || 'Sin motivo especificado' }}
              </p>
              <p class="text-sm text-gray-600">
                {{ new Date(a.fecha_inicio).toLocaleDateString() }} → 
                {{ new Date(a.fecha_fin).toLocaleDateString() }}
              </p>
              <p v-if="a.profesional" class="text-sm text-gray-500">
                👨‍⚕️ {{ a.profesional }}
              </p>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>
