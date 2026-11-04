package org.json;

import java.util.HashMap;
import java.util.Map;

/** CodexAstraUlt: Test-only report capture, not a substitute JSON parser. */
public final class JSONObject {
    public static final Object NULL = new Object();
    private final Map<String, Object> values = new HashMap<>();
    public JSONObject put(String name, Object value) throws JSONException {
        values.put(name, value); return this;
    }
    public long getLong(String name) { return ((Number)values.get(name)).longValue(); }
    public String getString(String name) { return (String)values.get(name); }
}
