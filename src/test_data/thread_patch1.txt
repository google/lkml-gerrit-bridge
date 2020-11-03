Return-Path: <SRS0=vZem=CJ=vger.kernel.org=linux-kselftest-owner@kernel.org>
X-Spam-Checker-Version: SpamAssassin 3.4.0 (2014-02-07) on
	aws-us-west-2-korg-lkml-1.web.codeaurora.org
X-Spam-Level: 
X-Spam-Status: No, score=-13.0 required=3.0 tests=BAYES_00,
	HEADER_FROM_DIFFERENT_DOMAINS,INCLUDES_PATCH,MAILING_LIST_MULTI,SIGNED_OFF_BY,
	SPF_HELO_NONE,SPF_PASS,URIBL_BLOCKED,USER_AGENT_GIT autolearn=unavailable
	autolearn_force=no version=3.4.0
Received: from mail.kernel.org (mail.kernel.org [198.145.29.99])
	by smtp.lore.kernel.org (Postfix) with ESMTP id 23F15C433E2
	for <linux-kselftest@archiver.kernel.org>; Mon, 31 Aug 2020 11:15:53 +0000 (UTC)
Received: from vger.kernel.org (vger.kernel.org [23.128.96.18])
	by mail.kernel.org (Postfix) with ESMTP id 0335F2098B
	for <linux-kselftest@archiver.kernel.org>; Mon, 31 Aug 2020 11:15:53 +0000 (UTC)
Received: (majordomo@vger.kernel.org) by vger.kernel.org via listexpand
        id S1726106AbgHaLPi (ORCPT
        <rfc822;linux-kselftest@archiver.kernel.org>);
        Mon, 31 Aug 2020 07:15:38 -0400
Received: from foss.arm.com ([217.140.110.172]:56602 "EHLO foss.arm.com"
        rhost-flags-OK-OK-OK-OK) by vger.kernel.org with ESMTP
        id S1726503AbgHaLFV (ORCPT <rfc822;linux-kselftest@vger.kernel.org>);
        Mon, 31 Aug 2020 07:05:21 -0400
Received: from usa-sjc-imap-foss1.foss.arm.com (unknown [10.121.207.14])
        by usa-sjc-mx-foss1.foss.arm.com (Postfix) with ESMTP id D4748101E;
        Mon, 31 Aug 2020 04:05:20 -0700 (PDT)
Received: from e124572.local (unknown [172.31.20.19])
        by usa-sjc-imap-foss1.foss.arm.com (Postfix) with ESMTPSA id 2FA233F71F;
        Mon, 31 Aug 2020 04:05:17 -0700 (PDT)
From:   Boyan Karatotev <boyan.karatotev@arm.com>
To:     linux-arm-kernel@lists.infradead.org,
        linux-kselftest@vger.kernel.org, linux-kernel@vger.kernel.org
Cc:     vincenzo.frascino@arm.com, amit.kachhap@arm.com,
        boian4o1@gmail.com, Boyan Karatotev <boyan.karatotev@arm.com>,
        Shuah Khan <shuah@kernel.org>,
        Catalin Marinas <catalin.marinas@arm.com>,
        Will Deacon <will@kernel.org>
Subject: [PATCH v2 1/4] kselftests/arm64: add a basic Pointer Authentication test
Date:   Mon, 31 Aug 2020 12:04:47 +0100
Message-Id: <20200831110450.30188-2-boyan.karatotev@arm.com>
X-Mailer: git-send-email 2.17.1
In-Reply-To: <20200831110450.30188-1-boyan.karatotev@arm.com>
References: <20200831110450.30188-1-boyan.karatotev@arm.com>
Sender: linux-kselftest-owner@vger.kernel.org
Precedence: bulk
List-ID: <linux-kselftest.vger.kernel.org>
X-Mailing-List: linux-kselftest@vger.kernel.org

PAuth signs and verifies return addresses on the stack. It does so by
inserting a Pointer Authentication code (PAC) into some of the unused top
bits of an address. This is achieved by adding paciasp/autiasp instructions
at the beginning and end of a function.

