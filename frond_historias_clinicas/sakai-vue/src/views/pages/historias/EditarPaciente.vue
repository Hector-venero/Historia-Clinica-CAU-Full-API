<script setup>
import PacienteForm from '@/components/PacienteForm.vue'
import pacienteService from '@/service/pacienteService'
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const paciente = ref({})

onMounted(async () => {
  const res = await pacienteService.getPaciente(route.params.id)
  paciente.value = res.data
})

const actualizarPaciente = async (data) => {
  await pacienteService.updatePaciente(route.params.id, data)
  router.push('/pacientes')
}
</script>

<template>
  <div class="p-4">
    <h1 class="text-2xl font-bold mb-4">Editar Paciente</h1>
    <PacienteForm :paciente="paciente" :onSubmit="actualizarPaciente" submitText="Guardar Cambios" />
  </div>
</template>
