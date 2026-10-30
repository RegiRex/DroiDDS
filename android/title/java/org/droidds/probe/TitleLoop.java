package org.droidds.probe;

/** CodexAstraUlt: Worker-owned tickets retire delayed frame callbacks across
 * pause/resume; a session token alone cannot distinguish two work chains. */
final class TitleLoop {
    private long epoch;
    private long appliedLifecycle;
    private boolean active;
    long resume() { epoch++; active = true; return epoch; }
    void pause() { epoch++; active = false; }
    boolean accepts(long ticket) { return active && ticket == epoch; }
    // CodexAstraUlt: A rapid pause/resume can finish before its queued worker
    // callback runs. Preserve the boundary even when the latest state is active.
    boolean synchronize(long lifecycle) {
        if (lifecycle == appliedLifecycle) return false;
        appliedLifecycle = lifecycle;
        pause();
        return true;
    }
}
