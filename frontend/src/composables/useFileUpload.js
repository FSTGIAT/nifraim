import { ref, computed } from 'vue'

const EXCEL_ACCEPT = ['.xlsx', '.xls']
const EXCEL_MIME_TYPES = {
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
  'application/vnd.ms-excel': ['.xls'],
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function getExtension(filename) {
  return filename.split('.').pop().toLowerCase()
}

function isValidExcel(file) {
  const ext = getExtension(file.name)
  return ext === 'xlsx' || ext === 'xls'
}

const hasFilePickerAPI = typeof window !== 'undefined' && typeof window.showOpenFilePicker === 'function'

export function useFileUpload({ multiple = false } = {}) {
  const files = ref([])
  const isDragging = ref(false)
  const needPassword = ref(false)
  const password = ref('')
  const error = ref('')
  const fileInputRef = ref(null)

  const hasFiles = computed(() => files.value.length > 0)

  const fileDetails = computed(() =>
    files.value.map(f => ({
      file: f,
      name: f.name,
      size: formatFileSize(f.size),
      extension: getExtension(f.name),
    }))
  )

  function addFiles(fileList) {
    const newFiles = Array.from(fileList).filter(isValidExcel)
    if (!multiple) {
      if (newFiles.length > 0) {
        files.value = [newFiles[0]]
      }
      return
    }
    for (const f of newFiles) {
      if (!files.value.some(sf => sf.name === f.name)) {
        files.value.push(f)
      }
    }
  }

  function removeFile(index) {
    files.value.splice(index, 1)
  }

  function clearFiles() {
    files.value = []
    password.value = ''
    needPassword.value = false
    error.value = ''
  }

  async function openFilePicker() {
    if (hasFilePickerAPI) {
      try {
        const handles = await window.showOpenFilePicker({
          multiple,
          types: [{
            description: 'Excel',
            accept: EXCEL_MIME_TYPES,
          }],
        })
        const picked = await Promise.all(handles.map(h => h.getFile()))
        addFiles(picked)
        return
      } catch (e) {
        if (e.name === 'AbortError') return
        // Fall through to input click on other errors
      }
    }
    fileInputRef.value?.click()
  }

  function handleDrop(e) {
    isDragging.value = false
    const dropped = e.dataTransfer?.files
    if (dropped && dropped.length > 0) {
      addFiles(dropped)
    }
  }

  function handleDragOver(e) {
    e.preventDefault()
    isDragging.value = true
  }

  function handleDragLeave() {
    isDragging.value = false
  }

  function handleFileInputChange(e) {
    const selected = e.target.files
    if (selected && selected.length > 0) {
      addFiles(selected)
    }
    e.target.value = ''
  }

  return {
    files,
    isDragging,
    needPassword,
    password,
    error,
    hasFiles,
    fileDetails,
    fileInputRef,
    addFiles,
    removeFile,
    clearFiles,
    openFilePicker,
    handleDrop,
    handleDragOver,
    handleDragLeave,
    handleFileInputChange,
  }
}
