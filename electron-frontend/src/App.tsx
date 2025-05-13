import { useRef } from 'react'
import axios from 'axios'

export default function App() {
  const fileInput = useRef<HTMLInputElement>(null)

  const handleSend = async () => {
    const file = fileInput.current?.files?.[0]
    if (!file) return alert('Lütfen bir dosya seçin.')

    const payload = {
      sender_id: 'user123',
      receiver_id: 'user456',
      file_name: file.name,
      file_size: file.size,
    }

    try {
      await axios.post('http://localhost:8000/api/transfer', payload)
      alert('Bilgiler başarıyla gönderildi.')
    } catch (err) {
      console.error(err)
      alert('Gönderim hatası.')
    }
  }

  return (
    <div style={{ padding: 40 }}>
      <h1>P2P Transfer Başlat</h1>

      <input type="file" ref={fileInput} />
      <button onClick={handleSend}>Gönder</button>
    </div>
  )
}