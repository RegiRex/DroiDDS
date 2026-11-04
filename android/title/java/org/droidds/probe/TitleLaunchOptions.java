package org.droidds.probe;

/** CodexAstraUlt: Immutable launch choices bind the visible selector, native
 * open and report to the same session; a recreated view cannot change them. */
final class TitleLaunchOptions {
    static final int AUTOMATIC = 0, CPU = 1, GPU = 2;
    final boolean nativeMode;
    final int vertexPolicy;

    TitleLaunchOptions(boolean nativeMode, int vertexPolicy) {
        if (vertexPolicy < AUTOMATIC || vertexPolicy > GPU) {
            throw new IllegalArgumentException("Unsupported vertex shader selection");
        }
        this.nativeMode = nativeMode;
        this.vertexPolicy = vertexPolicy;
    }

    // CodexAstraUlt: Invalid saved widget state falls back to the unchanged
    // automatic policy. Explicit new launch requests instead reject above.
    static TitleLaunchOptions restored(int route, int vertexPolicy) {
        return new TitleLaunchOptions(route != 1,
                vertexPolicy >= AUTOMATIC && vertexPolicy <= GPU ? vertexPolicy : AUTOMATIC);
    }

    // CodexAstraUlt: Keep pending idle choices, but show the actual latched
    // session even if a replaced Activity restores stale or absent widget state.
    TitleLaunchOptions displayed(boolean running, int selectedRoute, int selectedVertex) {
        return running ? this : restored(selectedRoute, selectedVertex);
    }

    String vertexPolicyName() {
        switch (vertexPolicy) {
            case CPU: return "cpu";
            case GPU: return "gpu";
            default: return "automatic";
        }
    }
}
