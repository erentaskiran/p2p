const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  selectFolder: () => ipcRenderer.invoke('select-folder'),
  sendDownloadRequest: (fileName: string, savePath: string) => ipcRenderer.send('send-download-request', { fileName, savePath }),
})