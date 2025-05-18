import { useState } from 'react'

interface ElectronAPI {
  sendDownloadRequest: (fileName: string) => void
  selectSavePath: (fileName: string) => Promise<string | null>
}

declare global {
  interface Window {
    electronAPI: ElectronAPI
  }
}

export default function App() {
  const [fileName, setFileName] = useState('')
  const [status, setStatus] = useState('')

  const handleSendRequest = async () => {
    if (!fileName.trim()) return alert('Dosya adı girin.')

    const savePath = await window.electronAPI.selectSavePath(fileName)
    if (!savePath) {
      setStatus('❌ Kullanıcı dosya kaydetme konumu seçmedi.')
      return
    }

    window.electronAPI.sendDownloadRequest(fileName)
    setStatus(`📨 İndirme isteği gönderildi: ${fileName}\n💾 Kaydedildiği yer: ${savePath}`)
  }

  return (
    <div style={{ padding: 40 }}>
      <h1>P2P Transfer</h1>
      <input
        type="text"
        placeholder="İndirilecek dosya (ör. asd.txt)"
        value={fileName}
        onChange={(e) => setFileName(e.target.value)}
        style={{ marginTop: 40 }}
      />
      <br />
      <button onClick={handleSendRequest} style={{ marginTop: 10 }}>
        İndirme İsteği Gönder
      </button>

      {status && <pre style={{ marginTop: 20, whiteSpace: 'pre-wrap' }}>{status}</pre>}
    </div>
  )
}