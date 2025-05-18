import electron from 'electron'
const { app, BrowserWindow, ipcMain, dialog } = electron
import path from 'path'
import { WebSocket } from 'ws'

let mainWindow: Electron.BrowserWindow | null = null

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 800,
    height: 600,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, 'preload.js'),
    },
  })

  mainWindow.loadURL('http://localhost:5173') // Vite dev server
}

app.whenReady().then(createWindow)

ipcMain.handle('select-shared-folder', async () => {
  const result = await dialog.showOpenDialog({
    properties: ['openDirectory'],
  })
  if (result.canceled || result.filePaths.length === 0) return null
  return result.filePaths[0]
})

ipcMain.on('send-download-request', (_event, fileName: string) => {
  const ws = new WebSocket('ws://localhost:8765')
  ws.on('open', () => {
    const msg = `receive_file:${fileName}`
    ws.send(msg)
    console.log('WebSocket mesajı gönderildi:', msg)
    ws.close()
  })
})