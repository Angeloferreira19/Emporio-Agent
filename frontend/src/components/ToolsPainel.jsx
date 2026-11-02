const topics = [
  { icon: '♫', label: 'Instrumentos e produtos', tone: 'mint' },
  { icon: '▤', label: 'Pedidos e entregas', tone: 'peach' },
  { icon: '↻', label: 'Trocas e políticas', tone: 'lavender' },
  { icon: '◷', label: 'Horários e informações', tone: 'yellow' },
]

export default function ToolsPainel({ onSuggestion }) {
  return (
    <aside className="info-panel" aria-label="Informações do atendimento">
      <div className="info-card store-card">
        <div className="store-card-art" aria-hidden="true">
          <span className="art-note note-one">♪</span>
          <span className="art-note note-two">♫</span>
          <span className="art-circle" />
          <span className="art-lines" />
        </div>
        <div className="store-card-content">
          <span className="eyebrow">EMPÓRIO DA MÚSICA</span>
          <h2>Música boa<br />começa aqui.</h2>
          <p>Conte com a gente para escolher o som certo para você.</p>
          <button onClick={() => onSuggestion('Quero ajuda para escolher um instrumento.')}>
            Vamos conversar <span aria-hidden="true">↗</span>
          </button>
        </div>
      </div>

      <div className="topics-section">
        <div className="section-title-row">
          <h2>Posso ajudar com</h2>
          <span className="topic-count">04</span>
        </div>
        <div className="topic-list">
          {topics.map((topic) => (
            <div className="topic-item" key={topic.label}>
              <span className={`topic-icon ${topic.tone}`} aria-hidden="true">{topic.icon}</span>
              <span>{topic.label}</span>
              <span className="topic-arrow" aria-hidden="true">↗</span>
            </div>
          ))}
        </div>
      </div>

      <div className="help-note">
        <span className="help-note-icon" aria-hidden="true">i</span>
        <p>Não encontrou o que procura? Escreva sua dúvida ali embaixo.</p>
      </div>
    </aside>
  )
}
