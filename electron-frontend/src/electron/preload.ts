const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  selectSharedFolder: () => ipcRenderer.invoke('select-shared-folder'),
  sendDownloadRequest: (fileName: string) => ipcRenderer.send('send-download-request', fileName),
})