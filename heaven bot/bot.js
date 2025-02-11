const { Client, GatewayIntentBits, EmbedBuilder } = require('discord.js');
const chalk = require('chalk');
const fs = require('fs');
const path = require('path');
require('dotenv').config();

const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildPresences,
        GatewayIntentBits.GuildMembers,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent
    ]
});

const dbFile = path.join(__dirname, 'database.json');
const VANITY_ROLES = {
    'nvn': '1284285993494773800',
    '.gg/nvn': '1284285993494773800'
};
const authorizedUserIDs = ['1084586006939975861'];
const authorizedRoleIDs = ['1331879889971970048'];

function loadDatabase() {
    if (fs.existsSync(dbFile)) {
        return JSON.parse(fs.readFileSync(dbFile, 'utf8'));
    }
    return { blacklist: {}, autoResponses: {}, autoReactions: {}, vanityRoles: {} };
}

function saveDatabase() {
    fs.writeFileSync(dbFile, JSON.stringify(database, null, 2), 'utf8');
}

let database = loadDatabase();

client.once('ready', () => {
    console.log(chalk.green(`✅ Bot en línea como ${client.user.tag}`));
    client.user.setPresence({
        activities: [{ name: 'Trabajando en Heaven', type: 0 }],
        status: 'online'
    });
});

client.on('presenceUpdate', (oldPresence, newPresence) => {
    const member = newPresence.member;
    if (!member) return;

    console.log(chalk.blue(`⚡ Cambio de presencia: ${member.user.tag}`));

    let assignedRoles = new Set();

    for (const [vanity, roleId] of Object.entries(VANITY_ROLES)) {
        if (newPresence.activities.some(activity =>
            (activity.type === 4 || activity.type === 0) &&
            activity.state?.includes(vanity))) {
            console.log(chalk.green(`✅ Vanity detectada: ${vanity}`));
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
                    console.log(chalk.green(`✅ Rol "${role.name}" asignado.`));
                }
            }
        }

        for (const roleId of Object.values(VANITY_ROLES)) {
            if (currentRoles.has(roleId) && !assignedRoles.has(roleId)) {
                const role = member.guild.roles.cache.get(roleId);
                if (role) {
                    await member.roles.remove(role);
                    console.log(chalk.red(`❌ Rol "${role.name}" removido.`));
                }
            }
        }
    } catch (error) {
        console.error(chalk.red(`❌ Error al actualizar roles: ${error.message}`));
    }
}

