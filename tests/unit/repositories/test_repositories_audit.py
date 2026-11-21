from app.repositories.audit import AuditLogRepository


async def test_append_and_list_filter_by_actor_and_action_with_total(session, tenants):
    repo = AuditLogRepository(session)
    await repo.append(actor="sam", action="POST /tickets")
    await repo.append(actor="sam", action="POST /approvals")
    await repo.append(actor="vic", action="POST /tickets")
    await session.commit()
    items, total = await repo.list()
    assert total == 3 and items[0].actor == "vic"  # newest first
    _, total = await repo.list(actor="sam")
    assert total == 2
    items, total = await repo.list(actor="sam", action="POST /tickets")
    assert total == 1 and items[0].action == "POST /tickets"
    items, total = await repo.list(page=2, page_size=2)
    assert len(items) == 1 and total == 3
