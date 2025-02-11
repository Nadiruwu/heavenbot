module.exports = {
    handlePresenceUpdate: (newPresence) => {
        console.log(`🔄 Presencia actualizada: ${newPresence.user.tag}`);
    }
};
