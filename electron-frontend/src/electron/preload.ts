const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  sendDownloadRequest: (fileName: string) => ipcRenderer.send('send-download-request', fileName),
  selectSavePath: (fileName: string) => ipcRenderer.invoke('select-save-path', fileName)
})