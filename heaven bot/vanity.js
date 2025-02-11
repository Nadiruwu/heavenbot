const { Client, GatewayIntentBits } = require('discord.js');
require('dotenv').config();

const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildPresences,
        GatewayIntentBits.GuildMembers
    ],
});

const VANITY_ROLES = {
    'nvn': '1284285993494773800',
    '.gg/nvn': '1284285993494773800'
};

client.once('ready', () => {
    console.log(`✅ Bot listo como ${client.user.tag}`);
});

client.on('presenceUpdate', (oldPresence, newPresence) => {
    const member = newPresence.member;
    if (!member) return;

    console.log(`⚡ Cambio de presencia detectado en: ${member.user.tag}`);
    console.log('🔍 Actividades detectadas:', newPresence.activities);

    let assignedRoles = new Set();

    for (const [vanity, roleId] of Object.entries(VANITY_ROLES)) {
        if (newPresence.activities.some(activity => 
            (activity.type === 4 || activity.type === 0) && 
            activity.state?.includes(vanity))) 
        {
            console.log(`✅ Vanity URL detectada: ${vanity}`);
            assignedRoles.add(roleId);
        }
    }

    updateMemberRoles(member, assignedRoles);
});

async function updateMemberRoles(member, assignedRoles) {
    try {
        const currentRoles = new Set(member.roles.cache.keys());

        for (const roleId of assignedRoles) {
            if (!currentRoles.has(roleId)) {
                const role = member.guild.roles.cache.get(roleId);
                if (role) {
                    await member.roles.add(role);
                    console.log(`✅ Rol "${role.name}" asignado a ${member.user.tag}`);
                }
            }
        }

        for (const roleId of Object.values(VANITY_ROLES)) {
            if (currentRoles.has(roleId) && !assignedRoles.has(roleId)) {
                const role = member.guild.roles.cache.get(roleId);
                if (role) {
                    await member.roles.remove(role);
                    console.log(`❌ Rol "${role.name}" removido de ${member.user.tag}`);
                }
            }
        }
    } catch (error) {
        console.error(`❌ Error al actualizar roles: ${error.message}`);
    }
}

client.login(process.env.BOT_TOKEN);
