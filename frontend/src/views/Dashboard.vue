<template>
  <section class="page">
    <header class="page-head">
      <div>
        <h2>运营概览</h2>
        <p class="page-desc">各模块与本页共用同一份统计口径：待处理、异常量均按状态统一统计。</p>
      </div>
    </header>
    <div class="stat-row">
      <article v-for="card in cards" :key="card.label" class="stat-card">
        <span class="stat-label">{{ card.label }}</span>
        <strong class="stat-value">{{ card.value }}</strong>
      </article>
    </div>
    <p v-if="missing.length" class="error-text">
      {{ missingNotice }}
    </p>
    <table class="data-table">
      <thead>
        <tr><th>业务模块</th><th>记录总数</th><th>待处理</th><th>异常量</th><th>数据状态</th></tr>
      </thead>
      <tbody>
        <tr v-for="row in moduleRows" :key="row.name">
          <td>{{ row.label }}</td>
          <td>{{ row.missing ? '—' : row.total }}</td>
          <td>{{ row.missing ? '—' : row.pending }}</td>
          <td>{{ row.missing ? '—' : row.abnormal }}</td>
          <td>
            <span v-if="row.missing" class="error-text">缺数：{{ row.reason }}</span>
            <span v-else>已统计</span>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { fetchJson } from '@/api/client'

type ModuleSummary = {
  name: string
  label: string
  total: number | null
  pending: number | null
  abnormal: number | null
  missing?: boolean
  reason?: string
}

type Overview = {
  cards: { label: string; value: number }[]
  modules: ModuleSummary[]
  missing: { name: string; label: string; reason: string }[]
}

const cards = ref<Overview['cards']>([])
const moduleRows = ref<ModuleSummary[]>([])
const missing = ref<Overview['missing']>([])
const errorMessage = ref('')

const missingNotice = computed(() => {
  if (!missing.value.length) return ''
  const labels = missing.value.map((item) => item.label).join('、')
  return `${labels} 的数据取不到，卡片合计未计入这些模块（没有按零处理）；请稍后刷新或检查对应模块接口。`
})

onMounted(async () => {
  try {
    const payload = await fetchJson<Overview>('/api/overview')
    cards.value = payload.cards
    moduleRows.value = payload.modules
    missing.value = payload.missing ?? []
  } catch (error) {
    // 不再用一片 0 兜底：取不到数时明确提示，避免概览数字与模块页对不上却没人发现
    errorMessage.value = error instanceof Error ? error.message : '运营概览数据加载失败'
  }
})
</script>
