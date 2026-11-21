---
title: API keys and authentication errors
category: api_failure
tags: [api, api-key, 401, 403, authentication, rotation]
summary: Causes of 401 and 403 responses from the API, how to create and rotate keys safely and what scopes mean.
---
# API keys and authentication errors

## 401 versus 403
A 401 Unauthorized response means the request had no valid credentials: a missing header, a mistyped key, or a key that has been revoked. A 403 Forbidden response means the key is valid but lacks permission for that action, usually because of its scope or the role of the user who created it.

## Sending the key
Send the key in the `Authorization` header as a bearer token. Keys must never be placed in a URL or a public repository. If a customer posts a key in a ticket, ask them to revoke it at once and do not repeat it in any reply.

## Creating and rotating keys
Admins create keys in Settings, API. Choose the narrowest scope that works, such as read-only for reporting jobs. To rotate a key, create the new one, update the client, check that requests succeed and only then revoke the old key.

## Scopes
A key can be limited to files, members or billing data. A request outside its scopes returns 403 with the missing scope in the message. Adding a scope means creating a new key; existing keys cannot be widened.

## Related problems
Repeated 429 responses are a rate limit issue, not an authentication one. A key that stops working after a member leaves was probably tied to that member's account and should be recreated by an admin.
