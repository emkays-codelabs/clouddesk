---
title: API rate limits and HTTP 429 errors
category: api_failure
tags: [api, rate-limit, 429, retry, backoff]
summary: How API rate limits work per plan, how to read the limit headers, and how to fix 429 responses in scheduled jobs.
---
# API rate limits and HTTP 429 errors

## What a 429 means
The CloudDesk API returns HTTP 429 Too Many Requests when a key sends more requests than its plan allows in a rolling minute. The limit is per workspace, so several scripts sharing one key count together. A nightly sync that fires many parallel requests at the same second is the most common cause.

## Limits by plan
Each subscription lists its limit in requests per minute. Free workspaces have a low limit, Pro and Business raise it, and Enterprise has the highest. The current limit is shown on the customer's subscription and in the `X-RateLimit-Limit` response header.

## Reading the headers
Every response carries `X-RateLimit-Limit`, `X-RateLimit-Remaining` and `X-RateLimit-Reset`. A 429 response adds `Retry-After`, the number of seconds to wait. Clients should pause for that long before the next call rather than retrying at once.

## Fixing a failing sync
Recommend exponential backoff with jitter: wait one second, then two, then four, with a small random addition, and stop after a fixed number of tries. Reduce parallelism, batch records into bulk endpoints, and spread jobs across the hour. Cache data that rarely changes instead of fetching it on every run.

## Requesting a higher limit
If a well-behaved client still needs more, the workspace admin can ask for a limit review. Support does not change limits directly; the request goes to the platform team with the average and peak request rates.
