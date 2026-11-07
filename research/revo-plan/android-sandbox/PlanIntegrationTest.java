package com.revolution.android;

import org.json.JSONObject;
import java.nio.file.Files;
import java.nio.file.Path;

public final class PlanIntegrationTest {
    private static int assertions=0;
    private static void require(boolean ok,String message){
        if(!ok) throw new AssertionError(message);
        assertions++;
    }
    private static JSONObject state(RevoGatherAdapter adapter){
        JSONObject result=new JSONObject();
        adapter.appendState(result);
        return result;
    }
    private static JSONObject settings(JSONObject plan,boolean permitted){
        return new JSONObject().put("routine","gather").put("account","Default")
            .put("patternName","e_lol").put("msPerStud",62.5)
            .put("enablePlannedExecution",permitted).put("actionPlan",plan);
    }
    public static void main(String[] args)throws Exception{
        JSONObject plan=new JSONObject(Files.readString(Path.of(args[0])));
        RevoGatherAdapter adapter=new RevoGatherAdapter(0);
        adapter.configure(settings(plan,true).toString());
        JSONObject configured=state(adapter);
        require(configured.getInt("patternStepCount")==18,"planned pattern should have 18 steps");
        require("e_lol".equals(configured.getString("patternName")),"wrong pattern chosen");
        require(configured.getString("lastDecision").startsWith("configured:e_lol"),"not configured");

        adapter.configure(settings(plan,false).toString());
        JSONObject denied=state(adapter);
        require(denied.getInt("patternStepCount")==0,"denied plan must have no steps");
        require("configure-error".equals(denied.getString("lastDecision")),"missing refusal");

        JSONObject mismatched=settings(plan,true).put("patternName","not_e_lol");
        adapter.configure(mismatched.toString());
        require(state(adapter).getInt("patternStepCount")==0,"mismatched plan should be rejected");

        JSONObject unsupported=new JSONObject(plan.toString());
        unsupported.getJSONArray("actions").getJSONObject(0).put("type","sleep");
        adapter.configure(settings(unsupported,true).toString());
        require(state(adapter).getInt("patternStepCount")==0,"unsupported action accepted");

        adapter.configure(new JSONObject().put("routine","gather").put("patternName","e_lol")
            .put("width",2).put("length",8).toString());
        require(state(adapter).getInt("patternStepCount")==18,"legacy e_lol regression");

        System.out.println("PASS: integrated native Revo adapter, "+assertions+
            " assertions; execution enabled only with explicit flag; no device gestures sent");
    }
}
