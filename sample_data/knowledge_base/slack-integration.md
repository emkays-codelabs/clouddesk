---
title: Slack integration stopped posting notifications
category: integration
tags: [slack, integration, notifications, oauth, webhook]
summary: Common reasons the Slack integration stops working and the reconnect steps for workspace admins.
---
# Slack integration stopped posting notifications

## How the integration works
The Slack integration posts file and comment notifications to channels chosen by the workspace admin. It connects through OAuth, so it keeps working only while the Slack authorisation stays valid and the CloudDesk app remains installed in the Slack workspace.

## Common causes
The usual reasons are a revoked authorisation, a Slack admin who removed the app, an archived or renamed channel the integration was posting to, and a change of the Slack workspace owner. A token that was valid for a former employee stops working when that person is deactivated in Slack.

## Reconnect steps
A workspace admin opens Settings, Integrations, Slack and selects Reconnect. Slack asks them to approve the permissions again. After approval, choose the notification channel and send a test message. If the channel is private, invite the CloudDesk app to it first.

## Checking for an incident
Before asking for a reconnect, check service status for an integrations incident. Delivery can be delayed during an incident even when the connection is healthy, and no action is then needed from the customer.

## When to escalate
If a reconnect succeeds but test messages never arrive, collect the channel name, the time of the last successful notification and the time of the test. Escalate to the integrations team with that information.
