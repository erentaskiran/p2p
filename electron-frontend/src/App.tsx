import { useState } from 'react'
interface ElectronAPI {
  selectSharedFolder: () => Promise<string | null>;
  sendDownloadRequest: (fileName: string) => void;
}

declare global {
  interface Window {
    electronAPI: ElectronAPI;
  }
}

export {};
export default function App() {
  const [fileName, setFileName] = useState('')
  const [sharedFolder, setSharedFolder] = useState('')
  const [status, setStatus] = useState('')

  const handleSelectFolder = async () => {
    const folderPath = await window.electronAPI.selectSharedFolder()
    if (folderPath) {
      setSharedFolder(folderPath)
      setStatus(`📁 Seçilen klasör: ${folderPath}`)
    } else {
      setStatus('❌ Klasör seçilmedi.')
    }
  }

  const handleSendRequest = () => {
    if (!fileName.trim()) return alert('Dosya adı girin.')
    window.electronAPI.sendDownloadRequest(fileName)
    setStatus(`📨 İndirme isteği gönderildi: ${fileName}`)
  }

  return (
    <div style={{ padding: 40 }}>
      <h1>Electron P2P Transfer</h1>

      <button onClick={handleSelectFolder}>📁 Klasör Seç (İndirilebilir)</button>
      {sharedFolder && <p>✅ Klasör: {sharedFolder}</p>}

      <input
        type="text"
        placeholder="İndirilecek dosya (ör. asd.txt)"
        value={fileName}
        onChange={(e) => setFileName(e.target.value)}
        style={{ marginTop: 20 }}
      />
      <br />
      <button onClick={handleSendRequest} style={{ marginTop: 10 }}>
        İndirme İsteği Gönder
      </button>

      {status && <p style={{ marginTop: 20 }}>{status}</p>}
    </div>
  )
}