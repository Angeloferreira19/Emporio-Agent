export default function MessageBubble({ message }) {
  const isUser = message.role === 'user'

  return (
    <div className={`message-row ${isUser ? 'user-row' : 'assistant-row'}`}>
      {!isUser && <div className="message-avatar" aria-hidden="true">♪</div>}
      <div className="message-content">
        <span className="message-author">{isUser ? 'Você' : 'Empório da Música'}</span>
        <div className={`message-bubble ${isUser ? 'user-bubble' : 'assistant-bubble'}`}>
          <p>{message.content}</p>
          {message.tools?.length > 0 && (
            <span className="tool-badge">
              <svg viewBox="0 0 16 16" fill="none" aria-hidden="true">
                <path d="M8 2.5v11M2.5 8h11M4.1 4.1l7.8 7.8m0-7.8-7.8 7.8" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
              </svg>
              Informação da loja consultada
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
