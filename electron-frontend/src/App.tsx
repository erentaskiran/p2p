import { useState, useRef } from 'react'
import type { ChangeEvent, DragEvent, KeyboardEvent } from 'react'
import { ArrowUpIcon, SendIcon } from './components/icons'
import path from 'path-browserify'
import './App.css'

interface ElectronAPI {
  sendDownloadRequest: (fileName: string, savePath: string) => void
  selectFolder: () => Promise<string | null>
}

declare global {
  interface Window {
    electronAPI: ElectronAPI
  }
}

export default function App() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [fileName, setFileName] = useState<string>('')
  const [fileNames, setFileNames] = useState<string[]>([])
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [status, setStatus] = useState<string>('')
  const fileInputRef = useRef<HTMLInputElement>(null)
  const handleFileChange = (event: ChangeEvent<HTMLInputElement>): void => {
    const files = event.target.files
    if (files && files.length > 0) {
      const file = files[0]
      setSelectedFile(file)
      setFileName(file.name)
      setSearchQuery('')
    }
  }

  const handleDrop = async (event: DragEvent<HTMLDivElement>): Promise<void> => {
  event.preventDefault()
  event.stopPropagation()

  const files = event.dataTransfer.files
  if (!files || files.length === 0) return

  const file = files[0]
  if (file.type !== 'text/plain') {
    setStatus('❌ Lütfen sadece .txt uzantılı dosya seçiniz.')
    return
  }

  try {
    const text = await file.text()
    const lines = text
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean)

    if (lines.length === 0) {
      setStatus('❌ .txt dosyası boş veya geçerli dosya ismi yok.')
      return
    }

    setFileNames(lines)
    setSelectedFile(file)
    setFileName('')
    setSearchQuery('')
    setStatus(`✅ ${lines.length} dosya algılandı. İndirmek için butona tıklayın.`)
  } catch (err) {
    console.error('Drop hatası:', err)
    setStatus('❌ .txt dosyası okunamadı.')
  }
}

  const handleDragOver = (event: DragEvent<HTMLDivElement>): void => {
    event.preventDefault()
    event.stopPropagation()
  }

  const handleClick = (): void => {
    if (fileInputRef.current) {
      fileInputRef.current.click()
    }
  }

  const handleSearchChange = (event: ChangeEvent<HTMLInputElement>): void => {
    setSearchQuery(event.target.value)
    setSelectedFile(null)
    setFileName('')
    setFileNames([])
  }

  const handleSearch = async (): Promise<void> => {
    if (!searchQuery.trim()) {
      alert('Lütfen bir dosya adı girin.')
      return
    }

    const folderPath = await window.electronAPI.selectFolder()
    if (!folderPath) {
      setStatus('❌ Kullanıcı klasör seçmedi.')
      return
    }

    const fullSavePath = path.join(folderPath, searchQuery.trim())
    window.electronAPI.sendDownloadRequest(searchQuery.trim(), fullSavePath)
    setStatus(`📨 İndirme isteği gönderildi: ${searchQuery}\n💾 Kaydedildiği yer: ${fullSavePath}`)
    setSelectedFile(null)
    setFileName('')
    setSearchQuery('')
  }

  const handleSearchKeyDown = (event: KeyboardEvent<HTMLInputElement>): void => {
    if (event.key === 'Enter') {
      handleSearch()
    }
  }

  const handleSendRequest = async (): Promise<void> => {
  const namesToSend = fileNames.length > 0 ? fileNames : [fileName.trim()]
  if (namesToSend.length === 0 || !namesToSend[0]) {
    alert('Dosya adı girin.')
    return
  }

  try {
    const folderPath = await window.electronAPI.selectFolder()
    if (!folderPath) {
      setStatus('❌ Kullanıcı klasör seçmedi.')
      return
    }

    namesToSend.forEach((name) => {
      const savePath = `${folderPath}/${name}`
      window.electronAPI.sendDownloadRequest(name, savePath)
    })

    setStatus(
      `📨 ${namesToSend.length} dosya için istek gönderildi.\n📁 Kaydedildiği Klasör: ${folderPath}`
    )

    setSelectedFile(null)
    setFileName('')
    setFileNames([])
    setSearchQuery('')
  } catch (error) {
    console.error('Toplu gönderim hatası:', error)
    setStatus('❌ Toplu gönderim sırasında bir hata oluştu.')
  }
}

  return (
    <div className="app-container">
      <div className="transfer-container">
        <h1 className="title">P2P Transfer</h1>
        <p className="subtitle">Peer-to-Peer Dosya Aktarımı</p>

        <div className="drop-area-container">
          <div className="search-container">
            <input
              type="text"
              className="search-input"
              placeholder="Bir dosya arayın..."
              value={searchQuery}
              onChange={handleSearchChange}
              onKeyDown={handleSearchKeyDown}
            />
          </div>

          <div
            className="drop-area"
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onClick={handleClick}
          >
            <ArrowUpIcon />
            <p className="drop-text">Bir .txt dosyasını sürekle & bırak veya seç</p>
            <p className="drop-instruction">bu dosya indirme listesini içermeli</p>
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              style={{ display: 'none' }}
              accept=".txt"
            />
            {selectedFile && (
              <p className="selected-file">
                Seçilen: {selectedFile.name} ({fileNames.length} dosya girdisi)
              </p>
            )}
          </div>
        </div>

        <button
          className="send-button"
          onClick={searchQuery.trim() ? handleSearch : handleSendRequest}
          disabled={
            !searchQuery.trim() &&
            !selectedFile &&
            !fileName.trim() &&
            fileNames.length === 0
          }
        >
          İndirme İsteği Gönder
          <SendIcon />
        </button>

        {status && (
          <div className="status-container">
            <p className="status-text">{status}</p>
          </div>
        )}

        <p className="footer-text">
          Dosyalar doğrudan peerlar arasında aktarılır. Sunucuda depolanmaz.
        </p>
      </div>
    </div>
  )
}