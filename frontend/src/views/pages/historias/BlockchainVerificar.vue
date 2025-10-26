<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

// PrimeVue (si tu proyecto ya lo usa; si no, se renderiza igual con classes)
import Button from 'primevue/button'
import Card from 'primevue/card'
import InputNumber from 'primevue/inputnumber'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import ProgressSpinner from 'primevue/progressspinner'
import Message from 'primevue/message'
import { useRoute } from 'vue-router'

const historiaId = ref(null)
const resultado = ref(null)
const error = ref(null)
const loadingAccion = ref(false)
const loadingTabla = ref(false)
const auditorias = ref([])
const totalAuditorias = ref(0)
const tablePage = ref(0)
const rows = ref(10)
const sortField = ref('fecha')
const sortOrder = ref(-1) // desc
const route = useRoute()

const limpiarEstado = () => {
  error.value = null
  resultado.value = null
}

const registrarEnBfa = async () => {
  if (!historiaId.value) {
    error.value = 'Ingresá un ID de historia válido.'
    return
  }
  limpiarEstado()
  loadingAccion.value = true
  try {
    const { data } = await axios.post(`/api/blockchain/registrar/${historiaId.value}`, {}, { withCredentials: true })
    resultado.value = {
      accion: 'registrar',
      mensaje: data.mensaje || 'Hash publicado correctamente',
      hash_local: data.hash,
      hash_bfa: null,
      tx_hash: data.tx_hash,
      valido: null
    }
  } catch (e) {
    error.value = e?.response?.data?.error || 'No se pudo registrar el hash en BFA.'
  } finally {
    loadingAccion.value = false
  }
}

const verificar = async () => {
  if (!historiaId.value) {
    error.value = 'Ingresá un ID de historia válido.'
    return
  }
  limpiarEstado()
  loadingAccion.value = true
  try {
    const { data } = await axios.get(`/api/blockchain/verificar/${historiaId.value}`, { withCredentials: true })
    resultado.value = {
      accion: 'verificar',
      mensaje: data.mensaje,
      hash_local: data.hash_local,
      hash_bfa: data.hash_bfa,
      tx_hash: data.tx_hash,
      valido: !!data.valido
    }
    // refrescamos auditorías para que aparezca la última verificación
    await cargarAuditorias()
  } catch (e) {
    error.value = e?.response?.data?.error || 'Error verificando integridad.'
  } finally {
    loadingAccion.value = false
  }
}

const cargarAuditorias = async () => {
  loadingTabla.value = true
  error.value = null
  try {
    // Backend devuelve todo; hacemos orden y paginado en front por simplicidad
    const { data } = await axios.get('/api/blockchain/auditorias', { withCredentials: true })
    // sort
    const sorted = [...data].sort((a, b) => {
      const aa = a[sortField.value]
      const bb = b[sortField.value]
      const cmp = aa > bb ? 1 : aa < bb ? -1 : 0
      return sortOrder.value === 1 ? cmp : -cmp
    })
    totalAuditorias.value = sorted.length
    // page
    const start = tablePage.value * rows.value
    const end = start + rows.value
    auditorias.value = sorted.slice(start, end)
  } catch (e) {
    error.value = e?.response?.data?.error || 'No se pudieron cargar las auditorías.'
  } finally {
    loadingTabla.value = false
  }
}

const onPage = async (ev) => {
  tablePage.value = ev.page
  rows.value = ev.rows
  await cargarAuditorias()
}

const onSort = async (ev) => {
  sortField.value = ev.sortField
  sortOrder.value = ev.sortOrder
  tablePage.value = 0
  await cargarAuditorias()
}

onMounted(() => {
  // Detectar ID desde la URL o query (?id=12)
  const pathParts = window.location.pathname.split('/')
  const posibleId = parseInt(pathParts[pathParts.length - 1])
  const queryId = route.query.id ? parseInt(route.query.id) : null

  if (!isNaN(posibleId)) {
    historiaId.value = posibleId
    console.log(`🧩 ID detectado desde path: ${posibleId}`)
  } else if (queryId) {
    historiaId.value = queryId
    console.log(`🧩 ID detectado desde query: ${queryId}`)
  }

  cargarAuditorias()
})

</script>

