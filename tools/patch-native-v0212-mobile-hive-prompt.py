#!/usr/bin/env python3
from pathlib import Path

p=Path("revo-android/app/src/main/java/com/revolution/android/RevoPreGatherRouter.java")
s=p.read_text()

xs=[22,160,27,158,22,44,161,23,77,169,23,44,171,31,159,31,160,44,15,159,60,111,214,56,80,100,141,178,212,41,62,90,103,141,173,209,14,59,81,99,112,160,195,215,43,67,94,106,140,173,206,219,65,91,114,146,159,194,219,66,92,118,151,170,198,15,78,106,148,160,194,220,59,81,117,149,169,195,14,61,81,118,149,169,196,14,60,79,116,161,193,213,15,59,79,106,160,193,212,14,59,78,106,159,193,213,14,65,91,140,173,205,218,43,77,105,159,187,211,223,55,90,120,172,205,44,80,116,161,192,18,67,102,142,186,208,41,77,104,158,189,14,33,67,102,143,186,217,23,43,69,103,157,189,214,21,43,63,89,119,171,210,18,41,63,88,119,170,211,23,58,78,106,159,209,24,81,118,169,215]
ys=[10,10,11,11,12,12,12,13,13,13,14,14,14,15,15,16,16,17,18,18,19,19,19,20,20,20,20,20,20,21,21,21,21,21,21,21,22,22,22,22,22,22,22,22,23,23,23,23,23,23,23,23,24,24,24,24,24,24,24,25,25,25,25,25,25,26,26,26,26,26,26,26,27,27,27,27,27,27,28,28,28,28,28,28,28,29,29,29,29,29,29,29,30,30,30,30,30,30,30,31,31,31,31,31,31,31,32,32,32,32,32,32,32,33,33,33,33,33,33,33,34,34,34,34,34,35,35,35,35,35,36,36,36,36,36,36,37,37,37,37,37,38,38,38,38,38,38,38,39,39,39,39,39,39,39,40,40,40,40,40,40,40,41,41,41,41,41,41,41,42,42,42,42,42,42,43,43,43,43,43]

def once(old,new,label):
    global s
    if old not in s:
        raise SystemExit("missing marker: "+label)
    s=s.replace(old,new,1)

