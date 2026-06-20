package org.pranesh.jarvis_ai;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

public class JarvisMmsReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        Intent broadcast = new Intent("org.pranesh.jarvis_ai.MMS_EVENT");
        broadcast.putExtra("action", intent != null ? intent.getAction() : "");
        context.sendBroadcast(broadcast);
    }
}
