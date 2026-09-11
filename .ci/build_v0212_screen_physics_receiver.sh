#!/usr/bin/env bash
set -euo pipefail

mkdir -p fake-physics/app/src/main/java/com/roblox/client fake-physics/app/src/main/res/values

cat > fake-physics/settings.gradle.kts <<'EOF'
pluginManagement { repositories { google(); mavenCentral(); gradlePluginPortal() } }
dependencyResolutionManagement { repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS); repositories { google(); mavenCentral() } }
rootProject.name = "FakeRobloxPhysics"
include(":app")
EOF

cat > fake-physics/build.gradle.kts <<'EOF'
plugins { id("com.android.application") version "8.12.2" apply false }
EOF

cat > fake-physics/app/build.gradle.kts <<'EOF'
plugins { id("com.android.application") }
android {
    namespace = "com.roblox.client"
    compileSdk = 36
    defaultConfig {
        applicationId = "com.roblox.client"
        minSdk = 30
        targetSdk = 36
        versionCode = 1
        versionName = "1.0"
    }
}
EOF

cat > fake-physics/app/src/main/res/values/styles.xml <<'EOF'
<resources>
  <style name="AppTheme" parent="android:style/Theme.Material.Light.NoActionBar">
    <item name="android:fontFamily">sans</item>
    <item name="android:windowFullscreen">true</item>
  </style>
</resources>
EOF

cat > fake-physics/app/src/main/AndroidManifest.xml <<'EOF'
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
  <application android:theme="@style/AppTheme" android:label="Fake Roblox Physics CI">
    <activity android:name=".MainActivity" android:screenOrientation="portrait" android:exported="true">
      <intent-filter>
        <action android:name="android.intent.action.MAIN"/>
        <category android:name="android.intent.category.LAUNCHER"/>
      </intent-filter>
    </activity>
    <receiver android:name=".LabelReceiver" android:exported="true">
      <intent-filter><action android:name="com.roblox.client.PHYSICS_LABEL"/></intent-filter>
    </receiver>
  </application>
</manifest>
EOF

cat > fake-physics/app/src/main/java/com/roblox/client/MainActivity.java <<'EOF'
package com.roblox.client;

import android.app.Activity;
import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.os.Bundle;
import android.os.SystemClock;
import android.util.Log;
import android.view.MotionEvent;
import android.view.View;

public class MainActivity extends Activity {
    static volatile String label = "boot";

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        setContentView(new PhysicsView(this));
    }

    static String actionName(int action) {
        switch (action) {
            case MotionEvent.ACTION_DOWN: return "DOWN";
            case MotionEvent.ACTION_UP: return "UP";
            case MotionEvent.ACTION_MOVE: return "MOVE";
            case MotionEvent.ACTION_CANCEL: return "CANCEL";
            case MotionEvent.ACTION_POINTER_DOWN: return "POINTER_DOWN";
            case MotionEvent.ACTION_POINTER_UP: return "POINTER_UP";
            default: return "A" + action;
        }
    }

    static final class PhysicsView extends View {
        final Paint paint = new Paint();

        PhysicsView(Context context) {
            super(context);
            setClickable(true);
            paint.setTextSize(38f);
        }

        @Override protected void onSizeChanged(int w, int h, int oldW, int oldH) {
            Log.i("RevoPhysicsReceiver", "PHYSICS_VIEW w=" + w + " h=" + h);
        }

        @Override protected void onDraw(Canvas canvas) {
            canvas.drawColor(Color.rgb(24, 30, 44));
            paint.setColor(Color.WHITE);
            canvas.drawText("Revolution joystick physics receiver: " + label, 40, 100, paint);
        }

        @Override public boolean onTouchEvent(MotionEvent event) {
            long recvUptimeMs = SystemClock.uptimeMillis();
            long recvElapsedMs = SystemClock.elapsedRealtime();
            StringBuilder out = new StringBuilder();
            out.append("PHYSICS_EVENT label=").append(label)
               .append(" action=").append(actionName(event.getActionMasked()))
               .append(" eventMs=").append(event.getEventTime())
               .append(" downMs=").append(event.getDownTime())
               .append(" recvUptimeMs=").append(recvUptimeMs)
               .append(" recvElapsedMs=").append(recvElapsedMs)
               .append(" deliveryLagMs=").append(recvUptimeMs - event.getEventTime())
               .append(" historySize=").append(event.getHistorySize())
               .append(" pointers=").append(event.getPointerCount())
               .append(" actionIndex=").append(event.getActionIndex());
            for (int i = 0; i < event.getPointerCount(); i++) {
                out.append(" p").append(i).append("id=").append(event.getPointerId(i))
                   .append(" p").append(i).append("x=").append(event.getRawX(i))
                   .append(" p").append(i).append("y=").append(event.getRawY(i));
            }
            Log.i("RevoPhysicsReceiver", out.toString());
            return true;
        }
    }
}
EOF

cat > fake-physics/app/src/main/java/com/roblox/client/LabelReceiver.java <<'EOF'
package com.roblox.client;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.util.Log;

public final class LabelReceiver extends BroadcastReceiver {
    @Override public void onReceive(Context context, Intent intent) {
        String value = intent == null ? "" : intent.getStringExtra("label");
        MainActivity.label = value == null ? "" : value;
        Log.i("RevoPhysicsReceiver", "PHYSICS_LABEL label=" + MainActivity.label);
    }
}
EOF

gradle -p fake-physics --stacktrace :app:assembleDebug
test -s fake-physics/app/build/outputs/apk/debug/app-debug.apk
