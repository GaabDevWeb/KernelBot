const noop = () => {};

/** Indicador de status removido da UI — API mantida para o TurnController. */
export function createStatusBadge(_element) {
    return {
        setProcessing: noop,
        setOnline: noop,
        setWarning: noop,
    };
}