client.on('messageCreate', async (message) => {
    if (message.author.bot) return;

    const lowerCaseContent = message.content.toLowerCase();
    const trigger = lowerCaseContent.startsWith('!') ? lowerCaseContent.slice(1) : lowerCaseContent;

    if (database.autoResponses[trigger] && database.autoResponses[trigger].trim() !== '') {
        return message.reply({ embeds: [new EmbedBuilder().setDescription(database.autoResponses[trigger])] });
    }

    if (database.autoReactions[trigger]) {
        return message.react(database.autoReactions[trigger]).catch(err => console.error(chalk.red(`❌ No se pudo reaccionar: ${err.message}`)));
    }

    if (message.content.startsWith('!')) {
        if (!authorizedUserIDs.includes(message.author.id) && !message.member.roles.cache.some(role => authorizedRoleIDs.includes(role.id))) {
            return message.reply({ embeds: [new EmbedBuilder().setColor('#ff0000').setDescription('❌ No tienes permisos suficientes para ejecutar este comando.')] });
        }

        const args = message.content.slice(1).split(/ +/);
        const command = args.shift().toLowerCase();

        if (command === 'addresponse') {
            if (args.length < 2) {
                return message.reply({ embeds: [new EmbedBuilder().setColor('#ff0000').setDescription('❌ Debes proporcionar un mensaje y una respuesta.')] });
            }

            const trigger = args[0].toLowerCase();
            const responseMessage = args.slice(1).join(' ');

            if (responseMessage.trim() === '') {
                return message.reply({ embeds: [new EmbedBuilder().setColor('#ff0000').setDescription('❌ La respuesta no puede estar vacía.')] });
            }

            database.autoResponses[trigger] = responseMessage;
            saveDatabase();

            const embed = new EmbedBuilder()
                .setColor('#00ff00')
                .setTitle('✅ Auto-respuesta añadida')
                .setDescription(`Se ha añadido una nueva auto-respuesta para el mensaje: **${trigger}**.\nRespuesta: **${responseMessage}**`)
                .setTimestamp();

            return message.reply({ embeds: [embed] });
        }

        if (command === 'help') {
            const embed = new EmbedBuilder()
                .setColor('#0099ff')
                .setTitle('Comandos del Bot')
                .setDescription('Aquí tienes una lista de los comandos disponibles:')
                .addFields(
                    { name: '!blacklist add <userID>', value: 'Añadir un usuario a la blacklist.', inline: false },
                    { name: '!blacklist remove <userID>', value: 'Eliminar un usuario de la blacklist.', inline: false },
                    { name: '!blacklist show', value: 'Mostrar todos los usuarios en la blacklist.', inline: false },
                    { name: '!user <userID>', value: 'Ver la información y roles actuales de un usuario.', inline: false },
                    { name: '!addresponse <mensaje> <respuesta>', value: 'Añadir una auto-respuesta para un mensaje específico.', inline: false },
                    { name: '!delresponse <mensaje>', value: 'Eliminar una auto-respuesta.', inline: false },
                    { name: '!addreaction <mensaje> <emoji>', value: 'Añadir una reacción automática a un mensaje.', inline: false },
                    { name: '!delreaction <mensaje>', value: 'Eliminar una reacción automática.', inline: false },
                    { name: '!ban <userID>', value: 'Banear a un usuario del servidor.', inline: false },
                    { name: '!help', value: 'Muestra esta lista de comandos.', inline: false }
                )
                .setFooter({ text: 'Dev by Código', iconURL: 'https://example.com/icon.png' })
                .setTimestamp();

            message.reply({ embeds: [embed] });
        }

        if (command === 'blacklist') {
            if (args[0] === 'add' && args[1]) {
                const userID = args[1];
                const reason = args.slice(2).join(' ') || 'Sin razón especificada';
                const attachments = message.attachments.map(att => att.url);

                database.blacklist[userID] = { reason, proofs: attachments };
                saveDatabase();

                const embed = new EmbedBuilder()
                    .setColor('#ff0000')
                    .setTitle('🔒 Usuario añadido a la Blacklist')
                    .setDescription(`El usuario **${userID}** ha sido añadido a la blacklist por: **${reason}**`)
                    .addFields(
                        { name: 'Pruebas adjuntas', value: attachments.length > 0 ? 'Haz clic en los enlaces a continuación para ver las pruebas.' : 'No se han adjuntado pruebas.', inline: false }
                    )
                    .setTimestamp();

                if (attachments.length > 0) {
                    attachments.forEach((url, index) => {
                        if (url.endsWith('.jpg') || url.endsWith('.jpeg') || url.endsWith('.png')) {
                            embed.setImage(url);
                        } else if (url.endsWith('.mp4') || url.endsWith('.mov') || url.endsWith('.webm')) {
                            embed.addFields({ name: `Prueba ${index + 1}`, value: `[Ver Video](${url})`, inline: false });
                        }
                    });
                }

                return message.reply({ embeds: [embed] });
            }

            if (args[0] === 'remove' && args[1]) {
                delete database.blacklist[args[1]];
                saveDatabase();

                const embed = new EmbedBuilder()
                    .setColor('#00ff00')
                    .setTitle('🔓 Usuario eliminado de la Blacklist')
                    .setDescription(`El usuario **${args[1]}** ha sido eliminado de la blacklist.`)
                    .setTimestamp();

                return message.reply({ embeds: [embed] });
            }

            if (args[0] === 'show') {
                const blacklistEntries = Object.entries(database.blacklist);

                if (blacklistEntries.length === 0) {
                    return message.reply({ embeds: [new EmbedBuilder().setColor('#ff0000').setDescription('🚫 La blacklist está vacía.')] });
                }

                const embed = new EmbedBuilder()
                    .setColor('#ff0000')
                    .setTitle('🚫 Blacklist')
                    .setDescription(
                        blacklistEntries.map(([id, data]) => {
                            return `🔹 **${id}** - Razón: ${data.reason}\n` +
                                (data.proofs.length > 0
                                    ? `  **Pruebas:**\n  ${data.proofs.map((proof, index) => {
                                        return proof.endsWith('.jpg') || proof.endsWith('.jpeg') || proof.endsWith('.png')
                                            ? `**Imagen ${index + 1}:** ![image](${proof})`
                                            : `**Video ${index + 1}:** [Ver Video](${proof})`;
                                    }).join('\n')}`
                                    : '  **Sin pruebas adjuntas**');
                        }).join('\n\n')
                    )
                    .setTimestamp();

                return message.reply({ embeds: [embed] });
            }
        }

        if (command === 'user') {
            const userID = args[0] || message.author.id;
            const member = await message.guild.members.fetch(userID).catch(() => null);

            if (!member) {
                return message.reply({
                    embeds: [new EmbedBuilder().setColor('#ff0000').setDescription('❌ Usuario no encontrado.')]
                });
            }

            const user = member.user;
            const roles = member.roles.cache
                .filter(role => role.id !== message.guild.id)
                .sort((a, b) => b.position - a.position)
                .map(role => role.toString())
                .join(', ') || 'Ningún rol asignado';

            const embed = new EmbedBuilder()
                .setColor('#0099ff')
                .setAuthor({ name: `${user.tag}`, iconURL: user.displayAvatarURL({ dynamic: true }) })
                .setThumbnail(user.displayAvatarURL({ dynamic: true, size: 1024 }))
                .addFields(
                    { name: '🆔 ID', value: `${user.id}`, inline: true },
                    { name: '📆 Cuenta creada', value: `<t:${Math.floor(user.createdTimestamp / 1000)}:F>`, inline: true },
                    { name: '📥 Se unió al servidor', value: `<t:${Math.floor(member.joinedTimestamp / 1000)}:F>`, inline: true },
                    { name: '🔰 Roles', value: roles, inline: false }
                )
                .setFooter({ text: `Solicitado por ${message.author.tag}`, iconURL: message.author.displayAvatarURL({ dynamic: true }) })
                .setTimestamp();

            return message.reply({ embeds: [embed] });
        }

        if (command === 'ban') {
            const userID = args[0];
            const reason = args.slice(1).join(' ') || 'Razón no especificada';
            const member = await message.guild.members.fetch(userID);

            if (!member) return message.reply({ embeds: [new EmbedBuilder().setColor('#ff0000').setDescription('❌ Usuario no encontrado.')] });
            if (!member.bannable) return message.reply({ embeds: [new EmbedBuilder().setColor('#ff0000').setDescription('❌ No puedo banear a este usuario.')] });

            await member.ban({ reason });
            return message.reply({ embeds: [new EmbedBuilder().setColor('#00ff00').setDescription(`✅ Usuario ${member.user.tag} baneado por: ${reason}`)] });
        }

        if (command === 'delresponse') {
            if (args.length < 1) {
                return message.reply({
                    embeds: [new EmbedBuilder().setColor('#ff0000').setDescription('❌ Debes proporcionar el mensaje clave para eliminar la auto-respuesta.')]
                });
            }

            const trigger = args[0].toLowerCase();

            if (!database.autoResponses[trigger]) {
                return message.reply({
                    embeds: [new EmbedBuilder().setColor('#ff0000').setDescription('❌ No existe una auto-respuesta con esa clave.')]
                });
            }

            delete database.autoResponses[trigger];
            saveDatabase();

            return message.reply({
                embeds: [new EmbedBuilder().setColor('#00ff00').setDescription(`✅ Auto-respuesta eliminada para el mensaje: **${trigger}**.`)]
            });
        }

        if (command === 'addreaction') {
            if (args.length < 2) {
                return message.reply({
                    embeds: [new EmbedBuilder().setColor('#ff0000').setDescription('❌ Debes proporcionar un mensaje clave y un emoji.')]
                });
            }
            const trigger = args[0].toLowerCase();
            const emoji = args[1];

            database.autoReactions[trigger] = emoji;
            saveDatabase();

            return message.reply({
                embeds: [new EmbedBuilder().setColor('#00ff00').setDescription(`✅ Se ha añadido una reacción automática.\n\n**Mensaje clave:** ${trigger}\n**Emoji:** ${emoji}`)]
            });
        }

        if (command === 'delreaction') {
            if (args.length < 1) {
                return message.reply({
                    embeds: [new EmbedBuilder().setColor('#ff0000').setDescription('❌ Debes proporcionar el mensaje clave para eliminar la auto-reacción.')]
                });
            }
            const trigger = args[0].toLowerCase();

            if (!database.autoReactions[trigger]) {
                return message.reply({
                    embeds: [new EmbedBuilder().setColor('#ff0000').setDescription('❌ No existe una auto-reacción con esa clave.')]
                });
            }
            delete database.autoReactions[trigger];
            saveDatabase();

            return message.reply({
                embeds: [new EmbedBuilder().setColor('#00ff00').setDescription(`✅ Auto-reacción eliminada para el mensaje: **${trigger}**.`)]
            });
        }
    }
});

client.login(process.env.BOT_TOKEN);