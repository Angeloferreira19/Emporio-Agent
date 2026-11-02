import { useState } from 'react'
import { sendMessage } from './api.js'
import ChatInput from './components/ChatInput.jsx'
import ChatWindow from './components/ChatWindow.jsx'
import ToolsPainel from './components/ToolsPainel.jsx'

function createSessionId() {
  const storedId = window.sessionStorage.getItem('emporio-session-id')
  if (storedId) return storedId

  const sessionId = window.crypto.randomUUID()
  window.sessionStorage.setItem('emporio-session-id', sessionId)
  return sessionId
}

export default function App() {
  const [sessionId] = useState(createSessionId)
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSend(message) {
    if (isLoading || !message.trim()) return

    setError('')
    setIsLoading(true)
    setMessages((current) => [...current, { role: 'user', content: message.trim() }])

    try {
      const response = await sendMessage(sessionId, message.trim())
      setMessages((current) => [
        ...current,
        {
          role: 'assistant',
          content: response.reply,
          tools: response.tools_used ?? [],
        },
      ])
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setIsLoading(false)
    }
  }

  function startNewConversation() {
    if (isLoading) return
    setMessages([])
    setError('')
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="/" aria-label="Empório da Música — início">
          <span className="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 32 32" fill="none">
              <path d="M19.5 5.5v16.1a4.5 4.5 0 1 1-3-4.25V9l11-2.5v12.6a4.5 4.5 0 1 1-3-4.25V4.5l-5 1Z" fill="currentColor" />
            </svg>
          </span>
          <span className="brand-copy">
            <strong>empório</strong>
            <span>da música</span>
          </span>
        </a>

        <button className="new-chat-button" onClick={startNewConversation} disabled={isLoading}>
          <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
            <path d="M10 4v12M4 10h12" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
          </svg>
          <span>Nova conversa</span>
        </button>

        <div className="sidebar-section">
          <span className="sidebar-label">SEU ATENDIMENTO</span>
          <button className="nav-item nav-item-active">
            <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
              <path d="M3 5.8A2.8 2.8 0 0 1 5.8 3h8.4A2.8 2.8 0 0 1 17 5.8v5.4a2.8 2.8 0 0 1-2.8 2.8H9l-4.5 3v-3.3A2.8 2.8 0 0 1 3 11.2V5.8Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
            </svg>
            <span>Assistente da loja</span>
            <span className="nav-dot" />
          </button>
        </div>

        <div className="sidebar-bottom">
          <div className="sidebar-note">
            <span className="note-icon" aria-hidden="true">♪</span>
            <p>Seu próximo som começa com uma boa conversa.</p>
          </div>
          <div className="sidebar-location">
            <span className="location-pin" aria-hidden="true">
              <svg viewBox="0 0 16 16" fill="none">
                <path d="M13 6.7c0 3.2-5 7.3-5 7.3S3 9.9 3 6.7a5 5 0 1 1 10 0Z" stroke="currentColor" strokeWidth="1.4" />
                <circle cx="8" cy="6.5" r="1.6" stroke="currentColor" strokeWidth="1.4" />
              </svg>
            </span>
            <span>Campo Grande, MS</span>
          </div>
        </div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div className="mobile-brand">
            <span className="brand-mark" aria-hidden="true">♪</span>
            <strong>Empório da Música</strong>
          </div>
          <div className="breadcrumb">
            <span>Atendimento</span>
            <span className="breadcrumb-separator">/</span>
            <strong>Assistente da loja</strong>
          </div>
          <div className="topbar-status">
            <span className="status-indicator" />
            <span>Atendimento digital</span>
          </div>
        </header>

        <div className="workspace">
          <section className="conversation-panel" aria-label="Conversa com o assistente">
            <div className="conversation-heading">
              <div className="assistant-avatar" aria-hidden="true">
                <svg viewBox="0 0 32 32" fill="none">
                  <path d="M19 5v15a4 4 0 1 1-2.5-3.7V8l10-2v12a4 4 0 1 1-2.5-3.7V4L19 5Z" fill="currentColor" />
                </svg>
              </div>
              <div>
                <h1>Assistente da loja</h1>
                <p>Empório da Música <span className="heading-divider">·</span> Campo Grande, MS</p>
              </div>
              <button
                className="icon-button mobile-new-chat"
                onClick={startNewConversation}
                aria-label="Começar nova conversa"
                disabled={isLoading}
              >
                <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
                  <path d="M10 4v12M4 10h12" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
                </svg>
              </button>
            </div>

            <div className="conversation-content">
              <ChatWindow
                messages={messages}
                isLoading={isLoading}
                onSuggestion={handleSend}
              />
              {error && (
                <div className="error-message" role="alert">
                  <span className="error-icon" aria-hidden="true">!</span>
                  <div>
                    <strong>Não consegui enviar sua mensagem.</strong>
                    <p>{error}</p>
                  </div>
                  <button onClick={() => setError('')} aria-label="Fechar aviso">×</button>
                </div>
              )}
            </div>

            <ChatInput onSend={handleSend} disabled={isLoading} />
          </section>

          <ToolsPainel onSuggestion={handleSend} />
        </div>
      </main>
    </div>
  )
}