This feature is partially backwards compatible with earlier versions of the
ARM architecture. To coerce the compiler into emitting fully backwards
compatible code the main file is compiled to target an earlier ARM version.
This allows the tests to check for the feature and print meaningful error
messages instead of crashing.

Add a test to verify that corrupting the return address results in a
SIGSEGV on return.

Cc: Shuah Khan <shuah@kernel.org>
Cc: Catalin Marinas <catalin.marinas@arm.com>
Cc: Will Deacon <will@kernel.org>
Reviewed-by: Vincenzo Frascino <Vincenzo.Frascino@arm.com>
Reviewed-by: Amit Daniel Kachhap <amit.kachhap@arm.com>
Signed-off-by: Boyan Karatotev <boyan.karatotev@arm.com>
---
 tools/testing/selftests/arm64/Makefile        |  2 +-
 .../testing/selftests/arm64/pauth/.gitignore  |  1 +
 tools/testing/selftests/arm64/pauth/Makefile  | 32 +++++++++++++++++
 tools/testing/selftests/arm64/pauth/helper.h  |  9 +++++
 tools/testing/selftests/arm64/pauth/pac.c     | 31 ++++++++++++++++
 .../selftests/arm64/pauth/pac_corruptor.S     | 35 +++++++++++++++++++
 6 files changed, 109 insertions(+), 1 deletion(-)
 create mode 100644 tools/testing/selftests/arm64/pauth/.gitignore
 create mode 100644 tools/testing/selftests/arm64/pauth/Makefile
 create mode 100644 tools/testing/selftests/arm64/pauth/helper.h
 create mode 100644 tools/testing/selftests/arm64/pauth/pac.c
 create mode 100644 tools/testing/selftests/arm64/pauth/pac_corruptor.S

diff --git a/tools/testing/selftests/arm64/Makefile b/tools/testing/selftests/arm64/Makefile
index 93b567d23c8b..525506fd97b9 100644
--- a/tools/testing/selftests/arm64/Makefile
+++ b/tools/testing/selftests/arm64/Makefile
@@ -4,7 +4,7 @@
 ARCH ?= $(shell uname -m 2>/dev/null || echo not)

 ifneq (,$(filter $(ARCH),aarch64 arm64))
-ARM64_SUBTARGETS ?= tags signal
+ARM64_SUBTARGETS ?= tags signal pauth
 else
 ARM64_SUBTARGETS :=
 endif
