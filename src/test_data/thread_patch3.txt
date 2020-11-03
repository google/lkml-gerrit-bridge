Return-Path: <SRS0=vZem=CJ=vger.kernel.org=linux-kselftest-owner@kernel.org>
X-Spam-Checker-Version: SpamAssassin 3.4.0 (2014-02-07) on
	aws-us-west-2-korg-lkml-1.web.codeaurora.org
X-Spam-Level: 
X-Spam-Status: No, score=-13.0 required=3.0 tests=BAYES_00,
	HEADER_FROM_DIFFERENT_DOMAINS,INCLUDES_PATCH,MAILING_LIST_MULTI,SIGNED_OFF_BY,
	SPF_HELO_NONE,SPF_PASS,USER_AGENT_GIT autolearn=unavailable
	autolearn_force=no version=3.4.0
Received: from mail.kernel.org (mail.kernel.org [198.145.29.99])
	by smtp.lore.kernel.org (Postfix) with ESMTP id 538D4C433E6
	for <linux-kselftest@archiver.kernel.org>; Mon, 31 Aug 2020 11:13:55 +0000 (UTC)
Received: from vger.kernel.org (vger.kernel.org [23.128.96.18])
	by mail.kernel.org (Postfix) with ESMTP id 338C6214D8
	for <linux-kselftest@archiver.kernel.org>; Mon, 31 Aug 2020 11:13:55 +0000 (UTC)
Received: (majordomo@vger.kernel.org) by vger.kernel.org via listexpand
        id S1726572AbgHaLKE (ORCPT
        <rfc822;linux-kselftest@archiver.kernel.org>);
        Mon, 31 Aug 2020 07:10:04 -0400
Received: from foss.arm.com ([217.140.110.172]:56620 "EHLO foss.arm.com"
        rhost-flags-OK-OK-OK-OK) by vger.kernel.org with ESMTP
        id S1726522AbgHaLF1 (ORCPT <rfc822;linux-kselftest@vger.kernel.org>);
        Mon, 31 Aug 2020 07:05:27 -0400
Received: from usa-sjc-imap-foss1.foss.arm.com (unknown [10.121.207.14])
        by usa-sjc-mx-foss1.foss.arm.com (Postfix) with ESMTP id 8C62B11D4;
        Mon, 31 Aug 2020 04:05:26 -0700 (PDT)
Received: from e124572.local (unknown [172.31.20.19])
        by usa-sjc-imap-foss1.foss.arm.com (Postfix) with ESMTPSA id 07AE53F71F;
        Mon, 31 Aug 2020 04:05:23 -0700 (PDT)
From:   Boyan Karatotev <boyan.karatotev@arm.com>
To:     linux-arm-kernel@lists.infradead.org,
        linux-kselftest@vger.kernel.org, linux-kernel@vger.kernel.org
Cc:     vincenzo.frascino@arm.com, amit.kachhap@arm.com,
        boian4o1@gmail.com, Boyan Karatotev <boyan.karatotev@arm.com>,
        Shuah Khan <shuah@kernel.org>,
        Catalin Marinas <catalin.marinas@arm.com>,
        Will Deacon <will@kernel.org>
Subject: [PATCH v2 3/4] kselftests/arm64: add PAuth test for whether exec() changes keys
Date:   Mon, 31 Aug 2020 12:04:49 +0100
Message-Id: <20200831110450.30188-4-boyan.karatotev@arm.com>
X-Mailer: git-send-email 2.17.1
In-Reply-To: <20200831110450.30188-1-boyan.karatotev@arm.com>
References: <20200831110450.30188-1-boyan.karatotev@arm.com>
Sender: linux-kselftest-owner@vger.kernel.org
Precedence: bulk
List-ID: <linux-kselftest.vger.kernel.org>
X-Mailing-List: linux-kselftest@vger.kernel.org

Kernel documentation states that it will change PAuth keys on exec() calls.

Verify that all keys are correctly switched to new ones.

Cc: Shuah Khan <shuah@kernel.org>
Cc: Catalin Marinas <catalin.marinas@arm.com>
Cc: Will Deacon <will@kernel.org>
Reviewed-by: Vincenzo Frascino <Vincenzo.Frascino@arm.com>
Reviewed-by: Amit Daniel Kachhap <amit.kachhap@arm.com>
Signed-off-by: Boyan Karatotev <boyan.karatotev@arm.com>
---
 tools/testing/selftests/arm64/pauth/Makefile  |   4 +
 .../selftests/arm64/pauth/exec_target.c       |  35 +++++
 tools/testing/selftests/arm64/pauth/helper.h  |  10 ++
 tools/testing/selftests/arm64/pauth/pac.c     | 148 ++++++++++++++++++
 4 files changed, 197 insertions(+)
 create mode 100644 tools/testing/selftests/arm64/pauth/exec_target.c

