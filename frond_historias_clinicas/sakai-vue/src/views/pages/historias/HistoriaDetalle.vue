<script setup>
import axios from 'axios'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Toast from 'primevue/toast'
import { useToast } from 'primevue/usetoast'
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const pacienteId = route.params.id

const paciente = ref({})
const convoluciones = ref([])
const toast = useToast()

const showDialog = ref(false)
const nuevaConvolucion = ref({
    titulo: '',
    detalle: ''
})

const fetchHistoria = async () => {
    try {
        const response = await axios.get(`/api/pacientes/${pacienteId}`)
        paciente.value = response.data.paciente
        convoluciones.value = response.data.convoluciones
    } catch (error) {
        console.error('Error al cargar historia:', error)
    }
}

const guardarConvolucion = async () => {
    try {
        await axios.post(`/api/pacientes/${pacienteId}/convoluciones`, nuevaConvolucion.value)
        toast.add({ severity: 'success', summary: 'Éxito', detail: 'Evento agregado', life: 3000 })
        showDialog.value = false
        nuevaConvolucion.value = { titulo: '', detalle: '' }
        await fetchHistoria()
    } catch (error) {
        console.error('Error al guardar convolución:', error)
        toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo guardar', life: 3000 })
    }
}

onMounted(() => {
    fetchHistoria()
})
</script>

<template>
    <Toast />
    <div class="card">
        <h2 class="text-2xl font-semibold mb-4">Historia Clínica de {{ paciente.nombre }}</h2>
        <p><strong>DNI:</strong> {{ paciente.dni }}</p>
        <p><strong>Fecha de Nacimiento:</strong> {{ paciente.fecha_nacimiento }}</p>

        <div class="flex justify-end my-4">
            <Button label="Nueva Convolución" icon="pi pi-plus" @click="showDialog = true" />
        </div>

        <h3 class="text-lg font-medium mt-6">Eventos / Convoluciones</h3>
        <DataTable :value="convoluciones" paginator :rows="5" responsiveLayout="scroll">
            <Column field="fecha" header="Fecha" />
            <Column field="titulo" header="Título" />
            <Column field="detalle" header="Detalle" />
        </DataTable>
    </div>

    <Dialog v-model:visible="showDialog" modal header="Nueva Convolución" :style="{ width: '500px' }">
        <div class="p-fluid">
            <div class="field mb-3">
                <label for="titulo">Título</label>
                <InputText id="titulo" v-model="nuevaConvolucion.titulo" />
            </div>
            <div class="field mb-3">
                <label for="detalle">Detalle</label>
                <Textarea id="detalle" v-model="nuevaConvolucion.detalle" rows="5" />
            </div>
        </div>
        <template #footer>
            <Button label="Cancelar" icon="pi pi-times" class="p-button-text" @click="showDialog = false" />
            <Button label="Guardar" icon="pi pi-check" @click="guardarConvolucion" />
        </template>
    </Dialog>
</template>
