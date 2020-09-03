Return-Path: <SRS0=OCv1=CF=vger.kernel.org=linux-kernel-owner@kernel.org>
X-Spam-Checker-Version: SpamAssassin 3.4.0 (2014-02-07) on
	aws-us-west-2-korg-lkml-1.web.codeaurora.org
X-Spam-Level: 
X-Spam-Status: No, score=-13.8 required=3.0 tests=BAYES_00,DKIMWL_WL_HIGH,
	DKIM_SIGNED,DKIM_VALID,DKIM_VALID_AU,HEADER_FROM_DIFFERENT_DOMAINS,
	INCLUDES_PATCH,MAILING_LIST_MULTI,SIGNED_OFF_BY,SPF_HELO_NONE,SPF_PASS,
	URIBL_BLOCKED,USER_AGENT_GIT autolearn=ham autolearn_force=no version=3.4.0
Received: from mail.kernel.org (mail.kernel.org [198.145.29.99])
	by smtp.lore.kernel.org (Postfix) with ESMTP id 6DA79C433DF
	for <linux-kernel@archiver.kernel.org>; Thu, 27 Aug 2020 20:42:02 +0000 (UTC)
Received: from vger.kernel.org (vger.kernel.org [23.128.96.18])
	by mail.kernel.org (Postfix) with ESMTP id 2962820825
	for <linux-kernel@archiver.kernel.org>; Thu, 27 Aug 2020 20:42:02 +0000 (UTC)
Authentication-Results: mail.kernel.org;
	dkim=pass (1024-bit key) header.d=chromium.org header.i=@chromium.org header.b="hjmK23h2"
Received: (majordomo@vger.kernel.org) by vger.kernel.org via listexpand
        id S1727015AbgH0Ul7 (ORCPT
        <rfc822;linux-kernel@archiver.kernel.org>);
        Thu, 27 Aug 2020 16:41:59 -0400
