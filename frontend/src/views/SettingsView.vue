<template>
  <div class="container">
    <div class="page-header">
      <h1 class="page-title">系统设置</h1>
      <p class="page-subtitle">
        {{ auth.isAdmin ? '配置文本生成、图片生成和发布账号' : '管理发布账号，模型配置由管理员维护' }}
      </p>
    </div>

    <div v-if="auth.isAdmin && loading" class="loading-container">
      <div class="spinner"></div>
      <p>加载配置中...</p>
    </div>

    <div v-else class="settings-container">
      <!-- 文本生成配置 -->
      <div v-if="auth.isAdmin" class="card">
        <div class="section-header">
          <div>
            <h2 class="section-title">文本生成配置</h2>
            <p class="section-desc">用于生成小红书图文大纲</p>
          </div>
          <button class="btn btn-small" @click="openAddTextModal">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
            添加
          </button>
        </div>

        <!-- 服务商列表表格 -->
        <ProviderTable
          :providers="textConfig.providers"
          :activeProvider="textConfig.active_provider"
          @activate="activateTextProvider"
          @edit="openEditTextModal"
          @delete="deleteTextProvider"
          @test="testTextProviderInList"
        />
      </div>

      <!-- 图片生成配置 -->
      <div v-if="auth.isAdmin" class="card">
        <div class="section-header">
          <div>
            <h2 class="section-title">图片生成配置</h2>
            <p class="section-desc">用于生成小红书配图</p>
          </div>
          <div class="section-actions">
            <button class="btn btn-small" @click="handleImageHealthCheck" :disabled="checkingImageHealth">
              {{ checkingImageHealth ? '检查中...' : '检查图片服务' }}
            </button>
            <button class="btn btn-small" @click="handleImageProbe" :disabled="probingImage">
              {{ probingImage ? '生成测试中...' : '真实生图测试' }}
            </button>
            <button class="btn btn-small" @click="openAddImageModal">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="12" y1="5" x2="12" y2="19"></line>
                <line x1="5" y1="12" x2="19" y2="12"></line>
              </svg>
              添加
            </button>
          </div>
        </div>

        <div v-if="imageHealthMessage" class="health-message" :class="{ ok: imageHealthOk, error: !imageHealthOk }">
          {{ imageHealthMessage }}
        </div>

        <!-- 服务商列表表格 -->
        <ProviderTable
          :providers="imageConfig.providers"
          :activeProvider="imageConfig.active_provider"
          @activate="activateImageProvider"
          @edit="openEditImageModal"
          @delete="deleteImageProvider"
          @test="testImageProviderInList"
        />
      </div>

      <div v-else class="card admin-notice">
        <h2 class="section-title">模型配置由管理员维护</h2>
        <p class="section-desc">文本生成配置和图片生成配置仅管理员可查看和修改。</p>
      </div>

      <PublishAccountSettings />
    </div>

    <!-- 文本服务商弹窗 -->
    <ProviderModal
      v-if="auth.isAdmin"
      :visible="showTextModal"
      :isEditing="!!editingTextProvider"
      :formData="textForm"
      :testing="testingText"
      :typeOptions="textTypeOptions"
      providerCategory="text"
      @close="closeTextModal"
      @save="saveTextProvider"
      @test="testTextConnection"
      @update:formData="updateTextForm"
    />

    <!-- 图片服务商弹窗 -->
    <ImageProviderModal
      v-if="auth.isAdmin"
      :visible="showImageModal"
      :isEditing="!!editingImageProvider"
      :formData="imageForm"
      :testing="testingImage"
      :typeOptions="imageTypeOptions"
      @close="closeImageModal"
      @save="saveImageProvider"
      @test="testImageConnection"
      @update:formData="updateImageForm"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import ProviderTable from '../components/settings/ProviderTable.vue'
import ProviderModal from '../components/settings/ProviderModal.vue'
import ImageProviderModal from '../components/settings/ImageProviderModal.vue'
import PublishAccountSettings from '../components/settings/PublishAccountSettings.vue'
import {
  useProviderForm,
  textTypeOptions,
  imageTypeOptions
} from '../composables/useProviderForm'
import { checkImageHealth, runImageProbe } from '../api'
import { useAuthStore } from '../stores/auth'

/**
 * 系统设置页面
 *
 * 功能：
 * - 管理文本生成服务商配置
 * - 管理图片生成服务商配置
 * - 测试 API 连接
 */

const auth = useAuthStore()

// 使用 composable 管理表单状态和逻辑
const {
  // 状态
  loading,
  testingText,
  testingImage,

  // 配置数据
  textConfig,
  imageConfig,

  // 文本服务商弹窗
  showTextModal,
  editingTextProvider,
  textForm,

  // 图片服务商弹窗
  showImageModal,
  editingImageProvider,
  imageForm,

  // 方法
  loadConfig,

  // 文本服务商方法
  activateTextProvider,
  openAddTextModal,
  openEditTextModal,
  closeTextModal,
  saveTextProvider,
  deleteTextProvider,
  testTextConnection,
  testTextProviderInList,
  updateTextForm,

  // 图片服务商方法
  activateImageProvider,
  openAddImageModal,
  openEditImageModal,
  closeImageModal,
  saveImageProvider,
  deleteImageProvider,
  testImageConnection,
  testImageProviderInList,
  updateImageForm
} = useProviderForm()

const checkingImageHealth = ref(false)
const probingImage = ref(false)
const imageHealthMessage = ref('')
const imageHealthOk = ref(false)

async function handleImageHealthCheck() {
  checkingImageHealth.value = true
  imageHealthMessage.value = ''
  try {
    const result = await checkImageHealth()
    imageHealthOk.value = result.success
    imageHealthMessage.value = result.success
      ? `图片服务可连接：${result.provider || ''} ${result.model || ''}。${result.message || ''}`
      : `图片服务不可用：${result.error || '未知错误'}`
  } finally {
    checkingImageHealth.value = false
  }
}

async function handleImageProbe() {
  const confirmed = confirm('真实生图测试会消耗 1 次图片服务调用额度，是否继续？')
  if (!confirmed) return

  probingImage.value = true
  imageHealthMessage.value = ''
  try {
    const result = await runImageProbe()
    imageHealthOk.value = result.success
    imageHealthMessage.value = result.success
      ? `真实生图成功，用时 ${result.elapsed_seconds || 0} 秒。`
      : `真实生图失败：${result.error || '未知错误'}${result.elapsed_seconds ? `（${result.elapsed_seconds} 秒）` : ''}`
  } finally {
    probingImage.value = false
  }
}

onMounted(() => {
  if (auth.isAdmin) {
    loadConfig()
  }
})
</script>

<style scoped>
.settings-container {
  max-width: 900px;
  margin: 0 auto;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

.section-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 4px;
  color: #1a1a1a;
}

.section-desc {
  font-size: 14px;
  color: #666;
  margin: 0;
}

/* 按钮样式 */
.btn-small {
  padding: 6px 12px;
  font-size: 13px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.health-message {
  margin: -6px 0 16px;
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.5;
}

.health-message.ok {
  border: 1px solid #b7eb8f;
  background: #f6ffed;
  color: #2f7a16;
}

.health-message.error {
  border: 1px solid #ffd6d6;
  background: #fff5f5;
  color: #a33;
}

.admin-notice {
  padding: 20px;
}

/* 加载状态 */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  color: #666;
}
</style>
