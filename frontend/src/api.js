export async function sendMessage(sessionId, message) {
    let response
    try {
        response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId, message }),
        })
    } catch (error) {
        if (error instanceof TypeError) {
            throw new Error(
                'Não foi possível conectar ao atendimento. Confira se o backend está em execução.',
                { cause: error },
            )
        }
        throw error
    }

    const responseText = await response.text()
    let data
    try {
        data = JSON.parse(responseText)
    } catch {
        if (!response.ok) {
            throw new Error(`Não foi possível conectar ao atendimento (HTTP ${response.status}).`)
        }
        throw new Error('O atendimento retornou uma resposta inválida. Tente novamente.')
    }

    if (!response.ok) {
        throw new Error(data.detail || `Não foi possível enviar a mensagem (HTTP ${response.status}).`)
    }

    if (typeof data.reply !== 'string') {
        throw new Error('O atendimento retornou uma resposta inválida. Tente novamente.')
    }

    return data
}