Received: from lindbergh.monkeyblade.net ([23.128.96.19]:59944 "EHLO
        lindbergh.monkeyblade.net" rhost-flags-OK-OK-OK-OK) by vger.kernel.org
        with ESMTP id S1726120AbgH0Ul7 (ORCPT
        <rfc822;linux-kernel@vger.kernel.org>);
        Thu, 27 Aug 2020 16:41:59 -0400
Received: from mail-io1-xd42.google.com (mail-io1-xd42.google.com [IPv6:2607:f8b0:4864:20::d42])
        by lindbergh.monkeyblade.net (Postfix) with ESMTPS id C6B0EC061264
        for <linux-kernel@vger.kernel.org>; Thu, 27 Aug 2020 13:41:58 -0700 (PDT)
Received: by mail-io1-xd42.google.com with SMTP id j2so5011242ioj.7
        for <linux-kernel@vger.kernel.org>; Thu, 27 Aug 2020 13:41:58 -0700 (PDT)
DKIM-Signature: v=1; a=rsa-sha256; c=relaxed/relaxed;
        d=chromium.org; s=google;
        h=from:to:cc:subject:date:message-id:mime-version
         :content-transfer-encoding;
        bh=OdZ52bJAKfpKjAFikGZ9iZdEwjptrhEb8wvk5fkUSlU=;
        b=hjmK23h2vxYMNmK6N1yVqijAiSJG+qNNU+BsyUsBkOI/NUftZvTY2xmY1DiUIwJ4cw
         lGPGoIqNS8b9XiVCBRQXusDK80yQvCCvka9KbaXqF1Fys1BtjDrGwG2k8NSsAZmXWuje
         sA4Hng9EYxH77vKG49pA8Mf2DR+AL7oTsE/Kk=
X-Google-DKIM-Signature: v=1; a=rsa-sha256; c=relaxed/relaxed;
        d=1e100.net; s=20161025;
        h=x-gm-message-state:from:to:cc:subject:date:message-id:mime-version
         :content-transfer-encoding;
        bh=OdZ52bJAKfpKjAFikGZ9iZdEwjptrhEb8wvk5fkUSlU=;
        b=PbC2kTOe43epwwU6vY2jT2xek7diy1grh8YHLAi+n1ukKLqIqxKZHYu7emA7vU6Iui
         a1rdPybQYFIqVBWoYOC0REaNXV8NRmeonXaKuBPKAVhHW1ZO5r5EG7SARABscneDE661
         9IkFF7jXK78B9whajCUhyqqI3ud654704jIMKzqLYwO3ctzvKJaS+n+JoB418JvEWPU5
         sdP2JM+R3ZHkeI5RipcLsHZJRkBB4u+0H32pDEwt7CA4majUPQZRFm4mAtCrs/o88W1W
         xXEnFtIy6aepx4xRmUcVSU1xyvSfFb7Xc1LU5zxjS2d6zENjFJ9DXeFH8DqKtutdsJaf
         INGA==
X-Gm-Message-State: AOAM531eKInaMx9W0urA/hskJgew4VH2lQBGHSpscUsqcuKYavNW9FXR
        dqS0Bzuy0lcwDO3TdSuogWSQYA==
X-Google-Smtp-Source: ABdhPJy+sf2ZHLgy5mPOmyLAqHckCTewsxG70PYl5CcoNyEnDtbRrrBwT5izhjwvxT+VlCOcPa0d7w==
X-Received: by 2002:a05:6602:2c03:: with SMTP id w3mr18332842iov.39.1598560918114;
        Thu, 27 Aug 2020 13:41:58 -0700 (PDT)
Received: from rrangel920.bld.corp.google.com (h184-60-195-141.arvdco.broadband.dynamic.tds.net. [184.60.195.141])
        by smtp.gmail.com with ESMTPSA id u17sm1640328ilj.0.2020.08.27.13.41.57
        (version=TLS1_3 cipher=TLS_AES_256_GCM_SHA384 bits=256/256);
        Thu, 27 Aug 2020 13:41:57 -0700 (PDT)
From:   Raul E Rangel <rrangel@chromium.org>
To:     linux-input@vger.kernel.org
Cc:     dmitry.torokhov@gmail.com, Shirish.S@amd.com,
        Raul E Rangel <rrangel@chromium.org>,
        Andy Shevchenko <andy@infradead.org>,
        Dan Murphy <dmurphy@ti.com>,
        Darren Hart <dvhart@infradead.org>,
        Jacek Anaszewski <jacek.anaszewski@gmail.com>,
        "Lee, Chun-Yi" <jlee@suse.com>, Pavel Machek <pavel@ucw.cz>,
        Rajat Jain <rajatja@google.com>,
        Stephen Boyd <swboyd@chromium.org>,
        linux-kernel@vger.kernel.org, linux-leds@vger.kernel.org,
        platform-driver-x86@vger.kernel.org
Subject: [PATCH v2 1/2] Input: i8042 - Prevent intermixing i8042 commands
Date:   Thu, 27 Aug 2020 14:41:53 -0600
Message-Id: <20200827144112.v2.1.I6981f9a9f0c12e60f8038f3b574184f8ffc1b9b5@changeid>
X-Mailer: git-send-email 2.28.0.297.g1956fa8f8d-goog
MIME-Version: 1.0
Content-Transfer-Encoding: 8bit
Sender: linux-kernel-owner@vger.kernel.org
Precedence: bulk
List-ID: <linux-kernel.vger.kernel.org>
X-Mailing-List: linux-kernel@vger.kernel.org

The i8042_mutex must be held by writers of the AUX and KBD ports, as
well as users of i8042_command. There were a lot of users of
i8042_command that were not calling i8042_lock_chip/i8042_unlock_chip.
This resulted in i8042_commands being issues in between PS/2
transactions.

This change moves the mutex lock into i8042_command and removes the
burden of locking the mutex from the callers.

It is expected that the i8042_mutex is locked before calling
i8042_aux_write or i8042_kbd_write. This is currently done by the PS/2
layer via ps2_begin_command and ps2_end_command. Other modules
(serio_raw) do not currently lock the mutex, so there is still a
possibility for intermixed commands.

Link: https://lore.kernel.org/linux-input/CAHQZ30ANTeM-pgdYZ4AbgxsnevBJnJgKZ1Kg+Uy8oSXZUvz=og@mail.gmail.com
Signed-off-by: Raul E Rangel <rrangel@chromium.org>
---
Tested this on a device with only a PS/2 keyboard. I was able to do
1200+ suspend/resume cycles.

Also tested this on a device with a PS/2 keyboard and a PS/2 mouse.
I was able to do 250+ iterations with out problems.

Changes in v2:
- Fixed bad indent
- Added Link: tag
- Removed left over rc variable

 drivers/input/serio/i8042.c         | 29 ++++++++++++++---------------
 drivers/leds/leds-clevo-mail.c      |  9 ---------
 drivers/platform/x86/acer-wmi.c     |  2 --
 drivers/platform/x86/amilo-rfkill.c |  6 +-----
 include/linux/i8042.h               | 10 ----------
 5 files changed, 15 insertions(+), 41 deletions(-)

diff --git a/drivers/input/serio/i8042.c b/drivers/input/serio/i8042.c
index 0dddf273afd94..65ca6b47f41e8 100644
--- a/drivers/input/serio/i8042.c
+++ b/drivers/input/serio/i8042.c
@@ -137,8 +137,7 @@ static DEFINE_SPINLOCK(i8042_lock);
 
 /*
  * Writers to AUX and KBD ports as well as users issuing i8042_command
- * directly should acquire i8042_mutex (by means of calling
- * i8042_lock_chip() and i8042_unlock_ship() helpers) to ensure that
+ * directly should acquire i8042_mutex to ensure that
  * they do not disturb each other (unfortunately in many i8042
  * implementations write to one of the ports will immediately abort
  * command that is being processed by another port).
@@ -173,18 +172,6 @@ static irqreturn_t i8042_interrupt(int irq, void *dev_id);
 static bool (*i8042_platform_filter)(unsigned char data, unsigned char str,
 				     struct serio *serio);
 
-void i8042_lock_chip(void)
-{
-	mutex_lock(&i8042_mutex);
-}
-EXPORT_SYMBOL(i8042_lock_chip);
-
-void i8042_unlock_chip(void)
-{
-	mutex_unlock(&i8042_mutex);
-}
-EXPORT_SYMBOL(i8042_unlock_chip);
-
 int i8042_install_filter(bool (*filter)(unsigned char data, unsigned char str,
 					struct serio *serio))
 {
@@ -343,10 +330,14 @@ int i8042_command(unsigned char *param, int command)
 	unsigned long flags;
 	int retval;
 
+	mutex_lock(&i8042_mutex);
+
 	spin_lock_irqsave(&i8042_lock, flags);
 	retval = __i8042_command(param, command);
 	spin_unlock_irqrestore(&i8042_lock, flags);
 
+	mutex_unlock(&i8042_mutex);
+
 	return retval;
 }
 EXPORT_SYMBOL(i8042_command);
@@ -379,10 +370,18 @@ static int i8042_kbd_write(struct serio *port, unsigned char c)
 static int i8042_aux_write(struct serio *serio, unsigned char c)
 {
 	struct i8042_port *port = serio->port_data;
+	unsigned long flags;
+	int retval = 0;
+
+	spin_lock_irqsave(&i8042_lock, flags);
 
-	return i8042_command(&c, port->mux == -1 ?
+	retval = __i8042_command(&c, port->mux == -1 ?
 					I8042_CMD_AUX_SEND :
 					I8042_CMD_MUX_SEND + port->mux);
+
+	spin_unlock_irqrestore(&i8042_lock, flags);
+
+	return retval;
 }
 
 
diff --git a/drivers/leds/leds-clevo-mail.c b/drivers/leds/leds-clevo-mail.c
index f512e99b976b1..6c3d7e54f95cf 100644
--- a/drivers/leds/leds-clevo-mail.c
+++ b/drivers/leds/leds-clevo-mail.c
@@ -95,17 +95,12 @@ MODULE_DEVICE_TABLE(dmi, clevo_mail_led_dmi_table);
 static void clevo_mail_led_set(struct led_classdev *led_cdev,
 				enum led_brightness value)
 {
-	i8042_lock_chip();
-
 	if (value == LED_OFF)
 		i8042_command(NULL, CLEVO_MAIL_LED_OFF);
 	else if (value <= LED_HALF)
 		i8042_command(NULL, CLEVO_MAIL_LED_BLINK_0_5HZ);
 	else
 		i8042_command(NULL, CLEVO_MAIL_LED_BLINK_1HZ);
-
-	i8042_unlock_chip();
-
 }
 
 static int clevo_mail_led_blink(struct led_classdev *led_cdev,
@@ -114,8 +109,6 @@ static int clevo_mail_led_blink(struct led_classdev *led_cdev,
 {
 	int status = -EINVAL;
 
-	i8042_lock_chip();
-
 	if (*delay_on == 0 /* ms */ && *delay_off == 0 /* ms */) {
 		/* Special case: the leds subsystem requested us to
 		 * chose one user friendly blinking of the LED, and
@@ -142,8 +135,6 @@ static int clevo_mail_led_blink(struct led_classdev *led_cdev,
 		       *delay_on, *delay_off);
 	}
 
-	i8042_unlock_chip();
-
 	return status;
 }
 
diff --git a/drivers/platform/x86/acer-wmi.c b/drivers/platform/x86/acer-wmi.c
index 60c18f21588dd..6cb6f800503b2 100644
--- a/drivers/platform/x86/acer-wmi.c
+++ b/drivers/platform/x86/acer-wmi.c
@@ -1044,9 +1044,7 @@ static acpi_status WMID_set_u32(u32 value, u32 cap)
 			return AE_BAD_PARAMETER;
 		if (quirks->mailled == 1) {
 			param = value ? 0x92 : 0x93;
-			i8042_lock_chip();
 			i8042_command(&param, 0x1059);
-			i8042_unlock_chip();
 			return 0;
 		}
 		break;
diff --git a/drivers/platform/x86/amilo-rfkill.c b/drivers/platform/x86/amilo-rfkill.c
index 493e169c8f615..c981c6e07ff94 100644
--- a/drivers/platform/x86/amilo-rfkill.c
+++ b/drivers/platform/x86/amilo-rfkill.c
@@ -28,12 +28,8 @@
 static int amilo_a1655_rfkill_set_block(void *data, bool blocked)
 {
 	u8 param = blocked ? A1655_WIFI_OFF : A1655_WIFI_ON;
-	int rc;
 
-	i8042_lock_chip();
-	rc = i8042_command(&param, A1655_WIFI_COMMAND);
-	i8042_unlock_chip();
-	return rc;
+	return i8042_command(&param, A1655_WIFI_COMMAND);
 }
 
 static const struct rfkill_ops amilo_a1655_rfkill_ops = {
diff --git a/include/linux/i8042.h b/include/linux/i8042.h
index 0261e2fb36364..1c081081c161d 100644
--- a/include/linux/i8042.h
+++ b/include/linux/i8042.h
@@ -55,8 +55,6 @@ struct serio;
 
 #if defined(CONFIG_SERIO_I8042) || defined(CONFIG_SERIO_I8042_MODULE)
 
-void i8042_lock_chip(void);
-void i8042_unlock_chip(void);
 int i8042_command(unsigned char *param, int command);
 int i8042_install_filter(bool (*filter)(unsigned char data, unsigned char str,
 					struct serio *serio));
@@ -65,14 +63,6 @@ int i8042_remove_filter(bool (*filter)(unsigned char data, unsigned char str,
 
 #else
 
-static inline void i8042_lock_chip(void)
-{
-}
-
-static inline void i8042_unlock_chip(void)
-{
-}
-
 static inline int i8042_command(unsigned char *param, int command)
 {
 	return -ENODEV;
-- 
2.28.0.297.g1956fa8f8d-goog

