import { useLayoutEffect, useRef } from 'react'
import MessageBubble from './MessageBubble.jsx'

const suggestions = [
  {
    icon: '♫',
    title: 'Quero encontrar um instrumento',
    prompt: 'Quais opções de violões vocês têm disponíveis?',
  },
  {
    icon: '⌕',
    title: 'Consultar um pedido',
    prompt: 'Como posso consultar o status do meu pedido?',
  },
  {
    icon: '↻',
    title: 'Tirar dúvida sobre troca',
    prompt: 'Quais são as regras para trocar um produto?',
  },
  {
    icon: '◷',
    title: 'Ver horário da loja',
    prompt: 'Qual é o horário de funcionamento da loja?',
  },
]

export default function ChatWindow({ messages, isLoading, onSuggestion }) {
  const welcomeRef = useRef(null)
  const messageListRef = useRef(null)

  useLayoutEffect(() => {
    if (!messages.length) {
      if (welcomeRef.current) welcomeRef.current.scrollTop = 0
      return
    }

    if (!messageListRef.current) return

    messageListRef.current.scrollTo({
      top: messageListRef.current.scrollHeight,
      behavior: 'instant',
    })
  }, [messages, isLoading])

  if (messages.length === 0) {
    return (
      <div className="welcome-screen" ref={welcomeRef}>
        <div className="welcome-kicker">
          <span className="sparkle" aria-hidden="true">✳</span>
          BEM-VINDO(A) AO EMPÓRIO
        </div>
        <h2>Oi! Vamos encontrar<br />o seu próximo <em>som?</em></h2>
        <p className="welcome-copy">
          Posso ajudar com instrumentos, pedidos, preços e dúvidas sobre a loja.
          O que você gostaria de saber?
        </p>
        <div className="suggestion-grid">
          {suggestions.map((suggestion) => (
            <button
              className="suggestion-card"
              key={suggestion.title}
              onClick={() => onSuggestion(suggestion.prompt)}
              disabled={isLoading}
            >
              <span className="suggestion-icon" aria-hidden="true">{suggestion.icon}</span>
              <span className="suggestion-title">{suggestion.title}</span>
              <span className="suggestion-arrow" aria-hidden="true">↗</span>
            </button>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="message-list" aria-live="polite" ref={messageListRef}>
      <div className="conversation-date"><span>CONVERSA DE HOJE</span></div>
      {messages.map((message, index) => (
        <MessageBubble key={`${message.role}-${index}`} message={message} />
      ))}
      {isLoading && (
        <div className="message-row assistant-row" aria-label="Assistente está pensando">
          <div className="message-avatar" aria-hidden="true">♪</div>
          <div className="typing-bubble"><span /><span /><span /></div>
        </div>
      )}
    </div>
  )
}