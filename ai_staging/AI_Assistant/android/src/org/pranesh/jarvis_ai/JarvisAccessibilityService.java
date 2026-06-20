package org.pranesh.jarvis_ai;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.AccessibilityServiceInfo;
import android.content.Intent;
import android.os.Bundle;
import android.view.accessibility.AccessibilityEvent;

public class JarvisAccessibilityService extends AccessibilityService {
    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        if (event == null || event.getEventType() == AccessibilityEvent.TYPE_NOTIFICATION_STATE_CHANGED) {
            return;
        }

        Intent broadcast = new Intent("org.pranesh.jarvis_ai.ACCESSIBILITY_EVENT");
        broadcast.putExtra("event_type", event.getEventType());
        CharSequence pkg = event.getPackageName();
        CharSequence text = null;
        if (event.getText() != null && event.getText().size() > 0) {
            text = event.getText().get(0);
        }
        if (pkg != null) {
            broadcast.putExtra("package", pkg.toString());
        }
        if (text != null) {
            broadcast.putExtra("text", text.toString());
        }
        sendBroadcast(broadcast);
    }

    @Override
    public void onInterrupt() {
        // No-op
    }

    @Override
    protected void onServiceConnected() {
        AccessibilityServiceInfo info = new AccessibilityServiceInfo();
        info.eventTypes = AccessibilityEvent.TYPES_ALL_MASK;
        info.feedbackType = AccessibilityServiceInfo.FEEDBACK_GENERIC;
        info.notificationTimeout = 100;
        setServiceInfo(info);
    }
}
