import { useRef, useState } from 'react'

export default function ChatInput({ onSend, disabled }) {
  const [value, setValue] = useState('')
  const textareaRef = useRef(null)

  function submitMessage(event) {
    event.preventDefault()
    const message = value.trim()
    if (!message || disabled) return
    onSend(message)
    setValue('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
  }

  function resizeTextarea(event) {
    event.currentTarget.style.height = 'auto'
    event.currentTarget.style.height = `${Math.min(event.currentTarget.scrollHeight, 144)}px`
  }

  function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      event.currentTarget.form?.requestSubmit()
    }
  }

  return (
    <div className="composer-wrap">
      <form className="composer" onSubmit={submitMessage}>
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onInput={resizeTextarea}
          onKeyDown={handleKeyDown}
          placeholder="Escreva sua mensagem..."
          aria-label="Escreva sua mensagem"
          rows={1}
          disabled={disabled}
        />
        <div className="composer-footer">
          <span className="composer-hint">Respostas baseadas nas informações da loja</span>
          <div className="composer-actions">
            <span className="keyboard-hint">Enter para enviar</span>
            <button
              className="send-button"
              type="submit"
              aria-label="Enviar mensagem"
              disabled={disabled || !value.trim()}
            >
              <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
                <path d="m4 10 12-6-4.5 12-2.2-4.8L4 10Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
                <path d="m9.3 11.2 3.3-3.3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
            </button>
          </div>
        </div>
      </form>
      <p className="disclaimer">O assistente pode cometer erros. Em caso de dúvida, confirme as informações com a loja.</p>
    </div>
  )
}
