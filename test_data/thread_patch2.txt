Return-Path: <SRS0=vZem=CJ=vger.kernel.org=linux-kselftest-owner@kernel.org>
X-Spam-Checker-Version: SpamAssassin 3.4.0 (2014-02-07) on
	aws-us-west-2-korg-lkml-1.web.codeaurora.org
X-Spam-Level: 
X-Spam-Status: No, score=-13.0 required=3.0 tests=BAYES_00,
	HEADER_FROM_DIFFERENT_DOMAINS,INCLUDES_PATCH,MAILING_LIST_MULTI,SIGNED_OFF_BY,
	SPF_HELO_NONE,SPF_PASS,URIBL_BLOCKED,USER_AGENT_GIT autolearn=unavailable
	autolearn_force=no version=3.4.0
Received: from mail.kernel.org (mail.kernel.org [198.145.29.99])
	by smtp.lore.kernel.org (Postfix) with ESMTP id 183F5C433E2
	for <linux-kselftest@archiver.kernel.org>; Mon, 31 Aug 2020 11:16:10 +0000 (UTC)
Received: from vger.kernel.org (vger.kernel.org [23.128.96.18])
	by mail.kernel.org (Postfix) with ESMTP id F1AA2208CA
	for <linux-kselftest@archiver.kernel.org>; Mon, 31 Aug 2020 11:16:09 +0000 (UTC)
Received: (majordomo@vger.kernel.org) by vger.kernel.org via listexpand
        id S1726167AbgHaLPM (ORCPT
        <rfc822;linux-kselftest@archiver.kernel.org>);
        Mon, 31 Aug 2020 07:15:12 -0400
Received: from foss.arm.com ([217.140.110.172]:56612 "EHLO foss.arm.com"
        rhost-flags-OK-OK-OK-OK) by vger.kernel.org with ESMTP
        id S1726521AbgHaLFY (ORCPT <rfc822;linux-kselftest@vger.kernel.org>);
        Mon, 31 Aug 2020 07:05:24 -0400
Received: from usa-sjc-imap-foss1.foss.arm.com (unknown [10.121.207.14])
        by usa-sjc-mx-foss1.foss.arm.com (Postfix) with ESMTP id 9C1AD11B3;
        Mon, 31 Aug 2020 04:05:23 -0700 (PDT)
Received: from e124572.local (unknown [172.31.20.19])
        by usa-sjc-imap-foss1.foss.arm.com (Postfix) with ESMTPSA id 412293F71F;
        Mon, 31 Aug 2020 04:05:21 -0700 (PDT)
From:   Boyan Karatotev <boyan.karatotev@arm.com>
To:     linux-arm-kernel@lists.infradead.org,
        linux-kselftest@vger.kernel.org, linux-kernel@vger.kernel.org
Cc:     vincenzo.frascino@arm.com, amit.kachhap@arm.com,
        boian4o1@gmail.com, Boyan Karatotev <boyan.karatotev@arm.com>,
        Shuah Khan <shuah@kernel.org>,
        Catalin Marinas <catalin.marinas@arm.com>,
        Will Deacon <will@kernel.org>
Subject: [PATCH v2 2/4] kselftests/arm64: add nop checks for PAuth tests
Date:   Mon, 31 Aug 2020 12:04:48 +0100
Message-Id: <20200831110450.30188-3-boyan.karatotev@arm.com>
X-Mailer: git-send-email 2.17.1
In-Reply-To: <20200831110450.30188-1-boyan.karatotev@arm.com>
References: <20200831110450.30188-1-boyan.karatotev@arm.com>
Sender: linux-kselftest-owner@vger.kernel.org
Precedence: bulk
List-ID: <linux-kselftest.vger.kernel.org>
X-Mailing-List: linux-kselftest@vger.kernel.org

PAuth adds sign/verify controls to enable and disable groups of
instructions in hardware for compatibility with libraries that do not
implement PAuth. The kernel always enables them if it detects PAuth.

Add a test that checks that each group of instructions is enabled, if the
kernel reports PAuth as detected.

Note: For groups, for the purpose of this patch, we intend instructions
that use a certain key.

