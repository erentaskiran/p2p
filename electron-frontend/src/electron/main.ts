import electron from 'electron'
const { app, BrowserWindow, ipcMain, dialog } = electron
import path from 'path'
import fs from 'fs'
import { WebSocket } from 'ws'

let mainWindow: Electron.BrowserWindow | null = null
let savePathFromUser: string | null = null

const sharedFolder = path.join(__dirname, '../../python-backend/publicFiles')

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

  mainWindow.loadURL('http://localhost:5173')
}

app.whenReady().then(() => {
  createWindow()

  fs.watch(sharedFolder, (event, filename) => {
    if (event === 'rename' && filename && savePathFromUser) {
      const sourceFile = path.join(sharedFolder, filename)
      const targetFile = savePathFromUser

      if (fs.existsSync(sourceFile)) {
        fs.copyFile(sourceFile, targetFile, (err) => {
          if (err) {
            console.error('❌ Dosya kopyalanamadı:', err)
          } else {
            console.log(`✅ ${filename} -> kullanıcı konumuna kopyalandı.`)
            savePathFromUser = null
          }
        })
      }
    }
  })
})

ipcMain.handle('select-save-path', async (_event, fileName: string) => {
  const result = await dialog.showSaveDialog({
    defaultPath: fileName,
    title: 'Dosyayı Kaydet',
  })

  if (result.canceled || !result.filePath) return null
  savePathFromUser = result.filePath
  return result.filePath
})

ipcMain.on('send-download-request', (_event, fileName: string) => {
  const sourcePath = path.join(sharedFolder, fileName)

  if (fs.existsSync(sourcePath)) {
    if (savePathFromUser) {
      fs.copyFile(sourcePath, savePathFromUser, (err) => {
        if (err) {
          console.error('❌ Mevcut dosya kopyalanamadı:', err)
        } else {
          console.log(`✅ Mevcut dosya ${fileName} direkt kopyalandı.`)
          savePathFromUser = null
        }
      })
    }
  } else {
    const ws = new WebSocket('ws://localhost:8765')
    ws.on('open', () => {
      const msg = `receive_file:${fileName}`
      ws.send(msg)
      console.log('WebSocket mesajı gönderildi:', msg)
      ws.close()
    })
  }
})