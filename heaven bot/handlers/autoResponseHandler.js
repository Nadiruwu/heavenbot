const fs = require('fs');
let AUTO_RESPONSES = new Map();
const RESPONSES_FILE = 'responses.json';

if (fs.existsSync(RESPONSES_FILE)) {
    try {
        const data = fs.readFileSync(RESPONSES_FILE, 'utf8');
        if (data) AUTO_RESPONSES = new Map(Object.entries(JSON.parse(data)));
    } catch (error) {
        console.error('Error al cargar respuestas:', error);
    }
}

function saveResponses() {
    fs.writeFileSync(RESPONSES_FILE, JSON.stringify(Object.fromEntries(AUTO_RESPONSES), null, 2));
}

async function handleAutoResponse(message) {
    if (AUTO_RESPONSES.has(message.content.toLowerCase())) {
        const { response, emoji } = AUTO_RESPONSES.get(message.content.toLowerCase());
        await message.reply(response);
        if (emoji) await message.react(emoji);
        return;
    }
}

module.exports = {
    handleAutoResponse
};