Cc: Shuah Khan <shuah@kernel.org>
Cc: Catalin Marinas <catalin.marinas@arm.com>
Cc: Will Deacon <will@kernel.org>
Reviewed-by: Vincenzo Frascino <Vincenzo.Frascino@arm.com>
Reviewed-by: Amit Daniel Kachhap <amit.kachhap@arm.com>
Signed-off-by: Boyan Karatotev <boyan.karatotev@arm.com>
---
 .../testing/selftests/arm64/pauth/.gitignore  |  1 +
 tools/testing/selftests/arm64/pauth/Makefile  |  7 ++-
 tools/testing/selftests/arm64/pauth/helper.c  | 40 +++++++++++++++
 tools/testing/selftests/arm64/pauth/helper.h  | 10 ++++
 tools/testing/selftests/arm64/pauth/pac.c     | 51 +++++++++++++++++++
 5 files changed, 107 insertions(+), 2 deletions(-)
 create mode 100644 tools/testing/selftests/arm64/pauth/helper.c

diff --git a/tools/testing/selftests/arm64/pauth/.gitignore b/tools/testing/selftests/arm64/pauth/.gitignore
index b557c916720a..155137d92722 100644
--- a/tools/testing/selftests/arm64/pauth/.gitignore
+++ b/tools/testing/selftests/arm64/pauth/.gitignore
@@ -1 +1,2 @@
+exec_target
 pac
