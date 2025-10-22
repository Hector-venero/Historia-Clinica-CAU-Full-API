<template>
  <div class="p-4">
    <h1 class="text-2xl font-bold mb-4">Listado de Pacientes</h1>

    <input
      v-model="busqueda"
      type="text"
      placeholder="Buscar por nombre o DNI"
      class="p-inputtext p-component w-full mb-4 border rounded px-3 py-2"
    />

    <div v-if="filtrados.length > 0" class="overflow-x-auto">
      <table class="min-w-full bg-white rounded shadow">
        <thead>
          <tr>
            <th class="py-2 px-4 border-b">DNI</th>
            <th class="py-2 px-4 border-b">Apellido</th>
            <th class="py-2 px-4 border-b">Nombre</th>
            <th class="py-2 px-4 border-b">Nacimiento</th>
            <th class="py-2 px-4 border-b">Sexo</th>
            <th class="py-2 px-4 border-b">Teléfono</th>
            <th class="py-2 px-4 border-b">Email</th>
            <th class="py-2 px-4 border-b">Acciones</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="paciente in filtrados" :key="paciente.id">
            <td class="py-2 px-4 border-b">{{ paciente.dni }}</td>
            <td class="py-2 px-4 border-b">{{ paciente.apellido }}</td>
            <td class="py-2 px-4 border-b">{{ paciente.nombre }}</td>
            <td class="py-2 px-4 border-b">{{ formatFecha(paciente.fecha_nacimiento) }}</td>
            <td class="py-2 px-4 border-b">{{ paciente.sexo }}</td>
            <td class="py-2 px-4 border-b">{{ paciente.telefono }}</td>
            <td class="py-2 px-4 border-b">{{ paciente.email }}</td>
            <td class="py-2 px-4 border-b flex gap-2">
              <button class="bg-green-500 text-white px-2 py-1 rounded" @click="editarPaciente(paciente.id)">
                Editar
              </button>
              <button class="bg-red-500 text-white px-2 py-1 rounded" @click="confirmarEliminar(paciente)">
                Eliminar
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <p v-else>No se encontraron pacientes.</p>

    <!-- Modal de confirmación -->
    <Dialog v-model:visible="mostrarDialog" modal header="Confirmar Eliminación" :style="{ width: '350px' }">
      <p>⚠️ Esta acción eliminará permanentemente el paciente y sus datos.<br>¿Estás seguro que querés continuar?</p>
      <template #footer>
        <Button label="Cancelar" icon="pi pi-times" class="p-button-text" @click="cancelarEliminar" />
        <Button label="Eliminar" icon="pi pi-check" class="p-button-danger" @click="eliminarPacienteConfirmado" />
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import pacienteService from '@/service/pacienteService'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

const pacientes = ref([])
const busqueda = ref('')
const router = useRouter()

const pacienteAEliminar = ref(null)
const mostrarDialog = ref(false)

const fetchPacientes = async () => {
  try {
    const res = await pacienteService.getPacientes()
    pacientes.value = res.data
  } catch (err) {
    console.error(err)
  }
}

onMounted(() => {
  fetchPacientes()
})

const filtrados = computed(() => {
  if (!busqueda.value) return pacientes.value
  return pacientes.value.filter(p =>
    p.nombre.toLowerCase().includes(busqueda.value.toLowerCase()) ||
    p.apellido.toLowerCase().includes(busqueda.value.toLowerCase()) ||
    p.dni.includes(busqueda.value)
  )
})

const editarPaciente = (id) => {
  router.push(`/pacientes/${id}/editar`)
}

const confirmarEliminar = (paciente) => {
  pacienteAEliminar.value = paciente
  mostrarDialog.value = true
}

const cancelarEliminar = () => {
  pacienteAEliminar.value = null
  mostrarDialog.value = false
}

const eliminarPacienteConfirmado = async () => {
  if (!pacienteAEliminar.value) return
  try {
    await pacienteService.deletePaciente(pacienteAEliminar.value.id)
    pacientes.value = pacientes.value.filter(p => p.id !== pacienteAEliminar.value.id)
    mostrarDialog.value = false
    pacienteAEliminar.value = null
  } catch (error) {
    console.error(error)
    alert('❌ Error al eliminar paciente.')
  }
}

const formatFecha = (fecha) => {
  if (!fecha) return ''
  return new Intl.DateTimeFormat('es-AR').format(new Date(fecha))
}
</script>

<style scoped></style>