diff --git a/tools/testing/selftests/arm64/pauth/.gitignore b/tools/testing/selftests/arm64/pauth/.gitignore
new file mode 100644
index 000000000000..b557c916720a
--- /dev/null
+++ b/tools/testing/selftests/arm64/pauth/.gitignore
@@ -0,0 +1 @@
+pac
diff --git a/tools/testing/selftests/arm64/pauth/Makefile b/tools/testing/selftests/arm64/pauth/Makefile
new file mode 100644
index 000000000000..01d35aaa610a
--- /dev/null
+++ b/tools/testing/selftests/arm64/pauth/Makefile
@@ -0,0 +1,32 @@
+# SPDX-License-Identifier: GPL-2.0
+# Copyright (C) 2020 ARM Limited
+
+# preserve CC value from top level Makefile
+ifeq ($(CC),cc)
+CC := $(CROSS_COMPILE)gcc
+endif
+
+CFLAGS += -mbranch-protection=pac-ret
+# check if the compiler supports ARMv8.3 and branch protection with PAuth
+pauth_cc_support := $(shell if ($(CC) $(CFLAGS) -march=armv8.3-a -E -x c /dev/null -o /dev/null 2>&1) then echo "1"; fi)
+
+ifeq ($(pauth_cc_support),1)
+TEST_GEN_PROGS := pac
+TEST_GEN_FILES := pac_corruptor.o
+endif
+
+include ../../lib.mk
+
+ifeq ($(pauth_cc_support),1)
+# pac* and aut* instructions are not available on architectures berfore
+# ARMv8.3. Therefore target ARMv8.3 wherever they are used directly
+$(OUTPUT)/pac_corruptor.o: pac_corruptor.S
+	$(CC) -c $^ -o $@ $(CFLAGS) -march=armv8.3-a
+
+# when -mbranch-protection is enabled and the target architecture is ARMv8.3 or
+# greater, gcc emits pac* instructions which are not in HINT NOP space,
+# preventing the tests from occurring at all. Compile for ARMv8.2 so tests can
+# run on earlier targets and print a meaningful error messages
+$(OUTPUT)/pac: pac.c $(OUTPUT)/pac_corruptor.o
+	$(CC) $^ -o $@ $(CFLAGS) -march=armv8.2-a
+endif
diff --git a/tools/testing/selftests/arm64/pauth/helper.h b/tools/testing/selftests/arm64/pauth/helper.h
new file mode 100644
index 000000000000..3e0a2a404bf4
--- /dev/null
+++ b/tools/testing/selftests/arm64/pauth/helper.h
@@ -0,0 +1,9 @@
+/* SPDX-License-Identifier: GPL-2.0 */
+/* Copyright (C) 2020 ARM Limited */
+
+#ifndef _HELPER_H_
+#define _HELPER_H_
+
+void pac_corruptor(void);
+
+#endif
diff --git a/tools/testing/selftests/arm64/pauth/pac.c b/tools/testing/selftests/arm64/pauth/pac.c
new file mode 100644
index 000000000000..7fc02b02dede
--- /dev/null
+++ b/tools/testing/selftests/arm64/pauth/pac.c
@@ -0,0 +1,31 @@
+// SPDX-License-Identifier: GPL-2.0
+// Copyright (C) 2020 ARM Limited
+
+#include <sys/auxv.h>
+#include <signal.h>
+
+#include "../../kselftest_harness.h"
+#include "helper.h"
+
+/*
+ * Tests are ARMv8.3 compliant. They make no provisions for features present in
+ * future version of the arm architecture
+ */
+
+#define ASSERT_PAUTH_ENABLED() \
+do { \
+	unsigned long hwcaps = getauxval(AT_HWCAP); \
+	/* data key instructions are not in NOP space. This prevents a SIGILL */ \
+	ASSERT_NE(0, hwcaps & HWCAP_PACA) TH_LOG("PAUTH not enabled"); \
+} while (0)
+
+
+/* check that a corrupted PAC results in SIGSEGV */
+TEST_SIGNAL(corrupt_pac, SIGSEGV)
+{
+	ASSERT_PAUTH_ENABLED();
+
+	pac_corruptor();
+}
+
+TEST_HARNESS_MAIN
diff --git a/tools/testing/selftests/arm64/pauth/pac_corruptor.S b/tools/testing/selftests/arm64/pauth/pac_corruptor.S
new file mode 100644
index 000000000000..0780052ac3b5
--- /dev/null
+++ b/tools/testing/selftests/arm64/pauth/pac_corruptor.S
@@ -0,0 +1,35 @@
+/* SPDX-License-Identifier: GPL-2.0 */
+/* Copyright (C) 2020 ARM Limited */
+
+.global pac_corruptor
+
+.text
+/*
+ * Corrupting a single bit of the PAC ensures the authentication will fail.  It
+ * also guarantees no possible collision. TCR_EL1.TBI0 is set by default so no
+ * top byte PAC is tested
+ */
+ pac_corruptor:
+	paciasp
+
+	/* make stack frame */
+	sub sp, sp, #16
+	stp x29, lr, [sp]
+	mov x29, sp
+
+	/* prepare mask for bit to be corrupted (bit 54) */
+	mov x1, xzr
+	add x1, x1, #1
+	lsl x1, x1, #54
+
+	/* get saved lr, corrupt selected bit, put it back */
+	ldr x0, [sp, #8]
+	eor x0, x0, x1
+	str x0, [sp, #8]
+
+	/* remove stack frame */
+	ldp x29, lr, [sp]
+	add sp, sp, #16
+
+	autiasp
+	ret
--
2.17.1