diff --git a/tools/testing/selftests/arm64/pauth/Makefile b/tools/testing/selftests/arm64/pauth/Makefile
index 01d35aaa610a..5c0dd129562f 100644
--- a/tools/testing/selftests/arm64/pauth/Makefile
+++ b/tools/testing/selftests/arm64/pauth/Makefile
@@ -12,7 +12,7 @@ pauth_cc_support := $(shell if ($(CC) $(CFLAGS) -march=armv8.3-a -E -x c /dev/nu
 
 ifeq ($(pauth_cc_support),1)
 TEST_GEN_PROGS := pac
-TEST_GEN_FILES := pac_corruptor.o
+TEST_GEN_FILES := pac_corruptor.o helper.o
 endif
 
 include ../../lib.mk
@@ -23,10 +23,13 @@ ifeq ($(pauth_cc_support),1)
 $(OUTPUT)/pac_corruptor.o: pac_corruptor.S
 	$(CC) -c $^ -o $@ $(CFLAGS) -march=armv8.3-a
 
+$(OUTPUT)/helper.o: helper.c
+	$(CC) -c $^ -o $@ $(CFLAGS) -march=armv8.3-a
+
 # when -mbranch-protection is enabled and the target architecture is ARMv8.3 or
 # greater, gcc emits pac* instructions which are not in HINT NOP space,
 # preventing the tests from occurring at all. Compile for ARMv8.2 so tests can
 # run on earlier targets and print a meaningful error messages
-$(OUTPUT)/pac: pac.c $(OUTPUT)/pac_corruptor.o
+$(OUTPUT)/pac: pac.c $(OUTPUT)/pac_corruptor.o $(OUTPUT)/helper.o
 	$(CC) $^ -o $@ $(CFLAGS) -march=armv8.2-a
 endif
diff --git a/tools/testing/selftests/arm64/pauth/helper.c b/tools/testing/selftests/arm64/pauth/helper.c
new file mode 100644
index 000000000000..a5d205fffe6f
--- /dev/null
+++ b/tools/testing/selftests/arm64/pauth/helper.c
@@ -0,0 +1,40 @@
+// SPDX-License-Identifier: GPL-2.0
+// Copyright (C) 2020 ARM Limited
+
+#include "helper.h"
+
+
+size_t keyia_sign(size_t ptr)
+{
+	asm volatile("paciza %0" : "+r" (ptr));
+	return ptr;
+}
+
+size_t keyib_sign(size_t ptr)
+{
+	asm volatile("pacizb %0" : "+r" (ptr));
+	return ptr;
+}
+
+size_t keyda_sign(size_t ptr)
+{
+	asm volatile("pacdza %0" : "+r" (ptr));
+	return ptr;
+}
+
+size_t keydb_sign(size_t ptr)
+{
+	asm volatile("pacdzb %0" : "+r" (ptr));
+	return ptr;
+}
+
+size_t keyg_sign(size_t ptr)
+{
+	/* output is encoded in the upper 32 bits */
+	size_t dest = 0;
+	size_t modifier = 0;
+
+	asm volatile("pacga %0, %1, %2" : "=r" (dest) : "r" (ptr), "r" (modifier));
+
+	return dest;
+}
diff --git a/tools/testing/selftests/arm64/pauth/helper.h b/tools/testing/selftests/arm64/pauth/helper.h
index 3e0a2a404bf4..e2ed910c9863 100644
--- a/tools/testing/selftests/arm64/pauth/helper.h
+++ b/tools/testing/selftests/arm64/pauth/helper.h
@@ -4,6 +4,16 @@
 #ifndef _HELPER_H_
 #define _HELPER_H_
 
+#include <stdlib.h>
+
+
 void pac_corruptor(void);
 
+/* PAuth sign a value with key ia and modifier value 0 */
+size_t keyia_sign(size_t val);
+size_t keyib_sign(size_t val);
+size_t keyda_sign(size_t val);
+size_t keydb_sign(size_t val);
+size_t keyg_sign(size_t val);
+
 #endif
diff --git a/tools/testing/selftests/arm64/pauth/pac.c b/tools/testing/selftests/arm64/pauth/pac.c
index 7fc02b02dede..035fdd6aae9b 100644
--- a/tools/testing/selftests/arm64/pauth/pac.c
+++ b/tools/testing/selftests/arm64/pauth/pac.c
@@ -12,12 +12,25 @@
  * future version of the arm architecture
  */
 
+#define PAC_COLLISION_ATTEMPTS 10
+/*
+ * The kernel sets TBID by default. So bits 55 and above should remain
+ * untouched no matter what.
+ * The VA space size is 48 bits. Bigger is opt-in.
+ */
+#define PAC_MASK (~0xff80ffffffffffff)
 #define ASSERT_PAUTH_ENABLED() \
 do { \
 	unsigned long hwcaps = getauxval(AT_HWCAP); \
 	/* data key instructions are not in NOP space. This prevents a SIGILL */ \
 	ASSERT_NE(0, hwcaps & HWCAP_PACA) TH_LOG("PAUTH not enabled"); \
 } while (0)
+#define ASSERT_GENERIC_PAUTH_ENABLED() \
+do { \
+	unsigned long hwcaps = getauxval(AT_HWCAP); \
+	/* generic key instructions are not in NOP space. This prevents a SIGILL */ \
+	ASSERT_NE(0, hwcaps & HWCAP_PACG) TH_LOG("Generic PAUTH not enabled"); \
+} while (0)
 
 
 /* check that a corrupted PAC results in SIGSEGV */
@@ -28,4 +41,42 @@ TEST_SIGNAL(corrupt_pac, SIGSEGV)
 	pac_corruptor();
 }
 
+/*
+ * There are no separate pac* and aut* controls so checking only the pac*
+ * instructions is sufficient
+ */
+TEST(pac_instructions_not_nop)
+{
+	size_t keyia = 0;
+	size_t keyib = 0;
+	size_t keyda = 0;
+	size_t keydb = 0;
+
+	ASSERT_PAUTH_ENABLED();
+
+	for (int i = 0; i < PAC_COLLISION_ATTEMPTS; i++) {
+		keyia |= keyia_sign(i) & PAC_MASK;
+		keyib |= keyib_sign(i) & PAC_MASK;
+		keyda |= keyda_sign(i) & PAC_MASK;
+		keydb |= keydb_sign(i) & PAC_MASK;
+	}
+
+	ASSERT_NE(0, keyia) TH_LOG("keyia instructions did nothing");
+	ASSERT_NE(0, keyib) TH_LOG("keyib instructions did nothing");
+	ASSERT_NE(0, keyda) TH_LOG("keyda instructions did nothing");
+	ASSERT_NE(0, keydb) TH_LOG("keydb instructions did nothing");
+}
+
+TEST(pac_instructions_not_nop_generic)
+{
+	size_t keyg = 0;
+
+	ASSERT_GENERIC_PAUTH_ENABLED();
+
+	for (int i = 0; i < PAC_COLLISION_ATTEMPTS; i++)
+		keyg |= keyg_sign(i) & PAC_MASK;
+
+	ASSERT_NE(0, keyg)  TH_LOG("keyg instructions did nothing");
+}
+
 TEST_HARNESS_MAIN
-- 
2.17.1

