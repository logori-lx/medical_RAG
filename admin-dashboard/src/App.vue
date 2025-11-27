<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

// --- 状态管理 ---
const config = ref({
  template_format: '',
  custom_rules: ''
})
const loading = ref(false)
const status = ref({ msg: 'Connecting...', type: 'gray' })
const toast = ref({ show: false, msg: '', type: 'success' })

// [新] 移动端 Tab 状态 ('presets' | 'settings')
// 默认在手机上显示表单(settings)，方便直接查看
const mobileTab = ref('settings')

// --- 预设模板 ---
const presets = {
  standard: {
    label: "Angular 标准",
    format: "<type>(<scope>): <subject>",
    rules: "1. Type must be: feat, fix, docs, style, refactor.\n2. Scope is optional.\n3. Subject must be lowercase."
  },
  module: {
    label: "模块化严格版",
    format: "[<Domain>][<Type>] <Summary>",
    rules: "1. <Domain> must be: Backend, Frontend, Infra.\n2. <Type> must be: Feat, Fix, Refactor.\n3. Example: [Backend][Fix] fix login bug."
  },
  simple: {
    label: "极简风格",
    format: "<Type>: <Summary>",
    rules: "1. Keep it simple.\n2. Type: Update, Fix, Add.\n3. Max 50 chars."
  }
}

// --- API 方法 ---
const loadConfig = async () => {
  loading.value = true
  try {
    const res = await axios.get('/api/v1/config')
    config.value = res.data
    status.value = { msg: 'Server Online', type: 'green' }
  } catch (error) {
    console.error(error)
    status.value = { msg: 'Server Offline', type: 'red' }
    showToast('无法连接到服务器', 'error')
  } finally {
    loading.value = false
  }
}

const saveConfig = async () => {
  try {
    await axios.post('/api/v1/config', config.value)
    showToast('配置已保存并在全团队生效', 'success')
  } catch (error) {
    showToast('保存失败', 'error')
  }
}

// --- 辅助方法 ---
const applyPreset = (key) => {
  config.value.template_format = presets[key].format
  config.value.custom_rules = presets[key].rules
  // [新] 手机端点击预设后，自动跳回编辑页查看效果
  if (window.innerWidth < 768) {
    mobileTab.value = 'settings'
    showToast(`已应用: ${presets[key].label}`, 'success')
  }
}

const showToast = (msg, type) => {
  toast.value = { show: true, msg, type }
  setTimeout(() => toast.value.show = false, 3000)
}

onMounted(() => {
  loadConfig()
})
</script>