<template>
  <div class="p-4 md:p-6 max-w-6xl mx-auto space-y-6">
    <div class="flex items-end gap-4 flex-wrap">
      <div class="w-64">
        <label class="block text-sm mb-1">ID de historia</label>
        <!-- Si no usás PrimeVue InputNumber, podés cambiar por input type="number" -->
        <InputNumber v-model="historiaId" inputClass="w-full p-2 border rounded" :useGrouping="false" :min="1" placeholder="Ej: 12" />
      </div>

      <div class="flex items-center gap-2">
        <Button :disabled="loadingAccion || !historiaId" @click="registrarEnBfa" label="Registrar en BFA" />
        <Button :disabled="loadingAccion || !historiaId" @click="verificar" label="Verificar integridad" severity="success" />
        <Button :disabled="loadingTabla" @click="cargarAuditorias" label="Refrescar auditorías" severity="secondary" outlined />
      </div>

      <div v-if="loadingAccion" class="flex items-center gap-2 ml-auto">
        <ProgressSpinner style="width:28px;height:28px" strokeWidth="6" aria-label="Cargando" />
        <span class="text-sm text-gray-500">Procesando…</span>
      </div>
    </div>

    <div v-if="error" class="max-w-3xl">
      <Message severity="error" :closable="false">{{ error }}</Message>
    </div>

    <!-- Resultado -->
    <Card v-if="resultado" class="border rounded-lg shadow-sm">
      <template #title>
        <div class="flex items-center justify-between">
          <span class="text-lg font-semibold">
            {{ resultado.accion === 'registrar' ? 'Registro en Blockchain' : 'Verificación de Integridad' }}
          </span>
          <Tag v-if="resultado.valido === true" value="VÁLIDO" severity="success" />
          <Tag v-else-if="resultado.valido === false" value="NO VÁLIDO" severity="danger" />
          <Tag v-else value="OK" severity="info" />
        </div>
      </template>
      <template #content>
        <div class="grid md:grid-cols-2 gap-4 text-sm">
          <div class="space-y-1">
            <div class="font-medium">Mensaje</div>
            <div class="font-mono break-all">{{ resultado.mensaje }}</div>
          </div>
          <div class="space-y-1">
            <div class="font-medium">Tx Hash</div>
            <div class="font-mono break-all">{{ resultado.tx_hash || '—' }}</div>
          </div>
          <div class="space-y-1 md:col-span-2">
            <div class="font-medium">Hash local (recalculado / registrado)</div>
            <div class="font-mono break-all">{{ resultado.hash_local || '—' }}</div>
          </div>
          <div class="space-y-1 md:col-span-2" v-if="resultado.hash_bfa !== null">
            <div class="font-medium">Hash en BFA (tx.input)</div>
            <div class="font-mono break-all">{{ resultado.hash_bfa || '—' }}</div>
          </div>
        </div>
      </template>
    </Card>

    <!-- Auditorías -->
    <Card class="border rounded-lg shadow-sm">
      <template #title>
        <div class="flex items-center justify-between">
          <span class="text-lg font-semibold">Auditorías de verificación</span>
          <div class="text-sm text-gray-500">Total: {{ totalAuditorias }}</div>
        </div>
      </template>
      <template #content>
        <div v-if="loadingTabla" class="py-10 flex items-center justify-center">
          <ProgressSpinner style="width:40px;height:40px" strokeWidth="6" aria-label="Cargando" />
        </div>

        <div v-else>
          <DataTable
            :value="auditorias"
            :paginator="true"
            :rows="rows"
            :totalRecords="totalAuditorias"
            :first="tablePage * rows"
            lazy
            @page="onPage"
            sortMode="single"
            :sortField="sortField"
            :sortOrder="sortOrder"
            @sort="onSort"
            responsiveLayout="scroll"
            size="small"
            class="text-sm"
          >
            <Column field="fecha" header="Fecha" sortable />
            <Column field="usuario" header="Usuario" sortable />
            <Column field="historia_id" header="Historia" sortable />
            <Column header="Resultado">
              <template #body="{ data }">
                <Tag :value="data.valido ? 'VÁLIDO' : 'NO VÁLIDO'" :severity="data.valido ? 'success' : 'danger'" />
              </template>
            </Column>
            <Column field="hash_local" header="Hash Local">
              <template #body="{ data }">
                <span class="font-mono break-all block max-w-[380px] truncate" :title="data.hash_local">{{ data.hash_local }}</span>
              </template>
            </Column>
            <Column field="hash_bfa" header="Hash BFA">
              <template #body="{ data }">
                <span class="font-mono break-all block max-w-[380px] truncate" :title="data.hash_bfa">{{ data.hash_bfa }}</span>
              </template>
            </Column>
          </DataTable>
        </div>
      </template>
    </Card>
  </div>
</template>

<style scoped>
/* fallback rápido si no tenés PrimeVue Tag/Button:
   (podés eliminar si usás los componentes reales) */
.p-tag {
  @apply inline-flex items-center px-2 py-1 rounded text-xs font-semibold;
}
.p-tag-success { @apply bg-green-100 text-green-700; }
.p-tag-danger { @apply bg-red-100 text-red-700; }
.p-tag-info   { @apply bg-blue-100 text-blue-700; }
</style>
