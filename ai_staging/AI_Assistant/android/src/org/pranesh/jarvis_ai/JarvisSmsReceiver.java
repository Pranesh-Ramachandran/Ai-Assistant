package org.pranesh.jarvis_ai;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.telephony.SmsMessage;

public class JarvisSmsReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        Bundle bundle = intent.getExtras();
        if (bundle == null) {
            return;
        }

        Object[] pdus = (Object[]) bundle.get("pdus");
        String format = bundle.getString("format");
        if (pdus == null) {
            return;
        }

        for (Object pdu : pdus) {
            SmsMessage sms = SmsMessage.createFromPdu((byte[]) pdu, format);
            if (sms == null) {
                continue;
            }
            Intent broadcast = new Intent("org.pranesh.jarvis_ai.SMS_EVENT");
            broadcast.putExtra("address", sms.getOriginatingAddress());
            broadcast.putExtra("body", sms.getMessageBody());
            broadcast.putExtra("timestamp", sms.getTimestampMillis());
            context.sendBroadcast(broadcast);
        }
    }
}
