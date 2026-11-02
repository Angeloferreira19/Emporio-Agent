const USE_MOCK = true

export async function sendMessage(sessionId, message) {
    if (USE_MOCK) {
        await new Promise(r => setTimeout(r, 800))
        return {
            reply: `Mock reply to "${message}"`,
            tools_used: [{name: 'buscar_produtos', args: { termo: 'violão' }}]
        }
    }
    const res = await fetch(`/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message }),
    })
    if (!res.ok) throw new Error(`Erro ao enviar mensagem: ${res.statusText}`)
    return res.json()
}