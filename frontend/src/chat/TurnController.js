/**
 * Ponto de entrada dos controllers de chat.
 * TurnController (sendMessage/SSE) permanece em ui.js — importe controllers auxiliares daqui.
 */
export { createMetaRenderer, createHistoryController } from "./MetaRenderer.js";
export { createComposerController } from "./ComposerController.js";