marker='''    private Match findAnyHive(Bitmap frame, Config c, long now) {
        return findAny(frame, new String[]{"claimhive","sendtrade","tradelocked","tradedisabled"}, c, now);
    }
'''
helper='''    // Android-native hive interaction detection. Roblox mobile renders a
    // top-center proximity banner with a neutral "Tap" box and blue action
    // panel. Claim Hive is distinguished with a sparse bright-pixel signature.
    // This intentionally replaces the desktop ClaimHive/SendTrade glyphs only;
    // cannon and other desktop templates still use the recovered matcher.
    private static final int[] MOBILE_CLAIM_X = new int[] {''' + ",".join(map(str,xs)) + '''};
    private static final int[] MOBILE_CLAIM_Y = new int[] {''' + ",".join(map(str,ys)) + '''};

    private static boolean isLightNeutral(int p) {
        int r=(p>>16)&255, g=(p>>8)&255, b=p&255;
        int hi=Math.max(r,Math.max(g,b)), lo=Math.min(r,Math.min(g,b));
        return lo >= 205 && hi - lo <= 28;
    }

    private static boolean isPromptBlue(int p) {
        int r=(p>>16)&255, g=(p>>8)&255, b=p&255;
        return b >= 170 && g >= 80 && b-r >= 70 && b-g >= 35;
    }

    private boolean isMobileTapPrompt(Bitmap frame) {
        int w=frame.getWidth(), h=frame.getHeight();
        int gx1=Math.max(0,Math.min(w-1,Math.round(w*0.3333333f)));
        int gy1=Math.max(0,Math.min(h-1,Math.round(h*0.1851852f)));
        int gx2=Math.max(0,Math.min(w-1,Math.round(w*0.3854167f)));
        int gy2=Math.max(0,Math.min(h-1,Math.round(h*0.2592593f)));
        int bx1=Math.max(0,Math.min(w-1,Math.round(w*0.4114583f)));
        int by1=gy1;
        int bx2=Math.max(0,Math.min(w-1,Math.round(w*0.65625f)));
        int by2=gy2;
        return isLightNeutral(frame.getPixel(gx1,gy1))
                && isLightNeutral(frame.getPixel(gx2,gy2))
                && isPromptBlue(frame.getPixel(bx1,by1))
                && isPromptBlue(frame.getPixel(bx2,by2));
    }

    private boolean isMobileClaimHive(Bitmap frame) {
        int fw=frame.getWidth(), fh=frame.getHeight();
        int left=Math.round(fw*0.4114583f), top=Math.round(fh*0.1703704f);
        int cw=Math.max(1,Math.round(fw*0.265625f));
        int ch=Math.max(1,Math.round(fh*0.1037037f));
        int matched=0;
        for(int i=0;i<MOBILE_CLAIM_X.length;i++){
            int x=left+Math.min(cw-1,(MOBILE_CLAIM_X[i]*cw)/255);
            int y=top+Math.min(ch-1,(MOBILE_CLAIM_Y[i]*ch)/56);
            x=Math.max(0,Math.min(fw-1,x)); y=Math.max(0,Math.min(fh-1,y));
            int p=frame.getPixel(x,y);
            int r=(p>>16)&255, g=(p>>8)&255, b=p&255;
            if(Math.min(r,Math.min(g,b))>=175) matched++;
        }
        // Real captures: Claim Hive=180/180; tested non-claim frames <=33/180.
        return matched >= 120;
    }

    private static boolean asksForHivePrompt(String[] names) {
        for(String n:names) {
            if("claimhive".equals(n)||"sendtrade".equals(n)
                    ||"tradelocked".equals(n)||"tradedisabled".equals(n)) return true;
        }
        return false;
    }

    private static boolean asksForClaim(String[] names) {
        for(String n:names) if("claimhive".equals(n)) return true;
        return false;
    }

    private static boolean asksForOccupiedHive(String[] names) {
        for(String n:names) {
            if("sendtrade".equals(n)||"tradelocked".equals(n)||"tradedisabled".equals(n)) return true;
        }
        return false;
    }

    private Match findMobileHivePrompt(Bitmap frame, String[] names) {
        if(!isMobileTapPrompt(frame)) return null;
        int fw=frame.getWidth(), fh=frame.getHeight();
        int x=Math.round(fw*0.4114583f), y=Math.round(fh*0.1703704f);
        int w=Math.max(1,Math.round(fw*0.265625f)), h=Math.max(1,Math.round(fh*0.1037037f));
        if(isMobileClaimHive(frame) && asksForClaim(names)) {
            return new Match("claimhive",x,y,w,h);
        }
        if(asksForOccupiedHive(names)) return new Match("mobileoccupied",x,y,w,h);
        return null;
    }

''' + marker
once(marker,helper,"mobile hive helpers")

old='''        if (now - lastSearchAtMs < FRAME_SEARCH_INTERVAL_MS) return null;
        lastSearchAtMs = now;
        int fw = frame.getWidth(), fh = frame.getHeight();
'''
new='''        if (now - lastSearchAtMs < FRAME_SEARCH_INTERVAL_MS) return null;
        lastSearchAtMs = now;

        if (asksForHivePrompt(names)) {
            Match mobile = findMobileHivePrompt(frame, names);
            if (mobile != null) {
                lastTemplate = mobile.name;
                lastMatch = mobile;
                Log.i(TAG, "mobile-hive-prompt=" + mobile.name + " at=" + mobile.x + "," + mobile.y);
            }
            // Never fall back to desktop hive glyphs on Android; they are tiny
            // text fragments and caused whole-frame false positives.
            return mobile;
        }

        int fw = frame.getWidth(), fh = frame.getHeight();
'''
once(old,new,"findAny mobile dispatch")

old_center = """                if (m != null) {
                    lastMatch = m;
                    if (move(frame, svc, c, Direction.BACKWARD, 2.0, "desktop ClaimHive: Backward 2")) {
                        transitionAfterGesture(State.BACK_OFF_INITIAL);
                    }
                } else {
"""
new_center = """                if (m != null) {
                    lastMatch = m;
                    // Mobile Claim Hive is already a definitive proximity prompt.
                    // Claim it while it is visible; backing away first makes the
                    // Android prompt disappear and falsely looks occupied.
                    if ("claimhive".equals(m.name)) {
                        claimedHive = 3;
                        if (tapInteraction(frame, svc, c, m, "mobile Tap: claim center hive")) {
                            transitionDelay(State.CLAIM_CENTER_WAIT, 450);
                        }
                    } else if (move(frame, svc, c, Direction.BACKWARD, 2.0, "desktop ClaimHive: Backward 2")) {
                        transitionAfterGesture(State.BACK_OFF_INITIAL);
                    }
                } else {
"""
once(old_center,new_center,"mobile direct center claim")

