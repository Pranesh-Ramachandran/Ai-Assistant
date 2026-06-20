package org.pranesh.jarvis_ai;

import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;
import android.app.Notification;
import android.content.Intent;
import android.os.Bundle;

public class JarvisNotificationListener extends NotificationListenerService {
    @Override
    public void onNotificationPosted(StatusBarNotification sbn) {
        if (sbn == null) {
            return;
        }

        Notification notification = sbn.getNotification();
        Bundle extras = notification.extras;

        String title = "";
        String text = "";
        if (extras != null) {
            CharSequence t = extras.getCharSequence(Notification.EXTRA_TITLE);
            CharSequence c = extras.getCharSequence(Notification.EXTRA_TEXT);
            if (t != null) title = t.toString();
            if (c != null) text = c.toString();
        }

        Intent broadcast = new Intent("org.pranesh.jarvis_ai.NOTIFICATION_EVENT");
        broadcast.putExtra("package", sbn.getPackageName());
        broadcast.putExtra("title", title);
        broadcast.putExtra("text", text);
        sendBroadcast(broadcast);
    }

    @Override
    public void onNotificationRemoved(StatusBarNotification sbn) {
        // Optional: handle removals
    }
}
