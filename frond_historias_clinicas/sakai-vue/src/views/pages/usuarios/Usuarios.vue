<template>
  <div class="p-4">
    <h1 class="text-2xl font-bold mb-4">Usuarios registrados</h1>

    <input
      v-model="busqueda"
      type="text"
      placeholder="Buscar por nombre o usuario"
      class="p-inputtext p-component w-full mb-4 border rounded px-3 py-2"
    />

    <div v-if="filtrados.length > 0" class="overflow-x-auto">
      <table class="min-w-full bg-white rounded shadow">
        <thead>
          <tr>
            <th class="py-2 px-4 border-b">ID</th>
            <th class="py-2 px-4 border-b">Nombre</th>
            <th class="py-2 px-4 border-b">Usuario</th>
            <th class="py-2 px-4 border-b">Email</th>
            <th class="py-2 px-4 border-b">Rol</th>
            <th class="py-2 px-4 border-b">Especialidad</th>
            <th class="py-2 px-4 border-b">Estado</th>
            <th class="py-2 px-4 border-b">Acciones</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="usuario in filtrados" :key="usuario.id">
            <td class="py-2 px-4 border-b">{{ usuario.id }}</td>
            <td class="py-2 px-4 border-b">{{ usuario.nombre }}</td>
            <td class="py-2 px-4 border-b">{{ usuario.username }}</td>
            <td class="py-2 px-4 border-b">{{ usuario.email }}</td>
            <td class="py-2 px-4 border-b">{{ usuario.rol }}</td>
            <td class="py-2 px-4 border-b">{{ usuario.especialidad }}</td>
            <!-- ✅ Nuevo Badge de estado -->
            <td class="py-2 px-4 border-b">
              <span
                :class="usuario.activo ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'"
                class="px-3 py-1 text-xs font-semibold rounded-full"
              >
                {{ usuario.activo ? 'Activo' : 'Inactivo' }}
              </span>
            </td>
            <td class="py-2 px-4 border-b flex gap-2">
              <button class="bg-green-500 text-white px-2 py-1 rounded" @click="editarUsuario(usuario.id)">
                Editar
              </button>
              <button class="bg-red-500 text-white px-2 py-1 rounded" @click="confirmarEliminar(usuario)">
                Eliminar
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <p v-else>No se encontraron usuarios.</p>

    <!-- Modal de confirmación -->
    <Dialog v-model:visible="mostrarDialog" modal header="Confirmar Eliminación" :style="{ width: '350px' }">
      <p>⚠️ Esta acción marcará el usuario como inactivo.<br>¿Estás seguro que querés continuar?</p>
      <template #footer>
        <Button label="Cancelar" icon="pi pi-times" class="p-button-text" @click="cancelarEliminar" />
        <Button label="Eliminar" icon="pi pi-check" class="p-button-danger" @click="eliminarUsuarioConfirmado" />
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import usuarioService from '@/service/usuarioService'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

const usuarios = ref([])
const busqueda = ref('')
const router = useRouter()

const usuarioAEliminar = ref(null)
const mostrarDialog = ref(false)

const fetchUsuarios = async () => {
  try {
    const res = await usuarioService.getUsuarios()
    usuarios.value = res.data
  } catch (err) {
    console.error(err)
  }
}

onMounted(fetchUsuarios)

const filtrados = computed(() => {
  if (!busqueda.value) return usuarios.value
  return usuarios.value.filter(u =>
    u.nombre.toLowerCase().includes(busqueda.value.toLowerCase()) ||
    u.username.toLowerCase().includes(busqueda.value.toLowerCase()) ||
    u.email.toLowerCase().includes(busqueda.value.toLowerCase())
  )
})

const editarUsuario = (id) => {
  router.push(`/usuarios/${id}/editar`)
}

const confirmarEliminar = (usuario) => {
  usuarioAEliminar.value = usuario
  mostrarDialog.value = true
}

const cancelarEliminar = () => {
  usuarioAEliminar.value = null
  mostrarDialog.value = false
}

const eliminarUsuarioConfirmado = async () => {
  if (!usuarioAEliminar.value) return
  try {
    await usuarioService.deleteUsuario(usuarioAEliminar.value.id)
    usuarios.value = usuarios.value.filter(u => u.id !== usuarioAEliminar.value.id)
    mostrarDialog.value = false
    usuarioAEliminar.value = null
  } catch (error) {
    console.error(error)
    alert('❌ Error al eliminar usuario.')
  }
}
</script>
