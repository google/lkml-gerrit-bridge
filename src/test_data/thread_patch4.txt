Return-Path: <SRS0=vZem=CJ=vger.kernel.org=linux-kselftest-owner@kernel.org>
X-Spam-Checker-Version: SpamAssassin 3.4.0 (2014-02-07) on
	aws-us-west-2-korg-lkml-1.web.codeaurora.org
X-Spam-Level: 
X-Spam-Status: No, score=-13.0 required=3.0 tests=BAYES_00,
	HEADER_FROM_DIFFERENT_DOMAINS,INCLUDES_PATCH,MAILING_LIST_MULTI,SIGNED_OFF_BY,
	SPF_HELO_NONE,SPF_PASS,URIBL_BLOCKED,USER_AGENT_GIT autolearn=unavailable
	autolearn_force=no version=3.4.0
Received: from mail.kernel.org (mail.kernel.org [198.145.29.99])
	by smtp.lore.kernel.org (Postfix) with ESMTP id A8785C433E2
	for <linux-kselftest@archiver.kernel.org>; Mon, 31 Aug 2020 11:15:38 +0000 (UTC)
Received: from vger.kernel.org (vger.kernel.org [23.128.96.18])
	by mail.kernel.org (Postfix) with ESMTP id 908132068E
	for <linux-kselftest@archiver.kernel.org>; Mon, 31 Aug 2020 11:15:38 +0000 (UTC)
Received: (majordomo@vger.kernel.org) by vger.kernel.org via listexpand
        id S1726292AbgHaLKr (ORCPT
        <rfc822;linux-kselftest@archiver.kernel.org>);
        Mon, 31 Aug 2020 07:10:47 -0400
Received: from foss.arm.com ([217.140.110.172]:56636 "EHLO foss.arm.com"
        rhost-flags-OK-OK-OK-OK) by vger.kernel.org with ESMTP
        id S1726523AbgHaLFe (ORCPT <rfc822;linux-kselftest@vger.kernel.org>);
        Mon, 31 Aug 2020 07:05:34 -0400
Received: from usa-sjc-imap-foss1.foss.arm.com (unknown [10.121.207.14])
        by usa-sjc-mx-foss1.foss.arm.com (Postfix) with ESMTP id 4129B12FC;
        Mon, 31 Aug 2020 04:05:29 -0700 (PDT)
Received: from e124572.local (unknown [172.31.20.19])
        by usa-sjc-imap-foss1.foss.arm.com (Postfix) with ESMTPSA id D10293F71F;
        Mon, 31 Aug 2020 04:05:26 -0700 (PDT)
From:   Boyan Karatotev <boyan.karatotev@arm.com>
To:     linux-arm-kernel@lists.infradead.org,
        linux-kselftest@vger.kernel.org, linux-kernel@vger.kernel.org
Cc:     vincenzo.frascino@arm.com, amit.kachhap@arm.com,
        boian4o1@gmail.com, Boyan Karatotev <boyan.karatotev@arm.com>,
        Shuah Khan <shuah@kernel.org>,
        Catalin Marinas <catalin.marinas@arm.com>,
        Will Deacon <will@kernel.org>
Subject: [PATCH v2 4/4] kselftests/arm64: add PAuth tests for single threaded consistency and key uniqueness
Date:   Mon, 31 Aug 2020 12:04:50 +0100
Message-Id: <20200831110450.30188-5-boyan.karatotev@arm.com>
X-Mailer: git-send-email 2.17.1
In-Reply-To: <20200831110450.30188-1-boyan.karatotev@arm.com>
References: <20200831110450.30188-1-boyan.karatotev@arm.com>
Sender: linux-kselftest-owner@vger.kernel.org
Precedence: bulk
List-ID: <linux-kselftest.vger.kernel.org>
X-Mailing-List: linux-kselftest@vger.kernel.org

PAuth adds 5 different keys that can be used to sign addresses.

Add a test that verifies that the kernel initializes them uniquely and
preserves them across context switches.

Cc: Shuah Khan <shuah@kernel.org>
Cc: Catalin Marinas <catalin.marinas@arm.com>
Cc: Will Deacon <will@kernel.org>
Reviewed-by: Vincenzo Frascino <Vincenzo.Frascino@arm.com>
Reviewed-by: Amit Daniel Kachhap <amit.kachhap@arm.com>
Signed-off-by: Boyan Karatotev <boyan.karatotev@arm.com>
---
 tools/testing/selftests/arm64/pauth/pac.c | 118 ++++++++++++++++++++++
 1 file changed, 118 insertions(+)

diff --git a/tools/testing/selftests/arm64/pauth/pac.c b/tools/testing/selftests/arm64/pauth/pac.c
index 1b9e3acfeb61..7d0ba2ec2e9e 100644
--- a/tools/testing/selftests/arm64/pauth/pac.c
+++ b/tools/testing/selftests/arm64/pauth/pac.c
@@ -1,10 +1,13 @@
 // SPDX-License-Identifier: GPL-2.0
 // Copyright (C) 2020 ARM Limited
 
+#define _GNU_SOURCE
+
 #include <sys/auxv.h>
 #include <sys/types.h>
 #include <sys/wait.h>
 #include <signal.h>
+#include <sched.h>
 
 #include "../../kselftest_harness.h"
 #include "helper.h"
@@ -21,6 +24,7 @@
  * The VA space size is 48 bits. Bigger is opt-in.
  */
 #define PAC_MASK (~0xff80ffffffffffff)
