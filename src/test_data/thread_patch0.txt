Return-Path: <SRS0=vZem=CJ=vger.kernel.org=linux-kselftest-owner@kernel.org>
X-Spam-Checker-Version: SpamAssassin 3.4.0 (2014-02-07) on
	aws-us-west-2-korg-lkml-1.web.codeaurora.org
X-Spam-Level: 
X-Spam-Status: No, score=-10.0 required=3.0 tests=BAYES_00,
	HEADER_FROM_DIFFERENT_DOMAINS,MAILING_LIST_MULTI,SIGNED_OFF_BY,SPF_HELO_NONE,
	SPF_PASS,URIBL_BLOCKED,USER_AGENT_GIT autolearn=unavailable
	autolearn_force=no version=3.4.0
Received: from mail.kernel.org (mail.kernel.org [198.145.29.99])
	by smtp.lore.kernel.org (Postfix) with ESMTP id 5E649C433E2
	for <linux-kselftest@archiver.kernel.org>; Mon, 31 Aug 2020 11:17:58 +0000 (UTC)
Received: from vger.kernel.org (vger.kernel.org [23.128.96.18])
	by mail.kernel.org (Postfix) with ESMTP id 46AFA2068E
	for <linux-kselftest@archiver.kernel.org>; Mon, 31 Aug 2020 11:17:58 +0000 (UTC)
Received: (majordomo@vger.kernel.org) by vger.kernel.org via listexpand
        id S1726771AbgHaLRj (ORCPT
        <rfc822;linux-kselftest@archiver.kernel.org>);
        Mon, 31 Aug 2020 07:17:39 -0400
Received: from foss.arm.com ([217.140.110.172]:56592 "EHLO foss.arm.com"
        rhost-flags-OK-OK-OK-OK) by vger.kernel.org with ESMTP
        id S1726472AbgHaLFS (ORCPT <rfc822;linux-kselftest@vger.kernel.org>);
        Mon, 31 Aug 2020 07:05:18 -0400
Received: from usa-sjc-imap-foss1.foss.arm.com (unknown [10.121.207.14])
        by usa-sjc-mx-foss1.foss.arm.com (Postfix) with ESMTP id AAEE61FB;
        Mon, 31 Aug 2020 04:05:17 -0700 (PDT)
Received: from e124572.local (unknown [172.31.20.19])
        by usa-sjc-imap-foss1.foss.arm.com (Postfix) with ESMTPSA id 502E93F71F;
        Mon, 31 Aug 2020 04:05:15 -0700 (PDT)
From:   Boyan Karatotev <boyan.karatotev@arm.com>
To:     linux-arm-kernel@lists.infradead.org,
        linux-kselftest@vger.kernel.org, linux-kernel@vger.kernel.org
Cc:     vincenzo.frascino@arm.com, amit.kachhap@arm.com,
        boian4o1@gmail.com, Boyan Karatotev <boyan.karatotev@arm.com>,
        Shuah Khan <shuah@kernel.org>,
        Catalin Marinas <catalin.marinas@arm.com>,
        Will Deacon <will@kernel.org>
Subject: [PATCH v2 0/4] kselftests/arm64: add PAuth tests
Date:   Mon, 31 Aug 2020 12:04:46 +0100
Message-Id: <20200831110450.30188-1-boyan.karatotev@arm.com>
X-Mailer: git-send-email 2.17.1
Sender: linux-kselftest-owner@vger.kernel.org
Precedence: bulk
List-ID: <linux-kselftest.vger.kernel.org>
X-Mailing-List: linux-kselftest@vger.kernel.org

Pointer Authentication (PAuth) is a security feature introduced in ARMv8.3.
It introduces instructions to sign addresses and later check for potential
corruption using a second modifier value and one of a set of keys. The
signature, in the form of the Pointer Authentication Code (PAC), is stored
in some of the top unused bits of the virtual address (e.g. [54: 49] if
TBID0 is enabled and TnSZ is set to use a 48 bit VA space). A set of
controls are present to enable/disable groups of instructions (which use
certain keys) for compatibility with libraries that do not utilize the
feature. PAuth is used to verify the integrity of return addresses on the
stack with less memory than the stack canary.

This patchset adds kselftests to verify the kernel's configuration of the
feature and its runtime behaviour. There are 7 tests which verify that:
	* an authentication failure leads to a SIGSEGV
	* the data/instruction instruction groups are enabled
	* the generic instructions are enabled
	* all 5 keys are unique for a single thread
	* exec() changes all keys to new unique ones
	* context switching preserves the 4 data/instruction keys
	* context switching preserves the generic keys

The tests have been verified to work on qemu without a working PAUTH
Implementation and on ARM's FVP with a full or partial PAuth
implementation.

Changes in v2:
* remove extra lines at end of files
* Patch 1: "kselftests: add a basic arm64 Pointer Authentication test"
	* add checks for a compatible compiler in Makefile
* Patch 4: "kselftests: add PAuth tests for single threaded consistency and
key uniqueness"
	* rephrase comment for clarity in pac.c

Cc: Shuah Khan <shuah@kernel.org>
Cc: Catalin Marinas <catalin.marinas@arm.com>
Cc: Will Deacon <will@kernel.org>
Reviewed-by: Vincenzo Frascino <Vincenzo.Frascino@arm.com>
Reviewed-by: Amit Daniel Kachhap <amit.kachhap@arm.com>
Signed-off-by: Boyan Karatotev <boyan.karatotev@arm.com>

Boyan Karatotev (4):
  kselftests/arm64: add a basic Pointer Authentication test
  kselftests/arm64: add nop checks for PAuth tests
  kselftests/arm64: add PAuth test for whether exec() changes keys
  kselftests/arm64: add PAuth tests for single threaded consistency and
    key uniqueness

 tools/testing/selftests/arm64/Makefile        |   2 +-
 .../testing/selftests/arm64/pauth/.gitignore  |   2 +
 tools/testing/selftests/arm64/pauth/Makefile  |  39 ++
 .../selftests/arm64/pauth/exec_target.c       |  35 ++
 tools/testing/selftests/arm64/pauth/helper.c  |  40 ++
 tools/testing/selftests/arm64/pauth/helper.h  |  29 ++
 tools/testing/selftests/arm64/pauth/pac.c     | 348 ++++++++++++++++++
 .../selftests/arm64/pauth/pac_corruptor.S     |  35 ++
 8 files changed, 529 insertions(+), 1 deletion(-)
 create mode 100644 tools/testing/selftests/arm64/pauth/.gitignore
 create mode 100644 tools/testing/selftests/arm64/pauth/Makefile
 create mode 100644 tools/testing/selftests/arm64/pauth/exec_target.c
 create mode 100644 tools/testing/selftests/arm64/pauth/helper.c
 create mode 100644 tools/testing/selftests/arm64/pauth/helper.h
 create mode 100644 tools/testing/selftests/arm64/pauth/pac.c
 create mode 100644 tools/testing/selftests/arm64/pauth/pac_corruptor.S

--
2.17.1