<template>
  <div class="min-h-screen bg-slate-950 font-sans text-slate-200 md:p-6 p-0 flex justify-center">
    
    <div class="w-full max-w-5xl bg-slate-900 md:rounded-2xl shadow-2xl overflow-hidden border-slate-800 md:border flex flex-col md:flex-row h-screen md:h-auto">
      
      <div class="md:hidden flex-none bg-slate-800 border-b border-slate-700 p-4 flex justify-between items-center sticky top-0 z-20">
        <h1 class="text-xl font-bold text-blue-400">🛡️ Git-Guard</h1>
        <div class="flex items-center gap-2">
          <span :class="`h-2 w-2 rounded-full bg-${status.type}-500 animate-pulse`"></span>
          <span :class="`text-xs font-mono text-${status.type}-400`">{{ status.msg }}</span>
        </div>
      </div>

      <div class="md:hidden flex-none bg-slate-800/50 p-2 grid grid-cols-2 gap-2 border-b border-slate-700">
        <button 
          @click="mobileTab = 'presets'"
          :class="[
            'py-2 text-sm font-bold rounded-lg transition-all',
            mobileTab === 'presets' ? 'bg-blue-600 text-white shadow-lg' : 'text-slate-400 hover:bg-slate-700'
          ]"
        >
          🧩 快速预设
        </button>
        <button 
          @click="mobileTab = 'settings'"
          :class="[
            'py-2 text-sm font-bold rounded-lg transition-all',
            mobileTab === 'settings' ? 'bg-blue-600 text-white shadow-lg' : 'text-slate-400 hover:bg-slate-700'
          ]"
        >
          ⚙️ 配置编辑
        </button>
      </div>

      <div 
        :class="[
          'w-full md:w-1/3 bg-slate-800/50 border-r border-slate-700 flex-col overflow-y-auto',
          mobileTab === 'presets' ? 'flex flex-1' : 'hidden md:flex'
        ]"
      >
        <div class="p-6 md:h-full">
          <div class="hidden md:block mb-8">
            <h1 class="text-2xl font-bold text-blue-400 flex items-center gap-2">
              <span class="text-3xl">🛡️</span> Git-Guard
            </h1>
            <div class="mt-3 flex items-center gap-2">
              <span :class="`h-2 w-2 rounded-full bg-${status.type}-500 animate-pulse`"></span>
              <span :class="`text-xs font-mono text-${status.type}-400`">{{ status.msg }}</span>
            </div>
          </div>

          <h3 class="text-xs font-bold text-slate-500 uppercase tracking-wider mb-4 px-1">Template Presets</h3>
          
          <div class="space-y-3 pb-20 md:pb-0">
            <button 
              v-for="(preset, key) in presets" 
              :key="key"
              @click="applyPreset(key)"
              class="w-full text-left p-4 rounded-xl bg-slate-700/30 hover:bg-slate-700 border border-slate-700/50 hover:border-blue-500 transition-all group active:scale-95"
            >
              <div class="flex items-center justify-between mb-1">
                <span class="font-bold text-slate-200 group-hover:text-blue-300 transition-colors">{{ preset.label }}</span>
                <i class="fa-solid fa-chevron-right text-xs text-slate-600 group-hover:text-blue-400"></i>
              </div>
              <div class="text-xs text-slate-500 font-mono truncate opacity-70 group-hover:opacity-100">{{ preset.format }}</div>
            </button>
          </div>
        </div>
      </div>

      <div 
        :class="[
          'w-full md:w-2/3 bg-slate-900 flex-col overflow-y-auto',
          mobileTab === 'settings' ? 'flex flex-1' : 'hidden md:flex'
        ]"
      >
        <div class="p-6 md:p-8 h-full flex flex-col">
          <form @submit.prevent="saveConfig" class="space-y-6 flex-1">
            
            <div>
              <label class="block text-sm font-bold text-blue-300 mb-2 px-1">Template Format</label>
              <input 
                v-model="config.template_format"
                type="text" 
                class="w-full bg-slate-950 text-white border border-slate-700 rounded-xl p-4 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition font-mono shadow-inner"
                placeholder="e.g. [<Module>] <Description>"
              >
              <p class="text-xs text-slate-500 mt-2 px-1">定义 AI 生成 Commit Message 的目标格式。</p>
            </div>

            <div class="flex-1 flex flex-col">
              <label class="block text-sm font-bold text-blue-300 mb-2 px-1">Custom AI Rules</label>
              <textarea 
                v-model="config.custom_rules"
                class="w-full flex-1 bg-slate-950 text-white border border-slate-700 rounded-xl p-4 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition font-mono text-sm leading-relaxed shadow-inner min-h-[200px]"
                placeholder="在此输入给 AI 的具体指令 (支持多行)..."
              ></textarea>
            </div>

            <div class="pt-4 md:pt-0 sticky bottom-0 bg-slate-900/95 backdrop-blur py-4 border-t border-slate-800 md:border-none md:static flex items-center justify-end gap-3 z-10">
              <button 
                type="button" 
                @click="loadConfig" 
                class="px-4 py-3 rounded-xl text-slate-400 hover:bg-slate-800 hover:text-white transition font-medium"
              >
                Reset
              </button>
              <button 
                type="submit" 
                class="flex-1 md:flex-none bg-blue-600 hover:bg-blue-500 text-white font-bold py-3 px-8 rounded-xl shadow-lg shadow-blue-900/20 active:scale-95 transition-all flex items-center justify-center gap-2"
                :disabled="loading"
              >
                <span v-if="loading" class="animate-spin">↻</span>
                <span>Save Config</span>
              </button>
            </div>
            
            <div class="h-4 md:hidden"></div>
          </form>
        </div>
      </div>

    </div>

    <div 
      v-if="toast.show"
      :class="[
        'fixed bottom-6 left-1/2 md:left-auto md:right-6 transform -translate-x-1/2 md:translate-x-0 px-6 py-3 rounded-full shadow-2xl transition-all duration-300 flex items-center gap-3 z-50 whitespace-nowrap',
        toast.type === 'error' ? 'bg-red-500 text-white' : 'bg-emerald-500 text-white'
      ]"
    >
      <span class="text-lg">{{ toast.type === 'error' ? '❌' : '✅' }}</span>
      <span class="font-bold text-sm">{{ toast.msg }}</span>
    </div>

  </div>
</template>

<style scoped>
/* 针对 Webkit 浏览器的滚动条美化 */
::-webkit-scrollbar {
  width: 6px;
}
::-webkit-scrollbar-track {
  background: #0f172a; 
}
::-webkit-scrollbar-thumb {
  background: #334155; 
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
  background: #475569; 
}
</style>