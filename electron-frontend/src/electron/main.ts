import electron from 'electron'
const { app, BrowserWindow, ipcMain, dialog } = electron
import path from 'path'
import fs from 'fs'
import { WebSocket } from 'ws'

let mainWindow: Electron.BrowserWindow | null = null

const sharedFolder = path.join(__dirname, '../../python-backend/publicFiles')

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 800,
    height: 800,
    title: 'P2P Transfer',
    icon: path.join(__dirname, 'assets/icon.png'),
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
})

ipcMain.handle('select-folder', async () => {
  const result = await dialog.showOpenDialog({
    properties: ['openDirectory'],
    title: 'Klasör Seç',
  })

  if (result.canceled || result.filePaths.length === 0) return null
  return result.filePaths[0]
})

ipcMain.on('send-download-request', async (_event, { fileName, savePath }) => {
  const sourcePath = path.join(sharedFolder, fileName)

  const copyFile = () => {
    fs.copyFile(sourcePath, savePath, (err) => {
      if (err) {
        console.error(`❌ ${fileName} kopyalanamadı:`, err)
      } else {
        console.log(`✅ ${fileName} klasöre kopyalandı: ${savePath}`)
      }
    })
  }
  if (fs.existsSync(sourcePath)) {
    copyFile()
    return
  }

  // WebSocket üzerinden dosyayı isteme
  const ws = new WebSocket('ws://localhost:8765')

  ws.on('open', () => {
    const msg = `receive_file:${fileName}`
    ws.send(msg)
    console.log('📡 WebSocket mesajı gönderildi:', msg)
    ws.close()
  })

  ws.on('error', (err) => {
    console.error(`❌ WebSocket hatası (${fileName}):`, err)
  })

  const maxRetries = 20
  const delay = 500
  let attempts = 0

  const waitForFile = setInterval(() => {
    if (fs.existsSync(sourcePath)) {
      clearInterval(waitForFile)
      console.log(`📁 ${fileName} artık mevcut, kopyalanıyor...`)
      copyFile()
    } else {
      attempts++
      if (attempts >= maxRetries) {
        clearInterval(waitForFile)
        console.error(`❌ ${fileName} belirlenen sürede oluşturulamadı.`)
      }
    }
  }, delay)
})