once(
'''    private static final long SLOT_TIMEOUT_MS = 7_500;
''',
'''    // Android screenshot delivery on emulators/phones can be much slower than desktop frame polling.
    // Keep desktop geometry, but allow enough time to observe the next mobile proximity prompt.
    private static final long SLOT_TIMEOUT_MS = 15_000;
''',
"mobile hive timeout adaptation")

once(
    '''move(frame, svc, c, Direction.FORWARD, SEEK_CHUNK_STUDS, "desktop ClaimHive: hold Forward (chunked Android)")''',
    '''moveMobileProbe(frame, svc, c, Direction.FORWARD, SEEK_CHUNK_STUDS, 250, "desktop ClaimHive: hold Forward (chunked Android)")''',
    "mobile initial hive probe timing")

once(
    '''move(frame, svc, c, sweepDirection(), SWEEP_CHUNK_STUDS, "desktop MoveToNextHive: leave current prompt")''',
    '''moveMobileProbe(frame, svc, c, sweepDirection(), SWEEP_CHUNK_STUDS, 170, "desktop MoveToNextHive: leave current prompt")''',
    "mobile leave-hive probe timing")

once(
    '''move(frame, svc, c, sweepDirection(), SWEEP_CHUNK_STUDS, "desktop MoveToNextHive: seek next prompt")''',
    '''moveMobileProbe(frame, svc, c, sweepDirection(), SWEEP_CHUNK_STUDS, 170, "desktop MoveToNextHive: seek next prompt")''',
    "mobile next-hive probe timing")

once(
    '''move(frame, svc, c, Direction.RIGHT, CANNON_SEEK_CHUNK_STUDS, "desktop GotoCannon: continue Right seeking Press E")''',
    '''moveMobileProbe(frame, svc, c, Direction.RIGHT, CANNON_SEEK_CHUNK_STUDS, 170, "desktop GotoCannon: continue Right seeking Press E")''',
    "mobile cannon probe timing")

move_marker='''    private boolean move(Bitmap frame, RevoAccessibilityService svc, Config c, Direction d, double studs, String label) {
'''
move_helper='''    // Tiny proximity-search motions need a longer touch hold on Android than
    // the desktop distance/speed formula produces. Keep long route geometry on
    // desktop timing; apply only a minimum to explicit mobile probe calls.
    private boolean moveMobileProbe(Bitmap frame, RevoAccessibilityService svc, Config c,
                                    Direction d, double studs, long minimumDurationMs, String label) {
        long now = SystemClock.elapsedRealtime();
        long duration = RevoMovementSpeed.durationMs(
                studs, c.baseMoveSpeed, c.msPerStud,
                c.hasteStacks, c.hastePlus, c.coconutHaste, c.bearMorph, c.oil, c.superSmoothie,
                MAX_GESTURE_MS);
        duration = Math.max(minimumDurationMs, duration);
        float w = frame.getWidth(), h = frame.getHeight();
        float cx = (float)(w * c.joyX), cy = (float)(h * c.joyY), r = (float)(Math.min(w, h) * c.joyR);
        float tx = cx, ty = cy;
        switch (d) {
            case FORWARD: ty -= r; break;
            case BACKWARD: ty += r; break;
            case LEFT: tx -= r; break;
            case RIGHT: tx += r; break;
        }
        boolean accepted = svc.joystick(displayId, cx, cy, tx, ty, duration);
        recordGesture(accepted, label + String.format(Locale.US, " %.2f studs %dms", studs, duration));
        nextActionAtMs = now + duration + 80;
        return accepted;
    }

''' + move_marker
once(move_marker,move_helper,"mobile probe timing helper")
p.write_text(s)
print("PASS: Android mobile hive Tap/Claim detector installed")

