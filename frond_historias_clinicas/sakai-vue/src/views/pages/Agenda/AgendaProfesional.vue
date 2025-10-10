<script setup>
import { ref, onMounted } from 'vue'
import turnosService from '@/service/turnosService'
import ausenciasService from '@/service/ausenciasService'
import { useToast } from 'primevue/usetoast'

const toast = useToast()

const turnos = ref([])
const ausencias = ref([])
const fechaAusencia = ref('')

const cargarDatos = async () => {
  try {
    const resTurnos = await turnosService.listar()
    turnos.value = resTurnos.data

    const resAusencias = await ausenciasService.listar()
    ausencias.value = resAusencias.data
  } catch (e) {
    console.error(e)
    toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo cargar agenda', life: 3000 })
  }
}

const agregarAusencia = async () => {
  if (!fechaAusencia.value) return
  try {
    await ausenciasService.crear({ fecha: fechaAusencia.value })
    toast.add({ severity: 'success', summary: 'Éxito', detail: 'Día bloqueado ✅', life: 3000 })
    fechaAusencia.value = ''
    await cargarDatos()
  } catch (e) {
    console.error(e)
    toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo bloquear día', life: 3000 })
  }
}

const eliminarAusencia = async (id) => {
  try {
    await ausenciasService.eliminar(id)
    toast.add({ severity: 'success', summary: 'Éxito', detail: 'Ausencia eliminada ✅', life: 3000 })
    await cargarDatos()
  } catch (e) {
    console.error(e)
    toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo eliminar', life: 3000 })
  }
}

onMounted(() => {
  cargarDatos()
})
</script>

<template>
  <div class="p-4">
    <Toast />

    <h1 class="text-2xl font-bold mb-4">📅 Agenda</h1>

    <!-- Turnos -->
    <h2 class="text-xl font-semibold mb-2">Turnos</h2>
    <DataTable :value="turnos" paginator :rows="5" responsiveLayout="scroll" class="mb-6">
      <Column field="start" header="Fecha/Hora" :body="(row) => new Date(row.start).toLocaleString()" />
      <Column field="paciente" header="Paciente" />
      <Column field="dni" header="DNI" />
      <Column field="profesional" header="Profesional" />
      <Column field="description" header="Motivo" />
    </DataTable>

    <!-- Ausencias -->
    <h2 class="text-xl font-semibold mb-2">Ausencias / Bloqueos</h2>
    <div class="flex items-center gap-2 mb-4">
      <input type="date" v-model="fechaAusencia" class="border p-2 rounded" />
      <button @click="agregarAusencia" class="bg-red-600 text-white px-4 py-2 rounded">Bloquear día</button>
    </div>

    <DataTable :value="ausencias" paginator :rows="5" responsiveLayout="scroll">
      <Column field="fecha" header="Fecha" :body="(row) => new Date(row.fecha).toLocaleDateString()" />
      <Column header="Acciones" :body="(row) => 
        h('button', { 
          class: 'text-sm text-red-500 hover:underline', 
          onClick: () => eliminarAusencia(row.id) 
        }, 'Eliminar')" />
    </DataTable>
  </div>
</template>