diff --git a/tools/testing/selftests/arm64/pauth/Makefile b/tools/testing/selftests/arm64/pauth/Makefile
index 5c0dd129562f..72e290b0b10c 100644
--- a/tools/testing/selftests/arm64/pauth/Makefile
+++ b/tools/testing/selftests/arm64/pauth/Makefile
@@ -13,6 +13,7 @@ pauth_cc_support := $(shell if ($(CC) $(CFLAGS) -march=armv8.3-a -E -x c /dev/nu
 ifeq ($(pauth_cc_support),1)
 TEST_GEN_PROGS := pac
 TEST_GEN_FILES := pac_corruptor.o helper.o
+TEST_GEN_PROGS_EXTENDED := exec_target
 endif
 
 include ../../lib.mk
@@ -30,6 +31,9 @@ $(OUTPUT)/helper.o: helper.c
 # greater, gcc emits pac* instructions which are not in HINT NOP space,
 # preventing the tests from occurring at all. Compile for ARMv8.2 so tests can
 # run on earlier targets and print a meaningful error messages
+$(OUTPUT)/exec_target: exec_target.c $(OUTPUT)/helper.o
+	$(CC) $^ -o $@ $(CFLAGS) -march=armv8.2-a
+
 $(OUTPUT)/pac: pac.c $(OUTPUT)/pac_corruptor.o $(OUTPUT)/helper.o
 	$(CC) $^ -o $@ $(CFLAGS) -march=armv8.2-a
 endif
diff --git a/tools/testing/selftests/arm64/pauth/exec_target.c b/tools/testing/selftests/arm64/pauth/exec_target.c
new file mode 100644
index 000000000000..07addef5a1d7
--- /dev/null
+++ b/tools/testing/selftests/arm64/pauth/exec_target.c
@@ -0,0 +1,35 @@
+// SPDX-License-Identifier: GPL-2.0
+// Copyright (C) 2020 ARM Limited
+
+#include <stdio.h>
+#include <stdlib.h>
+#include <sys/auxv.h>
+
+#include "helper.h"
+
+
+int main(void)
+{
+	struct signatures signed_vals;
+	unsigned long hwcaps;
+	size_t val;
+
+	fread(&val, sizeof(size_t), 1, stdin);
+
+	/* don't try to execute illegal (unimplemented) instructions) caller
+	 * should have checked this and keep worker simple
+	 */
+	hwcaps = getauxval(AT_HWCAP);
+
+	if (hwcaps & HWCAP_PACA) {
+		signed_vals.keyia = keyia_sign(val);
+		signed_vals.keyib = keyib_sign(val);
+		signed_vals.keyda = keyda_sign(val);
+		signed_vals.keydb = keydb_sign(val);
+	}
+	signed_vals.keyg = (hwcaps & HWCAP_PACG) ?  keyg_sign(val) : 0;
+
+	fwrite(&signed_vals, sizeof(struct signatures), 1, stdout);
+
+	return 0;
+}
diff --git a/tools/testing/selftests/arm64/pauth/helper.h b/tools/testing/selftests/arm64/pauth/helper.h
index e2ed910c9863..da6457177727 100644
--- a/tools/testing/selftests/arm64/pauth/helper.h
+++ b/tools/testing/selftests/arm64/pauth/helper.h
@@ -6,6 +6,16 @@
 
 #include <stdlib.h>
 
+#define NKEYS 5
+
+
+struct signatures {
+	size_t keyia;
+	size_t keyib;
+	size_t keyda;
+	size_t keydb;
+	size_t keyg;
+};
 
 void pac_corruptor(void);
 
diff --git a/tools/testing/selftests/arm64/pauth/pac.c b/tools/testing/selftests/arm64/pauth/pac.c
index 035fdd6aae9b..1b9e3acfeb61 100644
--- a/tools/testing/selftests/arm64/pauth/pac.c
+++ b/tools/testing/selftests/arm64/pauth/pac.c
@@ -2,6 +2,8 @@
 // Copyright (C) 2020 ARM Limited
 
 #include <sys/auxv.h>
+#include <sys/types.h>
+#include <sys/wait.h>
 #include <signal.h>
 
 #include "../../kselftest_harness.h"
@@ -33,6 +35,117 @@ do { \
 } while (0)
 
 
+void sign_specific(struct signatures *sign, size_t val)
+{
+	sign->keyia = keyia_sign(val);
+	sign->keyib = keyib_sign(val);
+	sign->keyda = keyda_sign(val);
+	sign->keydb = keydb_sign(val);
+}
+
+void sign_all(struct signatures *sign, size_t val)
+{
+	sign->keyia = keyia_sign(val);
+	sign->keyib = keyib_sign(val);
+	sign->keyda = keyda_sign(val);
+	sign->keydb = keydb_sign(val);
+	sign->keyg  = keyg_sign(val);
+}
+
+int are_same(struct signatures *old, struct signatures *new, int nkeys)
+{
+	int res = 0;
+
+	res |= old->keyia == new->keyia;
+	res |= old->keyib == new->keyib;
+	res |= old->keyda == new->keyda;
+	res |= old->keydb == new->keydb;
+	if (nkeys == NKEYS)
+		res |= old->keyg  == new->keyg;
+
+	return res;
+}
+
+int exec_sign_all(struct signatures *signed_vals, size_t val)
+{
+	int new_stdin[2];
+	int new_stdout[2];
+	int status;
+	ssize_t ret;
+	pid_t pid;
+
+	ret = pipe(new_stdin);
+	if (ret == -1) {
+		perror("pipe returned error");
+		return -1;
+	}
+
+	ret = pipe(new_stdout);
+	if (ret == -1) {
+		perror("pipe returned error");
+		return -1;
+	}
+
+	pid = fork();
+	// child
+	if (pid == 0) {
+		dup2(new_stdin[0], STDIN_FILENO);
+		if (ret == -1) {
+			perror("dup2 returned error");
+			exit(1);
+		}
+
+		dup2(new_stdout[1], STDOUT_FILENO);
+		if (ret == -1) {
+			perror("dup2 returned error");
+			exit(1);
+		}
+
+		close(new_stdin[0]);
+		close(new_stdin[1]);
+		close(new_stdout[0]);
+		close(new_stdout[1]);
+
+		ret = execl("exec_target", "exec_target", (char *) NULL);
+		if (ret == -1) {
+			perror("exec returned error");
+			exit(1);
+		}
+	}
+
+	close(new_stdin[0]);
+	close(new_stdout[1]);
+
+	ret = write(new_stdin[1], &val, sizeof(size_t));
+	if (ret == -1) {
+		perror("write returned error");
+		return -1;
+	}
+
+	/*
+	 * wait for the worker to finish, so that read() reads all data
+	 * will also context switch with worker so that this function can be used
+	 * for context switch tests
+	 */
+	waitpid(pid, &status, 0);
+	if (WIFEXITED(status) == 0) {
+		fprintf(stderr, "worker exited unexpectedly\n");
+		return -1;
+	}
+	if (WEXITSTATUS(status) != 0) {
+		fprintf(stderr, "worker exited with error\n");
+		return -1;
+	}
+
+	ret = read(new_stdout[0], signed_vals, sizeof(struct signatures));
+	if (ret == -1) {
+		perror("read returned error");
+		return -1;
+	}
+
+	return 0;
+}
+
 /* check that a corrupted PAC results in SIGSEGV */
 TEST_SIGNAL(corrupt_pac, SIGSEGV)
 {
@@ -79,4 +192,39 @@ TEST(pac_instructions_not_nop_generic)
 	ASSERT_NE(0, keyg)  TH_LOG("keyg instructions did nothing");
 }
 
+/*
+ * fork() does not change keys. Only exec() does so call a worker program.
+ * Its only job is to sign a value and report back the resutls
+ */
+TEST(exec_unique_keys)
+{
+	struct signatures new_keys;
+	struct signatures old_keys;
+	int ret;
+	int different = 0;
+	int nkeys = NKEYS;
+	unsigned long hwcaps = getauxval(AT_HWCAP);
+
+	/* generic and data key instructions are not in NOP space. This prevents a SIGILL */
+	ASSERT_NE(0, hwcaps & HWCAP_PACA) TH_LOG("PAUTH not enabled");
+	if (!(hwcaps & HWCAP_PACG)) {
+		TH_LOG("WARNING: Generic PAUTH not enabled. Skipping generic key checks");
+		nkeys = NKEYS - 1;
+	}
+
+	for (int i = 0; i < PAC_COLLISION_ATTEMPTS; i++) {
+		ret = exec_sign_all(&new_keys, i);
+		ASSERT_EQ(0, ret) TH_LOG("failed to run worker");
+
+		if (nkeys == NKEYS)
+			sign_all(&old_keys, i);
+		else
+			sign_specific(&old_keys, i);
+
+		different |= !are_same(&old_keys, &new_keys, nkeys);
+	}
+
+	ASSERT_EQ(1, different) TH_LOG("exec() did not change keys");
+}
+
 TEST_HARNESS_MAIN
-- 
2.17.1

