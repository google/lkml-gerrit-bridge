Return-Path: <linux-kernel-owner+w=401wt.eu-S1751045AbXAVR6a@vger.kernel.org>
Received: (majordomo@vger.kernel.org) by vger.kernel.org via listexpand
	id S1751045AbXAVR6a (ORCPT <rfc822;w@1wt.eu>);
	Mon, 22 Jan 2007 12:58:30 -0500
Received: (majordomo@vger.kernel.org) by vger.kernel.org id S1751400AbXAVR6a
	(ORCPT <rfc822;linux-kernel-outgoing>);
	Mon, 22 Jan 2007 12:58:30 -0500
Received: from mx1.redhat.com ([66.187.233.31]:60014 "EHLO mx1.redhat.com"
	rhost-flags-OK-OK-OK-OK) by vger.kernel.org with ESMTP
	id S1751045AbXAVR63 (ORCPT <rfc822;linux-kernel@vger.kernel.org>);
	Mon, 22 Jan 2007 12:58:29 -0500
Subject: Re: [PATCH] Remove final reference to superfluous smp_commence().
From: Ingo Molnar <mingo@redhat.com>
To: "Robert P. J. Day" <rpjday@mindspring.com>
Cc: Linux kernel mailing list <linux-kernel@vger.kernel.org>,
       Andrew Morton <akpm@osdl.org>
In-Reply-To: <Pine.LNX.4.64.0701201326330.24479@CPE00045a9c397f-CM001225dbafb6>
References: <Pine.LNX.4.64.0701201326330.24479@CPE00045a9c397f-CM001225dbafb6>
Content-Type: text/plain
Date: Mon, 22 Jan 2007 18:57:50 +0100
Message-Id: <1169488670.15515.17.camel@earth>
Mime-Version: 1.0
X-Mailer: Evolution 2.8.2.1 (2.8.2.1-3.fc6) 
Content-Transfer-Encoding: 7bit
Sender: linux-kernel-owner@vger.kernel.org
X-Mailing-List: linux-kernel@vger.kernel.org

On Sat, 2007-01-20 at 13:28 -0500, Robert P. J. Day wrote:
> Remove the last (and commented out) invocation of the obsolete
> smp_commence() call.
> 
> Signed-off-by: Robert P. J. Day <rpjday@mindspring.com>

thanks,

Acked-by: Ingo Molnar <mingo@redhat.com>

	Ingo

