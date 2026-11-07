package com.revolution.android;

import org.json.JSONObject;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

/** Runtime assertions for the actual native JSON validator, no Android device required. */
public final class PlanIntakeTest {
    private static int checks = 0;
    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
        checks++;
    }
    private static void mustReject(JSONObject candidate, String pattern, double timing) {
        try {
            RevoActionPlan.load(candidate, pattern, timing);
            throw new AssertionError("unsafe/unsupported action plan was accepted");
        } catch (IllegalArgumentException expected) {
            checks++;
        }
    }
    public static void main(String[] args) throws Exception {
        JSONObject original = new JSONObject(Files.readString(Path.of(args[0])));
        List<RevoActionPlan.Step> steps = RevoActionPlan.load(original, "e_lol", 62.5);
        check(steps.size() == 18, "expected 18 actual recovered e_lol steps");
        check("LEFT".equals(steps.get(0).direction) && steps.get(0).studs == 10.0,
                "wrong initial recovered movement");
        check("RIGHT".equals(steps.get(17).direction) && steps.get(17).studs == 10.0,
                "wrong final recovered movement");

        mustReject(original, "other_pattern", 62.5);
        mustReject(original, "e_lol", 50.0);
        JSONObject changed = new JSONObject(original.toString());
        changed.getJSONArray("actions").getJSONObject(0).put("type", "keyDown");
        mustReject(changed, "e_lol", 62.5);
        changed = new JSONObject(original.toString());
        changed.getJSONArray("actions").getJSONObject(0).put("studs", -1);
        mustReject(changed, "e_lol", 62.5);
        changed = new JSONObject(original.toString());
        changed.getJSONArray("actions").getJSONObject(0).put("durationMs", 50);
        mustReject(changed, "e_lol", 62.5);
        changed = new JSONObject(original.toString());
        changed.put("sourceSha256", "not-a-hash");
        mustReject(changed, "e_lol", 62.5);
        changed = new JSONObject(original.toString());
        changed.put("schema", "different");
        mustReject(changed, "e_lol", 62.5);
        changed = new JSONObject(original.toString());
        changed.put("dryRunOnly", false);
        mustReject(changed, "e_lol", 62.5);
        System.out.println("PASS: native movement plan intake; " + checks +
                " assertions, 18 steps; unsupported and malformed plans rejected");
    }
}
