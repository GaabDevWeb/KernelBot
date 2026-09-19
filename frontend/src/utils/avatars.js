/**
 * Avatares do bot — imagens fixas por conversa (sorteadas uma vez e persistidas).
 */

const AVATAR_BASE_PATH = "/assets/images/profiles/webp/";

export const BOT_AVATARS = [
    "PenPen121.webp",
    "PenPen14.webp",
    "PenPen4.webp",
    "PenPen7.webp",
    "PenPenVEMHEXA.webp",
];

/**
 * Sorteia um avatar aleatório para uma nova conversa.
 * @returns {string} nome do ficheiro
 */
export function pickRandomAvatar() {
    const idx = Math.floor(Math.random() * BOT_AVATARS.length);
    return BOT_AVATARS[idx];
}

/**
 * @param {string | null | undefined} filename
 * @returns {string} URL absoluta servida estaticamente
 */
export function avatarUrl(filename) {
    const safe = typeof filename === "string" && BOT_AVATARS.includes(filename)
        ? filename
        : BOT_AVATARS[0];
    return `${AVATAR_BASE_PATH}${safe}`;
}