+#define ARBITRARY_VALUE (0x1234)
 #define ASSERT_PAUTH_ENABLED() \
 do { \
 	unsigned long hwcaps = getauxval(AT_HWCAP); \
@@ -66,13 +70,36 @@ int are_same(struct signatures *old, struct signatures *new, int nkeys)
 	return res;
 }
 
+int are_unique(struct signatures *sign, int nkeys)
+{
+	size_t vals[nkeys];
+
+	vals[0] = sign->keyia & PAC_MASK;
+	vals[1] = sign->keyib & PAC_MASK;
+	vals[2] = sign->keyda & PAC_MASK;
+	vals[3] = sign->keydb & PAC_MASK;
+
+	if (nkeys >= 4)
+		vals[4] = sign->keyg & PAC_MASK;
+
+	for (int i = 0; i < nkeys - 1; i++) {
+		for (int j = i + 1; j < nkeys; j++) {
+			if (vals[i] == vals[j])
+				return 0;
+		}
+	}
+	return 1;
+}
+
 int exec_sign_all(struct signatures *signed_vals, size_t val)
 {
 	int new_stdin[2];
 	int new_stdout[2];
 	int status;
+	int i;
 	ssize_t ret;
 	pid_t pid;
+	cpu_set_t mask;
 
 	ret = pipe(new_stdin);
 	if (ret == -1) {
@@ -86,6 +113,20 @@ int exec_sign_all(struct signatures *signed_vals, size_t val)
 		return -1;
 	}
 
+	/*
+	 * pin this process and all its children to a single CPU, so it can also
+	 * guarantee a context switch with its child
+	 */
+	sched_getaffinity(0, sizeof(mask), &mask);
+
+	for (i = 0; i < sizeof(cpu_set_t); i++)
+		if (CPU_ISSET(i, &mask))
+			break;
+
+	CPU_ZERO(&mask);
+	CPU_SET(i, &mask);
+	sched_setaffinity(0, sizeof(mask), &mask);
+
 	pid = fork();
 	// child
 	if (pid == 0) {
@@ -192,6 +233,40 @@ TEST(pac_instructions_not_nop_generic)
 	ASSERT_NE(0, keyg)  TH_LOG("keyg instructions did nothing");
 }
 
+TEST(single_thread_unique_keys)
+{
+	int unique = 0;
+	int nkeys = NKEYS;
+	struct signatures signed_vals;
+	unsigned long hwcaps = getauxval(AT_HWCAP);
+
+	/* generic and data key instructions are not in NOP space. This prevents a SIGILL */
+	ASSERT_NE(0, hwcaps & HWCAP_PACA) TH_LOG("PAUTH not enabled");
+	if (!(hwcaps & HWCAP_PACG)) {
+		TH_LOG("WARNING: Generic PAUTH not enabled. Skipping generic key checks");
+		nkeys = NKEYS - 1;
+	}
+
+	/*
+	 * In Linux the PAC field can be up to 7 bits wide. Even if keys are
+	 * unique, there is about 5% chance for PACs to collide with different
+	 * addresses. This chance rapidly increases with fewer bits allocated
+	 * for the PAC (e.g. wider address). A comparison of the keys directly
+	 * will be more reliable.
+	 * All signed values need to be unique at least once out of n attempts
+	 * to be certain that the keys are unique
+	 */
+	for (int i = 0; i < PAC_COLLISION_ATTEMPTS; i++) {
+		if (nkeys == NKEYS)
+			sign_all(&signed_vals, i);
+		else
+			sign_specific(&signed_vals, i);
+		unique |= are_unique(&signed_vals, nkeys);
+	}
+
+	ASSERT_EQ(1, unique) TH_LOG("keys clashed every time");
+}
+
 /*
  * fork() does not change keys. Only exec() does so call a worker program.
  * Its only job is to sign a value and report back the resutls
@@ -227,4 +302,47 @@ TEST(exec_unique_keys)
 	ASSERT_EQ(1, different) TH_LOG("exec() did not change keys");
 }
 
+TEST(context_switch_keep_keys)
+{
+	int ret;
+	struct signatures trash;
+	struct signatures before;
+	struct signatures after;
+
+	ASSERT_PAUTH_ENABLED();
+
+	sign_specific(&before, ARBITRARY_VALUE);
+
+	/* will context switch with a process with different keys at least once */
+	ret = exec_sign_all(&trash, ARBITRARY_VALUE);
+	ASSERT_EQ(0, ret) TH_LOG("failed to run worker");
+
+	sign_specific(&after, ARBITRARY_VALUE);
+
+	ASSERT_EQ(before.keyia, after.keyia) TH_LOG("keyia changed after context switching");
+	ASSERT_EQ(before.keyib, after.keyib) TH_LOG("keyib changed after context switching");
+	ASSERT_EQ(before.keyda, after.keyda) TH_LOG("keyda changed after context switching");
+	ASSERT_EQ(before.keydb, after.keydb) TH_LOG("keydb changed after context switching");
+}
+
+TEST(context_switch_keep_keys_generic)
+{
+	int ret;
+	struct signatures trash;
+	size_t before;
+	size_t after;
+
+	ASSERT_GENERIC_PAUTH_ENABLED();
+
+	before = keyg_sign(ARBITRARY_VALUE);
+
+	/* will context switch with a process with different keys at least once */
+	ret = exec_sign_all(&trash, ARBITRARY_VALUE);
+	ASSERT_EQ(0, ret) TH_LOG("failed to run worker");
+
+	after = keyg_sign(ARBITRARY_VALUE);
+
+	ASSERT_EQ(before, after) TH_LOG("keyg changed after context switching");
+}
+
 TEST_HARNESS_MAIN
-- 
2.17.1

