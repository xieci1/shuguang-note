import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { createHistory, updateHistory } from '../api'
import { useGeneratorStore } from '../stores/generator'

type SaveStatus = 'idle' | 'saving' | 'saved' | 'error'

interface DraftAutosaveOptions {
  debounceMs?: number
  immediate?: boolean
  watchOutline?: boolean
}

export function useDraftAutosave(options: DraftAutosaveOptions = {}) {
  const store = useGeneratorStore()
  const debounceMs = options.debounceMs ?? 800
  const shouldWatchOutline = options.watchOutline ?? true

  const isSaving = ref(false)
  const saveStatus = ref<SaveStatus>('idle')
  const saveError = ref('')
  let saveTimer: number | null = null
  let saveVersion = 0

  const canSaveDraft = computed(() => store.outline.pages.length > 0)

  const saveStatusText = computed(() => {
    if (saveStatus.value === 'saving') return '保存中...'
    if (saveStatus.value === 'error') return '保存失败'
    if (saveStatus.value === 'saved') return '已保存'
    return store.recordId ? '已保存' : '未保存'
  })

  async function ensureDraftSaved(): Promise<boolean> {
    if (!canSaveDraft.value) return false

    const currentVersion = ++saveVersion
    isSaving.value = true
    saveStatus.value = 'saving'
    saveError.value = ''

    try {
      if (!store.recordId) {
        const result = await createHistory(
          store.topic || '未命名主题',
          {
            raw: store.outline.raw,
            pages: store.outline.pages
          },
          store.taskId || undefined
        )

        if (!result.success || !result.record_id) {
          throw new Error(result.error || '创建草稿失败')
        }

        store.setRecordId(result.record_id)
      } else {
        const result = await updateHistory(store.recordId, {
          outline: {
            raw: store.outline.raw,
            pages: store.outline.pages
          }
        })

        if (!result.success) {
          throw new Error(result.error || '保存草稿失败')
        }
      }

      store.markSaved()
      if (currentVersion === saveVersion) {
        saveStatus.value = 'saved'
      }
      return true
    } catch (error: any) {
      if (currentVersion === saveVersion) {
        saveStatus.value = 'error'
        saveError.value = error?.message || '保存草稿失败'
      }
      return false
    } finally {
      if (currentVersion === saveVersion) {
        isSaving.value = false
      }
    }
  }

  function scheduleSave() {
    if (!canSaveDraft.value) return
    if (saveTimer !== null) {
      clearTimeout(saveTimer)
    }
    saveTimer = window.setTimeout(() => {
      saveTimer = null
      ensureDraftSaved()
    }, debounceMs)
  }

  async function flushPendingSave(): Promise<boolean> {
    if (saveTimer !== null) {
      clearTimeout(saveTimer)
      saveTimer = null
    }
    return ensureDraftSaved()
  }

  if (shouldWatchOutline) {
    watch(
      () => ({
        topic: store.topic,
        raw: store.outline.raw,
        pages: store.outline.pages
      }),
      () => {
        saveStatus.value = 'idle'
        scheduleSave()
      },
      { deep: true }
    )
  }

  onMounted(() => {
    if (options.immediate && canSaveDraft.value) {
      scheduleSave()
    }
  })

  onUnmounted(() => {
    if (saveTimer !== null) {
      clearTimeout(saveTimer)
      saveTimer = null
    }
  })

  return {
    canSaveDraft,
    isSaving,
    saveStatus,
    saveStatusText,
    saveError,
    ensureDraftSaved,
    scheduleSave,
    flushPendingSave
  }
}
