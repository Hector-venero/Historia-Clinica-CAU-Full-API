<script setup>
import axios from 'axios'
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const router = useRouter()
const route = useRoute()

const paciente = ref(null)
const fecha = ref(new Date().toISOString().slice(0, 10)) // Hoy por default
const evolucion = ref('')

// Simular recibir paciente por parámetro (ejemplo: /agregar-evolucion/:id)
const pacienteId = route.params.id

const cargarPaciente = async () => {
  try {
    const res = await axios.get(`/api/pacientes/${pacienteId}`)
    paciente.value = res.data
  } catch (error) {
    console.error('Error al cargar paciente', error)
  }
}

const guardarEvolucion = async () => {
  try {
    await axios.post(`/api/pacientes/${pacienteId}/evoluciones`, {
      fecha: fecha.value,
      texto: evolucion.value,
    })
    alert('Evolución guardada correctamente ✅')
    router.push(`/pacientes/${pacienteId}/historias`)
  } catch (error) {
    console.error('Error al guardar evolución', error)
    alert('Error al guardar evolución ❌')
  }
}

cargarPaciente()
</script>

<template>
  <div class="p-4">
    <h1 class="text-2xl font-bold mb-4">Agregar Evolución</h1>

    <div v-if="paciente">
      <p><strong>Paciente:</strong> {{ paciente.apellido }}, {{ paciente.nombre }} (HC: {{ paciente.nro_hc }})</p>
      <p><strong>DNI:</strong> {{ paciente.dni }}</p>
    </div>

    <div class="mt-4">
      <label class="block font-medium mb-2">Fecha</label>
      <input type="date" v-model="fecha" class="p-2 border rounded w-full mb-4" />

      <label class="block font-medium mb-2">Evolución</label>
      <textarea
        v-model="evolucion"
        rows="8"
        placeholder="Escribí la evolución clínica..."
        class="w-full p-2 border rounded mb-4"
      ></textarea>

      <button @click="guardarEvolucion" class="bg-green-600 text-white px-4 py-2 rounded">Guardar Evolución</button>
    </div>
  </div>
</template>
