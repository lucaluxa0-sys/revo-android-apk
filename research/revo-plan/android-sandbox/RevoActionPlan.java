package com.revolution.android;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Locale;

/**
 * Converts a hash-identified, bounded offline Revo movement plan into
 * Android-ready movement geometry. Does not execute gestures.
 */
final class RevoActionPlan {
    static final class Step {
        final String direction;
        final double studs;
        Step(String direction, double studs) { this.direction = direction; this.studs = studs; }
    }

    private static String canonical(String s) {
        return s == null ? "" : s.toLowerCase(Locale.US).replaceAll("[^a-z0-9]", "");
    }

    static List<Step> load(JSONObject plan, String expectedPattern, double msPerStud) {
        if (plan == null || !"revo.action-plan.v1".equals(plan.optString("schema"))) {
            throw new IllegalArgumentException("unsupported movement plan schema");
        }
        if (!plan.optBoolean("dryRunOnly", false)) {
            throw new IllegalArgumentException("plan must originate from the offline compiler");
        }
        String provenance = plan.optString("sourceSha256", "");
        if (!provenance.matches("[0-9a-f]{64}")) {
            throw new IllegalArgumentException("movement plan has no valid source hash");
        }
        if (!canonical(plan.optString("pattern", "")).equals(canonical(expectedPattern)) ||
                canonical(expectedPattern).isEmpty()) {
            throw new IllegalArgumentException("configured pattern differs from movement plan");
        }
        double plannedCalibration = plan.optDouble("movementMsPerStud", Double.NaN);
        if (!Double.isFinite(msPerStud) || msPerStud <= 0 ||
                !Double.isFinite(plannedCalibration) ||
                Math.abs(plannedCalibration - msPerStud) > 0.00001) {
            throw new IllegalArgumentException("movement calibration differs from plan");
        }
        JSONArray actions = plan.optJSONArray("actions");
        if (actions == null || actions.length() < 1 || actions.length() > 512) {
            throw new IllegalArgumentException("invalid action count");
        }

        ArrayList<Step> checked = new ArrayList<>();
        for (int i = 0; i < actions.length(); i++) {
            JSONObject action = actions.optJSONObject(i);
            if (action == null || !"walk".equals(action.optString("type"))) {
                throw new IllegalArgumentException("unsupported native action at index " + i);
            }
            String direction = action.optString("direction", "");
            if (!("FORWARD".equals(direction) || "BACKWARD".equals(direction)
                    || "LEFT".equals(direction) || "RIGHT".equals(direction))) {
                throw new IllegalArgumentException("unsupported direction at index " + i);
            }
            double studs = action.optDouble("studs", Double.NaN);
            if (!Double.isFinite(studs) || studs <= 0 || studs > 160) {
                throw new IllegalArgumentException("invalid distance at index " + i);
            }
            long expectedMs = Math.max(50, Math.round(studs * msPerStud));
            long suppliedMs = action.optLong("durationMs", -1);
            if (expectedMs > 10000 || suppliedMs != expectedMs) {
                throw new IllegalArgumentException("gesture duration mismatch at index " + i);
            }
            checked.add(new Step(direction, studs));
        }
        return Collections.unmodifiableList(checked);
    }
}
