import { useEffect, useLayoutEffect, useState } from 'react'
import { sendMessage } from './api.js'
import ChatInput from './components/ChatInput.jsx'
import ChatWindow from './components/ChatWindow.jsx'
import ToolsPainel from './components/ToolsPainel.jsx'

const CONVERSATIONS_STORAGE_KEY = 'emporio-conversations'
const ACTIVE_CONVERSATION_STORAGE_KEY = 'emporio-active-conversation'
const LEGACY_SESSION_ID_KEY = 'emporio-session-id'
const THEME_STORAGE_KEY = 'emporio-theme'

function getInitialTheme() {
  let savedTheme
  try {
    savedTheme = window.localStorage.getItem(THEME_STORAGE_KEY)
  } catch (storageError) {
    console.error('Não foi possível ler a preferência de tema.', storageError)
  }
  if (savedTheme === 'light' || savedTheme === 'dark') return savedTheme

  return window.matchMedia('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light'
}

function createConversation() {
  return {
    id: window.crypto.randomUUID(),
    title: 'Nova conversa',
    messages: [],
    updatedAt: Date.now(),
  }
}

function isValidMessage(message) {
  return (
    message
    && ['user', 'assistant'].includes(message.role)
    && typeof message.content === 'string'
    && (message.tools === undefined || Array.isArray(message.tools))
  )
}

function parseMessages(serializedMessages) {
  try {
    const messages = JSON.parse(serializedMessages)
    return Array.isArray(messages) && messages.every(isValidMessage)
      ? messages
      : null
  } catch (error) {
    console.warn('Não foi possível ler o histórico salvo.', error)
    return null
  }
}

function getConversationTitle(messages) {
  const firstUserMessage = messages.find((message) => message.role === 'user')
  if (!firstUserMessage) return 'Nova conversa'

  const title = firstUserMessage.content.trim()
  return title.length > 38 ? `${title.slice(0, 38).trimEnd()}…` : title
}

function isValidConversation(conversation) {
  return (
    conversation
    && typeof conversation.id === 'string'
    && typeof conversation.title === 'string'
    && Number.isFinite(conversation.updatedAt)
    && Array.isArray(conversation.messages)
    && conversation.messages.every(isValidMessage)
  )
}

function loadLegacyConversation() {
  const sessionId = window.sessionStorage.getItem(LEGACY_SESSION_ID_KEY)
  if (!sessionId) return null

  const storageKey = `emporio-messages-${sessionId}`
  const storedMessages = window.sessionStorage.getItem(storageKey)
  const messages = storedMessages ? parseMessages(storedMessages) : []

  if (!messages) {
    console.warn('O histórico antigo está inválido e não será restaurado.')
    window.sessionStorage.removeItem(storageKey)
    return null
  }

  return {
    id: sessionId,
    title: getConversationTitle(messages),
    messages,
    updatedAt: Date.now(),
  }
}

function loadConversationState() {
  const savedActiveId = window.localStorage.getItem(
    ACTIVE_CONVERSATION_STORAGE_KEY,
  )
  const serializedConversations = window.localStorage.getItem(
    CONVERSATIONS_STORAGE_KEY,
  )

  if (serializedConversations) {
    let conversations
    try {
      conversations = JSON.parse(serializedConversations)
    } catch (error) {
      console.warn('Não foi possível ler a lista de conversas salva.', error)
    }

    if (Array.isArray(conversations) && conversations.every(isValidConversation)) {
      const savedConversations = conversations.filter(
        (conversation) => conversation.messages.length > 0,
      )
      const activeConversation = savedConversations.find(
        (conversation) => conversation.id === savedActiveId,
      )
      if (activeConversation) {
        return {
          conversations: savedConversations,
          activeConversationId: activeConversation.id,
        }
      }

      const activeDraft = savedActiveId
        ? {
            id: savedActiveId,
            title: 'Nova conversa',
            messages: [],
            updatedAt: Date.now(),
          }
        : null
      const legacyConversation = loadLegacyConversation()
      const currentConversation =
        activeDraft
        ?? legacyConversation
        ?? savedConversations[0]
        ?? createConversation()
      return {
        conversations: [
          currentConversation,
          ...savedConversations.filter(
            (conversation) => conversation.id !== currentConversation.id,
          ),
        ],
        activeConversationId: currentConversation.id,
      }
    }

    console.warn('A lista de conversas salva está inválida e será recriada.')
    window.localStorage.removeItem(CONVERSATIONS_STORAGE_KEY)
  }

  const legacyConversation = loadLegacyConversation()
  const firstConversation = legacyConversation ?? createConversation()
  return {
    conversations: [firstConversation],
    activeConversationId: firstConversation.id,
  }
}

export default function App() {
  const [conversationState, setConversationState] = useState(
    loadConversationState,
  )
  const [theme, setTheme] = useState(getInitialTheme)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const { conversations, activeConversationId } = conversationState
  const activeConversation =
    conversations.find((conversation) => conversation.id === activeConversationId)
    ?? conversations[0]
  const messages = activeConversation.messages

  useLayoutEffect(() => {
    document.documentElement.style.colorScheme = theme
    document.querySelector('meta[name="theme-color"]')?.setAttribute(
      'content',
      theme === 'dark' ? '#111c27' : '#f7f6f2',
    )
  }, [theme])

  useEffect(() => {
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, theme)
    } catch (storageError) {
      console.error('Não foi possível salvar a preferência de tema.', storageError)
    }
  }, [theme])

  useEffect(() => {
    try {
      const savedConversations = conversations.filter(
        (conversation) => conversation.messages.length > 0,
      )
      if (savedConversations.length > 0) {
        window.localStorage.setItem(
          CONVERSATIONS_STORAGE_KEY,
          JSON.stringify(savedConversations),
        )
      } else {
        window.localStorage.removeItem(CONVERSATIONS_STORAGE_KEY)
      }
      window.localStorage.setItem(
        ACTIVE_CONVERSATION_STORAGE_KEY,
        activeConversationId,
      )
    } catch (storageError) {
      console.error('Não foi possível salvar o histórico de conversas.', storageError)
    }
  }, [activeConversationId, conversations])

  async function handleSend(message) {
    if (isLoading || !message.trim()) return

    setError('')
    setIsLoading(true)
    const conversationId = activeConversation.id
    const userMessage = { role: 'user', content: message.trim() }
    setConversationState((current) => ({
      ...current,
      conversations: current.conversations.map((conversation) => {
        if (conversation.id !== conversationId) return conversation

        const nextMessages = [...conversation.messages, userMessage]
        return {
          ...conversation,
          title: getConversationTitle(nextMessages),
          messages: nextMessages,
          updatedAt: Date.now(),
        }
      }),
    }))

    try {
      const response = await sendMessage(conversationId, message.trim())
      setConversationState((current) => ({
        ...current,
        conversations: current.conversations.map((conversation) =>
          conversation.id === conversationId
            ? {
                ...conversation,
                messages: [
                  ...conversation.messages,
                  {
                    role: 'assistant',
                    content: response.reply,
                    tools: response.tools_used ?? [],
                  },
                ],
                updatedAt: Date.now(),
              }
            : conversation,
        ),
      }))
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setIsLoading(false)
    }
  }

  function startNewConversation() {
    if (isLoading) return

    if (!messages.length) {
      setError('')
      return
    }

    const conversation = createConversation()
    setConversationState((current) => ({
      conversations: [conversation, ...current.conversations],
      activeConversationId: conversation.id,
    }))
    setError('')
  }

  function selectConversation(conversationId) {
    if (isLoading || conversationId === activeConversationId) return
    setConversationState((current) => ({
      ...current,
      activeConversationId: conversationId,
    }))
    setError('')
  }

  function toggleTheme() {
    setTheme((currentTheme) => currentTheme === 'dark' ? 'light' : 'dark')
  }

  function deleteConversation(conversationId) {
    if (isLoading) return

    setConversationState((current) => {
      const remainingConversations = current.conversations.filter(
        (conversation) => conversation.id !== conversationId,
      )
      if (remainingConversations.length === 0) {
        const newConversation = createConversation()
        return {
          conversations: [newConversation],
          activeConversationId: newConversation.id,
        }
      }

      const mostRecentConversation = remainingConversations.reduce(
        (mostRecent, conversation) =>
          conversation.updatedAt > mostRecent.updatedAt
            ? conversation
            : mostRecent,
      )
      const nextActiveId = current.activeConversationId === conversationId
        ? mostRecentConversation.id
        : current.activeConversationId
      return {
        conversations: remainingConversations,
        activeConversationId: nextActiveId,
      }
    })
    setError('')
  }

  const sortedConversations = conversations.filter(
    (conversation) => conversation.messages.length > 0,
  ).sort(
    (first, second) => second.updatedAt - first.updatedAt,
  )

  return (
    <div className="app-shell" data-theme={theme}>
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

        <section className="sidebar-history" aria-label="Histórico de conversas">
          <div className="history-heading">
            <span className="sidebar-label">HISTÓRICO</span>
            <span className="history-count">{sortedConversations.length}</span>
          </div>
          <div className="history-list">
            {sortedConversations.length === 0 ? (
              <p className="history-empty">Suas conversas aparecerão aqui.</p>
            ) : sortedConversations.map((conversation) => (
              <div
                className={`history-item ${
                  conversation.id === activeConversationId ? 'history-item-active' : ''
                }`}
                key={conversation.id}
              >
                <button
                  className="history-select"
                  type="button"
                  onClick={() => selectConversation(conversation.id)}
                  disabled={isLoading}
                  aria-pressed={conversation.id === activeConversationId}
                  title={conversation.title}
                >
                  <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
                    <path d="M3 5.8A2.8 2.8 0 0 1 5.8 3h8.4A2.8 2.8 0 0 1 17 5.8v5.4a2.8 2.8 0 0 1-2.8 2.8H9l-4.5 3v-3.3A2.8 2.8 0 0 1 3 11.2V5.8Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
                  </svg>
                  <span>{conversation.title}</span>
                </button>
                <button
                  className="history-delete"
                  type="button"
                  onClick={() => deleteConversation(conversation.id)}
                  disabled={isLoading}
                  aria-label={`Excluir conversa: ${conversation.title}`}
                  title="Excluir conversa"
                >
                  <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
                    <path d="M4.5 6h11M8 6V4.5h4V6m2.5 0-.7 9.2H6.2L5.5 6m3 2.5v4m3-4v4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        </section>

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
            <button
              className="theme-toggle"
              type="button"
              onClick={toggleTheme}
              aria-label={theme === 'dark' ? 'Ativar tema claro' : 'Ativar modo escuro'}
              title={theme === 'dark' ? 'Ativar tema claro' : 'Ativar modo escuro'}
            >
              {theme === 'dark' ? (
                <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
                  <circle cx="10" cy="10" r="3.2" stroke="currentColor" strokeWidth="1.5" />
                  <path d="M10 2.5v1.7m0 11.6v1.7m7.5-7.5h-1.7M4.2 10H2.5m12.8-5.3-1.2 1.2m-8.2 8.2-1.2 1.2m10.6 0-1.2-1.2m-8.2-8.2L4.7 4.7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
              ) : (
                <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
                  <path d="M16.2 12.5A6.8 6.8 0 0 1 7.5 3.8 6.9 6.9 0 1 0 16.2 12.5Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
                  <path d="m13.5 3 .4 1.1L15 4.5l-1.1.4-.4 1.1-.4-1.1-1.1-.4 1.1-.4.4-1.1Z" fill="currentColor" />
                </svg>
              )}
            </button>
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
