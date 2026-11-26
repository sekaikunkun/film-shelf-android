package io.github.sekaikunkun.filmshelf.homeprobe;

import android.app.Activity;
import android.app.Instrumentation;
import android.app.UiAutomation;
import android.graphics.Rect;
import android.os.Bundle;
import android.os.SystemClock;
import android.view.accessibility.AccessibilityNodeInfo;
import android.accessibilityservice.AccessibilityServiceInfo;

import java.util.List;
import java.util.concurrent.FutureTask;
import java.util.concurrent.TimeUnit;

/** Read-only, fixed-output Home lookup without the stock dump's global idle gate. */
public final class HomeProbe extends Instrumentation {
    private static final String APP = "io.github.sekaikunkun.filmshelf";
    private static final String ID = APP + ":id/";
    private static final long POLL_MS = 2500;

    @Override public void onCreate(Bundle arguments) {
        super.onCreate(arguments);
        start();
    }

    @Override public void onStart() {
        Bundle output = new Bundle();
        // Bound the result even if an accessibility IPC stalls.
        FutureTask<Bundle> task = new FutureTask<>(this::probe);
        Thread reader = new Thread(task, "film-home-probe");
        reader.setDaemon(true);
        reader.start();
        try {
            output = task.get(POLL_MS + 1500, TimeUnit.MILLISECONDS);
        } catch (Exception failed) {
            task.cancel(true);
            output.putString("status", "probe_deadline_or_failure");
        }
        finish("home_controls_found".equals(output.getString("status"))
            ? Activity.RESULT_OK : Activity.RESULT_CANCELED, output);
    }

    private Bundle probe() {
        Bundle result = new Bundle();
        long deadline = SystemClock.uptimeMillis() + POLL_MS;
        UiAutomation automation = getUiAutomation(UiAutomation.FLAG_DONT_SUPPRESS_ACCESSIBILITY_SERVICES);
        if (automation == null) {
            result.putString("status", "automation_unavailable");
            return result;
        }
        AccessibilityServiceInfo service = automation.getServiceInfo();
        service.flags |= AccessibilityServiceInfo.FLAG_REPORT_VIEW_IDS;
        automation.setServiceInfo(service);
        while (SystemClock.uptimeMillis() < deadline && !Thread.currentThread().isInterrupted()) {
            AccessibilityNodeInfo root = automation.getRootInActiveWindow();
            if (root != null && APP.contentEquals(root.getPackageName() == null ? "" : root.getPackageName())
                && uniqueVisible(root.findAccessibilityNodeInfosByViewId(ID + "nativeContent"))) {
                Rect search = null;
                Rect settings = null;
                int searches = 0;
                int settingsMatches = 0;
                for (AccessibilityNodeInfo node : root.findAccessibilityNodeInfosByViewId(ID + "text")) {
                    if (!node.isVisibleToUser() || !node.isEnabled()) continue;
                    AccessibilityNodeInfo parent = node.getParent();
                    if (parent == null || !parent.isClickable() || !parent.isEnabled()) continue;
                    Rect bounds = new Rect();
                    node.getBoundsInScreen(bounds);
                    if (bounds.isEmpty()) continue;
                    CharSequence label = node.getText();
                    if (matches(label, "Search", "搜索", "搜尋")) {
                        searches++;
                        search = bounds;
                    }
                    if (matches(label, "Setting", "设置", "設定")) {
                        settingsMatches++;
                        settings = bounds;
                    }
                }
                if (searches == 1 && settingsMatches == 1) {
                    result.putString("status", "home_controls_found");
                    result.putString("search", coordinates(search));
                    result.putString("settings", coordinates(settings));
                    return result;
                }
            }
            SystemClock.sleep(100);
        }
        result.putString("status", "film_shelf_home_controls_unavailable");
        return result;
    }

    private static boolean uniqueVisible(List<AccessibilityNodeInfo> nodes) {
        return nodes.size() == 1 && nodes.get(0).isVisibleToUser();
    }

    private static boolean matches(CharSequence label, String english, String simplified, String traditional) {
        return label != null && (english.contentEquals(label)
            || simplified.contentEquals(label) || traditional.contentEquals(label));
    }

    private static String coordinates(Rect rectangle) {
        return rectangle.centerX() + "," + rectangle.centerY();
    }
}
